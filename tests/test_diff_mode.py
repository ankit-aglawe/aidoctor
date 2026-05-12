"""Tests for diff_mode hunk parsing and diagnostic filtering."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aidoctor.diff_mode import (
    GitNotAvailableError,
    filter_diagnostics_to_diff,
    get_changed_files,
    get_changed_lines,
    parse_hunks,
)
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


def _mock_subprocess_run(stdout: str, returncode: int = 0, stderr: str = ""):
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = returncode
    return proc


def test_get_changed_files_returns_paths() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _mock_subprocess_run("a.py\nb.py\n")
        files = get_changed_files()
    assert files == [Path("a.py"), Path("b.py")]


def test_get_changed_files_staged_flag() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _mock_subprocess_run("c.py\n")
        files = get_changed_files(staged=True)
    # Verify --cached was in args.
    args = mock_run.call_args[0][0]
    assert "--cached" in args
    assert files == [Path("c.py")]


def test_get_changed_files_empty_when_clean() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _mock_subprocess_run("")
        files = get_changed_files()
    assert files == []


def test_get_changed_files_raises_on_not_in_repo() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _mock_subprocess_run(
            "", returncode=128, stderr="fatal: not a git repository (or any of the parent dirs)"
        )
        with pytest.raises(GitNotAvailableError):
            get_changed_files()


def test_get_changed_files_raises_when_git_missing() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("git")
        with pytest.raises(GitNotAvailableError):
            get_changed_files()


def test_get_changed_lines_parses_per_file_hunks() -> None:
    diff_output = (
        "diff --git a.py a.py\n"
        "index 1234..5678 100644\n"
        "--- a.py\n"
        "+++ a.py\n"
        "@@ -1,0 +2 @@\n"
        "+new_line\n"
        "diff --git b.py b.py\n"
        "index 1111..2222 100644\n"
        "--- b.py\n"
        "+++ b.py\n"
        "@@ -10 +11,2 @@\n"
        "-old\n"
        "+new1\n"
        "+new2\n"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _mock_subprocess_run(diff_output)
        result = get_changed_lines()
    assert Path("a.py") in result
    assert Path("b.py") in result
    assert 2 in result[Path("a.py")]
    assert 11 in result[Path("b.py")]
    assert 12 in result[Path("b.py")]


def test_get_changed_lines_empty_diff() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _mock_subprocess_run("")
        result = get_changed_lines()
    assert result == {}
