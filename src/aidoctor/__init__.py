"""aidoctor — your agent writes bad code. This catches it.

Public API (covered by SemVer, breaking changes only in major bumps):

    from aidoctor import scan_paths, ScanResult

    result = scan_paths(["src/"])      # ScanResult
    result.score                        # Score (value, label, ...)
    result.diagnostics                  # list[Diagnostic]
    result.to_dict()                    # dict (schema_version=1)
    result.to_json()                    # str (deterministic JSON)

Stability contract:
    `scan_paths`, `ScanResult`, `ScanResult.score`, `ScanResult.to_dict`, and
    `ScanResult.to_json` are public. SemVer applies: breaking changes only in
    major bumps; deprecations get one minor-version warning before removal.

Internal modules (subject to change without notice):
    aidoctor.engine.*, aidoctor.rules.*, aidoctor.skill.*, aidoctor.cli.
    Workflow-skill authors: use the top-level imports above, not these.
"""

from __future__ import annotations

from aidoctor.scan import ScanResult
from aidoctor.scan import scan as scan_paths

__version__ = "2.0.0"

__all__ = ["ScanResult", "scan_paths", "__version__"]
