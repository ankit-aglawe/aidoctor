"""Tests for AI-Slop Imports rules."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from aidoctor.rules._base import RuleContext
from aidoctor.rules.imports import (
    ConditionalImportOutsideTryRule,
    DuplicateImportRule,
    ImportWithoutUseRule,
    WildcardImportRule,
)


def _run(rule_cls, source: str, filename: str = "x.py") -> list:
    ctx = RuleContext(file=Path(f"/tmp/{filename}"), source=source)
    wrapper = cst.MetadataWrapper(cst.parse_module(source))
    wrapper.visit(rule_cls(ctx))
    return ctx.diagnostics


def test_wildcard_import_fires() -> None:
    diags = _run(WildcardImportRule, "from os import *\n")
    assert len(diags) == 1
    assert diags[0].rule_id == "wildcard-import"


def test_wildcard_import_clean() -> None:
    assert _run(WildcardImportRule, "from os import getcwd, environ\n") == []


def test_wildcard_import_exempt_in_init_py() -> None:
    """v2.0 refinement: `__init__.py` re-exports via `from .submodule import *` are canonical.

    Fixes 16 FPs the real-world FP harness found in httpx (which uses
    `from .submodule import *` in __init__.py as designed).
    """
    src = "from .submodule import *\n"
    assert _run(WildcardImportRule, src, filename="__init__.py") == []


def test_duplicate_import_fires() -> None:
    diags = _run(DuplicateImportRule, "import json\nimport json\n")
    assert len(diags) == 1


def test_duplicate_import_clean() -> None:
    assert _run(DuplicateImportRule, "import json\nimport os\n") == []


def test_duplicate_from_import_fires() -> None:
    diags = _run(
        DuplicateImportRule, "from typing import Any\nfrom typing import Any\n"
    )
    assert len(diags) == 1


def test_conditional_import_outside_try_fires() -> None:
    diags = _run(
        ConditionalImportOutsideTryRule,
        "import sys\nif sys.version_info < (3, 11):\n    import tomli\n",
    )
    assert len(diags) == 1


def test_conditional_import_inside_try_clean() -> None:
    src = "try:\n    import tomllib\nexcept ImportError:\n    import tomli\n"
    assert _run(ConditionalImportOutsideTryRule, src) == []


def test_conditional_import_with_sibling_try_clean() -> None:
    """v2.0 refinement: if the file shows any try/except ImportError, the author
    is aware of import-fallback patterns. Don't nag on every conditional import.

    Fixes 34 FPs the real-world FP harness found in flask (which uses both
    try/except ImportError and version-gated imports legitimately).
    """
    src = (
        "try:\n"
        "    import tomllib\n"
        "except ImportError:\n"
        "    import tomli as tomllib\n"
        "\n"
        "import sys\n"
        "if sys.version_info < (3, 11):\n"
        "    import legacy_helper\n"
    )
    assert _run(ConditionalImportOutsideTryRule, src) == []


def test_unused_import_fires() -> None:
    diags = _run(ImportWithoutUseRule, "import json\nimport os\n\nx = os.getcwd()\n")
    rules = [d.rule_id for d in diags]
    assert "import-without-use" in rules
    messages = [d.message for d in diags]
    assert any("json" in m for m in messages)


def test_used_import_clean() -> None:
    src = "import json\nimport os\n\nprint(json.dumps({}))\nprint(os.getcwd())\n"
    assert _run(ImportWithoutUseRule, src) == []


def test_typing_only_import_under_type_checking_clean() -> None:
    src = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import json\n"
        "\n"
        "x = 1\n"
    )
    # json should NOT be flagged because it's gated.
    diags = _run(ImportWithoutUseRule, src)
    flagged = [d.message for d in diags]
    assert not any("json" in m for m in flagged)


def test_import_without_use_init_py_no_all_treats_as_reexport() -> None:
    """v2.0 refinement: `__init__.py` without `__all__` is implicitly a re-export
    package. Imports are considered re-exported; don't flag unused.

    Fixes the bulk of the 73 import-without-use FPs the real-world FP harness
    found in psf/requests (where __init__.py re-exports without declaring __all__).
    """
    src = (
        "from .core import handle_request, build_response\n"
        "from .auth import authenticate\n"
    )
    diags = _run(ImportWithoutUseRule, src, filename="__init__.py")
    assert diags == []  # __init__.py without __all__ = re-export everything


def test_import_without_use_init_py_with_all_still_flags() -> None:
    """If __init__.py declares __all__, fall back to standard logic.

    Imports NOT in __all__ AND not referenced internally still get flagged.
    """
    src = (
        "from .core import handle_request, build_response, unused_helper\n"
        '__all__ = ["handle_request", "build_response"]\n'
    )
    diags = _run(ImportWithoutUseRule, src, filename="__init__.py")
    flagged = [d.message for d in diags]
    assert any("unused_helper" in m for m in flagged)
    assert not any("handle_request" in m for m in flagged)
