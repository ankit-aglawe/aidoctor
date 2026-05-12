"""Tests for the `aidoctor deai` CLI subcommand.

The CLI is the moat exposed to humans + agents:
    aidoctor deai PATH [--json]

Emits, per ai-style HIGH-confidence finding, a paired (finding, proposed_fix)
record. The /aidoctor:deai skill consumes this output to orchestrate the
interactive apply loop with the agent's file-edit tools.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from aidoctor.cli import main

# --- fixtures ---


def _slop_file(tmp_path: Path) -> Path:
    """Mixed AI-slop file: section divider + emphasis label + emoji.

    Also includes a non-ai-style finding (hardcoded-api-key) to ensure /deai
    filters those out.
    """
    f = tmp_path / "ai_slop.py"
    f.write_text(
        "# ==================== HELPERS ====================\n"
        "# NOTE: this is important\n"
        "API_KEY = 'sk-prod-1234567890abcdef'\n"
        "# ✅ Done\n"
        "x = 1\n"
    )
    return f


def _clean_file(tmp_path: Path) -> Path:
    f = tmp_path / "clean.py"
    f.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
    return f


# --- behaviour tests ---


def test_deai_emits_findings_and_proposed_fixes(tmp_path: Path) -> None:
    runner = CliRunner()
    _slop_file(tmp_path)
    result = runner.invoke(main, ["deai", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["schema_version"] == 1
    assert "findings" in data
    assert len(data["findings"]) >= 3  # section-divider, emphasis-label, emoji
    # Every finding ships with a proposed_fix block — that's the whole pitch.
    for f in data["findings"]:
        assert "rule_id" in f
        assert "proposed_fix" in f
        fix = f["proposed_fix"]
        assert "ok" in fix
        if fix["ok"]:
            assert "original_code" in fix
            assert "replacement_code" in fix


def test_deai_filters_out_non_ai_style_findings(tmp_path: Path) -> None:
    """The slop file has a hardcoded-api-key (category=secrets), but /deai
    must return ONLY ai-style findings — that's the moat's scope."""
    runner = CliRunner()
    _slop_file(tmp_path)
    result = runner.invoke(main, ["deai", str(tmp_path), "--json"])
    data = json.loads(result.output)
    rule_ids = {f["rule_id"] for f in data["findings"]}
    assert "hardcoded-api-key" not in rule_ids
    assert all(rid.startswith("ai-") for rid in rule_ids), rule_ids


def test_deai_clean_file_returns_zero_findings(tmp_path: Path) -> None:
    runner = CliRunner()
    _clean_file(tmp_path)
    result = runner.invoke(main, ["deai", str(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["findings"] == []
    assert data["ai_residue_score"] == 100


def test_deai_ai_residue_score_at_zero_when_findings_present(tmp_path: Path) -> None:
    """ai_residue_score is 100 minus penalty per finding. Clean = 100, dirty < 100.

    Distinct from the scan score (which is calibrated across all rules); the
    residue score is /deai's own metric for 'how AI-flavored is this code?'.
    """
    runner = CliRunner()
    _slop_file(tmp_path)
    result = runner.invoke(main, ["deai", str(tmp_path), "--json"])
    data = json.loads(result.output)
    assert 0 <= data["ai_residue_score"] < 100


def test_deai_non_json_terminal_output(tmp_path: Path) -> None:
    """Default (no --json) prints a human-readable summary, not JSON."""
    runner = CliRunner()
    _slop_file(tmp_path)
    result = runner.invoke(main, ["deai", str(tmp_path)])
    assert result.exit_code == 0
    # Should NOT be valid JSON
    try:
        json.loads(result.output)
        assert False, "default output should be human-readable, not JSON"
    except json.JSONDecodeError:
        pass
    # Should mention the count and the residue concept
    assert "AI fingerprint" in result.output or "ai-style" in result.output


def test_deai_exits_zero_with_findings(tmp_path: Path) -> None:
    """/deai is discovery, not a CI gate. Exit 0 even with findings.

    (Users wire CI via `aidoctor scan --fail-on error` instead.)
    """
    runner = CliRunner()
    _slop_file(tmp_path)
    result = runner.invoke(main, ["deai", str(tmp_path), "--json"])
    assert result.exit_code == 0
