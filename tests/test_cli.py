"""Tests for the CLI surface via click.testing.CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from aidoctor.cli import main


def _make_clean_repo(tmp_path: Path) -> Path:
    (tmp_path / "clean.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n"
    )
    return tmp_path


def _make_slop_repo(tmp_path: Path) -> Path:
    (tmp_path / "slop.py").write_text(
        'API_KEY = "sk-prod-1234567890abcdef"\n'
        "from os import *\n"
    )
    return tmp_path


def test_scan_clean_repo_exits_zero(tmp_path: Path) -> None:
    runner = CliRunner()
    repo = _make_clean_repo(tmp_path)
    result = runner.invoke(main, ["scan", str(repo)])
    assert result.exit_code == 0
    assert "Score:" in result.output


def test_scan_slop_repo_default_exits_one(tmp_path: Path) -> None:
    """v2.0 default is --fail-on=error: violations now fail CI by default.

    This closes the v1.1 footgun where errors-but-exit-0 made aidoctor's CI
    integration silently broken. The old behavior is still reachable via
    --fail-on=none (see test below).
    """
    runner = CliRunner()
    repo = _make_slop_repo(tmp_path)
    result = runner.invoke(main, ["scan", str(repo)])
    assert result.exit_code == 1
    assert "Hardcoded Secrets" in result.output


def test_scan_slop_repo_with_fail_on_none_exits_zero(tmp_path: Path) -> None:
    """The opt-out path: --fail-on=none preserves v1.1 behavior for legacy callers."""
    runner = CliRunner()
    repo = _make_slop_repo(tmp_path)
    result = runner.invoke(main, ["scan", str(repo), "--fail-on", "none"])
    assert result.exit_code == 0
    assert "Hardcoded Secrets" in result.output


def test_scan_with_fail_on_error_exits_one(tmp_path: Path) -> None:
    runner = CliRunner()
    repo = _make_slop_repo(tmp_path)
    result = runner.invoke(main, ["scan", str(repo), "--fail-on", "error"])
    assert result.exit_code == 1


def test_scan_with_fail_on_warning_exits_one(tmp_path: Path) -> None:
    runner = CliRunner()
    repo = _make_slop_repo(tmp_path)
    result = runner.invoke(main, ["scan", str(repo), "--fail-on", "warning"])
    assert result.exit_code == 1


def test_scan_json_emits_valid_json(tmp_path: Path) -> None:
    runner = CliRunner()
    repo = _make_slop_repo(tmp_path)
    # --fail-on=none keeps exit 0 so we can parse the JSON regardless of slop level.
    result = runner.invoke(main, ["scan", str(repo), "--json", "--fail-on", "none"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == 1
    assert "score" in data
    assert data["score"]["value"] >= 0
    assert data["score"]["value"] <= 100


def test_scan_jsonl_emits_one_record_per_line(tmp_path: Path) -> None:
    """--jsonl streams one JSON object per line.

    Per W6/3: pipeable to `jq`/`grep`/log aggregators. The last line is always
    a summary record with type='summary' carrying the schema_version + score.
    Findings come first, summary last.
    """
    runner = CliRunner()
    repo = _make_slop_repo(tmp_path)
    result = runner.invoke(
        main, ["scan", str(repo), "--jsonl", "--fail-on", "none"]
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert len(lines) >= 2  # at least 1 finding + 1 summary

    # Every line is valid JSON
    records = [json.loads(ln) for ln in lines]

    # Last line is the summary
    summary = records[-1]
    assert summary["type"] == "summary"
    assert summary["schema_version"] == 1
    assert "score" in summary
    assert summary["score"]["value"] >= 0

    # Non-summary lines are findings
    findings = records[:-1]
    assert findings, "expected at least one finding line on a slop repo"
    for f in findings:
        assert f["type"] == "finding"
        assert "rule_id" in f
        assert "severity" in f
        assert "file" in f
        assert "line" in f


def test_scan_jsonl_clean_repo_just_summary(tmp_path: Path) -> None:
    """Clean repo emits exactly one line (the summary)."""
    runner = CliRunner()
    repo = _make_clean_repo(tmp_path)
    result = runner.invoke(main, ["scan", str(repo), "--jsonl"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert len(lines) == 1
    summary = json.loads(lines[0])
    assert summary["type"] == "summary"
    assert summary["score"]["value"] == 100


def test_scan_explain_prints_rule_doc(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--explain", "hardcoded-api-key"])
    assert result.exit_code == 0
    assert "hardcoded-api-key" in result.output
    assert "error" in result.output
    assert "secrets" in result.output


def test_scan_explain_unknown_rule_exits_two(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--explain", "no-such-rule"])
    assert result.exit_code == 2
    assert "no rule named" in result.output


def test_scan_no_python_files_exits_two(tmp_path: Path) -> None:
    runner = CliRunner()
    (tmp_path / "readme.md").write_text("nothing here\n")
    result = runner.invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 2
    assert "No Python files" in result.output


def test_skill_generic_strips_frontmatter() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "--format", "generic"])
    assert result.exit_code == 0
    assert not result.output.startswith("---")
    assert "# aidoctor" in result.output


def test_skill_claude_keeps_frontmatter() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "--format", "claude"])
    assert result.exit_code == 0
    assert result.output.startswith("---")
    assert "name: aidoctor" in result.output


def test_skill_cursor_uses_globs_frontmatter() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "--format", "cursor"])
    assert result.exit_code == 0
    assert result.output.startswith("---")
    assert "globs:" in result.output
    assert "'**/*.py'" in result.output
    assert "alwaysApply: true" in result.output


def test_skill_opencode_strips_frontmatter() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "--format", "opencode"])
    assert result.exit_code == 0
    assert not result.output.startswith("---")


def test_skill_codex_strips_frontmatter() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "--format", "codex"])
    assert result.exit_code == 0
    assert not result.output.startswith("---")


def test_skill_gemini_strips_frontmatter() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "--format", "gemini"])
    assert result.exit_code == 0
    assert not result.output.startswith("---")


def test_skill_raw_keeps_template_form() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "--format", "raw"])
    assert result.exit_code == 0
    assert result.output.startswith("---")


def test_install_dry_run_no_writes(tmp_path: Path) -> None:
    runner = CliRunner()
    # No agent dirs present — install should skip all.
    result = runner.invoke(main, ["install", "--dry-run"], env={"HOME": str(tmp_path)})
    assert result.exit_code == 0


def test_scan_pr_bad_url_exits_three(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan-pr", "not-a-url"])
    assert result.exit_code == 3
    assert "valid GitHub PR URL" in result.output


def test_help_text_lists_all_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    for cmd in ("scan", "scan-pr", "install", "skill"):
        assert cmd in result.output


def test_version_flag() -> None:
    from aidoctor import __version__

    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output
