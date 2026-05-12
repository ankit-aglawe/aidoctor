"""Tests for the score formula.

Calibration policy (W6, v2.0 breaking change):
- any `critical` severity rule fires → cap score at 39 ("Critical")
- any `error` severity rule fires  → cap score at 69 ("Needs work")
- otherwise: 100 - 4*unique_errors - 2*unique_warnings, floored at 0

The cap closes a v1.1 trust bug: files with hardcoded payment keys + RCE were
scoring 88/100 "Great." Three personas (Maya/Sam/Karen) flagged it.
"""

from __future__ import annotations

from pathlib import Path

from aidoctor.rules import Category, Diagnostic, Severity
from aidoctor.score import (
    ERROR_CAP,
    LABEL_CRITICAL,
    LABEL_GREAT,
    LABEL_NEEDS_WORK,
    SEVERE_CAP,
    WARNING_PENALTY,
    compute_score,
)


def _diag(rule_id: str, sev: Severity, line: int = 1) -> Diagnostic:
    return Diagnostic(
        rule_id=rule_id,
        severity=sev,
        category=Category.SECRETS,
        file=Path("/tmp/x.py"),
        line=line,
        column=0,
        message="m",
        help="h",
    )


def test_empty_diagnostics_perfect_score() -> None:
    s = compute_score([])
    assert s.value == 100
    assert s.label == LABEL_GREAT
    assert s.unique_critical_rules == 0


def test_one_unique_error_rule_caps_at_69() -> None:
    """v1.1 policy returned 96 here ('Great'). v2.0 caps any-error at 69."""
    s = compute_score([_diag("hardcoded-api-key", Severity.ERROR)])
    assert s.value == ERROR_CAP
    assert s.label == LABEL_NEEDS_WORK
    assert s.unique_error_rules == 1


def test_one_critical_rule_caps_at_39() -> None:
    """New in v2.0: critical severity (e.g., shell-true-with-variable) caps at 39."""
    s = compute_score([_diag("shell-true-with-variable", Severity.CRITICAL)])
    assert s.value == SEVERE_CAP
    assert s.label == LABEL_CRITICAL
    assert s.unique_critical_rules == 1


def test_critical_caps_below_error_cap() -> None:
    """If both critical and error fire, the critical cap (39) wins."""
    diags = [
        _diag("crit-rule", Severity.CRITICAL),
        _diag("err-rule", Severity.ERROR),
    ]
    s = compute_score(diags)
    assert s.value == SEVERE_CAP


def test_unique_rule_penalty_not_violation_count() -> None:
    """50 violations of one error rule still scores 69 — error cap wins over count."""
    diags = [_diag("hardcoded-api-key", Severity.ERROR, line=i) for i in range(50)]
    s = compute_score(diags)
    assert s.value == ERROR_CAP
    assert s.total_violations == 50


def test_many_errors_drop_below_error_cap() -> None:
    """Penalty math can take score below 69 when there are enough unique errors."""
    # 30 unique error rules × 4 penalty = 120 → 100-120 = 0, floored.
    diags = [_diag(f"rule-{i}", Severity.ERROR) for i in range(30)]
    s = compute_score(diags)
    assert s.value == 0
    assert s.label == LABEL_CRITICAL


def test_warnings_only_use_penalty_no_cap() -> None:
    """Pure-warning scans still use the penalty formula (no severity cap)."""
    diags = [_diag(f"rule-{i}", Severity.WARNING) for i in range(2)]
    s = compute_score(diags)
    assert s.value == 100 - 2 * WARNING_PENALTY
    assert s.label == LABEL_GREAT  # 96 still > 75


def test_mixed_error_and_warning_uses_error_cap() -> None:
    diags = [
        _diag("rule-a", Severity.ERROR),
        _diag("rule-b", Severity.WARNING),
    ]
    s = compute_score(diags)
    # Raw would be 100-4-2=94; capped at 69 because error fires.
    assert s.value == ERROR_CAP
    assert s.unique_error_rules == 1
    assert s.unique_warning_rules == 1


def test_label_boundaries_warnings_only() -> None:
    """With only warnings, label thresholds match the old policy."""
    # 13 unique warnings × 2 = 26 → 100-26 = 74 → Needs work (boundary at 75)
    diags = [_diag(f"rule-{i}", Severity.WARNING) for i in range(13)]
    s = compute_score(diags)
    assert s.value == 74
    assert s.label == LABEL_NEEDS_WORK
