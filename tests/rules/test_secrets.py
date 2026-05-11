"""Tests for hardcoded secret rules."""

from __future__ import annotations

from pathlib import Path

import libcst as cst
import pytest

from aidoctor.rules._base import RuleContext, Severity
from aidoctor.rules.secrets import HardcodedApiKeyRule


def run_rule(source: str) -> list:
    """Run HardcodedApiKeyRule against source text. Return diagnostics."""
    context = RuleContext(file=Path("/tmp/test.py"), source=source)
    module = cst.parse_module(source)
    wrapper = cst.MetadataWrapper(module)
    wrapper.visit(HardcodedApiKeyRule(context))
    return context.diagnostics


# Positive cases — should fire.
@pytest.mark.parametrize(
    "source,expected_rule",
    [
        # Plain assignment with secret-ish name and long string.
        ('API_KEY = "sk-prod-1234567890abcdef"\n', "hardcoded-api-key"),
        ('SECRET_TOKEN = "ghp_abcdefghijklmnop"\n', "hardcoded-api-key"),
        ('DATABASE_PASSWORD = "myrealpassword123"\n', "hardcoded-api-key"),
        ('access_token = "tok_1234567890abcdef"\n', "hardcoded-api-key"),
        # Annotated assignment.
        ('API_KEY: str = "sk-prod-1234567890abcdef"\n', "hardcoded-api-key"),
    ],
)
def test_hardcoded_api_key_positive(source: str, expected_rule: str) -> None:
    diags = run_rule(source)
    assert len(diags) == 1, f"expected 1 diagnostic, got {len(diags)} for {source!r}"
    assert diags[0].rule_id == expected_rule
    assert diags[0].severity == Severity.ERROR


# Negative cases — should NOT fire.
@pytest.mark.parametrize(
    "source",
    [
        # Variable name doesn't match.
        'GREETING = "hello world how are you"\n',
        # String too short.
        'API_KEY = "short"\n',
        # Placeholder value.
        'API_KEY = "your-api-key-here"\n',
        'TOKEN = "changeme"\n',
        # Not an assignment to a Name (attribute).
        'config.API_KEY = "sk-1234567890abcdef"\n',
        # No string value.
        "API_KEY = some_function()\n",
        # Empty source.
        "",
    ],
)
def test_hardcoded_api_key_negative(source: str) -> None:
    diags = run_rule(source)
    assert diags == [], f"expected no diagnostics, got {[d.rule_id for d in diags]}"


def test_diagnostic_position() -> None:
    source = "\n\nAPI_KEY = \"sk-prod-1234567890\"\n"
    diags = run_rule(source)
    assert len(diags) == 1
    # Line 3 (1-indexed), column 0.
    assert diags[0].line == 3
    assert diags[0].column == 0
