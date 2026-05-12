"""Fake Type Hints rules.

AI assistants reach for `Any` when uncertain, ship public functions without
return type annotations, and use `Generic` without binding a TypeVar.
"""

from __future__ import annotations

from typing import Any as _Any  # avoid clash with cst.Any if any

import libcst as cst

from aidoctor.rules._base import Category, Rule, Severity


class AnyEverywhereRule(Rule):
    """Detects `Any` used as a public function's parameter or return type.

    v2.0 refinement: only fire when EVERY annotation in the function signature
    is `Any` (no mixed-with-concrete-types). Mixed signatures like
    `def f(x: int, body: Any)` are intentional (author knows int, treats body
    as opaque). Fires only on `def f(x: Any) -> Any` or `def f(x: Any)`.

    Fixes 17 FPs found by the real-world FP harness on encode/httpx, which
    legitimately uses Any for HTTP body types alongside concrete types.
    """

    rule_id = "any-everywhere"
    severity = Severity.WARNING
    category = Category.TYPE_HINTS
    message = "Every annotation in this signature is `Any` — the AI hedge tell."
    help = (
        "AI assistants annotate parameters with `Any` when uncertain about the "
        "real type. This rule fires only when EVERY annotation in the signature "
        "is `Any` (the AI-hedge fingerprint). Mixed signatures with `Any` for "
        "one opaque value alongside concrete types are allowed — those are "
        "intentional. Replace blanket `Any` with specific types, a Union, a "
        "Protocol, or a TypeVar."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#any-everywhere"

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if node.name.value.startswith("_"):  # private functions are fine
            return

        any_annotations: list[cst.CSTNode] = []
        non_any_annotation_count = 0

        for param in node.params.params:
            if param.annotation is None:
                continue
            if _is_any_annotation(param.annotation.annotation):
                any_annotations.append(param)
            else:
                non_any_annotation_count += 1

        if node.returns is not None:
            if _is_any_annotation(node.returns.annotation):
                any_annotations.append(node.returns)
            else:
                non_any_annotation_count += 1

        # Fire only when there is at least one Any AND zero non-Any annotations.
        if any_annotations and non_any_annotation_count == 0:
            for n in any_annotations:
                self.report(n)


class MissingReturnTypeRule(Rule):
    """Detects public functions/methods without a return type annotation.

    v2.0 refinement (per real-world FP testing — 172 FPs in psf/requests):
    only fires if the module is *typing-aware*, i.e. has at least one other
    type annotation somewhere (function param/return, AnnAssign, etc).
    Pre-typing-era modules emit zero findings — no nagging legacy code.
    """

    rule_id = "missing-return-type"
    severity = Severity.WARNING
    category = Category.TYPE_HINTS
    message = "Public function missing return type annotation."
    help = (
        "Every public function should declare its return type. AI assistants "
        "often skip return annotations when generating quickly. Add `-> T` where "
        "T is the actual return type. For procedures that return nothing, use "
        "`-> None`. For private functions (leading underscore), this rule does "
        "not apply. This rule only fires on typing-aware modules (any annotation "
        "present); pre-typing legacy code is silent."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#missing-return-type"

    def __init__(self, context) -> None:  # type: ignore[no-untyped-def]
        super().__init__(context)
        self._typing_aware = False
        self._candidates: list[cst.CSTNode] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        # Any param annotation OR existing return annotation flips the
        # typing-aware bit for the whole module.
        for p in node.params.params:
            if p.annotation is not None:
                self._typing_aware = True
                break
        if node.returns is not None:
            self._typing_aware = True

        if node.name.value.startswith("_"):
            return
        if node.name.value.startswith("__") and node.name.value.endswith("__"):
            return
        if node.returns is None:
            self._candidates.append(node.name)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        # `x: int = 5` anywhere also signals typing-aware module.
        self._typing_aware = True

    def leave_Module(self, original_node: cst.Module) -> None:
        if not self._typing_aware:
            return  # untyped module — stay silent
        for cand in self._candidates:
            self.report(cand)


# `GenericWithoutTypeVarRule` was dropped in v2.0 per the HONESTY_AUDIT:
# baseline subagents rarely trip this pattern (LOW confidence), and the
# legitimate cases (TypeVar declared in a sibling module, imported via *)
# generate false positives. If a v2.x community user requests reinstatement,
# the rule can be revived from git history at commit 1d9d616 or earlier.


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
