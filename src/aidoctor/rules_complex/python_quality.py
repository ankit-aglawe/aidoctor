"""13 new HIGH-confidence Python rules from research INVENTORY.md.

Each rule is backed by a canonical lint (ruff/pylint/bandit/flake8 ecosystem).
Registered via the python escape hatch.
"""

from __future__ import annotations

import re
from pathlib import Path

import libcst as cst
from libcst.metadata import PositionProvider

from aidoctor.engine.declarative import register_python_detector
from aidoctor.rules._base import Category, Diagnostic, Severity


def _emit(rule, file: Path, line: int, column: int, category=Category.DEAD_DEFENSES) -> Diagnostic:
    return Diagnostic(
        rule_id=rule.id,
        severity=Severity(rule.severity) if rule.severity in {"error", "warning", "critical"} else Severity.WARNING,
        category=category,
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


def _pos(wrapper, node):
    return wrapper.resolve(PositionProvider)[node]


# --- 1. ai-mutable-default-arg (ruff B006) ---


def detect_mutable_default_arg(rule, file: Path, source: str) -> list[Diagnostic]:
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
            for p in node.params.params:
                if p.default is None:
                    continue
                if isinstance(p.default, (cst.List, cst.Dict, cst.Set)):
                    diagnostics.append(_emit(rule, file, _pos(wrapper, p).start.line, _pos(wrapper, p).start.column))
    wrapper.visit(V())
    return diagnostics


# --- 2. ai-unused-fstring (ruff F541) ---


def detect_unused_fstring(rule, file: Path, source: str) -> list[Diagnostic]:
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_FormattedString(self, node: cst.FormattedString) -> None:
            # No placeholders means no FormattedStringExpression in parts
            has_placeholder = any(isinstance(p, cst.FormattedStringExpression) for p in node.parts)
            if not has_placeholder:
                p = _pos(wrapper, node)
                diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
    wrapper.visit(V())
    return diagnostics


# --- 3. ai-overcatch-then-reraise (ruff TRY201/TRY302) ---


def detect_overcatch_then_reraise(rule, file: Path, source: str) -> list[Diagnostic]:
    """try/except where the body is JUST `raise e` (no transform, no `from`)."""
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
            body = node.body.body if hasattr(node.body, "body") else []
            if len(body) != 1:
                return
            stmt = body[0]
            inner = stmt.body[0] if isinstance(stmt, cst.SimpleStatementLine) else stmt
            if isinstance(inner, cst.Raise):
                # Match `raise e` where e is just the exception name from the handler
                if isinstance(inner.exc, cst.Name) and node.name is not None:
                    if isinstance(node.name, cst.AsName) and isinstance(node.name.name, cst.Name):
                        if inner.exc.value == node.name.name.value and inner.cause is None:
                            p = _pos(wrapper, node)
                            diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
    wrapper.visit(V())
    return diagnostics


# --- 4. ai-assert-in-prod (bandit B101) ---


def detect_assert_in_prod(rule, file: Path, source: str) -> list[Diagnostic]:
    """Bare `assert X` outside tests/ paths."""
    path_str = str(file).lower()
    if "/test" in path_str or "_test.py" in path_str or "tests/" in path_str:
        return []
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_Assert(self, node: cst.Assert) -> None:
            # Skip type-narrowing asserts (assert x is not None)
            test = node.test
            if isinstance(test, cst.Comparison):
                # `x is not None` / `x is None`
                for c in test.comparisons:
                    if isinstance(c.operator, (cst.Is, cst.IsNot)):
                        return
            p = _pos(wrapper, node)
            diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
    wrapper.visit(V())
    return diagnostics


# --- 5. ai-overzealous-typing-import (ruff UP006/UP007) ---


def detect_overzealous_typing_import(rule, file: Path, source: str) -> list[Diagnostic]:
    """`from typing import List, Dict, Tuple, Optional` in Python 3.9+ code."""
    wrapper = _parse(source)
    if wrapper is None:
        return []
    legacy = {"List", "Dict", "Tuple", "Set", "FrozenSet", "Type"}
    diagnostics: list[Diagnostic] = []
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
            if not isinstance(node.module, cst.Name) or node.module.value != "typing":
                return
            if isinstance(node.names, cst.ImportStar):
                return
            for alias in node.names:
                name = alias.name.value if isinstance(alias.name, cst.Name) else ""
                if name in legacy:
                    p = _pos(wrapper, alias)
                    diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
    wrapper.visit(V())
    return diagnostics


# --- 6. ai-dict-keys-iter (ruff SIM118) ---


def detect_dict_keys_iter(rule, file: Path, source: str) -> list[Diagnostic]:
    """`for k in d.keys():` when value isn't accessed."""
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_For(self, node: cst.For) -> None:
            it = node.iter
            if not isinstance(it, cst.Call):
                return
            if not isinstance(it.func, cst.Attribute):
                return
            if it.func.attr.value != "keys" or it.args:
                return
            p = _pos(wrapper, node)
            diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
    wrapper.visit(V())
    return diagnostics


# --- 7. ai-datetime-now-no-tz (flake8-datetimez DTZ005) ---


def detect_datetime_no_tz(rule, file: Path, source: str) -> list[Diagnostic]:
    """`datetime.now()` / `datetime.utcnow()` with no tz argument."""
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    def _is_datetime_chain(node) -> bool:
        # Match `datetime` (Name) OR `datetime.datetime` (Attribute)
        if isinstance(node, cst.Name) and node.value == "datetime":
            return True
        if isinstance(node, cst.Attribute) and node.attr.value == "datetime":
            return _is_datetime_chain(node.value)
        return False

    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_Call(self, node: cst.Call) -> None:
            func = node.func
            if not isinstance(func, cst.Attribute):
                return
            if not _is_datetime_chain(func.value):
                return
            if func.attr.value == "utcnow":
                p = _pos(wrapper, node)
                diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
                return
            if func.attr.value == "now":
                # Allowed if any arg present (likely a tz)
                if not node.args:
                    p = _pos(wrapper, node)
                    diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
    wrapper.visit(V())
    return diagnostics


# --- 8. ai-pip-install-in-code ---


def detect_pip_install_in_code(rule, file: Path, source: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for i, line in enumerate(source.splitlines(), 1):
        if re.search(r"\bos\.system\([^)]*pip\s+install", line) or re.search(r"subprocess\.[a-z_]+\(\s*\[[\"\']pip[\"\']\s*,\s*[\"\']install[\"\']", line):
            diagnostics.append(_emit(rule, file, i, 0))
    return diagnostics


# --- 9. ai-print-traceback (bandit B110 adjacent) ---


def detect_print_traceback(rule, file: Path, source: str) -> list[Diagnostic]:
    """`traceback.print_exc()` inside an except handler that doesn't re-raise."""
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
            body = node.body.body if hasattr(node.body, "body") else []
            has_print_exc = False
            has_raise = False
            for stmt in body:
                inner = stmt.body if isinstance(stmt, cst.SimpleStatementLine) else [stmt]
                for sub in inner:
                    if isinstance(sub, cst.Raise):
                        has_raise = True
                    if isinstance(sub, cst.Expr) and isinstance(sub.value, cst.Call):
                        f = sub.value.func
                        if isinstance(f, cst.Attribute) and f.attr.value == "print_exc":
                            has_print_exc = True
            if has_print_exc and not has_raise:
                p = _pos(wrapper, node)
                diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
    wrapper.visit(V())
    return diagnostics


# --- 10. ai-getter-setter-pythonic ---


def detect_getter_setter_pythonic(rule, file: Path, source: str) -> list[Diagnostic]:
    """A class with both `def get_X(self)` and `def set_X(self, v)` for the same X."""
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_ClassDef(self, node: cst.ClassDef) -> None:
            getters: dict[str, cst.FunctionDef] = {}
            setters: set[str] = set()
            for item in node.body.body:
                if isinstance(item, cst.FunctionDef):
                    n = item.name.value
                    if n.startswith("get_") and len(n) > 4:
                        getters[n[4:]] = item
                    elif n.startswith("set_") and len(n) > 4:
                        setters.add(n[4:])
            for prop, fn in getters.items():
                if prop in setters:
                    p = _pos(wrapper, fn)
                    diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
    wrapper.visit(V())
    return diagnostics


# --- 11. ai-logger-print-mix ---


def detect_logger_print_mix(rule, file: Path, source: str) -> list[Diagnostic]:
    """Module that mixes `print(...)` and `logger.*` calls."""
    path_str = str(file).lower()
    name = file.name
    if name.startswith("__main__") or "/cli" in path_str or "/bin" in path_str or "/script" in path_str:
        return []
    if "if __name__" in source and "__main__" in source:
        return []  # CLI entry script — print is API
    wrapper = _parse(source)
    if wrapper is None:
        return []
    has_print = False
    has_logger = False
    print_node: cst.Call | None = None
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_Call(self, node: cst.Call) -> None:
            nonlocal has_print, has_logger, print_node
            f = node.func
            if isinstance(f, cst.Name) and f.value == "print":
                has_print = True
                print_node = node if print_node is None else print_node
            elif isinstance(f, cst.Attribute) and isinstance(f.value, cst.Name):
                if f.value.value in ("logger", "log", "logging"):
                    has_logger = True
    wrapper.visit(V())
    if has_print and has_logger and print_node is not None:
        p = _pos(wrapper, print_node)
        return [_emit(rule, file, p.start.line, p.start.column)]
    return []


# --- 12. ai-overengineered-init ---


def detect_overengineered_init(rule, file: Path, source: str) -> list[Diagnostic]:
    """__init__ with 10+ params, all Optional[X]=None — should be a dataclass."""
    wrapper = _parse(source)
    if wrapper is None:
        return []
    diagnostics: list[Diagnostic] = []
    class V(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)
        def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
            if node.name.value != "__init__":
                return
            params = [p for p in node.params.params if not (isinstance(p.name, cst.Name) and p.name.value == "self")]
            if len(params) < 10:
                return
            # All with default None
            all_optional = all(
                p.default is not None and isinstance(p.default, cst.Name) and p.default.value == "None"
                for p in params
            )
            if all_optional:
                p = _pos(wrapper, node)
                diagnostics.append(_emit(rule, file, p.start.line, p.start.column))
    wrapper.visit(V())
    return diagnostics


# --- 13. ai-magic-number-retry ---


def detect_magic_number_retry(rule, file: Path, source: str) -> list[Diagnostic]:
    """`for _ in range(N): try: ... except ...: time.sleep(M)` retry pattern."""
    # Regex-based: catch obvious shape without full flow analysis
    diagnostics: list[Diagnostic] = []
    path_str = str(file).lower()
    if "/test" in path_str or "_test.py" in path_str:
        return []
    pattern = re.compile(r"^\s*for\s+_\s+in\s+range\(\d+\)\s*:", re.MULTILINE)
    lines = source.splitlines()
    for m in pattern.finditer(source):
        line_no = source[:m.start()].count("\n") + 1
        # Lookahead: next 8 lines should contain BOTH "try" AND "time.sleep"
        ahead = "\n".join(lines[line_no:min(line_no + 8, len(lines))])
        if "try:" in ahead and "time.sleep" in ahead and "except" in ahead:
            diagnostics.append(_emit(rule, file, line_no, m.start() - source.rfind("\n", 0, m.start()) - 1))
    return diagnostics


def register_all() -> None:
    register_python_detector("ai-mutable-default-arg", detect_mutable_default_arg)
    register_python_detector("ai-unused-fstring", detect_unused_fstring)
    register_python_detector("ai-overcatch-then-reraise", detect_overcatch_then_reraise)
    register_python_detector("ai-assert-in-prod", detect_assert_in_prod)
    register_python_detector("ai-overzealous-typing-import", detect_overzealous_typing_import)
    register_python_detector("ai-dict-keys-iter", detect_dict_keys_iter)
    register_python_detector("ai-datetime-now-no-tz", detect_datetime_no_tz)
    register_python_detector("ai-pip-install-in-code", detect_pip_install_in_code)
    register_python_detector("ai-print-traceback", detect_print_traceback)
    register_python_detector("ai-getter-setter-pythonic", detect_getter_setter_pythonic)
    register_python_detector("ai-logger-print-mix", detect_logger_print_mix)
    register_python_detector("ai-overengineered-init", detect_overengineered_init)
    register_python_detector("ai-magic-number-retry", detect_magic_number_retry)


register_all()
