"""Skill installer.

`aidoctor install` writes a rendered SKILL.md (or platform-specific format)
into each detected agent dir (Claude Code, Cursor, Continue.dev).

Pre-existing files are backed up to ~/.cache/aidoctor/install-backups/<timestamp>/.
"""

from __future__ import annotations

import datetime as dt
import logging
import shutil
import sys
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Iterable

import click
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.console import Console
from rich.text import Text

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover — only on py<3.11
    import tomli as tomllib  # type: ignore[no-redef]

from aidoctor import __version__ as AIDOCTOR_VERSION
from aidoctor.rules import CATEGORY_LABELS, RULES, Category

# Reference RULES module-level for the install step header (rule count, etc.)
_ = CATEGORY_LABELS

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class Platform:
    """One agent platform we can install into."""

    key: str
    display_name: str
    relative_path: str
    format: str
    agent_root_relative: str | None = None
    slash_command_relative_path: str | None = None
    slash_command_format: str | None = None

    @property
    def agent_root(self) -> str:
        """Directory under $HOME whose presence indicates this agent is installed.

        Defaults to the first segment of `relative_path` (e.g. `.claude`), but
        platforms whose config lives under a shared dir (e.g. OpenCode at
        `.config/opencode/`) override via the explicit `agent_root` field in
        platforms.toml — checking `.config` alone would false-positive on
        every Linux system.
        """
        if self.agent_root_relative:
            return self.agent_root_relative
        return Path(self.relative_path).parts[0]

    def absolute_path(self, home: Path | None = None) -> Path:
        home = home or Path.home()
        return home / self.relative_path

    def absolute_agent_root(self, home: Path | None = None) -> Path:
        home = home or Path.home()
        return home / self.agent_root

    def slash_command_path(self, home: Path | None = None) -> Path | None:
        if self.slash_command_relative_path is None:
            return None
        home = home or Path.home()
        return home / self.slash_command_relative_path


@dataclass(slots=True, frozen=True)
class InstallResult:
    """Outcome of installing into one platform."""

    platform: Platform
    path: Path
    written: bool
    backed_up_from: Path | None
    skipped_reason: str | None


def load_platforms() -> list[Platform]:
    """Read platforms.toml shipped alongside the skill template."""
    skill_pkg = files("aidoctor.skill")
    toml_text = (skill_pkg / "platforms.toml").read_text(encoding="utf-8")
    data = tomllib.loads(toml_text)
    return [
        Platform(
            key=key,
            display_name=v["display_name"],
            relative_path=v["path"],
            format=v["format"],
            agent_root_relative=v.get("agent_root"),
            slash_command_relative_path=v.get("slash_command_path"),
            slash_command_format=v.get("slash_command_format"),
        )
        for key, v in data.items()
    ]


def load_slash_command(fmt: str) -> str:
    """Return the slash command file content for the given format."""
    skill_pkg = files("aidoctor.skill")
    if fmt == "toml":
        return (skill_pkg / "slash_command.toml").read_text(encoding="utf-8")
    return (skill_pkg / "slash_command.md").read_text(encoding="utf-8")


_FRONTMATTER_RE = "---\n"


def split_frontmatter(rendered: str) -> tuple[str | None, str]:
    """Split a markdown string with optional YAML frontmatter.

    Returns (frontmatter_block_or_None, body). The frontmatter block excludes
    the leading and trailing `---` lines so it's directly YAML-parseable.
    """
    if not rendered.startswith(_FRONTMATTER_RE):
        return None, rendered
    end = rendered.find("\n---\n", len(_FRONTMATTER_RE))
    if end == -1:
        return None, rendered
    frontmatter = rendered[len(_FRONTMATTER_RE) : end]
    body = rendered[end + len(_FRONTMATTER_RE) + 1 :]
    return frontmatter, body


