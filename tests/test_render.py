"""Tests for terminal rendering (banner, score bar, face, category tables)."""

from __future__ import annotations

import io
from pathlib import Path

from rich.console import Console

from aidoctor.render import (
    CATEGORY_COLORS,
    render_banner,
    render_terminal,
    score_bar,
    score_color,
)
from aidoctor.rules import Category, Diagnostic, Severity
from aidoctor.scan import ScanResult
from aidoctor.score import compute_score


def _capture(callable_) -> str:
    buf = io.StringIO()
    console = Console(file=buf, width=80, force_terminal=False, color_system=None)
    callable_(console)
    return buf.getvalue()


def test_banner_includes_brand_name() -> None:
    text = _capture(render_banner)
    # ANSI-shadow blocks render as filled chars; check the tagline is present.
    assert "Catch AI Python slop" in text


def test_score_color_great() -> None:
    score = compute_score([])
    assert score_color(score) == "green"


def test_score_color_critical() -> None:
    diags = [
        Diagnostic(
            rule_id=f"r{i}",
            severity=Severity.ERROR,
            category=Category.SECRETS,
            file=Path("/tmp/x.py"),
            line=1,
            column=0,
            message="m",
            help="h",
        )
        for i in range(20)
    ]
    score = compute_score(diags)
    assert score_color(score) == "red"


def test_score_bar_has_correct_fill() -> None:
    score = compute_score([])  # 100
    bar = score_bar(score, width=10)
    plain = bar.plain
    # Bar uses [ and ] delimiters with 10 filled blocks at 100%.
    assert plain.startswith("[")
    assert plain.endswith("]")
    assert plain.count("█") == 10
    assert plain.count("░") == 0


def test_score_bar_partial_fill() -> None:
    # Half-score → half-filled bar.
    diags = [
        Diagnostic(
            rule_id=f"r{i}",
            severity=Severity.ERROR,
            category=Category.SECRETS,
            file=Path("/tmp/x.py"),
            line=1,
            column=0,
            message="m",
            help="h",
        )
        for i in range(12)
    ]
    score = compute_score(diags)  # ~52
    bar = score_bar(score, width=10)
    plain = bar.plain
    filled = plain.count("█")
    assert 4 <= filled <= 6  # rough half


def test_render_terminal_includes_diagnostics() -> None:
    result = ScanResult(files_scanned=1, files_skipped=0)
    diag = Diagnostic(
        rule_id="hardcoded-api-key",
        severity=Severity.ERROR,
        category=Category.SECRETS,
        file=Path("/tmp/x.py"),
        line=1,
        column=0,
        message="hardcoded secret",
        help="h",
    )
    result.diagnostics = [diag]
    score = compute_score(result.diagnostics)
    output = _capture(lambda c: render_terminal(result, score, console=c))
    # Banner tagline always renders cleanly; the ASCII block art may not.
    assert "Catch AI Python slop" in output
    assert "Score:" in output
    assert "Hardcoded Secrets" in output
    assert "hardcoded-api-key" in output


def test_render_terminal_clean_run() -> None:
    result = ScanResult(files_scanned=1, files_skipped=0)
    score = compute_score([])
    output = _capture(lambda c: render_terminal(result, score, console=c))
    assert "All clear" in output


def test_all_categories_have_colors() -> None:
    # Every Category enum value must have a color mapping.
    for cat in Category:
        assert cat in CATEGORY_COLORS
        assert CATEGORY_COLORS[cat]
