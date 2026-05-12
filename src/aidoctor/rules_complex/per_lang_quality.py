"""New HIGH-confidence rules for Rust, Go, JS/TS, React from research INVENTORY.

Each rule is backed by a canonical lint (clippy/gosec/eslint/typescript-eslint).
Registered via the python escape hatch using tree-sitter parsers.
"""

from __future__ import annotations

import re
from pathlib import Path

from aidoctor.engine.declarative import register_python_detector
from aidoctor.parsers import _tree_sitter as ts
from aidoctor.rules._base import Category, Diagnostic, Severity


def _emit(rule, file: Path, line: int, column: int,
          category=Category.DEAD_DEFENSES, severity=None) -> Diagnostic:
    sev = severity or (Severity(rule.severity) if rule.severity in {"error", "warning", "critical"} else Severity.WARNING)
    return Diagnostic(
        rule_id=rule.id, severity=sev, category=category,
        file=file, line=line, column=column,
        message=rule.message, help=rule.help, url=rule.ref or "",
    )


def _walk_ts(tree):
    """DFS iterator over tree-sitter nodes."""
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        yield node
        for c in reversed(node.children):
            stack.append(c)


# ====== RUST ======


def detect_rust_let_underscore_on_result(rule, file: Path, source: str) -> list[Diagnostic]:
    """`let _ = X` where X is a function call that likely returns Result."""
    src_b = source.encode("utf-8", errors="replace")
    tree = ts.parse(src_b, "rust")
    if tree is None:
        return []
    diagnostics: list[Diagnostic] = []
    for node in _walk_ts(tree):
        # let_declaration with pattern == `_` and a value that's a call expression
        if node.type == "let_declaration":
            pattern = node.child_by_field_name("pattern")
            value = node.child_by_field_name("value")
            if pattern is None or value is None:
                continue
            pat_text = src_b[pattern.start_byte:pattern.end_byte].decode("utf-8", errors="replace")
            if pat_text.strip() != "_":
                continue
            # Heuristic: value is a call_expression (likely Result-returning).
            # Allow with `// IGNORED:` comment on the line above as suppression.
            line_idx = node.start_point[0]
            lines = source.splitlines()
            if line_idx > 0 and "IGNORED:" in lines[line_idx - 1]:
                continue
            if value.type in ("call_expression", "macro_invocation", "try_expression"):
                diagnostics.append(_emit(rule, file, node.start_point[0] + 1, node.start_point[1]))
    return diagnostics


def detect_rust_box_dyn_error_in_library(rule, file: Path, source: str) -> list[Diagnostic]:
    """`pub fn ... -> Result<T, Box<dyn Error...>>` in a lib crate."""
    # Heuristic — pure regex over source. lib detection: file under src/lib.rs or has pub fn.
    if file.name == "main.rs" or "/bin/" in str(file):
        return []
    diagnostics: list[Diagnostic] = []
    pattern = re.compile(r"\bpub\s+(async\s+)?fn\s+\w+[\s\S]{0,200}?->\s*Result<[^,]+,\s*Box<\s*dyn\s+(std::error::Error|Error)")
    for m in pattern.finditer(source):
        line_no = source[:m.start()].count("\n") + 1
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


# ====== GO ======


def detect_go_defer_in_loop(rule, file: Path, source: str) -> list[Diagnostic]:
    """`defer X()` inside a for/range loop body."""
    src_b = source.encode("utf-8", errors="replace")
    tree = ts.parse(src_b, "go")
    if tree is None:
        return []
    diagnostics: list[Diagnostic] = []
    for node in _walk_ts(tree):
        if node.type in ("for_statement",):
            for inner in _walk_ts_subtree(node):
                if inner.type == "defer_statement":
                    diagnostics.append(_emit(rule, file, inner.start_point[0] + 1, inner.start_point[1]))
                    break  # only flag once per for-loop
    return diagnostics


def _walk_ts_subtree(root):
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        for c in reversed(node.children):
            stack.append(c)


