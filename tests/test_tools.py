"""tests/test_tools.py — unit tests for agent/tools.py"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.tools import make_tools, _resolve


# ── Helpers ──────────────────────────────────────────────────────────────

@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A temporary project root with some files."""
    (tmp_path / "hello.py").write_text('print("hello")\n')
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "util.py").write_text("x = 42\n")
    return tmp_path


@pytest.fixture()
def tools(project: Path):
    return {t.name: t for t in make_tools(project)}


# ── Sandbox ───────────────────────────────────────────────────────────────

def test_resolve_blocks_traversal(tmp_path: Path):
    with pytest.raises(PermissionError):
        _resolve(tmp_path, "../etc/passwd")


def test_resolve_allows_nested(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    result = _resolve(tmp_path, "sub/file.txt")
    assert str(result).startswith(str(tmp_path))


# ── read_file ─────────────────────────────────────────────────────────────

def test_read_file_success(tools):
    result = tools["read_file"].invoke({"path": "hello.py"})
    assert 'print("hello")' in result


def test_read_file_not_found(tools):
    result = tools["read_file"].invoke({"path": "missing.py"})
    assert "ERROR" in result


# ── write_file ────────────────────────────────────────────────────────────

def test_write_file_creates(tools, project: Path):
    tools["write_file"].invoke({"path": "new.txt", "content": "hi there"})
    assert (project / "new.txt").read_text() == "hi there"


def test_write_file_creates_subdirs(tools, project: Path):
    tools["write_file"].invoke({"path": "deep/nested/file.txt", "content": "x"})
    assert (project / "deep" / "nested" / "file.txt").exists()


def test_write_file_sandboxed(tools):
    result = tools["write_file"].invoke({"path": "../evil.txt", "content": "!"})
    assert "ERROR" in result or "denied" in result.lower()


# ── list_directory ────────────────────────────────────────────────────────

def test_list_directory_root(tools):
    result = tools["list_directory"].invoke({"path": "."})
    assert "hello.py" in result


def test_list_directory_subdir(tools):
    result = tools["list_directory"].invoke({"path": "sub"})
    assert "util.py" in result


# ── delete_file ───────────────────────────────────────────────────────────

def test_delete_file(tools, project: Path):
    tools["delete_file"].invoke({"path": "hello.py"})
    assert not (project / "hello.py").exists()


def test_delete_file_not_found(tools):
    result = tools["delete_file"].invoke({"path": "ghost.py"})
    assert "ERROR" in result


# ── search_code ───────────────────────────────────────────────────────────

def test_search_code_finds_match(tools):
    result = tools["search_code"].invoke({"query": "print", "path": "."})
    assert "hello.py" in result


def test_search_code_no_match(tools):
    result = tools["search_code"].invoke({"query": "zzz_not_here", "path": "."})
    assert "No matches" in result
