"""Tests for inline suppression parsing + diagnostic filtering."""

from __future__ import annotations

from pathlib import Path

from aidoctor.rules import Category, Diagnostic, Severity
from aidoctor.suppression import (
    filter_diagnostics,
    is_suppressed,
    parse_suppressions,
)


def _diag(rule_id: str, file: Path, line: int) -> Diagnostic:
    return Diagnostic(
        rule_id=rule_id,
        severity=Severity.ERROR,
        category=Category.SECRETS,
        file=file,
        line=line,
        column=0,
        message="m",
        help="h",
    )


def test_disable_next_line_suppresses_following_line() -> None:
    src = "x = 1\n# aidoctor: disable=hardcoded-api-key\nAPI_KEY = 'sk-aaaaaaaa'\n"
    sup = parse_suppressions(src)
    # disable= comment on line 2, suppresses line 3.
    assert is_suppressed("hardcoded-api-key", 3, sup)
    assert not is_suppressed("hardcoded-api-key", 1, sup)


def test_disable_line_suppresses_same_line() -> None:
    src = "API_KEY = 'sk-aaaaaaaa'  # aidoctor: disable-line=hardcoded-api-key\n"
    sup = parse_suppressions(src)
    assert is_suppressed("hardcoded-api-key", 1, sup)


def test_disable_file_suppresses_everywhere() -> None:
    src = "# aidoctor: disable-file=hardcoded-api-key\nAPI_KEY = 'x'\nAPI_KEY = 'y'\n"
    sup = parse_suppressions(src)
    assert is_suppressed("hardcoded-api-key", 1, sup)
    assert is_suppressed("hardcoded-api-key", 50, sup)


def test_wildcard_suppresses_all_rules() -> None:
    src = "# aidoctor: disable-file=*\nstuff\n"
    sup = parse_suppressions(src)
    assert is_suppressed("any-rule-name", 5, sup)


def test_multiple_rules_comma_separated() -> None:
    src = "# aidoctor: disable=rule-1,rule-2\nstuff\n"
    sup = parse_suppressions(src)
    assert is_suppressed("rule-1", 2, sup)
    assert is_suppressed("rule-2", 2, sup)
    assert not is_suppressed("rule-3", 2, sup)


def test_filter_diagnostics_drops_suppressed(tmp_path: Path) -> None:
    file = tmp_path / "x.py"
    file.write_text(
        "x = 1\n"
        "# aidoctor: disable=hardcoded-api-key\n"
        "API_KEY = 'real'\n"
        "OTHER = 'real'\n"
    )
    diags = [
        _diag("hardcoded-api-key", file, 3),  # suppressed
        _diag("hardcoded-api-key", file, 4),  # NOT suppressed
        _diag("other-rule", file, 3),  # NOT suppressed (only api-key was named)
    ]
    kept = filter_diagnostics(diags, {file: file.read_text()})
    assert len(kept) == 2
    rule_lines = {(d.rule_id, d.line) for d in kept}
    assert ("hardcoded-api-key", 4) in rule_lines
    assert ("other-rule", 3) in rule_lines