def detect_go_defer_before_err_check(rule, file: Path, source: str) -> list[Diagnostic]:
    """`resp, err := X(); defer resp.Body.Close(); if err != nil {...}` — nil-deref."""
    # Pure regex heuristic — looks for `defer ` followed within 3 lines by `if err`
    diagnostics: list[Diagnostic] = []
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"^\s*defer\s+\w+\.\w+(\.\w+)*\(\)", line):
            # Check next 3 lines for `if err != nil`
            ahead = "\n".join(lines[i + 1:i + 4])
            if re.search(r"\bif\s+err\s*!=\s*nil\b", ahead):
                diagnostics.append(_emit(rule, file, i + 1, 0))
    return diagnostics


def detect_go_http_body_not_closed(rule, file: Path, source: str) -> list[Diagnostic]:
    """`http.Get/Do` result `resp` without `defer resp.Body.Close()` in same function."""
    src_b = source.encode("utf-8", errors="replace")
    tree = ts.parse(src_b, "go")
    if tree is None:
        return []
    diagnostics: list[Diagnostic] = []
    # Simpler regex: look for http.Get/Post/Do without defer resp.Body.Close in same file
    # (function-scope analysis would be cleaner but is heavier)
    if not re.search(r"\bhttp\.(Get|Post|Head|Do|PostForm)\b", source):
        return []
    if "defer" in source and "Body.Close" in source:
        return []  # body close present somewhere — accept
    # Find the line of http.X call
    for i, line in enumerate(source.splitlines(), 1):
        if re.search(r"\bhttp\.(Get|Post|Head|Do|PostForm)\(", line):
            diagnostics.append(_emit(rule, file, i, 0))
            return diagnostics  # one finding per file
    return []


def detect_go_fmt_errorf_verb_v(rule, file: Path, source: str) -> list[Diagnostic]:
    """`fmt.Errorf("...: %v", err)` — should use `%w` for wrapping."""
    diagnostics: list[Diagnostic] = []
    pattern = re.compile(r'fmt\.Errorf\([^)]*%v[^)]*,\s*\w+(\.\w+)*\s*\)')
    for m in pattern.finditer(source):
        line_no = source[:m.start()].count("\n") + 1
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


