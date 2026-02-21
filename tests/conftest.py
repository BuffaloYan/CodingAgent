"""tests/conftest.py — shared fixtures"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml


@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    """A temporary workspace/ directory with one sample project."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "sample-project").mkdir()
    (ws / "sample-project" / "hello.py").write_text('print("hello")\n')
    return ws


@pytest.fixture()
def tmp_config(tmp_path: Path) -> Path:
    """A temporary config.yaml."""
    cfg = {
        "active_model": "openai/gpt-4o",
        "models": ["openai/gpt-4o"],
        "active_project": "sample-project",
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(cfg))
    return config_path


@pytest.fixture()
def tmp_env(tmp_path: Path) -> Path:
    """A temporary .env file."""
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=test-key\n")
    return env_path
