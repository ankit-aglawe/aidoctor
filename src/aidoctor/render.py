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
    GREAT_THRESHOLD,
    LABEL_CRITICAL,
    LABEL_GREAT,
    LABEL_NEEDS_WORK,
    NEEDS_WORK_THRESHOLD,
    Score,
)
from aidoctor.scan import ScanResult

BRAND_COLOR = "bright_cyan"
BRAND_DIM = "cyan"

# Single-color brand mark. "Ownable" brand identity like Claude's amber.
AI_COLOR = "bright_cyan"
AI_DIM = "cyan"
DOCTOR_COLOR = "bright_cyan"
DOCTOR_DIM = "cyan"

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
    """Render the AI Doctor brand banner — mono cyan, ANSI Shadow blocks."""
    banner = Text()
    banner.append("\n")
    banner.append(BANNER_AI, style=f"bold {AI_COLOR}")
    banner.append("\n")
    banner.append(BANNER_DOCTOR, style=f"bold {DOCTOR_COLOR}")
    banner.append("\n\n  ")
    banner.append(f"v{__version__}", style=DOCTOR_DIM)
    banner.append("  ·  ", style="dim")
    banner.append("Better Python from your AI assistant.", style=DOCTOR_DIM)
    console.print(
        Panel(
            banner,
            border_style=DOCTOR_COLOR,
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
        console.print()


def _short_path(path: Path) -> str:
    """Shorten a path relative to cwd if possible."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)
