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


def _run(rule_cls, source: str) -> list:
    ctx = RuleContext(file=Path("/tmp/x.py"), source=source)
    wrapper = cst.MetadataWrapper(cst.parse_module(source))
    wrapper.visit(rule_cls(ctx))
    return ctx.diagnostics


def test_wildcard_import_fires() -> None:
    diags = _run(WildcardImportRule, "from os import *\n")
    assert len(diags) == 1
    assert diags[0].rule_id == "wildcard-import"


def test_wildcard_import_clean() -> None:
    assert _run(WildcardImportRule, "from os import getcwd, environ\n") == []


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
