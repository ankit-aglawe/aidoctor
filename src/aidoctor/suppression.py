"""Inline suppression comments.

Supports three syntaxes:
    # aidoctor: disable=rule-1              (next line only)
    # aidoctor: disable=rule-1,rule-2       (multiple rules, next line)
    # aidoctor: disable-line=rule-1         (this line only)
    # aidoctor: disable-file=rule-1         (entire file)

All three accept "*" as a wildcard meaning "all rules".

Suppression is applied AFTER rules emit diagnostics — the scanner runs all rules,
then filters out diagnostics whose (rule_id, file, line) matches a suppression.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from aidoctor.rules import Diagnostic

NEXT_LINE_RE = re.compile(r"#\s*aidoctor:\s*disable=([\w\-*,\s]+)", re.IGNORECASE)
THIS_LINE_RE = re.compile(r"#\s*aidoctor:\s*disable-line=([\w\-*,\s]+)", re.IGNORECASE)
WHOLE_FILE_RE = re.compile(r"#\s*aidoctor:\s*disable-file=([\w\-*,\s]+)", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class FileSuppressions:
    """Suppression data for one file."""

    file_wide: frozenset[str]               # rule_ids suppressed everywhere
    by_line: dict[int, frozenset[str]]      # 1-indexed line → rule_ids suppressed on that line


def _parse_rule_list(raw: str) -> frozenset[str]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return frozenset(parts)


def parse_suppressions(source: str) -> FileSuppressions:
    """Walk source lines and collect all suppression directives."""
    file_wide: set[str] = set()
    by_line: dict[int, set[str]] = {}
    lines = source.splitlines()

    for idx, line in enumerate(lines, start=1):
        m = WHOLE_FILE_RE.search(line)
        if m:
            file_wide.update(_parse_rule_list(m.group(1)))

        m = THIS_LINE_RE.search(line)
        if m:
            by_line.setdefault(idx, set()).update(_parse_rule_list(m.group(1)))

        m = NEXT_LINE_RE.search(line)
        if m:
            # Disable on the NEXT non-blank, non-comment line. For v1 simplicity,
            # we apply it to idx+1 directly.
            next_idx = idx + 1
            by_line.setdefault(next_idx, set()).update(_parse_rule_list(m.group(1)))

    return FileSuppressions(
        file_wide=frozenset(file_wide),
        by_line={k: frozenset(v) for k, v in by_line.items()},
    )


def is_suppressed(rule_id: str, line: int, suppressions: FileSuppressions) -> bool:
    """Return True if this rule_id at this line is suppressed."""
    if "*" in suppressions.file_wide or rule_id in suppressions.file_wide:
        return True
    line_rules = suppressions.by_line.get(line, frozenset())
    if "*" in line_rules or rule_id in line_rules:
        return True
    return False


def filter_diagnostics(
    diagnostics: list[Diagnostic],
    source_by_file: dict[Path, str],
) -> list[Diagnostic]:
    """Drop diagnostics whose (file, line, rule_id) is suppressed by an inline comment."""
    cached: dict[Path, FileSuppressions] = {}
    keep: list[Diagnostic] = []
    for d in diagnostics:
        source = source_by_file.get(d.file)
        if source is None:
            keep.append(d)
            continue
        sup = cached.get(d.file)
        if sup is None:
            sup = parse_suppressions(source)
            cached[d.file] = sup
        if not is_suppressed(d.rule_id, d.line, sup):
            keep.append(d)
    return keep
