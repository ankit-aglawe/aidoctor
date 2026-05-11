"""--diff mode: scan only lines that changed.

Filters scan diagnostics to lines present in the unstaged or staged git diff.
Useful in pre-commit hooks and PR CI where only new violations matter.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

from aidoctor.rules import Diagnostic

logger = logging.getLogger(__name__)

HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


class GitNotAvailableError(Exception):
    """git is not installed or current dir is not a repo."""


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise GitNotAvailableError("git not found on PATH") from exc
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        if "not a git repository" in stderr.lower():
            raise GitNotAvailableError("not inside a git repository")
        raise GitNotAvailableError(f"git failed: {stderr}")
    return proc.stdout


def get_changed_files(cwd: Path | None = None, *, staged: bool = False) -> list[Path]:
    """List repository-relative paths that have changed (unstaged) or are staged."""
    args = ["diff", "--name-only"]
    if staged:
        args.append("--cached")
    out = _run_git(args, cwd=cwd)
    files = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        files.append(Path(line))
    return files


def parse_hunks(diff_text: str) -> set[int]:
    """Parse unified-diff hunk headers, return set of line numbers in the NEW file that changed.

    For unified=0 diffs, every line starting with '+' (and not '+++') is a changed line.
    The line numbers come from the hunk header `@@ -A,B +C,D @@`.
    """
    line_set: set[int] = set()
    cur_new_line = 0
    in_hunk = False

    for line in diff_text.splitlines():
        if line.startswith("@@"):
            m = HUNK_HEADER_RE.match(line)
            if m:
                cur_new_line = int(m.group(1))
                in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            line_set.add(cur_new_line)
            cur_new_line += 1
        elif line.startswith("-"):
            # Removed lines don't increment new-file line number.
            continue
        elif line.startswith(" "):
            cur_new_line += 1
        else:
            # Other content (e.g. blank diff separators) ends the hunk for tracking.
            in_hunk = False
    return line_set


def get_changed_lines(
    cwd: Path | None = None, *, staged: bool = False
) -> dict[Path, set[int]]:
    """Return mapping of repo-relative file path → set of changed line numbers (1-indexed)."""
    args = ["diff", "--unified=0", "--no-color", "--no-prefix"]
    if staged:
        args.append("--cached")
    out = _run_git(args, cwd=cwd)

    # Split by file boundaries.
    file_blocks: dict[Path, list[str]] = {}
    cur_file: Path | None = None
    for raw in out.splitlines():
        if raw.startswith("diff --git "):
            # Form: `diff --git a/path/to/file b/path/to/file` (we use --no-prefix so no a/b).
            parts = raw.split()
            if len(parts) >= 4:
                # With --no-prefix the format is `diff --git <path> <path>`.
                cur_file = Path(parts[2])
                file_blocks.setdefault(cur_file, [])
            continue
        if cur_file is not None:
            file_blocks[cur_file].append(raw)

    result: dict[Path, set[int]] = {}
    for path, lines in file_blocks.items():
        diff_text = "\n".join(lines)
        result[path] = parse_hunks(diff_text)
    return result


def filter_diagnostics_to_diff(
    diagnostics: Iterable[Diagnostic],
    changed_lines: dict[Path, set[int]],
    repo_root: Path,
) -> list[Diagnostic]:
    """Keep only diagnostics whose file+line is in `changed_lines`.

    repo_root is used to convert the diagnostic's absolute file path to a
    repo-relative path matching the diff's path format.
    """
    keep: list[Diagnostic] = []
    for d in diagnostics:
        try:
            rel = d.file.resolve().relative_to(repo_root.resolve())
        except ValueError:
            continue
        lines = changed_lines.get(rel)
        if not lines:
            continue
        if d.line in lines:
            keep.append(d)
    return keep
