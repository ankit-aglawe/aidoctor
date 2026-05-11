"""Fake Type Hints rules.

AI assistants reach for `Any` when uncertain, ship public functions without
return type annotations, and use `Generic` without binding a TypeVar.
"""

from __future__ import annotations

from typing import Any as _Any  # avoid clash with cst.Any if any

import libcst as cst

from aidoctor.rules._base import Category, Rule, Severity


class AnyEverywhereRule(Rule):
    """Detects `Any` used as a public function's parameter or return type."""

    rule_id = "any-everywhere"
    severity = Severity.WARNING
    category = Category.TYPE_HINTS
    message = "`Any` on a public function parameter or return type disables type-checking."
    help = (
        "AI assistants annotate parameters with `Any` when uncertain about the "
        "real type. This silently disables type-checking at the boundary. Replace "
        "`Any` with the specific type, a Union, a Protocol, or a TypeVar. If you "
        "genuinely need an opaque type, use `object` (forces explicit downcasting) "
        "or document why `Any` is correct."
    )
    url = "https://github.com/aidoctor/aidoctor#any-everywhere"

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if node.name.value.startswith("_"):  # private functions are fine
            return
        # Check params.
        for param in node.params.params:
            if param.annotation and _is_any_annotation(param.annotation.annotation):
                self.report(param)
        # Check return annotation.
        if node.returns and _is_any_annotation(node.returns.annotation):
            self.report(node.returns)


class MissingReturnTypeRule(Rule):
    """Detects public functions/methods without a return type annotation."""

    rule_id = "missing-return-type"
    severity = Severity.WARNING
    category = Category.TYPE_HINTS
    message = "Public function missing return type annotation."
    help = (
        "Every public function should declare its return type. AI assistants "
        "often skip return annotations when generating quickly. Add `-> T` where "
        "T is the actual return type. For procedures that return nothing, use "
        "`-> None`. For private functions (leading underscore), this rule does "
        "not apply."
    )
    url = "https://github.com/aidoctor/aidoctor#missing-return-type"

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if node.name.value.startswith("_"):
            return
        # __init__ etc. are dunder, conventionally don't annotate return.
        if node.name.value.startswith("__") and node.name.value.endswith("__"):
            return
        if node.returns is None:
            self.report(node.name)


class GenericWithoutTypeVarRule(Rule):
    """Detects `Generic[T]` where T is not declared via TypeVar in the same module."""

    rule_id = "generic-without-typevar"
    severity = Severity.WARNING
    category = Category.TYPE_HINTS
    message = "`Generic[X]` requires X to be a TypeVar declared with TypeVar()."
    help = (
        "Using `Generic[T]` without declaring `T = TypeVar('T')` makes the class "
        "non-generic at runtime (T is treated as a regular name). AI assistants "
        "produce this pattern when faking parameterized types. Declare the "
        "TypeVar at module scope: `T = TypeVar('T')` (or `from typing import "
        "TypeVar`) before the class."
    )
    url = "https://github.com/aidoctor/aidoctor#generic-without-typevar"

    def __init__(self, context: _Any) -> None:
        super().__init__(context)
        self._declared_typevars: set[str] = set()
        self._candidate_uses: list[tuple[cst.CSTNode, str]] = []

    def visit_Assign(self, node: cst.Assign) -> None:
        # Look for `T = TypeVar('T')` or `T = TypeVar('T', ...)`.
        if not isinstance(node.value, cst.Call):
            return
        func = node.value.func
        is_typevar = (
            (isinstance(func, cst.Name) and func.value == "TypeVar")
            or (
                isinstance(func, cst.Attribute)
                and isinstance(func.value, cst.Name)
                and func.value.value == "typing"
                and func.attr.value == "TypeVar"
            )
        )
        if not is_typevar:
            return
        for target in node.targets:
            if isinstance(target.target, cst.Name):
                self._declared_typevars.add(target.target.value)

    def visit_Subscript(self, node: cst.Subscript) -> None:
        # Look for `Generic[T]` usage.
        value = node.value
        if not isinstance(value, cst.Name) or value.value != "Generic":
            return
        for el in node.slice:
            if isinstance(el.slice, cst.Index):
                idx = el.slice.value
                if isinstance(idx, cst.Name):
                    self._candidate_uses.append((node, idx.value))

    def leave_Module(self, original_node: cst.Module) -> None:
        for node, name in self._candidate_uses:
            if name not in self._declared_typevars:
                self.report(node, message=f"`Generic[{name}]` but `{name}` is not a TypeVar in this module.")


def _is_any_annotation(node: cst.BaseExpression) -> bool:
    """Detect `Any` (Name) and `typing.Any` (Attribute)."""
    if isinstance(node, cst.Name) and node.value == "Any":
        return True
    if (
        isinstance(node, cst.Attribute)
        and isinstance(node.value, cst.Name)
        and node.value.value == "typing"
        and node.attr.value == "Any"
    ):
        return True
    return False
