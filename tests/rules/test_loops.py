"""Tests for Stale Loop Patterns rules."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from aidoctor.rules._base import RuleContext
from aidoctor.rules.loops import (
    MutateListDuringIterationRule,
    RangeLenRule,
    TimeSleepInTestRule,
)


def _run(rule_cls, source: str, file: Path | None = None) -> list:
    ctx = RuleContext(file=file or Path("/tmp/x.py"), source=source)
    wrapper = cst.MetadataWrapper(cst.parse_module(source))
    wrapper.visit(rule_cls(ctx))
    return ctx.diagnostics


def test_range_len_fires() -> None:
    assert len(_run(RangeLenRule, "for i in range(len(xs)):\n    pass\n")) == 1


def test_plain_range_clean() -> None:
    assert _run(RangeLenRule, "for i in range(10):\n    pass\n") == []


def test_enumerate_clean() -> None:
    assert _run(RangeLenRule, "for i, x in enumerate(xs):\n    pass\n") == []


def test_mutate_during_iteration_fires() -> None:
    src = "for item in items:\n    items.append(item * 2)\n"
    assert len(_run(MutateListDuringIterationRule, src)) == 1


def test_mutate_different_list_clean() -> None:
    src = "for item in items:\n    other.append(item)\n"
    assert _run(MutateListDuringIterationRule, src) == []


def test_iterate_copy_clean() -> None:
    # Iterating a slice copy is fine.
    src = "for item in items[:]:\n    items.append(item)\n"
    assert _run(MutateListDuringIterationRule, src) == []


def test_time_sleep_in_test_file_fires() -> None:
    src = "import time\ntime.sleep(2)\n"
    diags = _run(TimeSleepInTestRule, src, file=Path("/tmp/tests/test_foo.py"))
    assert len(diags) == 1


def test_time_sleep_in_non_test_clean() -> None:
    src = "import time\ntime.sleep(2)\n"
    diags = _run(TimeSleepInTestRule, src, file=Path("/tmp/src/app.py"))
    assert diags == []