def detect_go_context_background_midchain(rule, file: Path, source: str) -> list[Diagnostic]:
    """`context.Background()` called in non-main, non-init, non-test functions."""
    src_b = source.encode("utf-8", errors="replace")
    tree = ts.parse(src_b, "go")
    if tree is None:
        return []
    if file.name.endswith("_test.go"):
        return []
    diagnostics: list[Diagnostic] = []
    # Find function_declarations not named main/init, walk for context.Background calls
    for node in _walk_ts(tree):
        if node.type != "function_declaration":
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None:
            continue
        name = src_b[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
        if name in ("main", "init"):
            continue
        # Walk function body for context.Background()
        body = node.child_by_field_name("body")
        if body is None:
            continue
        for inner in _walk_ts_subtree(body):
            if inner.type == "call_expression":
                fn = inner.child_by_field_name("function")
                if fn is None:
                    continue
                fn_text = src_b[fn.start_byte:fn.end_byte].decode("utf-8", errors="replace")
                if fn_text == "context.Background":
                    diagnostics.append(_emit(rule, file, inner.start_point[0] + 1, inner.start_point[1]))
                    break  # one per function
    return diagnostics


# ====== JS / TS ======


def detect_ts_async_array_method(rule, file: Path, source: str) -> list[Diagnostic]:
    """`arr.forEach(async ...)` / `.map(async ...)` discarded promise."""
    diagnostics: list[Diagnostic] = []
    # forEach/map/filter with async arrow callback. Accepts `async u =>`,
    # `async (u, i) =>`, or `async function (...)` callbacks.
    pattern = re.compile(r"\.(forEach|map|filter|find|some|every|reduce)\(\s*async\b[^=)]*=>")
    for m in pattern.finditer(source):
        line_no = source[:m.start()].count("\n") + 1
        # Skip if result is awaited / Promise.all'd (heuristic: prev 50 chars contain "Promise.all" or "await")
        prefix = source[max(0, m.start() - 80):m.start()]
        if "Promise.all" in prefix or "await " in prefix:
            continue
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


def detect_ts_async_condition(rule, file: Path, source: str) -> list[Diagnostic]:
    """`if (promiseReturningFn())` — Promise truthy, always passes."""
    # Heuristic regex: `if (someFn(...))` where the name starts with `is`/`has`/`exists`/`check`/`fetch`/`load`/`get`
    diagnostics: list[Diagnostic] = []
    pattern = re.compile(r"\bif\s*\(\s*(is|has|exists|check|fetch|load|get)\w*\([^)]*\)\s*\)")
    for m in pattern.finditer(source):
        # Skip if `await ` is in the if condition
        if "await " in source[m.start():m.end()]:
            continue
        line_no = source[:m.start()].count("\n") + 1
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


def detect_ts_return_promise_any(rule, file: Path, source: str) -> list[Diagnostic]:
    """`Promise<any>` on async function return type."""
    if file.suffix not in (".ts", ".tsx", ".d.ts"):
        return []
    diagnostics: list[Diagnostic] = []
    pattern = re.compile(r":\s*Promise\s*<\s*any\s*>")
    for m in pattern.finditer(source):
        line_no = source[:m.start()].count("\n") + 1
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


def detect_js_zero_runtime_validation(rule, file: Path, source: str) -> list[Diagnostic]:
    """`as SomeType` cast on req.body / fetch().json() — type assertion without validation."""
    diagnostics: list[Diagnostic] = []
    if not re.search(r"\b(req\.body|req\.query|req\.params|response\.json\(\)|fetch\([^)]*\)\.json\(\))", source):
        return []
    # Look for `as TypeName` near those expressions
    pattern = re.compile(r"(req\.(body|query|params)|\.json\(\))\s*(?:as\s+\w+|\s+as\s+\w+)")
    for m in pattern.finditer(source):
        line_no = source[:m.start()].count("\n") + 1
        # Skip if zod/valibot/arktype is imported in the same file (means they're validating elsewhere)
        if re.search(r"from\s+['\"](?:zod|valibot|arktype|yup|joi)['\"]", source):
            continue
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


# ====== REACT ======


def detect_react_onclick_invocation(rule, file: Path, source: str) -> list[Diagnostic]:
    """`onClick={fn()}` invoked at render time (vs `onClick={fn}` or arrow)."""
    if file.suffix not in (".jsx", ".tsx"):
        return []
    diagnostics: list[Diagnostic] = []
    # Match onClick={X(...)} where X is a bare identifier (not arrow function)
    pattern = re.compile(r"\bonClick\s*=\s*\{\s*(\w+)\s*\([^{]*\)\s*\}")
    for m in pattern.finditer(source):
        # Skip if it's a known helper pattern (e.g. arrow factory)
        line_no = source[:m.start()].count("\n") + 1
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


def detect_react_state_any(rule, file: Path, source: str) -> list[Diagnostic]:
    """`useState<any>(...)` or `useState([])` with no type."""
    if file.suffix not in (".jsx", ".tsx"):
        return []
    diagnostics: list[Diagnostic] = []
    # useState<any> explicitly
    for m in re.finditer(r"\buseState\s*<\s*any\s*>", source):
        line_no = source[:m.start()].count("\n") + 1
        diagnostics.append(_emit(rule, file, line_no, 0))
    # useState([]) — implicit never[]
    for m in re.finditer(r"\buseState\s*\(\s*\[\s*\]\s*\)", source):
        line_no = source[:m.start()].count("\n") + 1
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


def detect_react_conditional_hook(rule, file: Path, source: str) -> list[Diagnostic]:
    """Hook call inside if/for/return — rules-of-hooks violation."""
    if file.suffix not in (".jsx", ".tsx"):
        return []
    diagnostics: list[Diagnostic] = []
    lines = source.splitlines()
    in_conditional = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Track conditional/loop blocks by indentation+keyword
        if re.match(r"^\s*(if|else if|for|while|switch)\b", line):
            in_conditional += 1
        if in_conditional > 0 and re.search(r"\buse[A-Z]\w+\s*\(", line):
            # Likely a hook call inside a conditional block (heuristic; tree-sitter would be better)
            diagnostics.append(_emit(rule, file, i + 1, 0))
        # Crude scope tracking via brace balance — assume single-level conditionals
        if stripped.endswith("}"):
            in_conditional = max(0, in_conditional - 1)
    return diagnostics


def detect_react_async_client_component(rule, file: Path, source: str) -> list[Diagnostic]:
    """`async function X()` in a file with `"use client"` — Next.js client-component conflict."""
    if file.suffix not in (".tsx", ".jsx"):
        return []
    if not re.search(r"^[\"']use client[\"']", source, re.MULTILINE):
        return []
    diagnostics: list[Diagnostic] = []
    for m in re.finditer(r"^\s*(export\s+(default\s+)?)?async\s+function\s+\w+", source, re.MULTILINE):
        line_no = source[:m.start()].count("\n") + 1
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


def detect_react_effect_as_event_handler(rule, file: Path, source: str) -> list[Diagnostic]:
    """`useEffect` body that's just a fetch/POST inside an `if (submitted)`-like guard."""
    if file.suffix not in (".jsx", ".tsx"):
        return []
    diagnostics: list[Diagnostic] = []
    # Heuristic: useEffect with `if (X)` where X is a boolean state, AND the deps array is [X]
    pattern = re.compile(
        r"useEffect\(\s*\(\)\s*=>\s*\{[^}]*?if\s*\(\s*(\w+)\s*\)\s*\{[^}]*?(fetch|axios|api\.)\b[^}]*?\}[^}]*?\}\s*,\s*\[\s*\1\s*\]\s*\)",
        re.DOTALL,
    )
    for m in pattern.finditer(source):
        line_no = source[:m.start()].count("\n") + 1
        diagnostics.append(_emit(rule, file, line_no, 0))
    return diagnostics


def detect_react_server_client_mixed(rule, file: Path, source: str) -> list[Diagnostic]:
    """Importing client-only hooks/handlers without `"use client"` directive (Next.js)."""
    if file.suffix not in (".tsx", ".jsx"):
        return []
    # File must be under `app/` directory to apply Next.js app router rules
    path_str = str(file).lower()
    if "/app/" not in path_str and "\\app\\" not in path_str:
        return []
    has_use_client = bool(re.search(r"^[\"']use client[\"']", source, re.MULTILINE))
    if has_use_client:
        return []
    has_client_api = bool(re.search(r"\b(useState|useEffect|useReducer|useContext|onClick|onChange|onSubmit)\b", source))
    if not has_client_api:
        return []
    # Fire at line 1 (file-level finding)
    return [_emit(rule, file, 1, 0)]


def register_all() -> None:
    # Rust
    register_python_detector("rust-let-underscore-on-result", detect_rust_let_underscore_on_result)
    register_python_detector("rust-box-dyn-error-in-library", detect_rust_box_dyn_error_in_library)
    # Go
    register_python_detector("go-defer-in-loop", detect_go_defer_in_loop)
    register_python_detector("go-defer-before-err-check", detect_go_defer_before_err_check)
    register_python_detector("go-http-body-not-closed", detect_go_http_body_not_closed)
    register_python_detector("go-fmt-errorf-verb-v", detect_go_fmt_errorf_verb_v)
    register_python_detector("go-context-background-midchain", detect_go_context_background_midchain)
    # JS/TS
    register_python_detector("ts-async-array-method", detect_ts_async_array_method)
    register_python_detector("ts-async-condition", detect_ts_async_condition)
    register_python_detector("ts-return-promise-any", detect_ts_return_promise_any)
    register_python_detector("js-zero-runtime-validation", detect_js_zero_runtime_validation)
    # React
    register_python_detector("react-onclick-invocation", detect_react_onclick_invocation)
    register_python_detector("react-state-any", detect_react_state_any)
    register_python_detector("react-conditional-hook", detect_react_conditional_hook)
    register_python_detector("react-async-client-component", detect_react_async_client_component)
    register_python_detector("react-effect-as-event-handler", detect_react_effect_as_event_handler)
    register_python_detector("react-server-client-mixed", detect_react_server_client_mixed)


register_all()
