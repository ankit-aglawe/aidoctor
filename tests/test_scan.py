"""Tests for the scan orchestrator."""

from __future__ import annotations

from pathlib import Path

from aidoctor.scan import scan, scan_file


def test_scan_file_returns_diagnostics(tmp_path: Path) -> None:
    f = tmp_path / "x.py"
    f.write_text('API_KEY = "sk-prod-1234567890abcdef"\n')
    diags, parse_err, _source = scan_file(f)
    assert parse_err is None
    rule_ids = {d.rule_id for d in diags}
    assert "hardcoded-api-key" in rule_ids


def test_scan_file_clean_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "clean.py"
    f.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
    diags, parse_err, _source = scan_file(f)
    assert parse_err is None
    assert diags == []


def test_scan_file_parse_error(tmp_path: Path) -> None:
    f = tmp_path / "broken.py"
    f.write_text("def not valid python\n")
    diags, parse_err, _source = scan_file(f)
    assert parse_err is not None
    assert "parse error" in parse_err.lower()


def test_scan_serial(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text('API_KEY = "sk-aaaaaaaaaaaaa"\n')
    (tmp_path / "b.py").write_text("x = 1\n")
    result = scan([tmp_path], jobs=1)
    assert result.files_scanned == 2
    assert result.files_skipped == 0
    assert any(d.rule_id == "hardcoded-api-key" for d in result.diagnostics)


def test_scan_parallel(tmp_path: Path) -> None:
    # Need > PARALLEL_THRESHOLD files to engage pool path.
    for i in range(6):
        (tmp_path / f"f{i}.py").write_text(f"# file {i}\nx = {i}\n")
    result = scan([tmp_path], jobs=2)
    assert result.files_scanned == 6


def test_scan_skips_parse_error_file(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("x = 1\n")
    (tmp_path / "bad.py").write_text("def )(\n")
    result = scan([tmp_path], jobs=1)
    assert result.files_scanned == 1
    assert result.files_skipped == 1
    assert len(result.parse_errors) == 1


def test_scan_applies_inline_suppression(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text(
        "# aidoctor: disable=hardcoded-api-key\n"
        'API_KEY = "sk-aaaaaaaaaaaa"\n'
    )
    result = scan([tmp_path], jobs=1)
    # The suppression should drop the hardcoded-api-key diagnostic.
    rule_ids = {d.rule_id for d in result.diagnostics}
    assert "hardcoded-api-key" not in rule_ids
