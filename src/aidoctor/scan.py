"""Scan orchestrator.

For each file: parse with libcst, run every rule visitor, collect diagnostics.
Uses multiprocessing.Pool when scanning more than 4 files; serial below that
threshold since pool startup cost dominates for tiny scans.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
from dataclasses import dataclass, field
from pathlib import Path

import libcst as cst

# Import rules_complex submodules for their side effect of registering python-kind
# detectors with the declarative engine. Multiprocess workers re-import this
# module, which re-runs these registrations in each worker process.
import aidoctor.rules_complex.security  # noqa: F401 - register OWASP detectors
from aidoctor.engine.declarative import Rule, apply_rule, load_manifest
from aidoctor.rules import RULES, Diagnostic, RuleContext

logger = logging.getLogger(__name__)


_MANIFEST_RULES_CACHE: list[Rule] | None = None


def _load_manifest_rules() -> list[Rule]:
    """Discover and load every JSONL manifest under rules/manifest/. Cached per process."""
    global _MANIFEST_RULES_CACHE
    if _MANIFEST_RULES_CACHE is not None:
        return _MANIFEST_RULES_CACHE
    manifests_dir = Path(__file__).parent / "rules" / "manifest"
    rules: list[Rule] = []
    if manifests_dir.exists():
        for jsonl in sorted(manifests_dir.glob("*.jsonl")):
            try:
                rules.extend(load_manifest(jsonl))
            except FileNotFoundError:
                continue
    _MANIFEST_RULES_CACHE = rules
    return rules

# Files under this count run serial — pool startup cost dominates for tiny scans.
PARALLEL_THRESHOLD = 4


class RuleExecutionError(Exception):
    """Wraps an exception raised by a rule visitor."""


@dataclass
class ScanResult:
    """Aggregated result of scanning a set of files.

    Public API (covered by SemVer): the `diagnostics`, `files_scanned`,
    `files_skipped`, `parse_errors` fields and the `score`, `to_dict`, `to_json`
    accessors. `rule_errors` is currently internal.
    """

    diagnostics: list[Diagnostic] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    parse_errors: list[tuple[Path, str]] = field(default_factory=list)
    rule_errors: list[tuple[Path, str, str]] = field(default_factory=list)
    @property
    def score(self):
        """Calibrated 0-100 score for the scan. Cached on first access."""
        cached = self.__dict__.get("_score")
        if cached is None:
            from aidoctor.score import compute_score
            cached = compute_score(self.diagnostics)
            self.__dict__["_score"] = cached
        return cached

    def to_dict(self) -> dict:
        """v1 JSON schema dict. Stable shape for workflow skills + CI consumers."""
        return build_json_payload(self, self.score)

    def to_json(self) -> str:
        """JSON serialization of `to_dict()`. Deterministic key order."""
        import json
        return json.dumps(self.to_dict(), sort_keys=True)


def build_json_payload(result: "ScanResult", score) -> dict:
    """JSON shape for `aidoctor scan --json` and `aidoctor scan-pr --json`.

    Single source of truth for the schema. Bumping `schema_version` here is the
    one place callers need to coordinate.
    """
    return {
        "schema_version": 1,
        "score": {
            "value": score.value,
            "label": score.label,
            "unique_error_rules": score.unique_error_rules,
            "unique_warning_rules": score.unique_warning_rules,
            "total_violations": score.total_violations,
        },
        "files_scanned": result.files_scanned,
        "files_skipped": result.files_skipped,
        "parse_errors": [
            {"file": str(p), "error": err} for p, err in result.parse_errors
        ],
        "diagnostics": [d.to_dict() for d in result.diagnostics],
    }


EXIT_OK = 0
EXIT_FAIL_ON = 1


def compute_exit_code(score, fail_on: str) -> int:
    """Decide exit code given the user's --fail-on policy.

    Severity ranking (worst first): critical > error > warning.
    A `fail_on` of N means: fail if any rule at severity N-or-worse fired.

    Policies:
        none      -> never fail (opt-out for legacy callers)
        critical  -> fail only on critical
        error     -> fail on critical or error (the v2.0 default)
        warning   -> fail on any rule
    """
    if fail_on == "none":
        return EXIT_OK
    has_critical = score.unique_critical_rules > 0
    has_error = score.unique_error_rules > 0
    has_warning = score.unique_warning_rules > 0
    if fail_on == "critical":
        return EXIT_FAIL_ON if has_critical else EXIT_OK
    if fail_on == "error":
        return EXIT_FAIL_ON if (has_critical or has_error) else EXIT_OK
    if fail_on == "warning":
        return EXIT_FAIL_ON if (has_critical or has_error or has_warning) else EXIT_OK
    return EXIT_OK


def scan_file(path: Path) -> tuple[list[Diagnostic], str | None, str]:
    """Scan one file. Returns (diagnostics, parse_error_or_None, source_text).

    Multi-language at v2.0:
        * .py  → libcst path (legacy Python RULES) + manifest rules for "python"
        * other → manifest rules for the matching language only (no libcst)

    Source text is returned so callers can apply inline suppression filters
    without re-reading the file from disk. Top-level so it pickles for
    multiprocessing.Pool.
    """
    from aidoctor.parsers import language_for_file

    target_lang = language_for_file(path)

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [], f"could not read file: {e}", ""

    context = RuleContext(file=path, source=source)

    # Python gets the libcst legacy-rule pass.
    if target_lang == "python":
        try:
            module = cst.parse_module(source)
        except cst.ParserSyntaxError as e:
            return [], f"libcst parse error: {e}", source
        wrapper = cst.MetadataWrapper(module)
        for rule_class in RULES:
            rule = rule_class(context)
            try:
                wrapper.visit(rule)
            # aidoctor: disable=except-exception-swallowing
            except Exception as e:  # noqa: BLE001
                logger.warning("rule %s failed on %s: %s", rule_class.rule_id, path, e)

    # Apply JSONL manifest rules whose `langs` includes the file's language.
    if target_lang is not None:
        for manifest_rule in _load_manifest_rules():
            if target_lang not in manifest_rule.langs:
                continue
            try:
                context.diagnostics.extend(apply_rule(manifest_rule, path, source))
            # aidoctor: disable=except-exception-swallowing
            except Exception as e:  # noqa: BLE001
                logger.warning("manifest rule %s failed on %s: %s", manifest_rule.id, path, e)

    return context.diagnostics, None, source


def scan(paths: list[Path], *, jobs: int | None = None) -> ScanResult:
    """Scan all files at the given paths.

    v2.0: discovers ALL supported language files (Python + Rust + Go + JS + TS)
    and dispatches each through scan_file() with per-language routing.

    jobs:
        None  -> use min(cpu_count, len(files)) workers if files > PARALLEL_THRESHOLD
        1     -> single-threaded (useful for debugging and tiny scans)
        N>1   -> use exactly N workers
    """
    from aidoctor.discover import find_source_files
    from aidoctor.suppression import filter_diagnostics
    # Keep `find_python_files` import name for tests that pin to it.
    find_python_files = find_source_files  # noqa: F841

    result = ScanResult()
    files = find_source_files(paths)
    source_by_file: dict[Path, str] = {}

    if jobs is None:
        worker_count = min(os.cpu_count() or 1, len(files))
        use_pool = len(files) > PARALLEL_THRESHOLD and worker_count > 1
    else:
        worker_count = max(1, jobs)
        use_pool = worker_count > 1 and len(files) > 1

    def _accumulate(path: Path, diagnostics: list[Diagnostic], parse_err: str | None, source: str) -> None:
        if parse_err is not None:
            result.parse_errors.append((path, parse_err))
            result.files_skipped += 1
            return
        result.diagnostics.extend(diagnostics)
        result.files_scanned += 1
        source_by_file[path] = source

    if use_pool:
        # imap streams results back as they finish — lower latency for big scans.
        with mp.get_context("spawn").Pool(worker_count) as pool:
            for path, (diagnostics, parse_err, source) in zip(
                files, pool.imap(scan_file, files), strict=True
            ):
                _accumulate(path, diagnostics, parse_err, source)
    else:
        for path in files:
            diagnostics, parse_err, source = scan_file(path)
            _accumulate(path, diagnostics, parse_err, source)

    # Apply inline suppression filters (`# aidoctor: disable=...`).
    result.diagnostics = filter_diagnostics(result.diagnostics, source_by_file)

    return result
