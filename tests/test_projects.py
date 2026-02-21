"""tests/test_projects.py — unit tests for core/projects.py"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


def _patch(ws: Path, cfg_path: Path = None):
    """Context manager patches for isolating project tests."""
    import yaml
    from unittest.mock import patch as _p

    patches = [
        _p("core.projects.WORKSPACE_ROOT", ws),
    ]
    if cfg_path:
        patches.append(_p("core.config.CONFIG_PATH", cfg_path))
    return patches


def apply_patches(patches):
    for p in patches:
        p.start()
    return patches


def stop_patches(patches):
    for p in patches:
        p.stop()


@pytest.fixture()
def ws_setup(tmp_path):
    import yaml

    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "proj-a").mkdir()
    (ws / "proj-b").mkdir()
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump({"active_project": "proj-a", "active_model": "openai/gpt-4o", "models": []}))
    patches = [
        patch("core.projects.WORKSPACE_ROOT", ws),
        patch("core.config.CONFIG_PATH", cfg_path),
    ]
    for p in patches:
        p.start()
    yield ws, cfg_path
    for p in patches:
        p.stop()


def test_list_projects(ws_setup):
    from core.projects import list_projects
    projects = list_projects()
    assert "proj-a" in projects
    assert "proj-b" in projects


def test_get_active_project(ws_setup):
    from core.projects import get_active_project
    result = get_active_project()
    assert result is not None
    assert result.name == "proj-a"


def test_set_active_project(ws_setup):
    from core.projects import set_active_project, get_active_project_name
    set_active_project("proj-b")
    assert get_active_project_name() == "proj-b"


def test_set_active_nonexistent_raises(ws_setup):
    from core.projects import set_active_project
    with pytest.raises(FileNotFoundError):
        set_active_project("does-not-exist")


def test_create_project(ws_setup):
    ws, _ = ws_setup
    from core.projects import create_project, get_active_project_name
    path = create_project("new-proj")
    assert path.is_dir()
    assert get_active_project_name() == "new-proj"


def test_create_project_duplicate_raises(ws_setup):
    from core.projects import create_project
    with pytest.raises(ValueError, match="already exists"):
        create_project("proj-a")


def test_create_project_empty_name_raises(ws_setup):
    from core.projects import create_project
    with pytest.raises(ValueError, match="empty"):
        create_project("   ")


def test_project_tree(ws_setup):
    ws, _ = ws_setup
    (ws / "proj-a" / "main.py").write_text("x=1")
    (ws / "proj-a" / "lib").mkdir()
    (ws / "proj-a" / "lib" / "util.py").write_text("y=2")
    from core.projects import project_tree
    items = project_tree(ws / "proj-a")
    paths = [i["path"] for i in items]
    assert "main.py" in paths
    assert "lib/util.py" in paths
