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
    """Raised when discovery finds zero scannable files at the given path(s).

    Kept named for v1.1 compat — actual matching extension set is per
    EXT_TO_LANGUAGE in aidoctor.parsers.
    """


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
    """v1.1-compat shim. Use `find_source_files` for the multi-language v2.0 walk."""
    return find_source_files(paths, respect_gitignore=respect_gitignore, languages={"python"})


def find_source_files(
    paths: list[Path],
    *,
    respect_gitignore: bool = True,
    languages: set[str] | None = None,
) -> list[Path]:
    """Walk paths, return all source files for the requested languages.

    `languages` defaults to every language in EXT_TO_LANGUAGE (all 5 supported).
    Pass a subset to restrict (e.g. {"python"} for the v1.1 compat case).

    Prunes ALWAYS_SKIP_DIRS before descending (so we never walk into `.venv`,
    `node_modules`, etc.) and honours `.gitignore` patterns at the scan root
    when respect_gitignore=True.
    """
    from aidoctor.parsers import EXT_TO_LANGUAGE, language_for_file

    target_langs = languages if languages is not None else set(EXT_TO_LANGUAGE.values())

    found: set[Path] = set()
    for original in paths:
        path = original.resolve()
        if path.is_file():
            lang = language_for_file(path)
            if lang in target_langs:
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
                file_path = dir_path / name
                lang = language_for_file(file_path)
                if lang not in target_langs:
                    continue
                if respect_gitignore and _is_ignored(file_path, path, gitignore_patterns):
                    continue
                found.add(file_path)
    if not found:
        lang_str = "/".join(sorted(target_langs)) if target_langs else "any"
        raise NoPythonFilesError(
            f"No {lang_str} source files found in: {', '.join(str(p) for p in paths)}"
        )
    return sorted(found)
