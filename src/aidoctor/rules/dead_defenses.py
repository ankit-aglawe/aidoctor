"""Dead Defenses rules.

AI assistants often produce defensive code that doesn't actually defend anything:
bare `except: pass`, swallowing `except Exception`, raises after unconditional returns,
redundant null checks after isinstance.
"""

from __future__ import annotations

import libcst as cst

from aidoctor.rules._base import Category, Rule, Severity


class BareExceptPassRule(Rule):
    """Detects `try: ... except: pass` (or `except Exception: pass`)."""

    rule_id = "bare-except-pass"
    severity = Severity.ERROR
    category = Category.DEAD_DEFENSES
    message = "Bare except + pass silently swallows all exceptions including SystemExit and KeyboardInterrupt."
    help = (
        "`except: pass` or `except Exception: pass` swallows every exception silently, "
        "including SystemExit and KeyboardInterrupt. AI assistants generate this when "
        "they want to 'be safe.' It hides real bugs. Either name the specific exception "
        "you expect (`except ValueError:`), log the error before continuing, or remove "
        "the try block entirely."
    )
    url = "https://github.com/aidoctor/aidoctor#bare-except-pass"

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
        # Check body: a single SimpleStatementLine containing only Pass.
        body = node.body
        if not isinstance(body, cst.IndentedBlock):
            return
        stmts = body.body
        if len(stmts) != 1:
            return
        only = stmts[0]
        if not isinstance(only, cst.SimpleStatementLine):
            return
        if len(only.body) != 1:
            return
        if not isinstance(only.body[0], cst.Pass):
            return
        # Now check the except clause itself — bare except or `except Exception`.
        if node.type is None:
            self.report(node)
        elif isinstance(node.type, cst.Name) and node.type.value in ("Exception", "BaseException"):
            self.report(node)


class ExceptExceptionSwallowingRule(Rule):
    """Detects `except Exception` (or BaseException) where only logging occurs and no re-raise."""

    rule_id = "except-exception-swallowing"
    severity = Severity.WARNING
    category = Category.DEAD_DEFENSES
    message = "Catching `Exception` without re-raising masks real bugs."
    help = (
        "`except Exception:` catches almost everything. AI assistants reach for it as "
        "a catch-all. Even when you log inside, swallowing means callers can't react. "
        "Catch the specific exception you can handle. If you want a top-level safety "
        "net, place it once at the program boundary and either log+exit or re-raise."
    )
    url = "https://github.com/aidoctor/aidoctor#except-exception-swallowing"

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
        if node.type is None:
            return
        if not isinstance(node.type, cst.Name) or node.type.value not in ("Exception", "BaseException"):
            return
        # If body contains a Raise statement, it's not swallowing.
        if _body_has_raise(node.body):
            return
        # If body is just `pass`, BareExceptPassRule covers it. Skip here.
        body = node.body
        if isinstance(body, cst.IndentedBlock) and len(body.body) == 1:
            stmt = body.body[0]
            if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1:
                if isinstance(stmt.body[0], cst.Pass):
                    return
        self.report(node)


class UnreachableRaiseRule(Rule):
    """Detects `raise X` after an unconditional `return` in the same block."""

    rule_id = "unreachable-raise"
    severity = Severity.ERROR
    category = Category.DEAD_DEFENSES
    message = "Raise after unconditional return is unreachable code."
    help = (
        "AI assistants sometimes stitch fragments where a `return` is immediately "
        "followed by a `raise`. The raise never executes. Remove the dead code. If "
        "you intended a conditional, restructure with an explicit `if` before the "
        "raise."
    )
    url = "https://github.com/aidoctor/aidoctor#unreachable-raise"

    def visit_IndentedBlock(self, node: cst.IndentedBlock) -> None:
        prev_was_return = False
        for stmt in node.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for small in stmt.body:
                    if isinstance(small, cst.Return):
                        prev_was_return = True
                    elif isinstance(small, cst.Raise) and prev_was_return:
                        self.report(small)
                        prev_was_return = False
                    else:
                        prev_was_return = False
            else:
                prev_was_return = False


class RedundantNullCheckAfterIsinstanceRule(Rule):
    """Detects `if x is not None and isinstance(x, T):` (the None check is redundant)."""

    rule_id = "redundant-null-check-after-isinstance"
    severity = Severity.WARNING
    category = Category.DEAD_DEFENSES
    message = "`x is not None and isinstance(x, T)` is redundant. isinstance handles None."
    help = (
        "`isinstance(x, T)` returns False if `x` is None (None isn't an instance of "
        "any type except NoneType). AI assistants add the `is not None` check "
        "defensively. Remove the redundant check: just write `if isinstance(x, T):`."
    )
    url = "https://github.com/aidoctor/aidoctor#redundant-null-check-after-isinstance"

    def visit_BooleanOperation(self, node: cst.BooleanOperation) -> None:
        if not isinstance(node.operator, cst.And):
            return
        left, right = node.left, node.right
        # Pattern: `x is not None and isinstance(x, T)` (or reversed).
        if _is_not_none_check(left) and _is_isinstance_check(right, _is_not_none_target(left)):
            self.report(node)
        elif _is_not_none_check(right) and _is_isinstance_check(left, _is_not_none_target(right)):
            self.report(node)


def _body_has_raise(body: cst.BaseSuite) -> bool:
    if not isinstance(body, cst.IndentedBlock):
        return False
    for stmt in body.body:
        if isinstance(stmt, cst.SimpleStatementLine):
            for small in stmt.body:
                if isinstance(small, cst.Raise):
                    return True
    return False


def _is_not_none_check(node: cst.BaseExpression) -> bool:
    """Check if expression is `x is not None`."""
    if not isinstance(node, cst.Comparison):
        return False
    if len(node.comparisons) != 1:
        return False
    target = node.comparisons[0]
    op = target.operator
    if not isinstance(op, cst.IsNot):
        return False
    comparator = target.comparator
    if isinstance(comparator, cst.Name) and comparator.value == "None":
        return True
    return False


def _is_not_none_target(node: cst.BaseExpression) -> str:
    """Extract the variable name from `x is not None`."""
    if isinstance(node, cst.Comparison) and isinstance(node.left, cst.Name):
        return node.left.value
    return ""


def _is_isinstance_check(node: cst.BaseExpression, target_name: str) -> bool:
    """Check if expression is `isinstance(target_name, T)`."""
    if not target_name:
        return False
    if not isinstance(node, cst.Call):
        return False
    if not isinstance(node.func, cst.Name) or node.func.value != "isinstance":
        return False
    if not node.args:
        return False
    first_arg = node.args[0].value
    if isinstance(first_arg, cst.Name) and first_arg.value == target_name:
        return True
    return False
