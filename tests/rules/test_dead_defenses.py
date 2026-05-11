"""Tests for Dead Defenses rules."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from aidoctor.rules._base import RuleContext
from aidoctor.rules.dead_defenses import (
    BareExceptPassRule,
    ExceptExceptionSwallowingRule,
    RedundantNullCheckAfterIsinstanceRule,
    UnreachableRaiseRule,
)


def _run(rule_cls, source: str) -> list:
    ctx = RuleContext(file=Path("/tmp/x.py"), source=source)
    wrapper = cst.MetadataWrapper(cst.parse_module(source))
    wrapper.visit(rule_cls(ctx))
    return ctx.diagnostics


def test_bare_except_pass_fires() -> None:
    src = "try:\n    x = 1\nexcept:\n    pass\n"
    assert len(_run(BareExceptPassRule, src)) == 1


def test_except_exception_pass_fires() -> None:
    src = "try:\n    x = 1\nexcept Exception:\n    pass\n"
    assert len(_run(BareExceptPassRule, src)) == 1


def test_specific_except_clean() -> None:
    src = "try:\n    x = 1\nexcept ValueError:\n    pass\n"
    assert _run(BareExceptPassRule, src) == []


def test_except_exception_with_log_no_reraise_fires() -> None:
    src = (
        "try:\n"
        "    x = 1\n"
        "except Exception as e:\n"
        "    print(e)\n"
    )
    diags = _run(ExceptExceptionSwallowingRule, src)
    assert len(diags) == 1


def test_except_exception_with_raise_clean() -> None:
    src = (
        "try:\n"
        "    x = 1\n"
        "except Exception as e:\n"
        "    print(e)\n"
        "    raise\n"
    )
    assert _run(ExceptExceptionSwallowingRule, src) == []


def test_unreachable_raise_after_return_fires() -> None:
    src = "def f():\n    return 1\n    raise ValueError('nope')\n"
    diags = _run(UnreachableRaiseRule, src)
    assert len(diags) == 1


def test_raise_before_return_clean() -> None:
    src = "def f(x):\n    if x is None:\n        raise ValueError('nope')\n    return x\n"
    assert _run(UnreachableRaiseRule, src) == []


def test_redundant_null_check_fires() -> None:
    src = "if x is not None and isinstance(x, int):\n    pass\n"
    diags = _run(RedundantNullCheckAfterIsinstanceRule, src)
    assert len(diags) == 1


def test_isinstance_alone_clean() -> None:
    src = "if isinstance(x, int):\n    pass\n"
    assert _run(RedundantNullCheckAfterIsinstanceRule, src) == []


def test_null_check_then_other_var_clean() -> None:
    # `x is not None and isinstance(y, int)` is NOT redundant — different vars.
    src = "if x is not None and isinstance(y, int):\n    pass\n"
    assert _run(RedundantNullCheckAfterIsinstanceRule, src) == []
