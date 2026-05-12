"""Multi-language parser abstraction.

aidoctor v2.0 scans 5 languages deterministically:
    Python — libcst (kept; mature, ships v1.1 rules unchanged)
    Rust / Go / JS / TS — tree-sitter (new in v2.0)

Each parser exposes a uniform interface:
    parse(source_bytes) -> parse tree (opaque type per parser)
    extract_comments(tree, source_bytes) -> Iterator[CommentNode]

The declarative engine routes rules to the right parser via the `languages`
field on each rule, with `LANG_TO_PARSER` providing the dispatch map.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CommentNode:
    """One source-code comment with its position (1-based line, 0-based column).

    `text` is the comment content with the comment marker stripped:
        Python   `# foo`     -> text="foo"
        Rust     `// foo`    -> text="foo"
        Go/JS/TS `// foo`    -> text="foo"
        block comments       -> marker stripped on both ends
    """
    line: int
    column: int
    text: str


# File extension → language identifier. Used by `find_source_files` to
# decide which parser walks each file. Extensions NOT in this map are skipped.
EXT_TO_LANGUAGE: dict[str, str] = {
    ".py":   "python",
    ".pyi":  "python",
    ".rs":   "rust",
    ".go":   "go",
    ".js":   "javascript",
    ".mjs":  "javascript",
    ".cjs":  "javascript",
    ".jsx":  "javascript",  # JSX parsed via tree-sitter-javascript
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".d.ts": "typescript",
}


# v2.0 supported language set (matches scanner availability)
SUPPORTED_LANGUAGES: frozenset[str] = frozenset(EXT_TO_LANGUAGE.values())


def language_for_file(path: Path) -> str | None:
    """Return the language id for a file's extension, or None if not supported."""
    name = path.name
    # Multi-dot extensions first (.d.ts before .ts)
    for ext, lang in sorted(EXT_TO_LANGUAGE.items(), key=lambda kv: -len(kv[0])):
        if name.endswith(ext):
            return lang
    return None
