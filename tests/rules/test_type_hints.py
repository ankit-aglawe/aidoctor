"""Tests for Fake Type Hints rules."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from aidoctor.rules._base import RuleContext
from aidoctor.rules.type_hints import (
    AnyEverywhereRule,
    GenericWithoutTypeVarRule,
    MissingReturnTypeRule,
)


def _run(rule_cls, source: str) -> list:
    ctx = RuleContext(file=Path("/tmp/x.py"), source=source)
    wrapper = cst.MetadataWrapper(cst.parse_module(source))
    wrapper.visit(rule_cls(ctx))
    return ctx.diagnostics


def test_any_mixed_with_concrete_does_not_fire() -> None:
    """v2.0 refinement: Any mixed with a specific type signals intentional use.

    Fixes 17 FPs the real-world FP harness found in httpx (which legitimately
    uses Any for HTTP body types alongside concrete request/response types).
    """
    src = "def f(x: Any) -> int:\n    return 1\n"
    assert _run(AnyEverywhereRule, src) == []  # mixed: int return = intentional

    src = "def f(x: int) -> Any:\n    return 1\n"
    assert _run(AnyEverywhereRule, src) == []  # mixed: int param = intentional


def test_all_any_signature_fires() -> None:
    """When every annotation in the signature is Any, that's the AI hedge tell."""
    src = "def f(x: Any) -> Any:\n    return 1\n"
    assert len(_run(AnyEverywhereRule, src)) >= 1

    src = "def f(x: Any, y: Any) -> Any:\n    return x\n"
    assert len(_run(AnyEverywhereRule, src)) >= 1


def test_only_annotation_is_any_fires() -> None:
    """`def f(x: Any)` with no other annotation — sole annotation IS Any → fires."""
    src = "def f(x: Any):\n    return x\n"
    assert len(_run(AnyEverywhereRule, src)) >= 1


def test_concrete_types_clean() -> None:
    src = "def f(x: int) -> int:\n    return x\n"
    assert _run(AnyEverywhereRule, src) == []


def test_any_on_private_function_clean() -> None:
    src = "def _f(x: Any) -> Any:\n    return 1\n"
    assert _run(AnyEverywhereRule, src) == []


def test_missing_return_fires_when_typing_aware() -> None:
    """In a typing-aware file (has any annotation), fire on missing return types.

    Refined v2.0: only fire if the file has at least one other type annotation.
    Fixes the 172 FPs the real-world FP harness found in psf/requests (which
    predates strong typing).
    """
    src = (
        "def helper(x: int) -> int:\n"  # this provides the typing-aware signal
        "    return x + 1\n"
        "def total(items):\n"
        "    return sum(items)\n"  # this should fire (missing return type)
    )
    diags = _run(MissingReturnTypeRule, src)
    # Only `total` is flagged; `helper` has its annotation.
    assert len(diags) == 1


def test_missing_return_silent_on_untyped_file() -> None:
    """File with no annotations anywhere = pre-typing-era code. Don't nag."""
    src = (
        "def total(items):\n"
        "    return sum(items)\n"
        "def double(x):\n"
        "    return x * 2\n"
    )
    diags = _run(MissingReturnTypeRule, src)
    assert diags == []  # NEW v2.0 behavior — no FP on untyped legacy code


def test_typed_return_clean() -> None:
    src = "def total(items: list[int]) -> int:\n    return sum(items)\n"
    assert _run(MissingReturnTypeRule, src) == []


def test_private_function_no_return_clean() -> None:
    src = "def _helper(x):\n    return x\n"
    assert _run(MissingReturnTypeRule, src) == []


def test_dunder_clean() -> None:
    src = "class C:\n    def __init__(self, x):\n        self.x = x\n"
    assert _run(MissingReturnTypeRule, src) == []


def test_generic_without_typevar_fires() -> None:
    src = "from typing import Generic\n\nclass Cache(Generic[T]):\n    pass\n"
    assert len(_run(GenericWithoutTypeVarRule, src)) == 1


def test_generic_with_typevar_clean() -> None:
    src = (
        "from typing import Generic, TypeVar\n\n"
        "T = TypeVar('T')\n\n"
        "class Cache(Generic[T]):\n    pass\n"
    )
    assert _run(GenericWithoutTypeVarRule, src) == []
