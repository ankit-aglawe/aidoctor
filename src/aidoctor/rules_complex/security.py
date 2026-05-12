"""OWASP-3 Python security rules — v1 syntactic-only.

These flag patterns where a non-constant value flows into a dangerous Python
sink. v1 has no taint analysis: a variable could still hold a hardcoded
literal assigned earlier, so the rule is intentionally syntactic. FP rate
is documented in HONESTY_AUDIT.md.

Rules registered here (severity=warning at v1; promotion to error gated on
FP-rate telemetry in v1.5):

    shell-true-with-variable          — subprocess.run(X, shell=True) where X is non-constant
    pickle-loads-on-non-constant      — pickle.loads(X) where X is non-constant
    eval-or-exec-on-non-constant      — eval(X) / exec(X) where X is non-constant
"""

from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.metadata import PositionProvider

from aidoctor.engine.declarative import register_python_detector
from aidoctor.rules._base import Category, Diagnostic, Severity

# Function names that accept a shell-style command + a `shell=True` kwarg.
_SUBPROCESS_FNS = {
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.Popen",
    "subprocess.getoutput",
    "subprocess.getstatusoutput",
}

# Functions whose first positional arg is the dangerous sink (pickle).
_PICKLE_FNS = {"pickle.loads", "pickle.load", "loads"}  # `loads` covers `from pickle import loads`

# eval/exec are bare builtins
_EVAL_EXEC_FNS = {"eval", "exec"}


def _func_name(node) -> str:
    """Render a libcst function expression as a dotted name. Returns '' if too complex."""
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        prefix = _func_name(node.value)
        return f"{prefix}.{node.attr.value}" if prefix else ""
    return ""


def _is_constant_literal(node) -> bool:
    """True if the libcst node is a compile-time literal.

    Covers: strings, bytes, ints, floats, bool, None, and tuples/lists of literals.
    A Name reference (even to a module-level constant) is NOT constant — we have
    no data-flow analysis at v1.
    """
    if isinstance(node, (cst.SimpleString, cst.FormattedString, cst.ConcatenatedString)):
        return True
    if isinstance(node, (cst.Integer, cst.Float, cst.Imaginary)):
        return True
    if isinstance(node, cst.Name) and node.value in ("True", "False", "None"):
        return True
    if isinstance(node, (cst.List, cst.Tuple, cst.Set)):
        return all(_is_constant_literal(el.value) for el in node.elements)
    if isinstance(node, cst.Dict):
        return all(
            isinstance(el, cst.DictElement)
            and _is_constant_literal(el.key)
            and _is_constant_literal(el.value)
            for el in node.elements
        )
    return False


def _emit(rule, file: Path, pos, severity=Severity.WARNING, category=Category.SECURITY) -> Diagnostic:
    return Diagnostic(
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


def _scan(file: Path, source: str, predicate, rule) -> list[Diagnostic]:
    """Walk every Call node, call `predicate(node)`; emit a Diagnostic where it returns True."""
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return []
    wrapper = cst.MetadataWrapper(module)
    diagnostics: list[Diagnostic] = []

    class _V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)

        def visit_Call(self, node: cst.Call) -> None:
            if predicate(node):
                diagnostics.append(_emit(rule, file, wrapper.resolve(PositionProvider)[node]))

    wrapper.visit(_V())
    return diagnostics


# --- detectors ---


def detect_shell_true(rule, file: Path, source: str) -> list[Diagnostic]:
    def predicate(node: cst.Call) -> bool:
        if _func_name(node.func) not in _SUBPROCESS_FNS:
            return False
        has_shell_true = any(
            arg.keyword is not None
            and arg.keyword.value == "shell"
            and isinstance(arg.value, cst.Name)
            and arg.value.value == "True"
            for arg in node.args
        )
        if not has_shell_true:
            return False
        first_positional = next((a for a in node.args if a.keyword is None), None)
        if first_positional is None:
            return False
        # Allowed: subprocess.run("hardcoded cmd", shell=True). Flagged otherwise.
        return not _is_constant_literal(first_positional.value)
    return _scan(file, source, predicate, rule)


def detect_pickle_loads_on_non_constant(rule, file: Path, source: str) -> list[Diagnostic]:
    def predicate(node: cst.Call) -> bool:
        if _func_name(node.func) not in _PICKLE_FNS:
            return False
        first_positional = next((a for a in node.args if a.keyword is None), None)
        if first_positional is None:
            return False
        return not _is_constant_literal(first_positional.value)
    return _scan(file, source, predicate, rule)


def detect_eval_or_exec_on_non_constant(rule, file: Path, source: str) -> list[Diagnostic]:
    def predicate(node: cst.Call) -> bool:
        if _func_name(node.func) not in _EVAL_EXEC_FNS:
            return False
        first_positional = next((a for a in node.args if a.keyword is None), None)
        if first_positional is None:
            return False
        return not _is_constant_literal(first_positional.value)
    return _scan(file, source, predicate, rule)


def register_all() -> None:
    """Register every detector in this module with the declarative engine.

    Idempotent — calling twice is harmless. Auto-called on module import so
    JSONL rules pointing to `detect.kind=python` find their callable in any
    worker process (multiprocess scan).
    """
    register_python_detector("shell-true-with-variable", detect_shell_true)
    register_python_detector("pickle-loads-on-non-constant", detect_pickle_loads_on_non_constant)
    register_python_detector("eval-or-exec-on-non-constant", detect_eval_or_exec_on_non_constant)


# Auto-register on import so multiprocess workers see the detectors.
register_all()
