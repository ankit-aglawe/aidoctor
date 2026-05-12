"""Tests for the declarative JSONL rule engine.

Per CEO Section 'Architecture: Skill-First Rule System' (locked mid-review):
rules are JSONL-first, with a Python escape hatch for flow-sensitive cases.

Phase 1 here covers: manifest loader + comment_regex detect kind.
That alone unlocks 4 ai_style rules (emphasis-label, section-divider,
hedge-comment, self-praise-comment).
"""

from __future__ import annotations

import json
from pathlib import Path

# --- manifest loader ---


def test_load_manifest_parses_jsonl(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import load_manifest

    manifest = tmp_path / "ai_style.jsonl"
    manifest.write_text(
        json.dumps({
            "id": "ai-emphasis-label",
            "severity": "warning",
            "confidence": "HIGH",
            "category": "ai-style",
            "langs": ["python"],
            "detect": {
                "kind": "comment_regex",
                "pattern": r"^#\s*(NOTE|IMPORTANT|CAREFUL|CRITICAL):",
            },
            "fix": {"kind": "strip_label"},
            "ref": "https://ai-doctor.dev/r/ai-emphasis-label",
            "message": "AI-style emphasis label",
            "help": "Remove the NOTE/IMPORTANT/etc. label; let the comment speak for itself.",
        }) + "\n"
    )
    rules = load_manifest(manifest)
    assert len(rules) == 1
    assert rules[0].id == "ai-emphasis-label"
    assert rules[0].severity == "warning"
    assert rules[0].confidence == "HIGH"
    assert "python" in rules[0].langs


def test_load_manifest_skips_blank_lines(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import load_manifest

    manifest = tmp_path / "x.jsonl"
    manifest.write_text(
        "\n\n"
        + json.dumps({
            "id": "r1", "severity": "warning", "confidence": "HIGH",
            "category": "ai-style", "langs": ["python"],
            "detect": {"kind": "comment_regex", "pattern": "x"},
            "message": "m", "help": "h",
        }) + "\n\n"
    )
    rules = load_manifest(manifest)
    assert len(rules) == 1


def test_load_manifest_rejects_malformed_line(tmp_path: Path) -> None:
    """A bad line warns but doesn't crash the loader.

    Skipping rather than crashing matters: a typo in one rule entry
    must not take down the whole scanner.
    """
    from aidoctor.engine.declarative import load_manifest

    manifest = tmp_path / "x.jsonl"
    manifest.write_text(
        "not valid json\n"
        + json.dumps({
            "id": "ok", "severity": "warning", "confidence": "HIGH",
            "category": "ai-style", "langs": ["python"],
            "detect": {"kind": "comment_regex", "pattern": "x"},
            "message": "m", "help": "h",
        }) + "\n"
    )
    rules = load_manifest(manifest)
    assert [r.id for r in rules] == ["ok"]


def test_load_manifest_validates_required_fields(tmp_path: Path) -> None:
    """Missing a required field is fatal at load time, not silent at scan time."""
    from aidoctor.engine.declarative import load_manifest

    manifest = tmp_path / "x.jsonl"
    # Missing 'detect' field
    manifest.write_text(json.dumps({
        "id": "r1", "severity": "warning", "confidence": "HIGH",
        "category": "ai-style", "langs": ["python"],
        "message": "m", "help": "h",
    }) + "\n")
    rules = load_manifest(manifest)
    # Invalid rule is dropped (skip-with-log policy, same as malformed line)
    assert rules == []


def test_load_manifest_missing_file(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import load_manifest

    with __import__("pytest").raises(FileNotFoundError):
        load_manifest(tmp_path / "does-not-exist.jsonl")


# --- comment_regex detect kind ---


def _make_rule(**overrides) -> object:
    from aidoctor.engine.declarative import Rule

    base = {
        "id": "ai-emphasis-label",
        "severity": "warning",
        "confidence": "HIGH",
        "category": "ai-style",
        "langs": ("python",),
        "detect": {
            "kind": "comment_regex",
            "pattern": r"^#\s*(NOTE|IMPORTANT|CAREFUL|CRITICAL):",
        },
        "fix": {"kind": "strip_label"},
        "ref": None,
        "message": "AI-style emphasis label",
        "help": "Remove the label.",
    }
    base.update(overrides)
    return Rule(**base)


def test_comment_regex_catches_note_label(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import apply_rule

    rule = _make_rule()
    f = tmp_path / "x.py"
    f.write_text("x = 1\n# NOTE: this is important\ny = 2\n")
    diags = apply_rule(rule, f)
    assert len(diags) == 1
    assert diags[0].rule_id == "ai-emphasis-label"
    assert diags[0].line == 2


def test_comment_regex_catches_multiple_lines(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import apply_rule

    rule = _make_rule()
    f = tmp_path / "x.py"
    f.write_text("# NOTE: a\nx = 1\n# IMPORTANT: b\ny = 2\n# CRITICAL: c\n")
    diags = apply_rule(rule, f)
    assert len(diags) == 3
    assert [d.line for d in diags] == [1, 3, 5]


def test_comment_regex_ignores_non_comments(tmp_path: Path) -> None:
    """A string containing '# NOTE:' isn't a comment and must not be flagged.

    This is the core difference between regex-on-bytes and regex-on-comment-tokens.
    """
    from aidoctor.engine.declarative import apply_rule

    rule = _make_rule()
    f = tmp_path / "x.py"
    f.write_text('x = "# NOTE: this is a string, not a comment"\n')
    diags = apply_rule(rule, f)
    assert diags == []


def test_comment_regex_misses_when_no_match(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import apply_rule

    rule = _make_rule()
    f = tmp_path / "x.py"
    f.write_text("# just a regular comment\nx = 1\n")
    diags = apply_rule(rule, f)
    assert diags == []


def test_comment_regex_diagnostic_has_correct_category(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import apply_rule
    from aidoctor.rules._base import Category

    rule = _make_rule()
    f = tmp_path / "x.py"
    f.write_text("# NOTE: x\n")
    diags = apply_rule(rule, f)
    assert diags[0].category == Category.AI_STYLE


def test_comment_regex_diagnostic_has_correct_severity(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import apply_rule
    from aidoctor.rules._base import Severity

    rule = _make_rule(severity="warning")
    f = tmp_path / "x.py"
    f.write_text("# NOTE: x\n")
    diags = apply_rule(rule, f)
    assert diags[0].severity == Severity.WARNING


# --- python escape hatch ---


def test_python_kind_dispatches_to_callable(tmp_path: Path) -> None:
    """detect.kind=python escape hatch lets complex rules live in rules_complex/."""
    # Register a fake python-kind detector
    from aidoctor.engine import declarative
    from aidoctor.engine.declarative import apply_rule

    def custom_detector(rule, file: Path, source: str):
        from aidoctor.rules._base import Category, Diagnostic, Severity
        if "MAGIC_TOKEN" in source:
            return [
                Diagnostic(
                    rule_id=rule.id,
                    severity=Severity.WARNING,
                    category=Category.AI_STYLE,
                    file=file,
                    line=1,
                    column=0,
                    message="found magic token",
                    help="remove magic token",
                )
            ]
        return []

    declarative.register_python_detector("custom-magic-rule", custom_detector)

    rule = _make_rule(
        id="custom-magic-rule",
        detect={"kind": "python", "fn": "custom-magic-rule"},
    )
    f = tmp_path / "x.py"
    f.write_text("MAGIC_TOKEN = 1\n")
    diags = apply_rule(rule, f)
    assert len(diags) == 1
    assert diags[0].rule_id == "custom-magic-rule"


def test_unknown_detect_kind_raises_clear_error(tmp_path: Path) -> None:
    """An unknown detect.kind is a programming error — fail loudly."""
    import pytest

    from aidoctor.engine.declarative import apply_rule

    rule = _make_rule(detect={"kind": "telepathy"})
    f = tmp_path / "x.py"
    f.write_text("x = 1\n")
    with pytest.raises(ValueError, match="telepathy"):
        apply_rule(rule, f)


# --- source_unicode_category detect kind (powers ai-emoji-in-code) ---


def _emoji_rule(**overrides) -> object:
    from aidoctor.engine.declarative import Rule

    base = {
        "id": "ai-emoji-in-code",
        "severity": "warning",
        "confidence": "HIGH",
        "category": "ai-style",
        "langs": ("python",),
        "detect": {
            "kind": "source_unicode_category",
            "categories": ["So", "Sk"],
        },
        "fix": {"kind": "delete_emoji"},
        "ref": None,
        "message": "Emoji in source code — common AI fingerprint",
        "help": "Remove the emoji. Use plain text or a logger.",
    }
    base.update(overrides)
    return Rule(**base)


def test_emoji_in_comment_is_flagged(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import apply_rule

    f = tmp_path / "x.py"
    f.write_text("# ✅ Done\nx = 1\n")  # checkmark emoji in comment
    diags = apply_rule(_emoji_rule(), f)
    assert len(diags) == 1
    assert diags[0].line == 1


def test_emoji_in_string_literal_is_ignored(tmp_path: Path) -> None:
    """Emojis in string literals are intentional output (CLI banners, prints).

    The ai-emoji-in-code rule targets emojis in comments / identifiers / operators —
    where they're a syntax-irrelevant AI tell. Use a different rule (inflated-print)
    for emoji-in-print-arg.
    """
    from aidoctor.engine.declarative import apply_rule

    f = tmp_path / "x.py"
    f.write_text('print("✨ Done")\n')  # sparkles emoji in string
    diags = apply_rule(_emoji_rule(), f)
    assert diags == []


def test_multiple_emojis_one_diagnostic_per_occurrence(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import apply_rule

    f = tmp_path / "x.py"
    f.write_text("# ✅ a\nx = 1  # \U0001F389 b\n")  # checkmark + party-popper
    diags = apply_rule(_emoji_rule(), f)
    assert len(diags) == 2
    assert sorted([d.line for d in diags]) == [1, 2]


def test_no_emoji_no_diagnostic(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import apply_rule

    f = tmp_path / "x.py"
    f.write_text("# regular comment\nx = 1\n")
    diags = apply_rule(_emoji_rule(), f)
    assert diags == []


def test_ast_call_with_kwarg_catches_shell_true(tmp_path: Path) -> None:
    """ast_call_with_kwarg: matches `subprocess.run(..., shell=True)` etc.

    This is the workhorse for the OWASP-3 pack (shell=True / verify=False /
    algorithm='none') and inflated-print's emoji-kwarg case.
    """
    from aidoctor.engine.declarative import Rule, apply_rule

    rule = Rule(
        id="shell-true-with-variable",
        severity="warning",
        confidence="HIGH",
        category="security",
        langs=("python",),
        detect={"kind": "ast_call_with_kwarg", "function": "subprocess.run", "kwarg": "shell", "value": True},
        fix=None,
        ref=None,
        message="subprocess.run with shell=True is RCE-prone",
        help="Use shell=False and pass argv list.",
    )
    f = tmp_path / "x.py"
    f.write_text("import subprocess\nsubprocess.run(cmd, shell=True)\n")
    diags = apply_rule(rule, f)
    assert len(diags) == 1
    assert diags[0].line == 2
    assert diags[0].rule_id == "shell-true-with-variable"


def test_ast_call_with_kwarg_ignores_unmatched_value(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import Rule, apply_rule

    rule = Rule(
        id="r", severity="warning", confidence="HIGH", category="security",
        langs=("python",),
        detect={"kind": "ast_call_with_kwarg", "function": "subprocess.run", "kwarg": "shell", "value": True},
        fix=None, ref=None, message="m", help="h",
    )
    f = tmp_path / "x.py"
    f.write_text("subprocess.run(cmd, shell=False)\n")
    diags = apply_rule(rule, f)
    assert diags == []


def test_ast_call_with_kwarg_ignores_other_function(tmp_path: Path) -> None:
    from aidoctor.engine.declarative import Rule, apply_rule

    rule = Rule(
        id="r", severity="warning", confidence="HIGH", category="security",
        langs=("python",),
        detect={"kind": "ast_call_with_kwarg", "function": "subprocess.run", "kwarg": "shell", "value": True},
        fix=None, ref=None, message="m", help="h",
    )
    f = tmp_path / "x.py"
    f.write_text("other.fn(cmd, shell=True)\n")
    diags = apply_rule(rule, f)
    assert diags == []


def test_ast_call_with_kwarg_simple_function_name(tmp_path: Path) -> None:
    """Function names without dots (e.g., `eval(x)`)."""
    from aidoctor.engine.declarative import Rule, apply_rule

    rule = Rule(
        id="eval-on-non-constant",
        severity="warning", confidence="HIGH", category="security",
        langs=("python",),
        # No kwarg/value — just match the function call shape regardless of args
        detect={"kind": "ast_call_with_kwarg", "function": "eval"},
        fix=None, ref=None, message="m", help="h",
    )
    f = tmp_path / "x.py"
    f.write_text("y = eval(user_input)\n")
    diags = apply_rule(rule, f)
    assert len(diags) == 1


def test_ast_call_with_kwarg_handles_string_value(tmp_path: Path) -> None:
    """JWT algorithm='none' — string value matching."""
    from aidoctor.engine.declarative import Rule, apply_rule

    rule = Rule(
        id="jwt-algorithm-none",
        severity="warning", confidence="HIGH", category="security",
        langs=("python",),
        detect={"kind": "ast_call_with_kwarg", "function": "jwt.decode", "kwarg": "algorithms", "value": ["none"]},
        fix=None, ref=None, message="m", help="h",
    )
    f = tmp_path / "x.py"
    f.write_text('import jwt\njwt.decode(token, algorithms=["none"])\n')
    diags = apply_rule(rule, f)
    assert len(diags) == 1


def test_emoji_categories_filter_works(tmp_path: Path) -> None:
    """Only the configured Unicode categories trigger.

    Category 'So' = Symbol, Other (covers most emojis). If a rule only lists 'Sk'
    (Symbol, Modifier) it should NOT fire on a standard emoji.
    """
    from aidoctor.engine.declarative import apply_rule

    f = tmp_path / "x.py"
    f.write_text("# ✅ checkmark\n")  # 'So' category
    rule_so_only = _emoji_rule(detect={"kind": "source_unicode_category", "categories": ["So"]})
    rule_sk_only = _emoji_rule(detect={"kind": "source_unicode_category", "categories": ["Sk"]})
    assert len(apply_rule(rule_so_only, f)) == 1
    assert apply_rule(rule_sk_only, f) == []
