"""Cross-language parser tests — verify uniform CommentNode extraction.

The declarative rule engine depends on every parser emitting comments with
the same shape (line, column, text-without-marker). These tests pin that
contract per language.
"""

from __future__ import annotations

from pathlib import Path


# --- file extension routing ---


def test_ext_routing_python() -> None:
    from aidoctor.parsers import language_for_file
    assert language_for_file(Path("foo.py")) == "python"
    assert language_for_file(Path("foo.pyi")) == "python"


def test_ext_routing_rust() -> None:
    from aidoctor.parsers import language_for_file
    assert language_for_file(Path("main.rs")) == "rust"


def test_ext_routing_go() -> None:
    from aidoctor.parsers import language_for_file
    assert language_for_file(Path("main.go")) == "go"


def test_ext_routing_js_variants() -> None:
    from aidoctor.parsers import language_for_file
    for ext in (".js", ".mjs", ".cjs", ".jsx"):
        assert language_for_file(Path(f"app{ext}")) == "javascript", ext


def test_ext_routing_ts_variants() -> None:
    from aidoctor.parsers import language_for_file
    assert language_for_file(Path("app.ts")) == "typescript"
    assert language_for_file(Path("app.tsx")) == "typescript"
    assert language_for_file(Path("types.d.ts")) == "typescript"


def test_ext_routing_unknown_returns_none() -> None:
    """Vue/Svelte/Astro/MDX/etc are NOT supported at v2.0; explicit None."""
    from aidoctor.parsers import language_for_file
    assert language_for_file(Path("app.vue")) is None
    assert language_for_file(Path("page.svelte")) is None
    assert language_for_file(Path("doc.mdx")) is None


# --- Python comment extraction ---


def test_python_extracts_comments() -> None:
    from aidoctor.parsers._python import extract_comments
    src = "x = 1\n# NOTE: hi\ny = 2  # inline\n"
    comments = list(extract_comments(src))
    assert len(comments) == 2
    assert comments[0].line == 2
    assert comments[0].text == "NOTE: hi"
    assert comments[1].line == 3
    assert "inline" in comments[1].text


def test_python_skips_hash_inside_strings() -> None:
    """`#` in a string is NOT a comment."""
    from aidoctor.parsers._python import extract_comments
    src = 'x = "# not a comment"\n'
    assert list(extract_comments(src)) == []


# --- Rust comment extraction ---


def test_rust_extracts_line_comments() -> None:
    from aidoctor.parsers._tree_sitter import extract_comments, parse
    src = b"// NOTE: hi\nfn main() { let x = 1; } // inline\n"
    tree = parse(src, "rust")
    assert tree is not None
    comments = list(extract_comments(tree, src, "rust"))
    assert len(comments) == 2
    assert comments[0].line == 1
    assert "NOTE: hi" in comments[0].text
    assert comments[1].line == 2
    assert "inline" in comments[1].text


def test_rust_extracts_block_comments() -> None:
    from aidoctor.parsers._tree_sitter import extract_comments, parse
    src = b"/* multi\nline\ncomment */\nfn main() {}\n"
    tree = parse(src, "rust")
    assert tree is not None
    comments = list(extract_comments(tree, src, "rust"))
    assert len(comments) == 1
    assert "multi" in comments[0].text


def test_rust_skips_string_with_slashes() -> None:
    from aidoctor.parsers._tree_sitter import extract_comments, parse
    src = b'fn main() { let x = "// not a comment"; }\n'
    tree = parse(src, "rust")
    assert tree is not None
    comments = list(extract_comments(tree, src, "rust"))
    assert comments == []


# --- Go comment extraction ---


def test_go_extracts_comments() -> None:
    from aidoctor.parsers._tree_sitter import extract_comments, parse
    src = b"package main\n// NOTE: hi\nfunc main() {}\n"
    tree = parse(src, "go")
    assert tree is not None
    comments = list(extract_comments(tree, src, "go"))
    assert len(comments) == 1
    assert "NOTE: hi" in comments[0].text


# --- JavaScript comment extraction ---


def test_javascript_extracts_comments() -> None:
    from aidoctor.parsers._tree_sitter import extract_comments, parse
    src = b"// NOTE: hi\nconst x = 1;\n"
    tree = parse(src, "javascript")
    assert tree is not None
    comments = list(extract_comments(tree, src, "javascript"))
    assert len(comments) == 1
    assert "NOTE: hi" in comments[0].text


# --- TypeScript comment extraction ---


def test_typescript_extracts_comments() -> None:
    from aidoctor.parsers._tree_sitter import extract_comments, parse
    src = b"// NOTE: hi\nconst x: number = 1;\n"
    tree = parse(src, "typescript")
    assert tree is not None
    comments = list(extract_comments(tree, src, "typescript"))
    assert len(comments) == 1
    assert "NOTE: hi" in comments[0].text


def test_typescript_handles_tsx() -> None:
    """TSX uses the same typescript parser (per EXT_TO_LANGUAGE)."""
    from aidoctor.parsers._tree_sitter import extract_comments, parse
    src = b"// inline\nconst Greeting = (): JSX.Element => <div />;\n"
    tree = parse(src, "typescript")
    assert tree is not None
    # TSX-typed code without proper JSX support might fail to parse, but
    # comment extraction should still find the first line.
    comments = list(extract_comments(tree, src, "typescript"))
    assert len(comments) >= 1


# --- Graceful parse-error handling ---


def test_parse_failure_returns_none() -> None:
    """Garbage syntax shouldn't crash — parsers return a tree with errors
    but don't raise. (Or in extreme cases, fail gracefully.)"""
    from aidoctor.parsers._tree_sitter import parse
    src = b">>> not valid rust <<<"
    tree = parse(src, "rust")
    # Should still return a tree (possibly with error nodes), not None.
    # None is reserved for grammar-load failures.
    assert tree is not None
