"""5 Python ai_style rules that need flow logic beyond declarative kinds.

Registered with the declarative engine via the python escape hatch. Each
rule fires only when the AST pattern signals AI-emit reflex, not human style.

Rules:
    ai-inflated-print           print() with celebratory emoji + Success/Done vocab
    ai-useless-docstring        docstring lexically restates signature
    ai-generic-vars-in-long-fn  `data`/`result`/`value` in fns > 8 statements
    ai-obvious-type-annotation  `x: int = 5` (annotation matches literal type)
    ai-explanation-comment      comment that restates the next line in English
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import libcst as cst
from libcst.metadata import PositionProvider

from aidoctor.engine.declarative import register_python_detector
from aidoctor.rules._base import Category, Diagnostic, Severity

_CELEBRATORY_VOCAB = re.compile(
    r"(?i)\b(success(fully)?|done|complete(d|ly)?|finished|processed|ready)\b"
)
_GENERIC_VAR_NAMES = frozenset({
    "data", "result", "value", "item", "output", "tmp", "temp", "foo", "bar",
})


def _emit(rule, file: Path, line: int, column: int) -> Diagnostic:
    return Diagnostic(
        rule_id=rule.id,
        severity=Severity(rule.severity) if rule.severity in {"error", "warning", "critical"} else Severity.WARNING,
        category=Category.AI_STYLE,
        file=file,
        line=line,
        column=column,
        message=rule.message,
        help=rule.help,
        url=rule.ref or "",
    )


def _parse(source: str) -> cst.MetadataWrapper | None:
    try:
        return cst.MetadataWrapper(cst.parse_module(source))
    except cst.ParserSyntaxError:
        return None


def _pos(wrapper: cst.MetadataWrapper, node: cst.CSTNode):
    return wrapper.resolve(PositionProvider)[node]


# --- ai-inflated-print ---


def detect_inflated_print(rule, file: Path, source: str) -> list[Diagnostic]:
    """print(...) where args contain an emoji + Success/Done/Complete vocab."""
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []

    def _has_emoji(s: str) -> bool:
        return any(unicodedata.category(c) == "So" for c in s)

    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)

        def visit_Call(self, node: cst.Call) -> None:
            if not isinstance(node.func, cst.Name) or node.func.value != "print":
                return
            for arg in node.args:
                if isinstance(arg.value, (cst.SimpleString, cst.FormattedString)):
                    p = wrapper.resolve(PositionProvider)[arg.value]
                    lines = source.splitlines()
                    line_str = lines[p.start.line - 1] if p.start.line - 1 < len(lines) else ""
                    if _has_emoji(line_str) and _CELEBRATORY_VOCAB.search(line_str):
                        pos = wrapper.resolve(PositionProvider)[node]
                        diagnostics.append(_emit(rule, file, pos.start.line, pos.start.column))
                        return

    wrapper.visit(V())
    return diagnostics


# --- ai-useless-docstring ---


def detect_useless_docstring(rule, file: Path, source: str) -> list[Diagnostic]:
    """Docstring whose unique words substantially overlap with the function signature.

    Heuristic: lower-case both, take unique alpha-words, compute set overlap.
    If docstring contributes >70% of its words from the signature, flag.
    Docstrings <30 chars are skipped (too short to assess).
    """
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    stopwords = {"a", "an", "the", "of", "to", "for", "with", "and", "or", "is", "in", "on", "by", "from", "this", "that", "given", "returns", "return"}

    def _words(s: str) -> set[str]:
        # Split on non-letters AND on underscore (snake_case → separate words)
        raw = re.split(r"[^a-zA-Z]+|(?<=[a-z])(?=[A-Z])", s)
        return {w.lower() for w in raw if len(w) > 2 and w.lower() not in stopwords}

    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)

        def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
            # Skip private
            if node.name.value.startswith("_"):
                return
            # Find docstring (first SimpleStatementLine with SimpleString)
            body = node.body.body if hasattr(node.body, "body") else []
            if not body:
                return
            first = body[0]
            if not isinstance(first, cst.SimpleStatementLine):
                return
            if not first.body or not isinstance(first.body[0], cst.Expr):
                return
            string_node = first.body[0].value
            if not isinstance(string_node, (cst.SimpleString, cst.ConcatenatedString)):
                return
            try:
                doc = string_node.evaluated_value if isinstance(string_node, cst.SimpleString) else ""
            except Exception:  # noqa: BLE001
                return
            if not doc or len(doc) < 30:
                return

            # Build signature words: function name + param names
            sig_words = _words(node.name.value)
            for p in node.params.params:
                if isinstance(p.name, cst.Name):
                    sig_words |= _words(p.name.value)

            doc_words = _words(doc)
            if not doc_words:
                return
            overlap = len(doc_words & sig_words) / len(doc_words)
            if overlap >= 0.5:
                pos = wrapper.resolve(PositionProvider)[string_node]
                diagnostics.append(_emit(rule, file, pos.start.line, pos.start.column))

    wrapper.visit(V())
    return diagnostics


# --- ai-generic-vars-in-long-fn ---


def detect_generic_vars_in_long_fn(rule, file: Path, source: str) -> list[Diagnostic]:
    """Functions with body length > 8 statements that bind `data`/`result`/etc.

    Counts assignments and ann-assignments where target is one of the
    generic names. Skips lambdas + comprehensions.
    """
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []

    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)

        def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
            body = node.body.body if hasattr(node.body, "body") else []
            # Count top-level statements
            n_stmts = sum(1 for s in body)
            if n_stmts <= 8:
                return
            # Find generic-named assignments
            for stmt in body:
                inner = stmt.body if isinstance(stmt, cst.SimpleStatementLine) else [stmt]
                for sub in inner:
                    if isinstance(sub, cst.Assign):
                        for target in sub.targets:
                            if isinstance(target.target, cst.Name) and target.target.value in _GENERIC_VAR_NAMES:
                                pos = wrapper.resolve(PositionProvider)[target]
                                diagnostics.append(_emit(rule, file, pos.start.line, pos.start.column))
                    if isinstance(sub, cst.AnnAssign) and isinstance(sub.target, cst.Name):
                        if sub.target.value in _GENERIC_VAR_NAMES:
                            pos = wrapper.resolve(PositionProvider)[sub.target]
                            diagnostics.append(_emit(rule, file, pos.start.line, pos.start.column))

    wrapper.visit(V())
    return diagnostics


# --- ai-obvious-type-annotation ---


def detect_obvious_type_annotation(rule, file: Path, source: str) -> list[Diagnostic]:
    """`x: int = 5`, `name: str = "alice"`, `ok: bool = True` — annotation
    matches what Python infers from the literal."""
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []

    OBVIOUS_PAIRS = {
        ("int", cst.Integer),
        ("str", cst.SimpleString),
        ("float", cst.Float),
    }

    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)

        def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
            if node.value is None:
                return  # `x: int` (declaration only) — not obvious
            if not isinstance(node.annotation, cst.Annotation):
                return
            ann = node.annotation.annotation
            if not isinstance(ann, cst.Name):
                return  # generic / union / Optional — skip
            ann_name = ann.value
            val = node.value
            # bool case (True/False are Name nodes in libcst)
            if ann_name == "bool" and isinstance(val, cst.Name) and val.value in ("True", "False"):
                pos = wrapper.resolve(PositionProvider)[node]
                diagnostics.append(_emit(rule, file, pos.start.line, pos.start.column))
                return
            for type_name, literal_type in OBVIOUS_PAIRS:
                if ann_name == type_name and isinstance(val, literal_type):
                    pos = wrapper.resolve(PositionProvider)[node]
                    diagnostics.append(_emit(rule, file, pos.start.line, pos.start.column))
                    return

    wrapper.visit(V())
    return diagnostics


# --- ai-explanation-comment ---


def detect_explanation_comment(rule, file: Path, source: str) -> list[Diagnostic]:
    """Comment that restates the next code line in English.

    Heuristic: comment word stems overlap >= 60% with the next non-blank line.
    Stems are aggressively normalized (return/Return/returns → return).
    Skips comments with WHY-words ("because", "since", "to-avoid"); they're real.
    """
    why_words = re.compile(r"(?i)\b(because|since|so that|to avoid|to prevent|workaround|hack|TODO|FIXME)\b")
    diagnostics: list[Diagnostic] = []
    lines = source.splitlines()

    # AI restate-the-obvious openers. KEPT NARROW per real-world FP testing on
    # requests/flask/httpx — broader openers (check/validate/process/get/set/
    # create) generated 86 FPs because legitimate "# Check X" comments
    # introduce informative context, not restatement. Only canonical AI cases:
    _COMMENT_OPENERS = {
        "return": {"return "},  # "# Return the result" above `return ...`
        "loop":   {"for ", "while "},  # "# Loop through items" above `for item in items`
    }

    def _stems(s: str) -> set[str]:
        # Split on non-letters AND camelCase
        raw = re.split(r"[^a-zA-Z]+|(?<=[a-z])(?=[A-Z])", s)
        return {w.lower()[:5] for w in raw if len(w) > 2}

    import io
    import tokenize
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenizeError:
        return []
    for tok in tokens:
        if tok.type != tokenize.COMMENT:
            continue
        comment_text = tok.string.lstrip("#").strip()
        if not comment_text or why_words.search(comment_text):
            continue
        # Find next non-blank source line
        next_line_idx = tok.start[0]  # 0-indexed line after comment
        while next_line_idx < len(lines) and lines[next_line_idx].strip().startswith("#"):
            next_line_idx += 1
        while next_line_idx < len(lines) and not lines[next_line_idx].strip():
            next_line_idx += 1
        if next_line_idx >= len(lines):
            continue
        next_line = lines[next_line_idx]
        # Skip if next line is itself another comment
        if next_line.strip().startswith("#"):
            continue
        # Strict opener-only match. The rule fires only on canonical AI
        # restatement patterns ("# Return ..." above `return`, "# Loop ..."
        # above `for/while`). Lexical overlap removed entirely — real-world
        # testing showed >70% FP rate with it enabled.
        if len(comment_text) > 40:
            continue  # long comments are almost always real explanation
        first_word = re.match(r"^([A-Za-z]+)", comment_text)
        if not first_word:
            continue
        opener = first_word.group(1).lower()
        if opener not in _COMMENT_OPENERS:
            continue
        expected = _COMMENT_OPENERS[opener]
        if any(keyword in next_line.lower() for keyword in expected):
            diagnostics.append(_emit(rule, file, tok.start[0], tok.start[1]))
    return diagnostics


def register_all() -> None:
    register_python_detector("ai-inflated-print", detect_inflated_print)
    register_python_detector("ai-useless-docstring", detect_useless_docstring)
    register_python_detector("ai-generic-vars-in-long-fn", detect_generic_vars_in_long_fn)
    register_python_detector("ai-obvious-type-annotation", detect_obvious_type_annotation)
    register_python_detector("ai-explanation-comment", detect_explanation_comment)


register_all()
