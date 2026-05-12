"""Declarative JSONL rule engine.

Most aidoctor rules are pattern matchers — comment text, source unicode
category, AST call shapes. Those live in JSONL manifest files and run through
this engine. Complex flow-sensitive rules use the `python` escape hatch and
live in `rules_complex/`.

Public surface (called from scan.py at integration time):
    load_manifest(path)       -> list[Rule]
    apply_rule(rule, file)    -> list[Diagnostic]
    register_python_detector(id, fn)

Supported detect kinds at this phase:
    comment_regex             — regex against tokenized comments (not bytes)
    source_unicode_category   — unicode category match in source, skips string literals
    ast_call_with_kwarg       — match function call shape + optional kwarg/value
    python                    — dispatch to a registered callable
"""

from __future__ import annotations

import io
import json
import logging
import re
import tokenize
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from aidoctor.engine.error_renderer import ErrorContext, render_error
from aidoctor.rules._base import Category, Diagnostic, Severity

logger = logging.getLogger(__name__)


REQUIRED_FIELDS = ("id", "severity", "confidence", "category", "langs", "detect", "message", "help")


@dataclass(frozen=True, slots=True)
class Rule:
    """A declarative rule loaded from a JSONL manifest line.

    detect / fix are kept as raw dicts; dispatch on `detect["kind"]` at apply time.
    Stronger typing can come later (Pydantic / TypedDict) — for v1 we lean on tests.
    """
    id: str
    severity: str
    confidence: str
    category: str
    langs: tuple[str, ...]
    detect: dict[str, Any]
    message: str
    help: str
    fix: dict[str, Any] | None = None
    ref: str | None = None


_PYTHON_DETECTORS: dict[str, Callable[[Rule, Path, str], list[Diagnostic]]] = {}


def register_python_detector(
    rule_id: str, fn: Callable[[Rule, Path, str], list[Diagnostic]]
) -> None:
    """Register a python-kind detector. Called from rules_complex/ modules."""
    _PYTHON_DETECTORS[rule_id] = fn


def load_manifest(path: Path) -> list[Rule]:
    """Load a JSONL manifest file. Malformed lines warn and skip; the loader never crashes."""
    if not path.exists():
        raise FileNotFoundError(
            render_error(
                FileNotFoundError(str(path)),
                ErrorContext(
                    attempting="loading rule manifest",
                    file=path,
                    remediation="check the manifest path or run `aidoctor doctor`",
                ),
            )
        )

    rules: list[Rule] = []
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("manifest %s line %d: malformed JSON (%s); skipping", path, lineno, e)
                continue

            missing = [f for f in REQUIRED_FIELDS if f not in data]
            if missing:
                logger.warning(
                    "manifest %s line %d: rule %r missing fields %s; skipping",
                    path, lineno, data.get("id", "<no id>"), missing,
                )
                continue

            rules.append(
                Rule(
                    id=data["id"],
                    severity=data["severity"],
                    confidence=data["confidence"],
                    category=data["category"],
                    langs=tuple(data["langs"]),
                    detect=data["detect"],
                    fix=data.get("fix"),
                    ref=data.get("ref"),
                    message=data["message"],
                    help=data["help"],
                )
            )
    return rules


def apply_rule(rule: Rule, file: Path, source: str | None = None) -> list[Diagnostic]:
    """Apply a single rule to a single file. Returns zero or more diagnostics.

    Dispatches on `rule.detect["kind"]`. Unknown kinds raise ValueError —
    failing loud at apply time beats silent zero-finding at scan time.
    """
    if source is None:
        source = file.read_text(encoding="utf-8", errors="replace")

    kind = rule.detect.get("kind")
    if kind == "comment_regex":
        return _detect_comment_regex(rule, file, source)
    if kind == "source_unicode_category":
        return _detect_source_unicode_category(rule, file, source)
    if kind == "ast_call_with_kwarg":
        return _detect_ast_call_with_kwarg(rule, file, source)
    if kind == "python":
        fn_id = rule.detect.get("fn") or rule.id
        fn = _PYTHON_DETECTORS.get(fn_id)
        if fn is None:
            raise ValueError(
                f"rule {rule.id}: detect.kind=python but no detector registered for {fn_id!r}. "
                f"Register it via aidoctor.engine.declarative.register_python_detector()."
            )
        return fn(rule, file, source)
    raise ValueError(
        f"rule {rule.id}: unknown detect.kind {kind!r}. "
        f"Supported kinds: comment_regex, source_unicode_category, ast_call_with_kwarg, python."
    )


def _detect_comment_regex(rule: Rule, file: Path, source: str) -> list[Diagnostic]:
    """Match a regex against tokenized comments (not raw bytes).

    Token-based detection means '# NOTE: x' inside a string literal is NOT
    flagged — that's the whole point. Use the standard `tokenize` module so
    we get the same comment boundaries the Python parser sees.
    """
    pattern = re.compile(rule.detect["pattern"])
    diagnostics: list[Diagnostic] = []
    severity = Severity(rule.severity) if rule.severity in {"error", "warning"} else Severity.WARNING
    category = _category(rule.category)

    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type != tokenize.COMMENT:
                continue
            if pattern.search(tok.string):
                line, column = tok.start
                diagnostics.append(
                    Diagnostic(
                        rule_id=rule.id,
                        severity=severity,
                        category=category,
                        file=file,
                        line=line,
                        column=column,
                        message=rule.message,
                        help=rule.help,
                        url=rule.ref or "",
                    )
                )
    except tokenize.TokenizeError:
        return []

    return diagnostics


