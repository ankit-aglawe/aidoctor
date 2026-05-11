"""Tests for Comment-Driven Decay rules."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from aidoctor.rules._base import RuleContext
from aidoctor.rules.decay import StubCommentRule, TodoWithoutTicketRule


def _run(rule_cls, source: str) -> list:
    ctx = RuleContext(file=Path("/tmp/x.py"), source=source)
    wrapper = cst.MetadataWrapper(cst.parse_module(source))
    wrapper.visit(rule_cls(ctx))
    return ctx.diagnostics


def test_bare_todo_fires() -> None:
    src = "# TODO: refactor this\nx = 1\n"
    assert len(_run(TodoWithoutTicketRule, src)) == 1


def test_todo_with_gh_ticket_clean() -> None:
    src = "# TODO(GH-123): refactor\nx = 1\n"
    assert _run(TodoWithoutTicketRule, src) == []


def test_todo_with_jira_clean() -> None:
    src = "# TODO(JIRA-456): refactor\nx = 1\n"
    assert _run(TodoWithoutTicketRule, src) == []


def test_todo_with_url_clean() -> None:
    src = "# TODO see https://github.com/example/issues/42\nx = 1\n"
    assert _run(TodoWithoutTicketRule, src) == []


def test_fixme_without_ticket_fires() -> None:
    src = "# FIXME: handle null\nx = 1\n"
    assert len(_run(TodoWithoutTicketRule, src)) == 1


def test_hack_without_ticket_fires() -> None:
    src = "# HACK: monkey-patching the global state\nx = 1\n"
    assert len(_run(TodoWithoutTicketRule, src)) == 1


def test_stub_implement_this_fires() -> None:
    src = "def f():\n    # implement this\n    pass\n"
    assert len(_run(StubCommentRule, src)) == 1


def test_stub_placeholder_fires() -> None:
    src = "# placeholder\nx = 1\n"
    assert len(_run(StubCommentRule, src)) == 1


def test_normal_comment_clean() -> None:
    src = "# This is a description, not a stub.\nx = 1\n"
    assert _run(StubCommentRule, src) == []


def test_normal_function_clean() -> None:
    src = "def f():\n    # Returns the sum of x.\n    return sum(x)\n"
    assert _run(StubCommentRule, src) == []
