"""/aidoctor:deai orchestrator — the moat skill exposed as a Python API + CLI.

Pipeline:
    1. Scan the given paths with the standard scanner.
    2. Load the JSONL manifests to learn which rules are ai-style + HIGH confidence.
    3. Filter scan findings down to the ai-style HIGH set.
    4. For each surviving finding, ask the engine to propose a fix.
    5. Compute an "AI residue score" (0–100, 100 = clean) over the ai-style findings only.

Output is a structured dict (DeaiResult.to_dict()) that the `aidoctor deai`
CLI command and `/aidoctor:deai` skill both consume.

The skill applies fixes interactively via the agent's file-edit tools; this
module's job ends at proposing them. That keeps the apply step transparent
(every change is visible in a diff) and avoids reinventing safe-write logic
the agent already has.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aidoctor.engine.declarative import Rule
from aidoctor.engine.fixes import RewriteResult, propose_fix
from aidoctor.rules._base import Diagnostic


@dataclass(slots=True)
class DeaiFinding:
    """A scan finding plus the engine's proposed fix for it."""
    diagnostic: Diagnostic
    proposed_fix: RewriteResult

    def to_dict(self) -> dict[str, Any]:
        d = self.diagnostic.to_dict()
        d["proposed_fix"] = {
            "ok": self.proposed_fix.ok,
            "original_code": self.proposed_fix.original_code,
            "replacement_code": self.proposed_fix.replacement_code,
            "line_range": list(self.proposed_fix.line_range),
            "reason_if_failed": self.proposed_fix.reason_if_failed,
        }
        return d


@dataclass(slots=True)
class DeaiResult:
    """Output of /aidoctor:deai. Public schema (covered by SemVer)."""
    findings: list[DeaiFinding] = field(default_factory=list)
    files_scanned: int = 0
    ai_residue_score: int = 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "ai_residue_score": self.ai_residue_score,
            "files_scanned": self.files_scanned,
            "findings": [f.to_dict() for f in self.findings],
        }


# How much each ai-style finding subtracts from the residue score.
# Caps at 0 so noisy files don't go negative.
_RESIDUE_PENALTY_PER_FINDING = 10


def run(paths: list[Path]) -> DeaiResult:
    """Run the /deai pipeline against the given paths. Pure function — no I/O
    beyond reading source files."""
    from aidoctor.scan import _load_manifest_rules, scan

    scan_result = scan(paths, jobs=1)

    # Build a lookup: rule_id → (Rule, source-cache-by-file).
    manifest_rules: dict[str, Rule] = {r.id: r for r in _load_manifest_rules()}

    # File source cache so we don't re-read for every finding.
    source_cache: dict[Path, str] = {}

    findings: list[DeaiFinding] = []
    for d in scan_result.diagnostics:
        rule = manifest_rules.get(d.rule_id)
        if rule is None:
            continue  # legacy v1.1 Python rule, not part of the moat
        if rule.category != "ai-style":
            continue
        if rule.confidence != "HIGH":
            continue
        if d.file not in source_cache:
            try:
                source_cache[d.file] = d.file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
        fix = propose_fix(rule, source_cache[d.file], d)
        findings.append(DeaiFinding(diagnostic=d, proposed_fix=fix))

    residue = max(0, 100 - len(findings) * _RESIDUE_PENALTY_PER_FINDING)
    return DeaiResult(
        findings=findings,
        files_scanned=scan_result.files_scanned,
        ai_residue_score=residue,
    )
