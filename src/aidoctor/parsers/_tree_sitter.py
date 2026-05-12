"""Generic tree-sitter parser wrapper for the 4 non-Python languages.

Each language has its own pip package (tree-sitter-rust, tree-sitter-go,
tree-sitter-javascript, tree-sitter-typescript). We load them lazily — a
user scanning only .py files shouldn't pay the import cost of all four.

Comment node names vary slightly per language; the per-language module
declares its set in `_COMMENT_NODE_TYPES`.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Iterator

import tree_sitter

from aidoctor.parsers import CommentNode

logger = logging.getLogger(__name__)


# Comment node type names per language (from each grammar's grammar.js)
_COMMENT_NODE_TYPES: dict[str, frozenset[str]] = {
    "rust":       frozenset({"line_comment", "block_comment"}),
    "go":         frozenset({"comment"}),
    "javascript": frozenset({"comment"}),
    "typescript": frozenset({"comment"}),
}


# Comment markers to strip from extracted text (per language)
_COMMENT_MARKERS: dict[str, tuple[str, ...]] = {
    "rust":       ("//", "/*", "*/"),
    "go":         ("//", "/*", "*/"),
    "javascript": ("//", "/*", "*/"),
    "typescript": ("//", "/*", "*/"),
}


@lru_cache(maxsize=8)
def _get_parser(language: str) -> tree_sitter.Parser:
    """Return a cached tree-sitter Parser for the given language.

    Raises ImportError if the grammar package isn't installed (e.g. user
    has aidoctor[core] without language extras).
    """
    if language == "rust":
        import tree_sitter_rust as ts_lang
    elif language == "go":
        import tree_sitter_go as ts_lang
    elif language == "javascript":
        import tree_sitter_javascript as ts_lang
    elif language == "typescript":
        import tree_sitter_typescript as ts_lang
        return tree_sitter.Parser(tree_sitter.Language(ts_lang.language_typescript()))
    else:
        raise ValueError(f"unsupported tree-sitter language: {language!r}")
    return tree_sitter.Parser(tree_sitter.Language(ts_lang.language()))


def parse(source: bytes, language: str) -> tree_sitter.Tree | None:
    """Parse source bytes via tree-sitter. Returns None on grammar-load failure."""
    try:
        parser = _get_parser(language)
    except (ImportError, ValueError) as e:
        logger.warning("tree-sitter grammar for %s unavailable: %s", language, e)
        return None
    return parser.parse(source)


def extract_comments(
    tree: tree_sitter.Tree, source: bytes, language: str,
) -> Iterator[CommentNode]:
    """Walk the parse tree (DFS) and yield every comment node as a CommentNode.

    Comment marker (e.g. leading `//`, `/*`, `*/`) is stripped from text.
    Line is 1-based, column is 0-based to match aidoctor's existing convention.
    """
    comment_types = _COMMENT_NODE_TYPES.get(language, frozenset())
    if not comment_types:
        return

    markers = _COMMENT_MARKERS.get(language, ())

    def _strip_markers(text: str) -> str:
        stripped = text
        for marker in markers:
            if stripped.startswith(marker):
                stripped = stripped[len(marker):]
                break
        for marker in markers:
            if stripped.endswith(marker):
                stripped = stripped[:-len(marker)]
                break
        return stripped

    # DFS via stack — simpler than cursor.walk(), no duplication risk.
    stack: list[tree_sitter.Node] = [tree.root_node]
    seen_offsets: set[int] = set()
    while stack:
        node = stack.pop()
        if node.type in comment_types and node.start_byte not in seen_offsets:
            seen_offsets.add(node.start_byte)
            raw = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            yield CommentNode(
                line=node.start_point[0] + 1,
                column=node.start_point[1],
                text=_strip_markers(raw),
            )
        # Push children in reverse so DFS visits them left-to-right
        for child in reversed(node.children):
            stack.append(child)
