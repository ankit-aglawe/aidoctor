"""Tests for the score formula."""

from __future__ import annotations

from pathlib import Path

from aidoctor.rules import Category, Diagnostic, Severity
from aidoctor.score import (
    ERROR_PENALTY,
    LABEL_CRITICAL,
    LABEL_GREAT,
    LABEL_NEEDS_WORK,
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


def test_one_unique_error_rule() -> None:
    s = compute_score([_diag("hardcoded-api-key", Severity.ERROR)])
    assert s.value == 100 - ERROR_PENALTY
    assert s.unique_error_rules == 1
    assert s.unique_warning_rules == 0


def test_unique_rule_penalty_not_violation_count() -> None:
    # 50 violations of one rule = same penalty as 1 violation of that rule.
    diags = [_diag("hardcoded-api-key", Severity.ERROR, line=i) for i in range(50)]
    s = compute_score(diags)
    assert s.value == 100 - ERROR_PENALTY  # only 1 unique error rule
    assert s.total_violations == 50


def test_mixed_severity_combo() -> None:
    diags = [
        _diag("rule-a", Severity.ERROR),
        _diag("rule-b", Severity.WARNING),
        _diag("rule-b", Severity.WARNING),  # duplicate same rule
    ]
    s = compute_score(diags)
    assert s.value == 100 - ERROR_PENALTY - WARNING_PENALTY
    assert s.unique_error_rules == 1
    assert s.unique_warning_rules == 1


def test_score_floors_at_zero() -> None:
    # 30 unique error rules at 4 penalty = -20, floored to 0.
    diags = [_diag(f"rule-{i}", Severity.ERROR) for i in range(30)]
    s = compute_score(diags)
    assert s.value == 0
    assert s.label == LABEL_CRITICAL


def test_label_boundaries() -> None:
    # Boundary at 75 (Great vs Needs work) and 50 (Needs work vs Critical).
    # 7 unique error rules at 4 penalty = 100 - 28 = 72 → Needs work
    diags = [_diag(f"rule-{i}", Severity.ERROR) for i in range(7)]
    s = compute_score(diags)
    assert s.value == 72
    assert s.label == LABEL_NEEDS_WORK

    # 6 unique error rules at 4 penalty = 100 - 24 = 76 → Great
    diags = [_diag(f"rule-{i}", Severity.ERROR) for i in range(6)]
    s = compute_score(diags)
    assert s.value == 76
    assert s.label == LABEL_GREAT

    # 13 unique error rules at 4 penalty = 100 - 52 = 48 → Critical
    diags = [_diag(f"rule-{i}", Severity.ERROR) for i in range(13)]
    s = compute_score(diags)
    assert s.value == 48
    assert s.label == LABEL_CRITICAL