def _detect_source_unicode_category(
    rule: Rule, file: Path, source: str
) -> list[Diagnostic]:
    """Find Unicode chars in matching categories — skipping string literals.

    Token-based: walks Python tokens, ignores STRING and FSTRING_* tokens.
    Emojis in `print("✨")` are intentional UX content; emojis in comments,
    identifiers, or operators are AI fingerprints.
    """
    categories = set(rule.detect.get("categories", []))
    if not categories:
        return []
    severity = Severity(rule.severity) if rule.severity in {"error", "warning"} else Severity.WARNING
    category = _category(rule.category)

    # Token types whose content we should NOT scan (string literal contents are intentional).
    SKIP_TYPES = {tokenize.STRING}
    # f-string parts (3.12+); guard with getattr for older Pythons.
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        if hasattr(tokenize, name):
            SKIP_TYPES.add(getattr(tokenize, name))

    diagnostics: list[Diagnostic] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type in SKIP_TYPES:
                continue
            line, base_col = tok.start
            for offset, ch in enumerate(tok.string):
                if unicodedata.category(ch) in categories:
                    diagnostics.append(
                        Diagnostic(
                            rule_id=rule.id,
                            severity=severity,
                            category=category,
                            file=file,
                            line=line,
                            column=base_col + offset,
                            message=rule.message,
                            help=rule.help,
                            url=rule.ref or "",
                        )
                    )
    except tokenize.TokenizeError:
        return []
    return diagnostics


def _detect_ast_call_with_kwarg(
    rule: Rule, file: Path, source: str
) -> list[Diagnostic]:
    """Match a libcst Call node by function name (dotted or simple), optionally
    with a specific keyword argument and value.

    spec keys:
        function:  required. Dotted name like "subprocess.run" or simple "eval".
        kwarg:     optional. Name of the keyword argument to match.
        value:     optional. If present, the kwarg's value must match (literal compare).
                   When kwarg is given but value is absent, any kwarg presence matches.
    """
    import libcst as cst
    from libcst.metadata import PositionProvider

    spec = rule.detect
    target_func = spec.get("function", "")
    target_kwarg = spec.get("kwarg")
    target_value_present = "value" in spec
    target_value = spec.get("value")

    if not target_func:
        return []

    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return []

    wrapper = cst.MetadataWrapper(module)
    severity = Severity(rule.severity) if rule.severity in {"error", "warning"} else Severity.WARNING
    category = _category(rule.category)
    diagnostics: list[Diagnostic] = []

    class _Visitor(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)

        def visit_Call(self, node: cst.Call) -> None:
            if _func_name(node.func) != target_func:
                return
            if target_kwarg is None:
                _record(node)
                return
            for arg in node.args:
                if arg.keyword is None or arg.keyword.value != target_kwarg:
                    continue
                if not target_value_present:
                    _record(node)
                    return
                if _literal_matches(arg.value, target_value):
                    _record(node)
                    return

    def _record(node: cst.Call) -> None:
        pos = wrapper.resolve(PositionProvider)[node]
        diagnostics.append(
            Diagnostic(
                rule_id=rule.id,
                severity=severity,
                category=category,
                file=file,
                line=pos.start.line,
                column=pos.start.column,
                message=rule.message,
                help=rule.help,
                url=rule.ref or "",
            )
        )

    wrapper.visit(_Visitor())
    return diagnostics


def _func_name(node) -> str:
    """Render a libcst function expression as a dotted name. Returns '' if too complex."""
    import libcst as cst

    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        prefix = _func_name(node.value)
        return f"{prefix}.{node.attr.value}" if prefix else ""
    return ""


def _literal_matches(node, expected) -> bool:
    """Compare a libcst node's literal value to a Python value.

    Supports: True/False/None, int, float, str, list-of-literals.
    Returns False for non-literal expressions (variables, function calls, etc.).
    """
    import libcst as cst

    if isinstance(node, cst.Name):
        if node.value == "True":
            return expected is True
        if node.value == "False":
            return expected is False
        if node.value == "None":
            return expected is None
        return False
    if isinstance(node, cst.SimpleString):
        # Strip quotes — libcst keeps them
        return node.evaluated_value == expected if isinstance(expected, str) else False
    if isinstance(node, cst.Integer):
        return isinstance(expected, int) and not isinstance(expected, bool) and int(node.value) == expected
    if isinstance(node, cst.Float):
        return isinstance(expected, float) and float(node.value) == expected
    if isinstance(node, cst.List):
        if not isinstance(expected, list):
            return False
        if len(node.elements) != len(expected):
            return False
        return all(_literal_matches(el.value, ex) for el, ex in zip(node.elements, expected, strict=True))
    return False


def _category(name: str) -> Category:
    """Resolve a string category to the Category enum. Defaults to DECAY if unknown."""
    try:
        return Category(name)
    except ValueError:
        return Category.DECAY
