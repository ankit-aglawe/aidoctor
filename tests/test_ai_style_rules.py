"""Integration tests for the 5 declarative ai_style rules.

These are pure JSONL rules — no Python code in rules_complex. They exercise
the comment_regex + source_unicode_category detect kinds end-to-end through
the scan pipeline.
"""

from __future__ import annotations

from pathlib import Path


def test_ai_style_manifest_loadable() -> None:
    """The original 5 ai_style rules + 7 universal patterns (v2.0 Phase 2c)."""
    import aidoctor
    from aidoctor.engine.declarative import load_manifest

    manifest = Path(aidoctor.__file__).parent / "rules" / "manifest" / "ai_style.jsonl"
    rules = load_manifest(manifest)
    ids = {r.id for r in rules}
    # The 5 original cross-language rules
    assert "ai-emphasis-label" in ids
    assert "ai-section-divider" in ids
    assert "ai-hedge-comment" in ids
    assert "ai-self-praise-comment" in ids
    assert "ai-emoji-in-code" in ids
    # The 7 universal patterns added in v2.0 Phase 2c
    assert "ai-marketing-vocab" in ids
    assert "ai-conjunctive-opener" in ids
    assert "ai-em-dash-overuse" in ids
    assert "ai-todo-without-ticket-multilang" in ids
    assert "ai-stub-body-comment-multilang" in ids
    assert "ai-rule-of-three-padding" in ids
    assert "ai-negative-parallelism" in ids
    # v2.0 ai_style total = 12 (existing 5 + 7 new universal)
    assert len(ids) >= 12


def test_scan_catches_emphasis_label(tmp_path: Path) -> None:
    from aidoctor.scan import scan

    f = tmp_path / "x.py"
    f.write_text("x = 1\n# NOTE: this is important\ny = 2\n")
    result = scan([tmp_path], jobs=1)
    rule_ids = {d.rule_id for d in result.diagnostics}
    assert "ai-emphasis-label" in rule_ids


def test_scan_catches_section_divider(tmp_path: Path) -> None:
    from aidoctor.scan import scan

    f = tmp_path / "x.py"
    f.write_text("# ====================== SECTION 1 ======================\nx = 1\n")
    result = scan([tmp_path], jobs=1)
    rule_ids = {d.rule_id for d in result.diagnostics}
    assert "ai-section-divider" in rule_ids


def test_scan_catches_self_praise_in_comment(tmp_path: Path) -> None:
    from aidoctor.scan import scan

    f = tmp_path / "x.py"
    f.write_text("# Using a list comprehension for Pythonic style\nresult = [x * 2 for x in items]\n")
    result = scan([tmp_path], jobs=1)
    rule_ids = {d.rule_id for d in result.diagnostics}
    assert "ai-self-praise-comment" in rule_ids


def test_scan_catches_emoji_in_comment(tmp_path: Path) -> None:
    from aidoctor.scan import scan

    f = tmp_path / "x.py"
    f.write_text("# ✅ Done\nx = 1\n")
    result = scan([tmp_path], jobs=1)
    rule_ids = {d.rule_id for d in result.diagnostics}
    assert "ai-emoji-in-code" in rule_ids


def test_scan_ignores_emoji_in_string_literal(tmp_path: Path) -> None:
    """Emojis in print/string literals are intentional output, not AI fingerprints."""
    from aidoctor.scan import scan

    f = tmp_path / "x.py"
    f.write_text('print("✨ Welcome to the CLI")\n')
    result = scan([tmp_path], jobs=1)
    rule_ids = {d.rule_id for d in result.diagnostics}
    assert "ai-emoji-in-code" not in rule_ids


def test_scan_catches_hedge_comment(tmp_path: Path) -> None:
    from aidoctor.scan import scan

    f = tmp_path / "x.py"
    f.write_text("# Note: this assumes the input is sorted\nfor item in items:\n    pass\n")
    result = scan([tmp_path], jobs=1)
    rule_ids = {d.rule_id for d in result.diagnostics}
    assert "ai-hedge-comment" in rule_ids


def test_clean_python_no_ai_style_findings(tmp_path: Path) -> None:
    """A normal Python module with regular comments must not fire ai_style rules."""
    from aidoctor.scan import scan

    f = tmp_path / "x.py"
    f.write_text(
        "def add(a: int, b: int) -> int:\n"
        "    # standard inline comment\n"
        "    return a + b\n"
    )
    result = scan([tmp_path], jobs=1)
    rule_ids = {d.rule_id for d in result.diagnostics}
    ai_style_ids = {r for r in rule_ids if r.startswith("ai-")}
    assert ai_style_ids == set()
