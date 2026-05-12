"""Tests for `aidoctor doctor` — diagnostics for bug reports + sanity check.

Prints versions, parser status, manifest count, configured platforms. The
output is the canonical paste-this-when-filing-a-bug helper.
"""

from __future__ import annotations

import json

from click.testing import CliRunner

from aidoctor.cli import main


def test_doctor_runs_and_exits_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 0


def test_doctor_includes_aidoctor_version() -> None:
    import aidoctor

    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    assert aidoctor.__version__ in result.output


def test_doctor_includes_python_version() -> None:
    import sys

    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    py = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert py in result.output


def test_doctor_lists_loaded_manifests() -> None:
    """Every shipped .jsonl manifest is enumerated with its rule count."""
    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    assert "owasp.jsonl" in result.output
    assert "ai_style.jsonl" in result.output


def test_doctor_json_mode_emits_structured_output() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["doctor", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "aidoctor_version" in data
    assert "python_version" in data
    assert "manifests" in data
    assert isinstance(data["manifests"], list)
    # Each manifest entry has name + rule_count
    for m in data["manifests"]:
        assert "name" in m
        assert "rule_count" in m


def test_doctor_includes_total_rule_count() -> None:
    """The aggregate rule count helps users sanity-check upgrades."""
    runner = CliRunner()
    result = runner.invoke(main, ["doctor", "--json"])
    data = json.loads(result.output)
    assert "total_rules" in data
    # v2.0: 24 legacy (dropped generic-without-typevar) + 3 OWASP + 5 ai_style = 32
    assert data["total_rules"] >= 30
