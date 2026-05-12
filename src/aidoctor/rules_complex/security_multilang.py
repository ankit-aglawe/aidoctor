"""Per-language security rules using tree-sitter via the python escape hatch.

Each detector parses source via the appropriate tree-sitter grammar, walks
the parse tree, and emits Diagnostics. Registered with the declarative
engine under detect.kind = "python" with fn = "<rule-id>".

Rules (v2.0):
    rust-unsafe-without-safety-comment   — `unsafe { ... }` w/o `// SAFETY:` preceding
    go-weak-crypto                       — `crypto/md5`, `crypto/sha1` for password/auth
    go-sql-string-format                 — `db.Query(fmt.Sprintf(...))` SQL injection
    js-eval-on-variable                  — `eval(x)` where x is not a constant string
    react-dangerously-set-inner-html     — `dangerouslySetInnerHTML={...}` without sanitizer
"""

from __future__ import annotations

from pathlib import Path

from aidoctor.engine.declarative import register_python_detector
from aidoctor.parsers import _tree_sitter as ts
from aidoctor.rules._base import Category, Diagnostic, Severity


def _emit(rule, file: Path, line: int, col: int, severity=Severity.WARNING) -> Diagnostic:
    return Diagnostic(
        rule_id=rule.id,
        severity=severity,
        category=Category.SECURITY,
        file=file,
        line=line,
        column=col,
        message=rule.message,
        help=rule.help,
        url=rule.ref or "",
    )


# --- Rust: unsafe without // SAFETY: comment ---


def detect_rust_unsafe_without_safety(rule, file: Path, source: str) -> list[Diagnostic]:
    """Flag `unsafe { ... }` blocks not preceded by a `// SAFETY:` comment.

    Mirrors clippy::undocumented_unsafe_blocks. Very low FP rate: legitimate
    unsafe code always has a SAFETY comment justifying it.
    """
    src_bytes = source.encode("utf-8", errors="replace")
    tree = ts.parse(src_bytes, "rust")
    if tree is None:
        return []
    diagnostics: list[Diagnostic] = []
    lines = source.splitlines()

    # DFS for unsafe_block nodes
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "unsafe_block":
            line = node.start_point[0] + 1
            col = node.start_point[1]
            # Check the previous line for a SAFETY comment
            prev_line_idx = line - 2  # 0-indexed previous line
            has_safety = False
            for i in range(max(0, prev_line_idx - 2), prev_line_idx + 1):
                if i < len(lines) and "SAFETY:" in lines[i]:
                    has_safety = True
                    break
            if not has_safety:
                diagnostics.append(_emit(rule, file, line, col))
        for child in reversed(node.children):
            stack.append(child)
    return diagnostics


# --- Go: weak crypto (md5/sha1 for password/auth/secret contexts) ---


def detect_go_weak_crypto(rule, file: Path, source: str) -> list[Diagnostic]:
    """Flag `crypto/md5` or `crypto/sha1` imports in files that also reference
    password/token/secret/auth identifiers — gosec G401-like."""
    src_bytes = source.encode("utf-8", errors="replace")
    tree = ts.parse(src_bytes, "go")
    if tree is None:
        return []
    import re

    has_weak_import = bool(re.search(r'"crypto/(md5|sha1)"', source))
    has_auth_context = bool(re.search(r"(?i)\b(password|passwd|secret|token|auth|session|nonce)\b", source))
    if not (has_weak_import and has_auth_context):
        return []
    # Find the import line for the message location
    for i, line in enumerate(source.splitlines(), 1):
        m = re.search(r'"crypto/(md5|sha1)"', line)
        if m:
            return [_emit(rule, file, i, line.index(m.group(0)))]
    return []


# --- Go: SQL string-format injection ---


def detect_go_sql_string_format(rule, file: Path, source: str) -> list[Diagnostic]:
    """Flag `db.Query/Exec(fmt.Sprintf(...))` or string-concat SQL. gosec G201/G202."""
    src_bytes = source.encode("utf-8", errors="replace")
    tree = ts.parse(src_bytes, "go")
    if tree is None:
        return []
    import re

    diagnostics: list[Diagnostic] = []
    for i, line in enumerate(source.splitlines(), 1):
        # Pattern 1: db.Query(fmt.Sprintf(...))
        if re.search(r"\.(Query|Exec|QueryRow)\w*\(\s*fmt\.(Sprintf|Sprint)\b", line):
            diagnostics.append(_emit(rule, file, i, 0, severity=Severity.WARNING))
            continue
        # Pattern 2: db.Query("..." + ...)
        if re.search(r"\.(Query|Exec|QueryRow)\w*\([^)]*\+\s*\w", line):
            diagnostics.append(_emit(rule, file, i, 0, severity=Severity.WARNING))
    return diagnostics


# --- JS/TS: eval on non-constant ---


def detect_js_eval_on_variable(rule, file: Path, source: str) -> list[Diagnostic]:
    """Flag `eval(<non-string-literal>)` and `new Function(<non-literal>)`.

    Conservative: only fire when the first arg is NOT a string literal token.
    """
    target_lang = "typescript" if file.suffix in (".ts", ".tsx", ".d.ts") else "javascript"
    src_bytes = source.encode("utf-8", errors="replace")
    tree = ts.parse(src_bytes, target_lang)
    if tree is None:
        return []
    diagnostics: list[Diagnostic] = []

    def _walk(node):
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            args = node.child_by_field_name("arguments")
            if func is not None and args is not None:
                fn_name = src_bytes[func.start_byte:func.end_byte].decode("utf-8", errors="replace")
                if fn_name in ("eval", "Function"):
                    # Check first arg
                    arg_nodes = [c for c in args.named_children]
                    if arg_nodes and arg_nodes[0].type != "string":
                        diagnostics.append(_emit(rule, file, node.start_point[0] + 1, node.start_point[1]))
        for child in node.children:
            _walk(child)

    _walk(tree.root_node)
    return diagnostics


# --- React: dangerouslySetInnerHTML without sanitizer call nearby ---


def detect_react_dangerously_set_inner_html(rule, file: Path, source: str) -> list[Diagnostic]:
    """Flag JSX attribute `dangerouslySetInnerHTML={...}` (in .tsx/.jsx).

    Conservative v1: fires on every use. Suppress with sanitizer-named import
    (DOMPurify / sanitize-html) present in same file.
    """
    if file.suffix not in (".jsx", ".tsx"):
        return []
    import re

    if not re.search(r"dangerouslySetInnerHTML", source):
        return []
    has_sanitizer = bool(re.search(r"(DOMPurify|sanitize[-_]?html|sanitizer)", source))
    if has_sanitizer:
        return []
    diagnostics: list[Diagnostic] = []
    for i, line in enumerate(source.splitlines(), 1):
        if "dangerouslySetInnerHTML" in line:
            diagnostics.append(_emit(rule, file, i, line.index("dangerouslySetInnerHTML")))
    return diagnostics


def register_all() -> None:
    """Register every multi-lang security detector. Auto-called on import."""
    register_python_detector("rust-unsafe-without-safety-comment", detect_rust_unsafe_without_safety)
    register_python_detector("go-weak-crypto", detect_go_weak_crypto)
    register_python_detector("go-sql-string-format", detect_go_sql_string_format)
    register_python_detector("js-eval-on-variable", detect_js_eval_on_variable)
    register_python_detector("react-dangerously-set-inner-html", detect_react_dangerously_set_inner_html)


register_all()
