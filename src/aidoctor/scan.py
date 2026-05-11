"""Scan orchestrator.

For each file: parse with libcst, run every rule visitor, collect diagnostics.
Uses multiprocessing.Pool when scanning more than 4 files (per Eng-D3 from eng review).
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
from dataclasses import dataclass, field
from pathlib import Path

import libcst as cst

from aidoctor.rules import RULES, Diagnostic, RuleContext

logger = logging.getLogger(__name__)

# Files under this count run serial — pool startup cost dominates for tiny scans.
PARALLEL_THRESHOLD = 4


class RuleExecutionError(Exception):
    """Wraps an exception raised by a rule visitor."""


@dataclass
class ScanResult:
    """Aggregated result of scanning a set of files."""

    diagnostics: list[Diagnostic] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    parse_errors: list[tuple[Path, str]] = field(default_factory=list)
    rule_errors: list[tuple[Path, str, str]] = field(default_factory=list)


def scan_file(path: Path) -> tuple[list[Diagnostic], str | None]:
    """Scan one file. Return (diagnostics, parse_error_message_or_None).

    This is a top-level function so it pickles cleanly for multiprocessing.Pool.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [], f"could not read file: {e}"

    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as e:
        return [], f"libcst parse error: {e}"

    wrapper = cst.MetadataWrapper(module)
    context = RuleContext(file=path, source=source)

    for rule_class in RULES:
        rule = rule_class(context)
        try:
            wrapper.visit(rule)
        except Exception as e:  # noqa: BLE001 - intentionally broad for rule isolation
            # Rule crashed on this file. Log + continue so one broken rule doesn't kill the scan.
            logger.warning(
                "rule %s failed on %s: %s", rule_class.rule_id, path, e
            )

    return context.diagnostics, None


def scan(paths: list[Path], *, jobs: int | None = None) -> ScanResult:
    """Scan all files at the given paths.

    jobs:
        None  -> use min(cpu_count, len(files)) workers if files > PARALLEL_THRESHOLD
        1     -> single-threaded (useful for debugging and tiny scans)
        N>1   -> use exactly N workers
    """
    from aidoctor.discover import find_python_files
    from aidoctor.suppression import filter_diagnostics

    result = ScanResult()
    files = find_python_files(paths)
    source_by_file: dict[Path, str] = {}

    if jobs is None:
        worker_count = min(os.cpu_count() or 1, len(files))
        use_pool = len(files) > PARALLEL_THRESHOLD and worker_count > 1
    else:
        worker_count = max(1, jobs)
        use_pool = worker_count > 1 and len(files) > 1

    if use_pool:
        # imap streams results back as they finish — lower latency for big scans.
        with mp.get_context("spawn").Pool(worker_count) as pool:
            for path, (diagnostics, parse_err) in zip(
                files, pool.imap(scan_file, files), strict=True
            ):
                if parse_err is not None:
                    result.parse_errors.append((path, parse_err))
                    result.files_skipped += 1
                    continue
                result.diagnostics.extend(diagnostics)
                result.files_scanned += 1
                try:
                    source_by_file[path] = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
    else:
        for path in files:
            diagnostics, parse_err = scan_file(path)
            if parse_err is not None:
                result.parse_errors.append((path, parse_err))
                result.files_skipped += 1
                continue
            result.diagnostics.extend(diagnostics)
            result.files_scanned += 1
            try:
                source_by_file[path] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

    # Apply inline suppression filters (`# aidoctor: disable=...`).
    result.diagnostics = filter_diagnostics(result.diagnostics, source_by_file)

    return result
