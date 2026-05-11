"""N+1 / Performance rules.

AI assistants frequently produce O(N^2) accumulation patterns and inefficient
string concatenation in loops. These rules are AST-level heuristics — they
catch the obvious cases without dataflow analysis.
"""

from __future__ import annotations

from typing import Any

import libcst as cst

from aidoctor.rules._base import Category, Rule, Severity


class NestedLoopAppendRule(Rule):
    """Detects O(N*M) `list.append` patterns inside nested for loops.

    Heuristic: a `<name>.append(...)` call inside a for-loop that's nested inside
    another for-loop is usually a flattenable list comprehension or itertools.chain.
    """

    rule_id = "nested-loop-append"
    severity = Severity.WARNING
    category = Category.PERF
    message = "Nested for-loop with .append builds a list O(N*M) one item at a time."
    help = (
        "AI assistants often write `for x in xs: for y in ys: out.append(f(x, y))` "
        "when a list comprehension or `itertools.product` is clearer and faster. "
        "Prefer `out = [f(x, y) for x in xs for y in ys]` or `list(itertools.chain.from_iterable(...))`. "
        "Comprehensions allocate once; .append in a tight loop incurs repeated "
        "method-lookup and list-resize overhead."
    )
    url = "https://github.com/aidoctor/aidoctor#nested-loop-append"

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self._for_depth = 0

    def visit_For(self, node: cst.For) -> None:
        self._for_depth += 1

    def leave_For(self, original_node: cst.For) -> None:
        self._for_depth -= 1

    def visit_Call(self, node: cst.Call) -> None:
        if self._for_depth < 2:
            return
        func = node.func
        if isinstance(func, cst.Attribute) and func.attr.value == "append":
            self.report(node)


class StrConcatInLoopRule(Rule):
    """Detects `s += '...'` (or `s = s + '...'`) inside a for/while loop body."""

    rule_id = "str-concat-in-loop"
    severity = Severity.WARNING
    category = Category.PERF
    message = "String concatenation inside a loop is O(N^2). Use .join() or io.StringIO."
    help = (
        "Each `s += other` copies the entire current string into a new object — "
        "O(N^2) total work for N iterations. CPython has a special case that "
        "sometimes optimizes this, but it's brittle and breaks under refactoring. "
        "Collect parts in a list and call `''.join(parts)` once, or use "
        "`io.StringIO()` + `.write(...)` + `.getvalue()`."
    )
    url = "https://github.com/aidoctor/aidoctor#str-concat-in-loop"

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self._loop_depth = 0

    def visit_For(self, node: cst.For) -> None:
        self._loop_depth += 1

    def leave_For(self, original_node: cst.For) -> None:
        self._loop_depth -= 1

    def visit_While(self, node: cst.While) -> None:
        self._loop_depth += 1

    def leave_While(self, original_node: cst.While) -> None:
        self._loop_depth -= 1

    def visit_AugAssign(self, node: cst.AugAssign) -> None:
        if self._loop_depth <= 0:
            return
        # `s += X` where X is a string literal or a Name (best-effort heuristic).
        if not isinstance(node.operator, cst.AddAssign):
            return
        if not isinstance(node.target, cst.Name):
            return
        if isinstance(node.value, (cst.SimpleString, cst.FormattedString, cst.ConcatenatedString)):
            self.report(node)
            return
        # `s += other_name` where other_name is plausibly a string — too noisy without dataflow.
        # Keep the rule tight: only flag when RHS is clearly a string literal.

    def visit_Assign(self, node: cst.Assign) -> None:
        # Catch `s = s + literal` form inside a loop.
        if self._loop_depth <= 0:
            return
        if not isinstance(node.value, cst.BinaryOperation):
            return
        if not isinstance(node.value.operator, cst.Add):
            return
        target_names = {t.target.value for t in node.targets if isinstance(t.target, cst.Name)}
        if not target_names:
            return
        # LHS name appears on RHS, and RHS contains a string literal.
        left = node.value.left
        right = node.value.right
        lhs_is_target = isinstance(left, cst.Name) and left.value in target_names
        rhs_is_target = isinstance(right, cst.Name) and right.value in target_names
        if not (lhs_is_target or rhs_is_target):
            return
        other = right if lhs_is_target else left
        if isinstance(other, (cst.SimpleString, cst.FormattedString, cst.ConcatenatedString)):
            self.report(node)


class RepeatedDictLookupRule(Rule):
    """Detects `d[k]` referenced 3+ times in the same simple statement body when k is a literal.

    Catches AI-generated patterns like:
        config["host"] = config["host"].lower()
        if config["host"] == "localhost": ...
    where a local binding (`host = config["host"]`) would be clearer and ~2-3x faster.
    """

    rule_id = "repeated-dict-lookup"
    severity = Severity.WARNING
    category = Category.PERF
    message = "Same dict key looked up 3+ times in one block. Bind to a local."
    help = (
        "Repeated `d[\"key\"]` lookups within one block read the dict each time. "
        "Bind the value to a local variable once at the top of the block: "
        "`x = d[\"key\"]` then reference `x`. AI assistants generate this pattern "
        "when they're stitching independently-generated lines that all reach into "
        "the same dict. Three or more lookups of the same literal key is the threshold."
    )
    url = "https://github.com/aidoctor/aidoctor#repeated-dict-lookup"

    def __init__(self, context: Any) -> None:
        super().__init__(context)

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._scan_block(node.body)

    def _scan_block(self, body: cst.BaseSuite) -> None:
        """Count `name["literal"]` occurrences inside this function body."""

        class _Collector(cst.CSTVisitor):
            def __init__(self) -> None:
                super().__init__()
                # key = (var_name, literal_key) → list of nodes
                self.counts: dict[tuple[str, str], list[cst.Subscript]] = {}

            def visit_Subscript(self, node: cst.Subscript) -> None:
                value = node.value
                if not isinstance(value, cst.Name):
                    return
                if len(node.slice) != 1:
                    return
                slice_el = node.slice[0]
                if not isinstance(slice_el.slice, cst.Index):
                    return
                idx = slice_el.slice.value
                if not isinstance(idx, cst.SimpleString):
                    return
                key_val = idx.evaluated_value
                if not isinstance(key_val, str):
                    return
                key = (value.value, key_val)
                self.counts.setdefault(key, []).append(node)

        collector = _Collector()
        body.visit(collector)
        for (var, key), occurrences in collector.counts.items():
            if len(occurrences) >= 3:
                self.report(
                    occurrences[0],
                    message=f"`{var}[{key!r}]` looked up {len(occurrences)} times. Bind to a local.",
                )
