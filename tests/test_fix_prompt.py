"""Tests for the --fix-prompt CLI flag."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from aidoctor.cli import main


def test_fix_prompt_emits_markdown(tmp_path: Path) -> None:
    (tmp_path / "slop.py").write_text(
        'API_KEY = "sk-prod-1234567890abcdef"\n'
        "from os import *\n"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--fix-prompt"])
    assert result.exit_code == 0
    assert "# Fix aidoctor violations" in result.output
    assert "aidoctor skill installed" in result.output
    assert "hardcoded-api-key" in result.output
    assert "wildcard-import" in result.output


def test_fix_prompt_empty_when_clean(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--fix-prompt"])
    assert result.exit_code == 0
    assert "No violations to fix" in result.output


def test_fix_prompt_includes_line_numbers(tmp_path: Path) -> None:
    (tmp_path / "slop.py").write_text(
        "x = 1\n"
        'API_KEY = "sk-prod-1234567890abcdef"\n'  # line 2
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--fix-prompt"])
    assert "Line 2" in result.output


def test_fix_prompt_includes_help_text(tmp_path: Path) -> None:
    (tmp_path / "slop.py").write_text(
        'API_KEY = "sk-prod-1234567890abcdef"\n'
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--fix-prompt"])
    assert "Fix guidance:" in result.output
    assert "os.environ" in result.output
