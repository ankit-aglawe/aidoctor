"""Terminal rendering: AI Doctor banner, ASCII doctor face, score bar, categories.

The banner is the brand mark. The face is the shareable screenshot moment.
Keep both.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aidoctor import __version__
from aidoctor.rules import CATEGORY_LABELS, Category, Diagnostic, Severity
from aidoctor.score import (
    LABEL_GREAT,
    LABEL_NEEDS_WORK,
    Score,
)
from aidoctor.scan import ScanResult

BRAND_COLOR = "bright_cyan"
BRAND_DIM = "cyan"

# Cyan brand. "Ownable" identity like Claude's amber.
AI_COLOR = "bright_cyan"
AI_DIM = "cyan"
DOCTOR_COLOR = "bright_cyan"
DOCTOR_DIM = "cyan"

# Per-row cyan gradient for the brand banner. Translated from
# vercel-labs/skills' GRAYS pattern (255→238) into our cyan palette.
# Lightest at the top, peak bright_cyan at the AI/DOCTOR transition,
# fading to deep teal at the bottom. 12 values for 12 banner rows.
BANNER_GRADIENT = [
    "color(195)",  # ice-pale
    "color(159)",
    "color(123)",
    "color(87)",
    "color(51)",
    "color(51)",   # AI bottom — peak
    "color(45)",   # DOCTOR top
    "color(45)",
    "color(39)",
    "color(38)",
    "color(31)",
    "color(30)",   # deepest teal
]

# ANSI Shadow style. Both lines left-aligned at the same column.
BANNER_AI = r"""  █████╗ ██╗
  ██╔══██╗██║
  ███████║██║
  ██╔══██║██║
  ██║  ██║██║
  ╚═╝  ╚═╝╚═╝"""

BANNER_DOCTOR = r"""  ██████╗  ██████╗  ██████╗████████╗ ██████╗ ██████╗
  ██╔══██╗██╔═══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗
  ██║  ██║██║   ██║██║        ██║   ██║   ██║██████╔╝
  ██║  ██║██║   ██║██║        ██║   ██║   ██║██╔══██╗
  ██████╔╝╚██████╔╝╚██████╗   ██║   ╚██████╔╝██║  ██║
  ╚═════╝  ╚═════╝  ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝"""

# Per-category colors. Picked to be (a) distinct on dark + light terminals,
# (b) loosely thematic: secrets/red, async/magenta, etc.
CATEGORY_COLORS: dict[Category, str] = {
    Category.SECRETS: "bright_red",
    Category.DEAD_DEFENSES: "red",
    Category.ASYNC_MISMATCH: "bright_magenta",
    Category.TYPE_HINTS: "bright_blue",
    Category.IMPORTS: "blue",
    Category.LOOPS: "bright_yellow",
    Category.PERF: "bright_green",
    Category.DECAY: "bright_white",
}

def score_color(score: Score) -> str:
    if score.label == LABEL_GREAT:
        return "green"
    if score.label == LABEL_NEEDS_WORK:
        return "yellow"
    return "red"


def score_bar(score: Score, width: int = 50) -> Text:
    """Horizontal score bar with a red→yellow→green gradient by fill position.

    Each filled cell is colored by where it sits on the 0-100 scale: bottom
    third red, middle yellow, top third green. Empty cells dim gray.
    """
    filled = int((score.value / 100) * width)
    bar = Text()
    bar.append("[", style="white")
    for i in range(filled):
        # Position-based gradient — independent of the user's actual score.
        position_pct = (i / width) * 100
        if position_pct < 33:
            color = "red"
        elif position_pct < 66:
            color = "yellow"
        else:
            color = "green"
        bar.append("█", style=color)
    bar.append("░" * (width - filled), style="bright_black")
    bar.append("]", style="white")
    return bar


def render_banner(console: Console) -> None:
    """Render the AI Doctor brand banner — cyan gradient ANSI Shadow.

    Each row of the banner is painted a slightly different shade of cyan, going
    from ice-pale at the top to deep teal at the bottom. Lifts the per-row
    gradient pattern from vercel-labs/skills, translated into our brand palette.
    """
    banner = Text()
    banner.append("\n")
    all_lines = BANNER_AI.split("\n") + BANNER_DOCTOR.split("\n")
    for i, line in enumerate(all_lines):
        shade = BANNER_GRADIENT[i] if i < len(BANNER_GRADIENT) else BANNER_GRADIENT[-1]
        banner.append(line, style=f"bold {shade}")
        banner.append("\n")
    banner.append("\n  ")
    banner.append(f"v{__version__}", style="color(45) dim")
    banner.append("  ·  ", style="dim")
    banner.append("Better Python from your AI assistant.", style="color(45) dim")
    console.print(
        Panel(
            banner,
            border_style="color(51)",
            expand=False,
            padding=(0, 1),
        )
    )


def render_terminal(result: ScanResult, score: Score, console: Console | None = None) -> None:
    """Render the full scan report to stdout."""
    if console is None:
        console = Console()

    # Brand banner first
    render_banner(console)

    # Diagnosis panel: score + bar, no kitsch face.
    color = score_color(score)
    header = Text()
    header.append("  Score: ", style="white")
    header.append(f"{score.value}/100", style=f"bold {color}")
    header.append(f"  ({score.label})\n  ", style=color)
    header.append(score_bar(score))

    console.print(Panel(header, title="diagnosis", border_style=color, expand=False, padding=(1, 1)))

    # File summary
    summary = Text()
    summary.append(f"  Scanned: {result.files_scanned} files", style="white")
    if result.files_skipped > 0:
        summary.append(f"  •  Skipped: {result.files_skipped}", style="yellow")
    summary.append(
        f"  •  Violations: {score.total_violations} "
        f"({score.unique_error_rules} unique errors, "
        f"{score.unique_warning_rules} unique warnings)",
        style="white",
    )
    console.print(summary)
    console.print()

    if not result.diagnostics:
        console.print(Text("✓ All clear — no violations found.", style="bold green"))
        return

    # Group diagnostics by category
    by_category: dict[Category, list[Diagnostic]] = defaultdict(list)
    for d in result.diagnostics:
        by_category[d.category].append(d)

    for category in Category:
        diags = by_category.get(category)
        if not diags:
            continue
        label = CATEGORY_LABELS[category]
        cat_color = CATEGORY_COLORS.get(category, "white")
        unique_rules_in_cat = {d.rule_id for d in diags}
        title = f"{label}  ({len(diags)} violations, {len(unique_rules_in_cat)} rule(s))"
        table = Table(
            title=title,
            title_style=f"bold {cat_color}",
            title_justify="left",
            show_header=True,
            header_style="bold",
            expand=False,
            box=None,
        )
        table.add_column("Rule", style=cat_color, no_wrap=True)
        table.add_column("Severity", no_wrap=True)
        table.add_column("Location", style="bright_white", no_wrap=True)
        table.add_column("Message", style="white")
        for d in sorted(diags, key=lambda x: (x.rule_id, str(x.file), x.line)):
            sev_color = "red" if d.severity == Severity.ERROR else "yellow"
            table.add_row(
                d.rule_id,
                Text(d.severity.value, style=sev_color),
                f"{_short_path(d.file)}:{d.line}",
                d.message,
            )
        console.print(table)
        # Show docs URLs once per rule_id seen in this category — helps the
        # user (or their agent) look up the full rationale without re-running
        # `aidoctor scan --explain <id>`. DX-F4 from /plan-devex-review.
        seen_urls: dict[str, str] = {}
        for d in diags:
            if d.url and d.rule_id not in seen_urls:
                seen_urls[d.rule_id] = d.url
        if seen_urls:
            for rule_id, url in seen_urls.items():
                console.print(Text(f"    {rule_id} → {url}", style="dim"))
        console.print()


def _short_path(path: Path) -> str:
    """Shorten a path relative to cwd if possible."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)
