"""Find Python files to scan.

Respects .gitignore, skips common vendor/cache dirs.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

# Directories we always skip, even without .gitignore.
ALWAYS_SKIP_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".eggs",
        "site-packages",
        ".idea",
        ".vscode",
    }
)


class NoPythonFilesError(Exception):
    """Raised when discovery finds zero .py files at the given path(s)."""


def _read_gitignore(directory: Path) -> list[str]:
    """Read .gitignore patterns from a directory. Returns simple glob patterns only."""
    try:
        text = (directory / ".gitignore").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    patterns = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        patterns.append(line.rstrip("/"))
    return patterns


def _is_ignored(path: Path, root: Path, patterns: list[str]) -> bool:
    """Check if path matches any gitignore pattern relative to root."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    rel_str = str(rel)
    name = path.name
    for pat in patterns:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_str, pat):
            return True
        # Patterns with leading slash anchor to root.
        if pat.startswith("/") and fnmatch.fnmatch(rel_str, pat.lstrip("/")):
            return True
    return False


def find_python_files(
    paths: list[Path],
    respect_gitignore: bool = True,
) -> list[Path]:
    """Walk paths, return all .py files.

    Prunes ALWAYS_SKIP_DIRS before descending (so we never walk into `.venv`,
    `node_modules`, etc.) and honours `.gitignore` patterns at the scan root
    when respect_gitignore=True.
    """
    found: set[Path] = set()
    for original in paths:
        path = original.resolve()
        if path.is_file():
            if path.suffix == ".py":
                found.add(path)
            continue
        if not path.is_dir():
            continue
        gitignore_patterns = _read_gitignore(path) if respect_gitignore else []
        # os.walk lets us prune in-place, so we never descend into vendored deps.
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if d not in ALWAYS_SKIP_DIRS]
            dir_path = Path(dirpath)
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                file_path = dir_path / name
                if respect_gitignore and _is_ignored(file_path, path, gitignore_patterns):
                    continue
                found.add(file_path)
    if not found:
        raise NoPythonFilesError(
            f"No Python files found in: {', '.join(str(p) for p in paths)}"
        )
    return sorted(found)
