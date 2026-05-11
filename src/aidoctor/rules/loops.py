"""Stale Loop Patterns.

AI assistants reach for Python 2-era patterns that have better Python 3 idioms:
mutating a list while iterating it, `range(len(x))` instead of enumerate,
`time.sleep` in test files (which makes test suites unreliable).
"""

from __future__ import annotations

import libcst as cst

from aidoctor.rules._base import Category, Rule, Severity

# Method names that mutate a list in place.
LIST_MUTATING_METHODS = frozenset(
    {"append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse"}
)


class RangeLenRule(Rule):
    """Detects `for i in range(len(x)):` patterns."""

    rule_id = "range-len-loop"
    severity = Severity.WARNING
    category = Category.LOOPS
    message = "Use `enumerate(x)` instead of `range(len(x))`."
    help = (
        "`for i in range(len(x)):` is a Python-2 idiom. In Python 3, use "
        "`for i, item in enumerate(x):` to get both index and value, or "
        "`for item in x:` if you only need the value. AI assistants produce "
        "this pattern when translating from older code or when uncertain."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#range-len-loop"

    def visit_For(self, node: cst.For) -> None:
        iter_expr = node.iter
        if not isinstance(iter_expr, cst.Call):
            return
        if not isinstance(iter_expr.func, cst.Name) or iter_expr.func.value != "range":
            return
        if len(iter_expr.args) != 1:
            return
        inner = iter_expr.args[0].value
        if not isinstance(inner, cst.Call):
            return
        if isinstance(inner.func, cst.Name) and inner.func.value == "len":
            self.report(node)


class MutateListDuringIterationRule(Rule):
    """Detects mutating a list inside a `for x in same_list` loop."""

    rule_id = "mutate-list-during-iteration"
    severity = Severity.ERROR
    category = Category.LOOPS
    message = "Mutating a list while iterating it produces unpredictable results."
    help = (
        "`for x in lst: lst.append(...)` (or remove/pop) gives unpredictable behavior "
        "in Python: items may be skipped, duplicated, or trigger IndexError. AI "
        "assistants generate this when implementing filters or batched operations. "
        "Iterate over a copy (`for x in lst[:]`), build a new list with comprehension, "
        "or collect deletions for a post-loop sweep."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#mutate-list-during-iteration"

    def visit_For(self, node: cst.For) -> None:
        # Find the iterated name (only handles direct `for x in name` for v1).
        if not isinstance(node.iter, cst.Name):
            return
        list_name = node.iter.value
        # Walk the body looking for `list_name.<mutating>(...)`.
        for call in _iter_method_calls_on(node.body, list_name):
            method = call.func.attr.value
            if method in LIST_MUTATING_METHODS:
                self.report(call)


class TimeSleepInTestRule(Rule):
    """Detects `time.sleep(...)` calls in test files (path contains /tests/ or test_ prefix)."""

    rule_id = "time-sleep-in-test"
    severity = Severity.WARNING
    category = Category.LOOPS
    message = "time.sleep in tests makes the suite slow and flaky. Use mocks or freezegun."
    help = (
        "Real `time.sleep` in test code makes the suite slow and dependent on wall "
        "clock. AI assistants generate this to 'wait for' async or network operations. "
        "Use proper synchronization primitives (Event, asyncio.wait), mock the clock "
        "with freezegun or pytest-mock, or use `asyncio.sleep` inside async tests "
        "(which test runners can fast-forward)."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#time-sleep-in-test"

    def __init__(self, context: cst.CSTVisitor) -> None:
        super().__init__(context)
        # Compute once per file rather than per Call node — 80% of source files
        # in a typical repo aren't tests, and most Call nodes wouldn't match anyway.
        path_str = str(self.context.file)
        name = path_str.rsplit("/", 1)[-1]
        self._is_test_file = (
            "/tests/" in path_str
            or "/test/" in path_str
            or name.startswith("test_")
            or path_str.endswith("_test.py")
        )

    def visit_Call(self, node: cst.Call) -> None:
        if not self._is_test_file:
            return
        # Match `time.sleep(...)`.
        func = node.func
        if (
            isinstance(func, cst.Attribute)
            and isinstance(func.value, cst.Name)
            and func.value.value == "time"
            and func.attr.value == "sleep"
        ):
            self.report(node)


def _iter_method_calls_on(body: cst.BaseSuite, var_name: str):
    """Yield Call nodes that look like `var_name.method(...)` inside a body."""

    class _Collector(cst.CSTVisitor):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[cst.Call] = []

        def visit_Call(self, node: cst.Call) -> None:
            func = node.func
            if (
                isinstance(func, cst.Attribute)
                and isinstance(func.value, cst.Name)
                and func.value.value == var_name
            ):
                self.calls.append(node)

    collector = _Collector()
    body.visit(collector)
    yield from collector.calls
