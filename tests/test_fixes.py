"""Tests for declarative-engine fix kinds.

These produce the text replacements that /aidoctor:deai applies (W12).
The RewriteResult shape is the locked API contract from eng-review finding 1B.
"""

from __future__ import annotations

from pathlib import Path


# --- RewriteResult shape ---


def test_rewrite_result_has_expected_fields() -> None:
    from aidoctor.engine.fixes import RewriteResult

    r = RewriteResult(
        ok=True,
        original_code="# NOTE: x",
        replacement_code="# x",
        line_range=(2, 2),
    )
    assert r.ok is True
    assert r.original_code == "# NOTE: x"
    assert r.replacement_code == "# x"
    assert r.line_range == (2, 2)
    assert r.reason_if_failed is None


def test_rewrite_result_failed_has_reason() -> None:
    from aidoctor.engine.fixes import RewriteResult

    r = RewriteResult(
        ok=False,
        original_code="",
        replacement_code="",
        line_range=(0, 0),
        reason_if_failed="unknown fix kind",
    )
    assert r.ok is False
    assert r.reason_if_failed == "unknown fix kind"


# --- strip_label fix ---


def _diag(rule_id: str, line: int, source: str, file: Path):
    """Test helper: build a minimal Diagnostic for fix testing."""
    from aidoctor.rules._base import Category, Diagnostic, Severity

    return Diagnostic(
        rule_id=rule_id,
        severity=Severity.WARNING,
        category=Category.AI_STYLE,
        file=file,
        line=line,
        column=0,
        message="m",
        help="h",
    )


def _rule(fix_spec: dict, rule_id: str = "r"):
    from aidoctor.engine.declarative import Rule

    return Rule(
        id=rule_id,
        severity="warning",
        confidence="HIGH",
        category="ai-style",
        langs=("python",),
        detect={"kind": "comment_regex", "pattern": ".*"},
        fix=fix_spec,
        ref=None,
        message="m",
        help="h",
    )


def test_strip_label_removes_emphasis_prefix(tmp_path: Path) -> None:
    from aidoctor.engine.fixes import propose_fix

    rule = _rule({"kind": "strip_label"})
    source = "x = 1\n# NOTE: do this carefully\ny = 2\n"
    diag = _diag(rule.id, line=2, source=source, file=tmp_path / "x.py")

    result = propose_fix(rule, source, diag)
    assert result.ok is True
    assert result.original_code == "# NOTE: do this carefully"
    assert result.replacement_code == "# do this carefully"
    assert result.line_range == (2, 2)


def test_strip_label_handles_each_label_variant(tmp_path: Path) -> None:
    from aidoctor.engine.fixes import propose_fix

    rule = _rule({"kind": "strip_label"})
    for label in ("NOTE", "IMPORTANT", "CAREFUL", "CRITICAL", "TIP", "HACK"):
        source = f"# {label}: be careful\n"
        diag = _diag(rule.id, line=1, source=source, file=tmp_path / "x.py")
        result = propose_fix(rule, source, diag)
        assert result.ok is True
        assert result.replacement_code == "# be careful", f"failed for {label}"


# --- delete_emoji fix ---


def test_delete_emoji_strips_unicode_So_chars(tmp_path: Path) -> None:
    from aidoctor.engine.fixes import propose_fix

    rule = _rule({"kind": "delete_emoji"})
    source = "# ✅ done\n"  # checkmark = U+2705 (So)
    diag = _diag(rule.id, line=1, source=source, file=tmp_path / "x.py")

    result = propose_fix(rule, source, diag)
    assert result.ok is True
    # Emoji removed; comment text preserved (one trailing space trimmed)
    assert "✅" not in result.replacement_code
    assert "done" in result.replacement_code


def test_delete_emoji_preserves_text_around_emoji(tmp_path: Path) -> None:
    from aidoctor.engine.fixes import propose_fix

    rule = _rule({"kind": "delete_emoji"})
    source = "# Done✅ successfully\n"
    diag = _diag(rule.id, line=1, source=source, file=tmp_path / "x.py")

    result = propose_fix(rule, source, diag)
    assert result.ok is True
    assert "Done" in result.replacement_code
    assert "successfully" in result.replacement_code
    assert "✅" not in result.replacement_code


# --- strip_comment fix ---


def test_strip_comment_removes_full_line(tmp_path: Path) -> None:
    """For section dividers, the entire comment line is noise — strip it."""
    from aidoctor.engine.fixes import propose_fix

    rule = _rule({"kind": "strip_comment"})
    source = "x = 1\n# ====================== SECTION 1 ======================\ny = 2\n"
    diag = _diag(rule.id, line=2, source=source, file=tmp_path / "x.py")

    result = propose_fix(rule, source, diag)
    assert result.ok is True
    # The entire line is removed (replacement is empty)
    assert result.replacement_code == ""


def test_strip_comment_handles_inline_comment(tmp_path: Path) -> None:
    """Inline comments (`x = 1  # NOTE: foo`) keep the code, strip the comment.

    This is the more conservative behavior: we don't delete user code, only the comment tail.
    """
    from aidoctor.engine.fixes import propose_fix

    rule = _rule({"kind": "strip_comment"})
    source = "x = 1  # =============== divider ===============\n"
    diag = _diag(rule.id, line=1, source=source, file=tmp_path / "x.py")

    result = propose_fix(rule, source, diag)
    assert result.ok is True
    assert result.replacement_code.strip() == "x = 1"


# --- template_replacement fix ---


def test_template_replacement_substitutes_placeholders(tmp_path: Path) -> None:
    from aidoctor.engine.fixes import propose_fix

    rule = _rule({
        "kind": "template_replacement",
        "template": "raise {EXC}(f\"timeout: {{detail}}\")",
        "bindings": {"EXC": "TimeoutError"},
    })
    source = "pass\n"
    diag = _diag(rule.id, line=1, source=source, file=tmp_path / "x.py")

    result = propose_fix(rule, source, diag)
    assert result.ok is True
    assert result.replacement_code == "raise TimeoutError(f\"timeout: {detail}\")"


# --- unknown fix kind ---


def test_unknown_fix_kind_returns_failure(tmp_path: Path) -> None:
    """Unknown fix kinds return RewriteResult(ok=False), not raise.

    Reason: /aidoctor:deai loops over many findings; one bad fix-kind shouldn't
    abort the whole loop. The user sees 'fix unavailable: <reason>' and moves on.
    """
    from aidoctor.engine.fixes import propose_fix

    rule = _rule({"kind": "telepathy"})
    source = "x = 1\n"
    diag = _diag(rule.id, line=1, source=source, file=tmp_path / "x.py")

    result = propose_fix(rule, source, diag)
    assert result.ok is False
    assert "telepathy" in (result.reason_if_failed or "").lower()


def test_no_fix_in_rule_returns_failure(tmp_path: Path) -> None:
    """A rule without a fix block can be detected but not applied."""
    from aidoctor.engine.fixes import propose_fix

    rule = _rule(None)  # fix=None
    source = "x = 1\n"
    diag = _diag(rule.id, line=1, source=source, file=tmp_path / "x.py")

    result = propose_fix(rule, source, diag)
    assert result.ok is False
