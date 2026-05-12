"""Tests for the skill installer."""

from __future__ import annotations

from pathlib import Path

from aidoctor.install import (
    Platform,
    install_all,
    install_one,
    load_platforms,
    render_skill,
)


def test_load_platforms() -> None:
    platforms = load_platforms()
    keys = {p.key for p in platforms}
    assert "claude" in keys
    assert "cursor" in keys
    assert "opencode" in keys
    assert "codex" in keys
    assert "gemini" in keys


def test_slash_command_supported_platforms() -> None:
    platforms = {p.key: p for p in load_platforms()}
    # These platforms support custom slash commands.
    assert platforms["claude"].slash_command_relative_path is not None
    assert platforms["opencode"].slash_command_relative_path is not None
    assert platforms["gemini"].slash_command_relative_path is not None
    # These don't.
    assert platforms["cursor"].slash_command_relative_path is None
    assert platforms["codex"].slash_command_relative_path is None


def test_install_writes_slash_command_for_claude(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    install_all(home=tmp_path, dry_run=False)
    slash = tmp_path / ".claude" / "commands" / "aidoctor.md"
    assert slash.exists()
    content = slash.read_text()
    assert "Scan the current directory" in content
    assert "aidoctor scan" in content


def test_install_writes_toml_slash_command_for_gemini(tmp_path: Path) -> None:
    (tmp_path / ".gemini").mkdir()
    install_all(home=tmp_path, dry_run=False)
    slash = tmp_path / ".gemini" / "commands" / "aidoctor.toml"
    assert slash.exists()
    content = slash.read_text()
    assert 'name = "aidoctor"' in content
    assert "prompt =" in content


def test_install_skips_slash_command_for_cursor(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    install_all(home=tmp_path, dry_run=False)
    # Cursor has no slash command convention — no commands dir should exist.
    assert not (tmp_path / ".cursor" / "commands").exists()


def test_platform_absolute_path(tmp_path: Path) -> None:
    p = Platform(
        key="test",
        display_name="Test",
        relative_path="my/path/skill.md",
        format="generic",
    )
    assert p.absolute_path(home=tmp_path) == tmp_path / "my/path/skill.md"


def test_render_skill_contains_frontmatter() -> None:
    rendered = render_skill()
    assert rendered.startswith("---\n")
    assert "name: aidoctor" in rendered
    # Description should now NOT contain workflow language (writing-skills rule).
    desc_line = next(line for line in rendered.splitlines() if line.startswith("description:"))
    assert "Apply before returning" not in desc_line
    # Should mention some trigger symptoms.
    assert "hardcoded secrets" in desc_line.lower()
    # Should reference our rule count (v2.0: 24 after dropping generic-without-typevar).
    assert "rule_count: 24" in rendered


def test_install_skips_when_agent_dir_missing(tmp_path: Path) -> None:
    # No agent dirs exist — nothing should write.
    results = install_all(home=tmp_path, dry_run=False)
    for r in results:
        assert not r.written
        assert r.skipped_reason and "not found" in r.skipped_reason


def test_install_writes_skill_when_agent_dir_present(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    results = install_all(home=tmp_path, dry_run=False)
    claude = next(r for r in results if r.platform.key == "claude")
    assert claude.written
    assert claude.path.exists()
    content = claude.path.read_text()
    assert content.startswith("---\n")
    assert "name: aidoctor" in content


def test_install_idempotent(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    # First install.
    install_all(home=tmp_path)
    # Second install — should detect "already up to date".
    results = install_all(home=tmp_path)
    claude = next(r for r in results if r.platform.key == "claude")
    assert not claude.written
    assert claude.skipped_reason == "already up to date"


def test_install_force_overwrites(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    install_all(home=tmp_path)
    # Force re-install — should overwrite even though content matches.
    results = install_all(home=tmp_path, force=True)
    claude = next(r for r in results if r.platform.key == "claude")
    assert claude.written


def test_install_backs_up_existing_skill(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir(parents=True)
    target_dir = tmp_path / ".claude" / "skills" / "aidoctor"
    target_dir.mkdir(parents=True)
    target = target_dir / "SKILL.md"
    target.write_text("---\nname: old-skill\n---\n# Old content\n")
    results = install_all(home=tmp_path)
    claude = next(r for r in results if r.platform.key == "claude")
    assert claude.written
    assert claude.backed_up_from is not None
    backup = Path(str(claude.backed_up_from))
    assert backup.exists()
    assert backup.read_text() == "---\nname: old-skill\n---\n# Old content\n"


def test_install_dry_run_does_not_write(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    results = install_all(home=tmp_path, dry_run=True)
    claude = next(r for r in results if r.platform.key == "claude")
    assert not claude.written
    assert claude.skipped_reason == "dry-run"
    assert not (tmp_path / ".claude/skills/aidoctor/SKILL.md").exists()


def test_install_one_writes_to_correct_path(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    platform = next(p for p in load_platforms() if p.key == "cursor")
    result = install_one(platform, "test content\n", home=tmp_path)
    assert result.written
    expected = tmp_path / ".cursor/rules/aidoctor.mdc"
    assert result.path == expected
    assert expected.read_text() == "test content\n"
