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

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover — only on py<3.11
    import tomli as tomllib  # type: ignore[no-redef]

from aidoctor import __version__ as AIDOCTOR_VERSION
from aidoctor.rules import CATEGORY_LABELS, RULES, Category

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class Platform:
    """One agent platform we can install into."""

    key: str
    display_name: str
    relative_path: str
    format: str

    def absolute_path(self, home: Path | None = None) -> Path:
        home = home or Path.home()
        return home / self.relative_path


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
        )
        for key, v in data.items()
    ]


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

    # Detect whether the parent agent dir exists at all (e.g. ~/.claude).
    # We treat the FIRST path segment under home as the agent root.
    agent_root_name = Path(platform.relative_path).parts[0]
    agent_root = (home or Path.home()) / agent_root_name
    if not agent_root.exists():
        return InstallResult(
            platform=platform,
            path=target,
            written=False,
            backed_up_from=None,
            skipped_reason=f"{agent_root_name}/ not found (agent not installed)",
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
) -> list[InstallResult]:
    """Install into all platforms whose agent root exists. Returns a list of results."""
    if platforms is None:
        platforms = load_platforms()
    rendered = render_skill()
    backup_root = backup_path(home)
    return [
        install_one(
            p,
            rendered,
            home=home,
            dry_run=dry_run,
            force=force,
            backup_root=backup_root,
        )
        for p in platforms
    ]


# CLI wiring lives in cli.py; install_all() and install_one() are the public API.


def cli_run(dry_run: bool, force: bool) -> int:
    """Convenience entry for the `aidoctor install` subcommand. Returns exit code."""
    results = install_all(dry_run=dry_run, force=force)
    written = 0
    skipped = 0
    for r in results:
        if r.written:
            backup_note = (
                f" (backed up old to {r.backed_up_from})" if r.backed_up_from else ""
            )
            click.echo(f"  [✓] {r.platform.display_name}: wrote {r.path}{backup_note}")
            written += 1
        else:
            click.echo(f"  [-] {r.platform.display_name}: {r.skipped_reason}")
            skipped += 1
    click.echo()
    if written == 0 and skipped == len(results):
        click.echo(
            "No platforms updated. Either no agents are installed, or skills are already up to date."
        )
    else:
        click.echo(f"Done. {written} written, {skipped} skipped.")
    return 0
