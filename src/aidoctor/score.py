"""Score formula.

Calibration policy (v2.0, locked by W6 CEO/eng review):

    if any unique rule with severity=critical fires:
        score = min(raw, SEVERE_CAP=39)   → label "Critical"
    elif any unique rule with severity=error fires:
        score = min(raw, ERROR_CAP=69)    → label "Needs work"
    else:
        score = raw = 100 - 4*unique_errors - 2*unique_warnings  (floored at 0)

The caps close a v1.1 trust bug: files with hardcoded payment keys + RCE
scored 88/100 'Great'. Three personas (Maya/Sam/Karen) flagged it as the
single biggest credibility hole; CEO plan item 5 + eng review made it the
v2.0 default.

ERROR_PENALTY=4 and WARNING_PENALTY=2 are frozen across v2.x. Changing the
caps or penalties invalidates leaderboard comparability — bump scoring_version
in build_json_payload first.
"""

from __future__ import annotations

from dataclasses import dataclass

from aidoctor.rules import Diagnostic, Severity

ERROR_PENALTY = 4
WARNING_PENALTY = 2

# Caps. Any rule at this severity locks the score at or below the cap value.
SEVERE_CAP = 39   # critical fires → at most 39
ERROR_CAP = 69    # error fires    → at most 69

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
    unique_critical_rules: int = 0


def compute_score(diagnostics: list[Diagnostic]) -> Score:
    """Compute the 0-100 score from a list of diagnostics.

    Critical and error severities apply a hard cap on top of the penalty
    formula. The cap signals 'this isn't great' regardless of how few unique
    rules fired; the penalty math distinguishes mildly bad from severely bad
    when many unique rules fire.
    """
    unique_criticals: set[str] = set()
    unique_errors: set[str] = set()
    unique_warnings: set[str] = set()
    for d in diagnostics:
        if d.severity == Severity.CRITICAL:
            unique_criticals.add(d.rule_id)
        elif d.severity == Severity.ERROR:
            unique_errors.add(d.rule_id)
        elif d.severity == Severity.WARNING:
            unique_warnings.add(d.rule_id)
    raw = 100 - len(unique_errors) * ERROR_PENALTY - len(unique_warnings) * WARNING_PENALTY
    value = max(0, raw)

    if unique_criticals:
        value = min(value, SEVERE_CAP)
    elif unique_errors:
        value = min(value, ERROR_CAP)

    return Score(
        value=value,
        label=_label(value),
        unique_error_rules=len(unique_errors),
        unique_warning_rules=len(unique_warnings),
        unique_critical_rules=len(unique_criticals),
        total_violations=len(diagnostics),
    )


def _label(value: int) -> str:
    if value >= GREAT_THRESHOLD:
        return LABEL_GREAT
    if value >= NEEDS_WORK_THRESHOLD:
        return LABEL_NEEDS_WORK
    return LABEL_CRITICAL
