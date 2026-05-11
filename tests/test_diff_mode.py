"""Tests for diff_mode hunk parsing and diagnostic filtering."""

from __future__ import annotations

from pathlib import Path

from aidoctor.diff_mode import filter_diagnostics_to_diff, parse_hunks
from aidoctor.rules import Category, Diagnostic, Severity


def test_parse_hunks_basic_addition() -> None:
    diff = (
        "@@ -1,3 +1,5 @@\n"
        " context\n"
        "+added_1\n"
        "+added_2\n"
        " more context\n"
        " end\n"
    )
    lines = parse_hunks(diff)
    assert lines == {2, 3}


def test_parse_hunks_unified_zero_format() -> None:
    diff = (
        "@@ -10,0 +11 @@\n"
        "+new_line_at_11\n"
        "@@ -50 +51,2 @@\n"
        "-removed\n"
        "+replacement_a\n"
        "+replacement_b\n"
    )
    lines = parse_hunks(diff)
    assert lines == {11, 51, 52}


def test_parse_hunks_no_changes_returns_empty() -> None:
    assert parse_hunks("") == set()


def test_filter_diagnostics_by_line(tmp_path: Path) -> None:
    file_path = tmp_path / "app.py"
    file_path.write_text("x = 1\ny = 2\nz = 3\n")
    # Build diagnostics on lines 1, 2, 3.
    diags = [
        Diagnostic(
            rule_id="r",
            severity=Severity.ERROR,
            category=Category.SECRETS,
            file=file_path,
            line=n,
            column=0,
            message="m",
            help="h",
        )
        for n in (1, 2, 3)
    ]
    # Only line 2 is in the diff.
    rel = file_path.relative_to(tmp_path)
    changed = {rel: {2}}
    kept = filter_diagnostics_to_diff(diags, changed, repo_root=tmp_path)
    assert len(kept) == 1
    assert kept[0].line == 2


def test_filter_drops_diagnostics_for_unchanged_files(tmp_path: Path) -> None:
    file_path = tmp_path / "untouched.py"
    file_path.write_text("x = 1\n")
    diag = Diagnostic(
        rule_id="r",
        severity=Severity.ERROR,
        category=Category.SECRETS,
        file=file_path,
        line=1,
        column=0,
        message="m",
        help="h",
    )
    # No entry for this file in changed_lines.
    kept = filter_diagnostics_to_diff([diag], {}, repo_root=tmp_path)
    assert kept == []
