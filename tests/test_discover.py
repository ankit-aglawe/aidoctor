"""Tests for Python file discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from aidoctor.discover import NoPythonFilesError, find_python_files


def test_finds_python_files_in_directory(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    (tmp_path / "readme.md").write_text("not python\n")
    found = find_python_files([tmp_path])
    assert {p.name for p in found} == {"a.py", "b.py"}


def test_passes_through_single_python_file(tmp_path: Path) -> None:
    f = tmp_path / "single.py"
    f.write_text("x = 1\n")
    found = find_python_files([f])
    assert found == [f.resolve()]


def test_skips_non_python_file_passed_explicitly(tmp_path: Path) -> None:
    f = tmp_path / "readme.md"
    f.write_text("readme\n")
    with pytest.raises(NoPythonFilesError):
        find_python_files([f])


def test_skips_pycache_and_venv(tmp_path: Path) -> None:
    (tmp_path / "real.py").write_text("x = 1\n")
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "hidden.py").write_text("x = 1\n")
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "lib.py").write_text("x = 1\n")
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "x.py").write_text("x = 1\n")
    found = find_python_files([tmp_path])
    assert {p.name for p in found} == {"real.py"}


def test_respects_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored.py\n")
    (tmp_path / "kept.py").write_text("x = 1\n")
    (tmp_path / "ignored.py").write_text("x = 1\n")
    found = find_python_files([tmp_path])
    assert {p.name for p in found} == {"kept.py"}


def test_empty_directory_raises(tmp_path: Path) -> None:
    (tmp_path / "x.txt").write_text("not py\n")
    with pytest.raises(NoPythonFilesError):
        find_python_files([tmp_path])


def test_nonexistent_path_ignored(tmp_path: Path) -> None:
    real = tmp_path / "real.py"
    real.write_text("x = 1\n")
    bogus = tmp_path / "does-not-exist"
    found = find_python_files([real, bogus])
    assert found == [real.resolve()]


def test_recurses_into_subdirectories(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "deep.py").write_text("x = 1\n")
    found = find_python_files([tmp_path])
    assert {p.name for p in found} == {"deep.py"}


def test_disable_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored.py\n")
    (tmp_path / "kept.py").write_text("x = 1\n")
    (tmp_path / "ignored.py").write_text("x = 1\n")
    found = find_python_files([tmp_path], respect_gitignore=False)
    assert {p.name for p in found} == {"kept.py", "ignored.py"}
