"""Click-based CLI entry point.

Commands: `scan`, `scan-pr <url>`, `install`, `skill`. Run `aidoctor --help`
to list everything.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

import click
from rich.console import Console

from aidoctor.discover import NoPythonFilesError
from aidoctor.install import cli_run as install_cli_run, split_frontmatter
from aidoctor.render import render_terminal
from aidoctor.rules import RULES
from aidoctor.scan import build_json_payload, compute_exit_code, scan
from aidoctor.score import compute_score

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_FILES = 2


@click.group()
@click.version_option()
def main() -> None:
    """aidoctor — your agent writes bad Python. This catches it."""


@main.command(name="scan")
@click.argument("path", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit a JSON report instead of the terminal-rendered output.",
)
@click.option(
    "--explain",
    type=str,
    metavar="RULE",
    default=None,
    help="Print the static rich doc for RULE and exit.",
)
@click.option(
    "--diff",
    "diff_mode",
    is_flag=True,
    help="Scan only lines that changed (unstaged git diff).",
)
@click.option(
    "--staged",
    is_flag=True,
    help="Scan only staged lines. Implies --diff.",
)
@click.option(
    "--fail-on",
    type=click.Choice(["critical", "error", "warning", "none"], case_sensitive=False),
    default="error",
    show_default=True,
    help="Exit non-zero if violations of the given severity (or worse) are found.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Print per-file scan timing and warnings.",
)
def scan_cmd(
    path: tuple[Path, ...],
    json_output: bool,
    explain: str | None,
    diff_mode: bool,
    staged: bool,
    fail_on: str,
    verbose: bool,
) -> None:
    """Scan PATH(s) for AI-slop Python patterns. Defaults to current directory."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    # --explain RULE prints the rich doc for RULE and exits.
    if explain is not None:
        _print_rule_doc(explain)
        sys.exit(EXIT_OK)

    targets = list(path) if path else [Path.cwd()]
    use_diff = diff_mode or staged

    try:
        result = scan(targets)
    except NoPythonFilesError as e:
        click.echo(f"aidoctor: {e}", err=True)
        sys.exit(EXIT_NO_FILES)

    # Apply --diff filter if requested.
    # aidoctor: disable=conditional-import-outside-try
    if use_diff:
        from aidoctor.diff_mode import (  # noqa: PLC0415 - lazy import keeps cold-start fast
            GitNotAvailableError,
            filter_diagnostics_to_diff,
            get_changed_lines,
        )

        try:
            changed = get_changed_lines(cwd=Path.cwd(), staged=staged)
        except GitNotAvailableError as e:
            click.echo(f"aidoctor: --diff requires git: {e}", err=True)
            sys.exit(EXIT_USAGE)
        result.diagnostics = filter_diagnostics_to_diff(
            result.diagnostics, changed, repo_root=Path.cwd()
        )

    score = compute_score(result.diagnostics)

    if json_output:
        click.echo(json.dumps(build_json_payload(result, score), indent=2))
    else:
        render_terminal(result, score, console=Console())

    sys.exit(compute_exit_code(score, fail_on))


def _print_rule_doc(rule_id: str) -> None:
    """Print the static rich doc for a single rule and exit."""
    for rule_class in RULES:
        if rule_class.rule_id == rule_id:
            click.echo(f"{rule_class.rule_id}  ({rule_class.severity.value}, {rule_class.category.value})")
            click.echo("=" * (len(rule_class.rule_id) + 40))
            click.echo()
            click.echo(rule_class.message)
            click.echo()
            click.echo(rule_class.help)
            if rule_class.url:
                click.echo()
                click.echo(f"More: {rule_class.url}")
            return
    click.echo(f"aidoctor: no rule named {rule_id!r}", err=True)
    click.echo()
    click.echo("Available rules:")
    for rule_class in RULES:
        click.echo(f"  - {rule_class.rule_id}")
    sys.exit(EXIT_USAGE)


@main.command(name="install")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be written without writing.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing skill files even if content matches.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip prompts. Install into every detected agent. Use this in CI.",
)
def install_cmd(dry_run: bool, force: bool, yes: bool) -> None:
    """Install the aidoctor skill into your AI agent dirs.

    Detects which agents are installed (Claude Code, Cursor, Codex, Gemini CLI,
    OpenCode), prompts you for which to install into, and writes the SKILL files.
    In a TTY: interactive prompts. In CI or with --yes: installs into all detected.
    Existing files are backed up to ~/.cache/aidoctor/install-backups/<timestamp>/.
    """
    rc = install_cli_run(dry_run=dry_run, force=force, yes=yes)
    sys.exit(rc)


