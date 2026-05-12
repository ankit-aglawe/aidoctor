"""Tests for the central error renderer.

Per CEO Section 2's 15-row error/rescue table: every rescue site uses one
shared renderer so error UX (classname, what-was-attempted, file:line,
remediation) stays consistent across the codebase. Drift here = broken
brand promise in CEO Section 2.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_renders_classname_and_message() -> None:
    from aidoctor.engine.error_renderer import ErrorContext, render_error

    exc = ValueError("invalid syntax")
    out = render_error(exc, ErrorContext(attempting="parsing file"))
    assert "ValueError" in out
    assert "invalid syntax" in out


def test_renders_attempting_line() -> None:
    from aidoctor.engine.error_renderer import ErrorContext, render_error

    exc = RuntimeError("boom")
    out = render_error(exc, ErrorContext(attempting="loading rule manifest"))
    assert "loading rule manifest" in out


def test_includes_file_when_given() -> None:
    from aidoctor.engine.error_renderer import ErrorContext, render_error

    p = Path("/tmp/x.py")
    out = render_error(
        OSError("perm denied"),
        ErrorContext(attempting="reading file", file=p),
    )
    assert str(p) in out


def test_includes_file_and_line_when_both_given() -> None:
    from aidoctor.engine.error_renderer import ErrorContext, render_error

    p = Path("/tmp/x.py")
    out = render_error(
        SyntaxError("bad"),
        ErrorContext(attempting="parsing", file=p, line=42),
    )
    assert f"{p}:42" in out


def test_omits_file_when_not_given() -> None:
    from aidoctor.engine.error_renderer import ErrorContext, render_error

    out = render_error(ValueError("x"), ErrorContext(attempting="doing thing"))
    assert "at:" not in out


def test_includes_remediation_when_given() -> None:
    from aidoctor.engine.error_renderer import ErrorContext, render_error

    out = render_error(
        ConnectionError("api down"),
        ErrorContext(
            attempting="calling LLM",
            remediation="set ANTHROPIC_API_KEY or run aidoctor doctor",
        ),
    )
    assert "set ANTHROPIC_API_KEY" in out


def test_omits_remediation_when_not_given() -> None:
    from aidoctor.engine.error_renderer import ErrorContext, render_error

    out = render_error(ValueError("x"), ErrorContext(attempting="thing"))
    lower = out.lower()
    assert "fix:" not in lower
    assert "remediation" not in lower


def test_full_rendering_golden() -> None:
    """Snapshot the canonical format so drift across rescue sites is caught."""
    from aidoctor.engine.error_renderer import ErrorContext, render_error

    p = Path("/repo/payments.py")
    out = render_error(
        OSError("permission denied"),
        ErrorContext(
            attempting="reading payments.py",
            file=p,
            line=12,
            remediation="run with --jobs 1 to skip parallel mode and surface the error",
        ),
    )
    expected = (
        "ERROR OSError: permission denied\n"
        "  while: reading payments.py\n"
        f"  at:    {p}:12\n"
        "  fix:   run with --jobs 1 to skip parallel mode and surface the error"
    )
    assert out == expected


def test_rejects_empty_attempting() -> None:
    """`attempting` is mandatory — every error must say what was being tried.

    Per CEO Section 2: 'Catching an error with only a generic log message is
    insufficient. Log the full context: what was being attempted ...'
    """
    from aidoctor.engine.error_renderer import ErrorContext

    with pytest.raises(ValueError):
        ErrorContext(attempting="")
