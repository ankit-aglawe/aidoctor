"""Find Python files to scan.

Respects .gitignore, skips common vendor/cache dirs.
"""

from __future__ import annotations

import fnmatch
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
    gitignore = directory / ".gitignore"
    if not gitignore.exists():
        return []
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    patterns = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # We treat all non-comment lines as glob patterns. Negations (!) ignored for v1.
        if line.startswith("!"):
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

    Skips ALWAYS_SKIP_DIRS unconditionally and .gitignore matches when respect_gitignore=True.
    Returns a deduplicated, sorted list of absolute paths.
    """
    found: set[Path] = set()
    for path in paths:
        path = path.resolve()
        if path.is_file():
            if path.suffix == ".py":
                found.add(path)
            continue
        if not path.is_dir():
            continue
        root = path
        gitignore_patterns = _read_gitignore(root) if respect_gitignore else []
        for sub in path.rglob("*.py"):
            # Skip any path containing a skip-dir component.
            if any(part in ALWAYS_SKIP_DIRS for part in sub.parts):
                continue
            if respect_gitignore and _is_ignored(sub, root, gitignore_patterns):
                continue
            found.add(sub)
    if not found:
        raise NoPythonFilesError(
            f"No Python files found in: {', '.join(str(p) for p in paths)}"
        )
    return sorted(found)
