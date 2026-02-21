"""
core/projects.py
Project management: list, create, switch projects inside workspace/.
"""

from __future__ import annotations

from pathlib import Path

from core.config import WORKSPACE_ROOT, load_config, save_config


def ensure_workspace() -> Path:
    """Create workspace/ if it doesn't exist yet."""
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    return WORKSPACE_ROOT


def list_projects() -> list[str]:
    """Return sorted list of project names (subdirs of workspace/)."""
    ensure_workspace()
    return sorted(
        p.name for p in WORKSPACE_ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")
    )


def get_active_project() -> Path | None:
    """Return Path to active project dir, or None if not set / missing."""
    cfg = load_config()
    name = cfg.get("active_project", "").strip()
    if not name:
        return None
    path = WORKSPACE_ROOT / name
    return path if path.is_dir() else None


def get_active_project_name() -> str:
    """Return active project name string (empty string if none)."""
    cfg = load_config()
    return cfg.get("active_project", "").strip()


def set_active_project(name: str) -> Path:
    """Switch active project to *name* (must already exist in workspace/)."""
    path = WORKSPACE_ROOT / name
    if not path.is_dir():
        raise FileNotFoundError(f"Project '{name}' not found in workspace/")
    cfg = load_config()
    cfg["active_project"] = name
    save_config(cfg)
    return path


def create_project(name: str) -> Path:
    """
    Create workspace/<name>/ and switch to it.
    Raises ValueError if name is invalid or already exists.
    """
    name = name.strip()
    if not name:
        raise ValueError("Project name cannot be empty.")
    if "/" in name or "\\" in name:
        raise ValueError("Project name must not contain path separators.")

    path = WORKSPACE_ROOT / name
    if path.exists():
        raise ValueError(f"Project '{name}' already exists.")

    path.mkdir(parents=True)
    set_active_project(name)
    return path


def project_tree(project_path: Path) -> list[dict]:
    """
    Return a flat list of dicts describing every file/dir inside project_path.
    Each dict: {"path": relative_str, "is_dir": bool, "name": str}
    Sorted: dirs before files, then alphabetically.
    """
    items = []
    for p in sorted(project_path.rglob("*")):
        if any(part.startswith(".") for part in p.parts):
            continue  # skip hidden files/dirs
        rel = p.relative_to(project_path)
        items.append({"path": str(rel), "is_dir": p.is_dir(), "name": p.name})
    return items
