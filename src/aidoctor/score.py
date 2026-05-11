"""Score formula.

Mirrors react-doctor: penalty per unique rule tripped, not per violation.
This incentivizes fixing categories of issues, not chasing line counts.

ERROR_PENALTY=4 and WARNING_PENALTY=2 are frozen for v1. Changing them
invalidates leaderboard scores across versions, so any bump needs a
scoring_version stamp in the JSON output.
"""

from __future__ import annotations

from dataclasses import dataclass

from aidoctor.rules import Diagnostic, Severity

ERROR_PENALTY = 4
WARNING_PENALTY = 2

LABEL_GREAT = "Great"
LABEL_NEEDS_WORK = "Needs work"
LABEL_CRITICAL = "Critical"

GREAT_THRESHOLD = 75
NEEDS_WORK_THRESHOLD = 50


@dataclass(slots=True, frozen=True)
class Score:
    value: int
    label: str
    unique_error_rules: int
    unique_warning_rules: int
    total_violations: int


def compute_score(diagnostics: list[Diagnostic]) -> Score:
    """Compute the 0-100 score from a list of diagnostics."""
    unique_errors: set[str] = set()
    unique_warnings: set[str] = set()
    for d in diagnostics:
        if d.severity == Severity.ERROR:
            unique_errors.add(d.rule_id)
        elif d.severity == Severity.WARNING:
            unique_warnings.add(d.rule_id)
    raw = 100 - len(unique_errors) * ERROR_PENALTY - len(unique_warnings) * WARNING_PENALTY
    value = max(0, raw)
    return Score(
        value=value,
        label=_label(value),
        unique_error_rules=len(unique_errors),
        unique_warning_rules=len(unique_warnings),
        total_violations=len(diagnostics),
    )


def _label(value: int) -> str:
    if value >= GREAT_THRESHOLD:
        return LABEL_GREAT
    if value >= NEEDS_WORK_THRESHOLD:
        return LABEL_NEEDS_WORK
    return LABEL_CRITICAL
