"""AI-Slop Imports rules.

AI assistants often produce import patterns humans wouldn't write:
wildcard imports, duplicate imports of the same name, conditional imports
without a try/except guard, and imports that are never used.
"""

from __future__ import annotations

from typing import Any

import libcst as cst

from aidoctor.rules._base import Category, Rule, Severity


class WildcardImportRule(Rule):
    """Detects `from X import *` patterns.

    v2.0 refinement: exempt `__init__.py` files. `from .submodule import *` in
    a package's __init__ is the canonical Python re-export idiom (used by
    httpx, flask, and most well-maintained packages).
    """

    rule_id = "wildcard-import"
    severity = Severity.WARNING
    category = Category.IMPORTS
    message = "Wildcard import obscures what's in scope. Import names explicitly."
    help = (
        "`from module import *` makes it impossible to tell where a name comes from "
        "and breaks tools (linters, type checkers, IDE autocomplete) that need to "
        "resolve names statically. AI assistants often generate this when they're "
        "uncertain what to import. Import names explicitly: `from module import a, b, c`. "
        "Exempt: `__init__.py` files where `from .submodule import *` is canonical."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#wildcard-import"

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if self.context.file.name == "__init__.py":
            return
        if isinstance(node.names, cst.ImportStar):
            self.report(node)


class DuplicateImportRule(Rule):
    """Detects the same module imported twice in the same file."""

    rule_id = "duplicate-import"
    severity = Severity.WARNING
    category = Category.IMPORTS
    message = "Same module imported twice in this file."
    help = (
        "Importing the same module multiple times in a file is dead code that AI "
        "assistants often produce when stitching together snippets. Remove the "
        "duplicate. If aliases differ intentionally (e.g. `import numpy as np` and "
        "`import numpy.linalg as nla`), the rule won't fire because the dotted "
        "module names differ."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#duplicate-import"

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self._seen: dict[str, cst.CSTNode] = {}

    def _key(self, name: cst.CSTNode) -> str:
        """Render a module name path like 'os.path' or 'numpy' as a stable string."""
        if isinstance(name, cst.Name):
            return name.value
        if isinstance(name, cst.Attribute):
            return f"{self._key(name.value)}.{name.attr.value}"
        return ""

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            key = self._key(alias.name)
            if not key:
                continue
            if key in self._seen:
                self.report(alias)
            else:
                self._seen[key] = alias

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is None:
            return
        mod = self._key(node.module)
        if isinstance(node.names, cst.ImportStar):
            return
        for alias in node.names:
            name = self._key(alias.name)
            if not name:
                continue
            key = f"{mod}::{name}"
            if key in self._seen:
                self.report(alias)
            else:
                self._seen[key] = alias


class ConditionalImportOutsideTryRule(Rule):
    """Detects `if VERSION...: import X` patterns without try/except guard.

    v2.0 refinement: if the file already has ANY `try/except ImportError`
    sibling, the author is aware of import-fallback patterns. Don't nag.

    Fixes 34 FPs the real-world FP harness found in pallets/flask, which
    legitimately mixes try-except-ImportError with version-gated imports.
    """

    rule_id = "conditional-import-outside-try"
    severity = Severity.WARNING
    category = Category.IMPORTS
    message = "Conditional import outside try/except. Wrap in try/except ImportError."
    help = (
        "AI assistants often write `if sys.version_info < (3, 11): import tomli` "
        "without a try/except guard. If the import fails on an unexpected system, "
        "the error is cryptic and uncatchable. Wrap conditional imports in "
        "try/except ImportError to fail loudly with a useful message, or restructure "
        "to use importlib.util.find_spec for capability checks. "
        "Exempt: files that already contain `try/except ImportError` elsewhere."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#conditional-import-outside-try"

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self._has_try_except_importerror = False
        self._candidates: list[cst.CSTNode] = []

    def _contains_import(self, body: cst.BaseStatement) -> bool:
        """Check if a statement body contains an Import or ImportFrom."""
        for stmt in _iter_simple_statements(body):
            if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                return True
        return False

    def visit_If(self, node: cst.If) -> None:
        if self._contains_import(node.body):
            self._candidates.append(node)

    def visit_Try(self, node: cst.Try) -> bool:
        # Detect `try: ... except ImportError`.
        for handler in node.handlers:
            t = handler.type
            if t is None:
                continue
            if isinstance(t, cst.Name) and t.value == "ImportError":
                self._has_try_except_importerror = True
            elif isinstance(t, cst.Tuple):
                for el in t.elements:
                    v = el.value if hasattr(el, "value") else None
                    if isinstance(v, cst.Name) and v.value == "ImportError":
                        self._has_try_except_importerror = True
        # Don't recurse into the try body for `if X: import Y` checks.
        return False

    def leave_Module(self, original_node: cst.Module) -> None:
        if self._has_try_except_importerror:
            return  # author is import-fallback-aware; stay silent
        for cand in self._candidates:
            self.report(cand)


class ImportWithoutUseRule(Rule):
    """Detects imports that are never used in the file.

    Heuristic: collect all imported bindings, then collect all Name references.
    If a binding is never referenced (and isn't `__all__` exported), flag it.
    Skips type-checking-only imports inside `if TYPE_CHECKING:` blocks.
    """

    rule_id = "import-without-use"
    severity = Severity.WARNING
    category = Category.IMPORTS
    message = "Imported but never used."
    help = (
        "Unused imports are the most common AI slop pattern: AI assistants import "
        "things they think they'll need, then change their mind. Remove the import. "
        "If you intentionally export it for re-import elsewhere, add it to `__all__`. "
        "If it's for type-checking only, move it under `if TYPE_CHECKING:`."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#import-without-use"

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self._bindings: dict[str, cst.CSTNode] = {}
        self._used: set[str] = set()
        self._in_type_checking = False
        self._in_import = False
        self._all_exported: set[str] = set()

    def visit_Import(self, node: cst.Import) -> None:
        self._in_import = True
        if self._in_type_checking:
            return
        for alias in node.names:
            name = alias.asname.name.value if alias.asname else _last_attr(alias.name)
            if name:
                self._bindings[name] = alias

    def leave_Import(self, original_node: cst.Import) -> None:
        self._in_import = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        self._in_import = True
        # `from __future__ import X` is a language directive, not a runtime import.
        if (
            node.module is not None
            and isinstance(node.module, cst.Name)
            and node.module.value == "__future__"
        ):
            return
        if self._in_type_checking or isinstance(node.names, cst.ImportStar):
            return
        for alias in node.names:
            # PEP 484 explicit-re-export: `from .core import X as X` means
            # "this module publicly re-exports X". Don't flag it as unused.
            if (
                alias.asname is not None
                and isinstance(alias.name, cst.Name)
                and alias.asname.name.value == alias.name.value
            ):
                continue
            name = alias.asname.name.value if alias.asname else _last_attr(alias.name)
            if name:
                self._bindings[name] = alias

    def leave_ImportFrom(self, original_node: cst.ImportFrom) -> None:
        self._in_import = False

    def visit_If(self, node: cst.If) -> None:
        # Detect `if TYPE_CHECKING:` and skip imports inside.
        test = node.test
        if isinstance(test, cst.Name) and test.value == "TYPE_CHECKING":
            self._in_type_checking = True

    def leave_If(self, original_node: cst.If) -> None:
        test = original_node.test
        if isinstance(test, cst.Name) and test.value == "TYPE_CHECKING":
            self._in_type_checking = False

    def visit_Name(self, node: cst.Name) -> None:
        # Any Name reference outside an import statement counts as a use.
        if self._in_import:
            return
        if node.value in self._bindings:
            self._used.add(node.value)

    def visit_Assign(self, node: cst.Assign) -> None:
        # Capture __all__ contents.
        for target in node.targets:
            if isinstance(target.target, cst.Name) and target.target.value == "__all__":
                self._collect_all(node.value)

    def _collect_all(self, value: cst.BaseExpression) -> None:
        if isinstance(value, (cst.List, cst.Tuple)):
            for el in value.elements:
                if isinstance(el, cst.Element) and isinstance(el.value, cst.SimpleString):
                    sval = el.value.evaluated_value
                    if isinstance(sval, str):
                        self._all_exported.add(sval)

    def leave_Module(self, original_node: cst.Module) -> None:
        # v2.0 refinement: __init__.py without __all__ is implicitly a re-export
        # package. Fixes the bulk of the 73 FPs in psf/requests.
        if self.context.file.name == "__init__.py" and not self._all_exported:
            return  # implicit-re-export package; every import is "used"
        unused = set(self._bindings) - self._used - self._all_exported
        for name in unused:
            self.report(self._bindings[name], message=f"`{name}` imported but never used")


def _last_attr(node: cst.CSTNode) -> str:
    """Return the rightmost attribute name (e.g. for `os.path`, return 'os')."""
    # `import os.path` binds `os`, not `path`. Match Python semantics.
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return _last_attr(node.value)
    return ""


def _iter_simple_statements(body: cst.BaseStatement | cst.BaseSuite) -> Any:
    """Iterate small statements inside a compound block."""
    if isinstance(body, cst.IndentedBlock):
        for stmt in body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                yield from stmt.body
            else:
                yield stmt
    elif isinstance(body, cst.SimpleStatementSuite):
        yield from body.body