def render_skill() -> str:
    """Render the Jinja2 skill template using the current rule set."""
    env = Environment(
        loader=PackageLoader("aidoctor", "skill"),
        autoescape=select_autoescape(disabled_extensions=("md", "j2"), default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("template.md.j2")

    rules_by_category: dict[str, list[dict]] = {}
    categories_present: list[str] = []
    for rule_class in RULES:
        cat = rule_class.category.value
        if cat not in rules_by_category:
            rules_by_category[cat] = []
            categories_present.append(cat)
        rules_by_category[cat].append(
            {
                "rule_id": rule_class.rule_id,
                "severity": rule_class.severity.value,
                "message": rule_class.message,
                "help": rule_class.help,
            }
        )

    categories_with_labels = [
        (cat, CATEGORY_LABELS[Category(cat)]) for cat in categories_present
    ]

    return template.render(
        aidoctor_version=AIDOCTOR_VERSION,
        today=dt.date.today().isoformat(),
        rule_count=len(RULES),
        categories=categories_present,
        rules_by_category=rules_by_category,
        categories_with_labels=categories_with_labels,
    )


def backup_path(home: Path | None = None) -> Path:
    """Return the backup directory for this install run."""
    home = home or Path.home()
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return home / ".cache" / "aidoctor" / "install-backups" / ts


def install_one(
    platform: Platform,
    rendered: str,
    home: Path | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
    backup_root: Path | None = None,
) -> InstallResult:
    """Install the rendered skill into one platform's path.

    Returns an InstallResult describing what happened. Idempotent.
    """
    target = platform.absolute_path(home)
    target_dir = target.parent

    # Skip if the agent isn't installed on this machine.
    if not platform.absolute_agent_root(home).exists():
        return InstallResult(
            platform=platform,
            path=target,
            written=False,
            backed_up_from=None,
            skipped_reason=f"~/{platform.agent_root}/ not found (agent not installed)",
        )

    # Existing skill content check — skip if identical (idempotent).
    if target.exists():
        try:
            existing = target.read_text(encoding="utf-8")
        except OSError as e:
            return InstallResult(
                platform=platform,
                path=target,
                written=False,
                backed_up_from=None,
                skipped_reason=f"could not read existing file: {e}",
            )
        if existing == rendered and not force:
            return InstallResult(
                platform=platform,
                path=target,
                written=False,
                backed_up_from=None,
                skipped_reason="already up to date",
            )

    backed_up_from: Path | None = None
    if target.exists() and not dry_run:
        backup_root = backup_root or backup_path(home)
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_file = backup_root / f"{platform.key}-{target.name}"
        shutil.copy2(target, backup_file)
        backed_up_from = backup_file

    if dry_run:
        return InstallResult(
            platform=platform,
            path=target,
            written=False,
            backed_up_from=None,
            skipped_reason="dry-run",
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")

    # Also write the /aidoctor slash command file if this platform supports it.
    slash_target = platform.slash_command_path(home)
    if slash_target is not None and platform.slash_command_format is not None:
        slash_content = load_slash_command(platform.slash_command_format)
        slash_target.parent.mkdir(parents=True, exist_ok=True)
        slash_target.write_text(slash_content, encoding="utf-8")

    return InstallResult(
        platform=platform,
        path=target,
        written=True,
        backed_up_from=backed_up_from,
        skipped_reason=None,
    )


def install_all(
    platforms: Iterable[Platform] | None = None,
    home: Path | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
    selected: set[str] | None = None,
) -> list[InstallResult]:
    """Install into platforms whose agent root exists.

    If `selected` is provided, only install into platforms whose `key` is in the set —
    every other detected platform is reported as `skipped_reason="declined"`. Pass
    `None` (default) to install into every detected platform (legacy behavior).
    """
    if platforms is None:
        platforms = load_platforms()
    platforms = list(platforms)
    rendered = render_skill()
    backup_root = backup_path(home)
    results: list[InstallResult] = []
    for p in platforms:
        if selected is not None and p.key not in selected:
            results.append(
                InstallResult(
                    platform=p,
                    path=p.absolute_path(home),
                    written=False,
                    backed_up_from=None,
                    skipped_reason="declined",
                )
            )
            continue
        results.append(
            install_one(
                p,
                rendered,
                home=home,
                dry_run=dry_run,
                force=force,
                backup_root=backup_root,
            )
        )
    return results


# CLI wiring lives in cli.py; install_all() and install_one() are the public API.


def _detected_platforms(platforms: list[Platform], home: Path | None) -> tuple[list[Platform], list[Platform]]:
    """Split platforms into (present, missing) based on whether each agent's root dir exists."""
    present, missing = [], []
    for p in platforms:
        (present if p.absolute_agent_root(home).exists() else missing).append(p)
    return present, missing


def _step(console: Console, icon: str, icon_style: str, text: str, text_style: str = "") -> None:
    """Print a single step line — `◇ Source: ...` rhythm from vercel-labs/skills.

    icon: ◇ (pending/info), ◆ (active prompt), ✓ (done), ✗ (skipped), ● (selected), ○ (unselected).
    """
    line = Text()
    line.append(f"{icon} ", style=icon_style)
    line.append(text, style=text_style)
    console.print(line)


_PRECOMMIT_BLOCK = """  # aidoctor:hook:start
  - repo: https://github.com/ankit-aglawe/aidoctor
    rev: v2.0.0
    hooks:
      - id: aidoctor
        args: [--fail-on, error]
  # aidoctor:hook:end"""

# Match the block from `# aidoctor:hook:start` through `# aidoctor:hook:end`
# anywhere in the file. DOTALL so .*? spans newlines.
_PRECOMMIT_BLOCK_RE = __import__("re").compile(
    r"[ \t]*# aidoctor:hook:start[\s\S]*?# aidoctor:hook:end[ \t]*",
)


def install_pre_commit(target_dir: Path) -> int:
    """Write or update `.pre-commit-config.yaml` in target_dir with the aidoctor hook.

    Idempotent via `# aidoctor:hook:start` / `# aidoctor:hook:end` markers:
        * If markers exist, the block between them is replaced.
        * Otherwise, the block is appended under an existing `repos:` key,
          or a new `repos:` section is created.

    Existing user content above/below the block is preserved verbatim.
    """
    cfg = target_dir / ".pre-commit-config.yaml"

    if not cfg.exists():
        cfg.write_text(f"# Generated by `aidoctor install --pre-commit`\nrepos:\n{_PRECOMMIT_BLOCK}\n")
        return 0

    existing = cfg.read_text()

    # Case 1: existing aidoctor block — replace in place. The regex captures the
    # original block (including its leading indent); substituting with the full
    # _PRECOMMIT_BLOCK (which carries its own 2-space indent) is idempotent.
    if _PRECOMMIT_BLOCK_RE.search(existing):
        updated = _PRECOMMIT_BLOCK_RE.sub(_PRECOMMIT_BLOCK, existing)
        if updated != existing:
            cfg.write_text(updated)
        return 0

    # Case 2: no aidoctor block but has a `repos:` key — append our block at the
    # end of file so it joins the repos list. (pre-commit allows trailing
    # additions to repos: as long as the list-of-mappings structure stays valid.)
    import re

    if re.search(r"^repos:", existing, re.MULTILINE):
        if not existing.endswith("\n"):
            existing += "\n"
        cfg.write_text(existing + _PRECOMMIT_BLOCK + "\n")
        return 0

    # Case 3: no `repos:` key — create one and add our block under it.
    if not existing.endswith("\n"):
        existing += "\n"
    cfg.write_text(existing + "\nrepos:\n" + _PRECOMMIT_BLOCK + "\n")
    return 0


def cli_run(dry_run: bool, force: bool, yes: bool = False, interactive: bool | None = None) -> int:
    """Convenience entry for the `aidoctor install` subcommand. Returns exit code.

    Interactive in a TTY (unless --yes); silent install-all-detected in CI / pipes.
    UX mirrors vercel-labs/skills (banner + ◇ step icons in our cyan).
    """
    # Lazy import to avoid a circular dep — render imports rules/score which import install.
    from aidoctor.render import render_banner  # noqa: PLC0415

    console = Console()
    platforms = load_platforms()
    present, missing = _detected_platforms(platforms, home=None)

    if interactive is None:
        interactive = sys.stdin.isatty() and not yes

    # Header — brand banner + tagline
    render_banner(console)

    # Step 1: source + payload summary
    _step(console, "◇", "bright_cyan", "Source: https://pypi.org/project/aidoctor/", "white")
    _step(console, "◇", "bright_cyan", "6 skills: scan, simplify, audit, rules, help, python-rules + using-aidoctor", "white")
    _step(console, "◇", "bright_cyan", f"{len(RULES)} rules across 8 categories", "white")
    # Non-Python project note (DX-F7): the skills are global, not project-bound.
    if not any(Path.cwd().rglob("*.py")):
        _step(console, "◇", "bright_cyan", "No Python files detected in this dir — skills install globally regardless. You can scan a different project later with `aidoctor scan <path>`.", "dim")
    console.print()

    # Step 2: detection
    _step(console, "◆", "bright_cyan", "Detected agents", "bold white")
    for p in present:
        console.print(Text(f"  ● {p.display_name:<18} ~/{p.agent_root}", style="green"))
    for p in missing:
        console.print(Text(f"  ○ {p.display_name:<18} (not installed)", style="dim"))
    console.print()

    if not present:
        _step(console, "✗", "yellow", "No agents detected. Install at least one (Claude Code, Cursor, Codex, Gemini CLI, OpenCode) first.", "yellow")
        return 0

    # Step 3: agent selection
    selected: set[str] | None = None
    if interactive:
        if click.confirm(f"Install into all {len(present)} detected agents?", default=True):
            selected = {p.key for p in present}
        else:
            selected = set()
            for p in present:
                if click.confirm(f"  Install into {p.display_name}?", default=True):
                    selected.add(p.key)
            if not selected:
                _step(console, "✗", "yellow", "Nothing selected. Exiting.", "yellow")
                return 0
        console.print()

    # Step 4: install
    results = install_all(dry_run=dry_run, force=force, selected=selected)
    written = 0
    skipped = 0
    _step(console, "◆", "bright_cyan", "Writing", "bold white")
    for r in results:
        if r.written:
            backup_note = f"  (backed up old)" if r.backed_up_from else ""
            console.print(Text(f"  ✓ {r.platform.display_name:<18} {r.path}{backup_note}", style="green"))
            written += 1
        else:
            console.print(Text(f"  ○ {r.platform.display_name:<18} {r.skipped_reason}", style="dim"))
            skipped += 1
    console.print()
    if written == 0 and skipped == len(results):
        _step(console, "○", "dim", "Nothing to do — agents already up to date (or no agents installed).", "dim")
    else:
        _step(console, "✓", "green", f"Done. {written} written, {skipped} skipped.", "bold")
        if written > 0 and not dry_run:
            console.print()
            done = Text("  Try ", style="white")
            done.append("/aidoctor:scan", style="bright_cyan bold")
            done.append(" in Claude Code, or say ", style="white")
            done.append('"scan this"', style="italic")
            done.append(" to any agent.", style="white")
            console.print(done)
    return 0
