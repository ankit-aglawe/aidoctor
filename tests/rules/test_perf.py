"""Tests for N+1 / Performance rules."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from aidoctor.rules._base import RuleContext
from aidoctor.rules.perf import (
    NestedLoopAppendRule,
    RepeatedDictLookupRule,
    StrConcatInLoopRule,
)


def _run(rule_cls, source: str) -> list:
    ctx = RuleContext(file=Path("/tmp/x.py"), source=source)
    wrapper = cst.MetadataWrapper(cst.parse_module(source))
    wrapper.visit(rule_cls(ctx))
    return ctx.diagnostics


def test_nested_loop_append_fires() -> None:
    src = (
        "out = []\n"
        "for x in xs:\n"
        "    for y in ys:\n"
        "        out.append((x, y))\n"
    )
    assert len(_run(NestedLoopAppendRule, src)) >= 1


def test_single_loop_append_clean() -> None:
    src = "out = []\nfor x in xs:\n    out.append(x)\n"
    assert _run(NestedLoopAppendRule, src) == []


def test_list_comprehension_clean() -> None:
    src = "out = [(x, y) for x in xs for y in ys]\n"
    assert _run(NestedLoopAppendRule, src) == []


def test_str_concat_with_literal_in_loop_fires() -> None:
    src = "out = ''\nfor x in xs:\n    out += 'line\\n'\n"
    assert len(_run(StrConcatInLoopRule, src)) >= 1


def test_str_concat_with_fstring_in_loop_fires() -> None:
    src = "out = ''\nfor x in xs:\n    out += f'{x}'\n"
    assert len(_run(StrConcatInLoopRule, src)) >= 1


def test_str_concat_outside_loop_clean() -> None:
    src = "out = ''\nout += 'just once'\n"
    assert _run(StrConcatInLoopRule, src) == []


def test_str_concat_in_while_loop_fires() -> None:
    src = "out = ''\nwhile True:\n    out += 'x'\n"
    assert len(_run(StrConcatInLoopRule, src)) >= 1


def test_str_concat_assign_form_in_loop_fires() -> None:
    src = "out = ''\nfor x in xs:\n    out = out + 'line'\n"
    assert len(_run(StrConcatInLoopRule, src)) >= 1


def test_repeated_dict_lookup_fires_at_three() -> None:
    src = (
        "def f(c):\n"
        "    c['host'] = c['host'].lower()\n"
        "    if c['host'] == 'localhost':\n"
        "        pass\n"
    )
    diags = _run(RepeatedDictLookupRule, src)
    assert len(diags) == 1


def test_repeated_dict_lookup_under_threshold_clean() -> None:
    src = "def f(c):\n    c['host'] = c['host'].lower()\n"  # only 2 lookups
    assert _run(RepeatedDictLookupRule, src) == []


def test_repeated_dict_lookup_different_keys_clean() -> None:
    src = (
        "def f(c):\n"
        "    a = c['host']\n"
        "    b = c['port']\n"
        "    d = c['scheme']\n"
    )
    assert _run(RepeatedDictLookupRule, src) == []
