"""Tests for the scan orchestrator."""

from __future__ import annotations

from pathlib import Path

from aidoctor.rules._base import Category, Diagnostic, Severity
from aidoctor.scan import compute_exit_code, scan, scan_file
from aidoctor.score import compute_score


def _diag(rule_id: str, sev: Severity) -> Diagnostic:
    return Diagnostic(
        rule_id=rule_id, severity=sev, category=Category.SECRETS,
        file=Path("/tmp/x.py"), line=1, column=0, message="m", help="h",
    )


# --- compute_exit_code with critical severity (W6/2) ---


def test_exit_code_fail_on_error_blocks_on_critical() -> None:
    """fail_on=error blocks on critical too — critical is 'error or worse'."""
    score = compute_score([_diag("crit-rule", Severity.CRITICAL)])
    assert compute_exit_code(score, "error") == 1


def test_exit_code_fail_on_critical_only_blocks_on_critical() -> None:
    """fail_on=critical lets errors and warnings through; blocks only on critical."""
    score = compute_score([_diag("err-rule", Severity.ERROR)])
    assert compute_exit_code(score, "critical") == 0

    score = compute_score([_diag("crit-rule", Severity.CRITICAL)])
    assert compute_exit_code(score, "critical") == 1


def test_exit_code_fail_on_warning_blocks_on_critical() -> None:
    """warning is the most-strict; blocks on warning, error, AND critical."""
    score = compute_score([_diag("crit-rule", Severity.CRITICAL)])
    assert compute_exit_code(score, "warning") == 1


def test_exit_code_fail_on_none_never_blocks() -> None:
    """The opt-out path: --fail-on=none lets everything through."""
    score = compute_score([_diag("crit-rule", Severity.CRITICAL)])
    assert compute_exit_code(score, "none") == 0


def test_exit_code_clean_score_always_zero() -> None:
    """Clean scan exits 0 regardless of fail-on policy."""
    score = compute_score([])
    for policy in ("none", "critical", "error", "warning"):
        assert compute_exit_code(score, policy) == 0, f"failed for {policy}"


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
