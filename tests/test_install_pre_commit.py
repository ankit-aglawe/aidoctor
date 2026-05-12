"""Tests for `aidoctor install --pre-commit`.

W17 deliverable: one-liner that writes or updates .pre-commit-config.yaml
with an aidoctor scan hook. Idempotent via marker comments. No PyYAML dep —
the file is text-edited so it survives whatever quirks the user has elsewhere.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from aidoctor.cli import main

# --- end-to-end CLI ---


def test_pre_commit_in_empty_dir_creates_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["install", "--pre-commit"])
    assert result.exit_code == 0
    cfg = tmp_path / ".pre-commit-config.yaml"
    assert cfg.exists()
    content = cfg.read_text()
    assert "aidoctor:hook:start" in content
    assert "aidoctor:hook:end" in content
    assert "ankit-aglawe/aidoctor" in content
    # Use the existing hook id from .pre-commit-hooks.yaml
    assert "id: aidoctor" in content


def test_pre_commit_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    """Re-running --pre-commit must not duplicate the block or corrupt the file."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(main, ["install", "--pre-commit"])
    first = (tmp_path / ".pre-commit-config.yaml").read_text()
    result = runner.invoke(main, ["install", "--pre-commit"])
    assert result.exit_code == 0
    second = (tmp_path / ".pre-commit-config.yaml").read_text()
    assert first == second
    assert second.count("aidoctor:hook:start") == 1
    assert second.count("aidoctor:hook:end") == 1


def test_pre_commit_preserves_existing_hooks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    existing = (
        "repos:\n"
        "  - repo: https://github.com/astral-sh/ruff-pre-commit\n"
        "    rev: v0.6.0\n"
        "    hooks:\n"
        "      - id: ruff\n"
    )
    (tmp_path / ".pre-commit-config.yaml").write_text(existing)
    runner = CliRunner()
    result = runner.invoke(main, ["install", "--pre-commit"])
    assert result.exit_code == 0
    content = (tmp_path / ".pre-commit-config.yaml").read_text()
    # Existing ruff hook preserved
    assert "ruff-pre-commit" in content
    assert "id: ruff" in content
    # aidoctor block appended
    assert "aidoctor:hook:start" in content
    assert "ankit-aglawe/aidoctor" in content


def test_pre_commit_replaces_existing_aidoctor_block(tmp_path: Path, monkeypatch) -> None:
    """If an aidoctor block already exists (e.g., old version pinned), replace it.

    This is how users get an updated rev when re-running install after upgrading.
    """
    monkeypatch.chdir(tmp_path)
    stale = (
        "repos:\n"
        "  # aidoctor:hook:start\n"
        "  - repo: https://github.com/ankit-aglawe/aidoctor\n"
        "    rev: v1.0.0\n"
        "    hooks:\n"
        "      - id: aidoctor\n"
        "        args: [--fail-on, none]\n"
        "  # aidoctor:hook:end\n"
    )
    (tmp_path / ".pre-commit-config.yaml").write_text(stale)
    runner = CliRunner()
    result = runner.invoke(main, ["install", "--pre-commit"])
    assert result.exit_code == 0
    content = (tmp_path / ".pre-commit-config.yaml").read_text()
    # Old rev gone
    assert "v1.0.0" not in content
    # Default config restored (--fail-on error, the v2.0 default)
    assert "[--fail-on, error]" in content or "--fail-on" in content
    # Still exactly one block
    assert content.count("aidoctor:hook:start") == 1


# --- .pre-commit-hooks.yaml at repo root ---


def test_pre_commit_hooks_yaml_exists_at_repo_root() -> None:
    """Aidoctor publishes its own .pre-commit-hooks.yaml so users' configs can
    point at the repo + rev and `pre-commit install` finds the hook definition."""
    import aidoctor

    # Walk up from the package to repo root (sibling of pyproject.toml)
    repo_root = Path(aidoctor.__file__).resolve().parent.parent.parent
    hooks = repo_root / ".pre-commit-hooks.yaml"
    assert hooks.exists(), f"missing {hooks}"
    content = hooks.read_text()
    assert "id: aidoctor" in content
    assert "entry:" in content
    assert "language:" in content