@main.command(name="skill")
@click.option(
    "--format",
    "out_format",
    type=click.Choice(
        ["claude", "cursor", "opencode", "codex", "gemini", "generic", "raw"],
        case_sensitive=False,
    ),
    default="generic",
    help="Output format. `claude` writes the SKILL.md form; `cursor` the .mdc form; "
    "`opencode`, `codex`, and `gemini` use plain markdown in their respective rules "
    "dirs; `generic` strips frontmatter for any agent or system prompt; `raw` is the "
    "Jinja template unchanged.",
)
def skill_cmd(out_format: str) -> None:
    """Print the rendered aidoctor skill markdown to stdout.

    Use this for any AI agent / IDE / system prompt that we don't have a native
    installer for. Pipe the output wherever the agent expects it:

        aidoctor skill --format generic > my-agent/rules/aidoctor.md
        aidoctor skill --format claude | pbcopy   # Claude Code
        aidoctor skill --format cursor > .cursor/rules/aidoctor.mdc
        aidoctor skill --format opencode > ~/.config/opencode/rules/aidoctor.md
        aidoctor skill --format codex > ~/.codex/rules/aidoctor.md
        aidoctor skill --format gemini > ~/.gemini/rules/aidoctor.md

    Skill content is generated from the same 25 rules the CLI enforces, so you
    cannot drift between the rule set and the skill text.
    """
    from aidoctor.install import render_skill

    rendered = render_skill()
    fmt = out_format.lower()
    frontmatter, body = split_frontmatter(rendered)

    if fmt in {"raw", "claude"}:
        click.echo(rendered, nl=False)
        return

    if fmt in {"generic", "opencode", "codex", "gemini"}:
        # OpenCode, Codex, and Gemini CLI all read plain markdown rules; the
        # SKILL.md-style frontmatter is Claude-specific and confuses other agents.
        click.echo(body, nl=False)
        return

    if fmt == "cursor":
        # Cursor's .mdc files prefer simple frontmatter with description + globs.
        # Re-key the description out of our frontmatter into Cursor's shape.
        desc_match = re.search(r"^description:\s*(.+)$", frontmatter or "", re.MULTILINE)
        desc = desc_match.group(1) if desc_match else "AI Doctor — Python static analyzer for AI-generated code."
        cursor_frontmatter = (
            "---\n"
            f"description: {desc}\n"
            "globs:\n"
            "  - '**/*.py'\n"
            "alwaysApply: true\n"
            "---\n\n"
        )
        click.echo(cursor_frontmatter + body, nl=False)
        return

    raise click.UsageError(f"unknown skill format: {fmt}")


@main.command(name="rules")
@click.option(
    "--category",
    type=str,
    default=None,
    help="Filter by category (e.g. secrets, dead-defenses, async-mismatch).",
)
@click.option(
    "--severity",
    type=click.Choice(["error", "warning"], case_sensitive=False),
    default=None,
    help="Filter by severity.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit JSON instead of terminal output.",
)
def rules_cmd(category: str | None, severity: str | None, json_output: bool) -> None:
    """List all aidoctor rules with their IDs, severities, categories, and one-line messages.

    Use `aidoctor scan --explain <rule-id>` for the full rationale on any one rule.
    """
    matched = []
    for rule_class in RULES:
        if category and rule_class.category.value != category:
            continue
        if severity and rule_class.severity.value != severity:
            continue
        matched.append(rule_class)

    if json_output:
        click.echo(json.dumps(
            {
                "count": len(matched),
                "rules": [
                    {
                        "rule_id": r.rule_id,
                        "severity": r.severity.value,
                        "category": r.category.value,
                        "message": r.message,
                        "url": r.url,
                    }
                    for r in matched
                ],
            },
            indent=2,
        ))
        return

    # Terminal output — group by category, severity coloring
    console = Console()
    by_category: dict[str, list] = {}
    for r in matched:
        by_category.setdefault(r.category.value, []).append(r)

    console.print(f"\n  [bold]{len(matched)} rules[/bold] across {len(by_category)} categories\n")
    for cat in sorted(by_category):
        console.print(f"  [bright_cyan bold]{cat}[/bright_cyan bold]")
        for r in by_category[cat]:
            sev_color = "red" if r.severity.value == "error" else "yellow"
            console.print(
                f"    [{sev_color}]{r.severity.value:>7}[/{sev_color}]  "
                f"[bold]{r.rule_id:<35}[/bold]  {r.message}"
            )
        console.print()
    console.print(
        "  Look up a single rule:  [dim]aidoctor scan --explain <rule-id>[/dim]\n"
    )


@main.command(name="scan-pr")
@click.argument("url", required=True)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON instead of terminal output.")
@click.option(
    "--fail-on",
    type=click.Choice(["critical", "error", "warning", "none"], case_sensitive=False),
    default="error",
    show_default=True,
    help="Exit non-zero if violations of the given severity (or worse) are found.",
)
def scan_pr_cmd(url: str, json_output: bool, fail_on: str) -> None:
    """Scan the changed Python files of a GitHub PR.

    URL format: https://github.com/<owner>/<repo>/pull/<num>

    Uses GITHUB_TOKEN env var for auth when set. Without a token, anonymous
    GitHub API calls are subject to 60/hour rate limit.
    """
    # aidoctor: disable=conditional-import-outside-try
    from aidoctor.scan_pr import cli_run as scan_pr_cli_run  # noqa: PLC0415

    rc = scan_pr_cli_run(url=url, json_output=json_output, fail_on=fail_on)
    sys.exit(rc)


if __name__ == "__main__":
    main()
