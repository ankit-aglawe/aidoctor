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


def test_any_on_param_fires() -> None:
    src = "def f(x: Any) -> int:\n    return 1\n"
    assert len(_run(AnyEverywhereRule, src)) >= 1


def test_any_on_return_fires() -> None:
    src = "def f(x: int) -> Any:\n    return 1\n"
    assert len(_run(AnyEverywhereRule, src)) >= 1


def test_concrete_types_clean() -> None:
    src = "def f(x: int) -> int:\n    return x\n"
    assert _run(AnyEverywhereRule, src) == []


def test_any_on_private_function_clean() -> None:
    src = "def _f(x: Any) -> Any:\n    return 1\n"
    assert _run(AnyEverywhereRule, src) == []


def test_missing_return_fires() -> None:
    src = "def total(items):\n    return sum(items)\n"
    assert len(_run(MissingReturnTypeRule, src)) == 1


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
