"""tests/test_config.py — unit tests for core/config.py"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


def test_load_config_defaults(tmp_path: Path):
    """load_config() returns defaults when no config.yaml exists."""
    with patch("core.config.CONFIG_PATH", tmp_path / "nonexistent.yaml"):
        from core.config import load_config

        cfg = load_config()
    assert "active_model" in cfg
    assert "models" in cfg
    assert isinstance(cfg["models"], list)


def test_load_config_reads_file(tmp_path: Path):
    """load_config() merges on-disk values over defaults."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"active_model": "anthropic/claude-3-5-sonnet-20241022"}))
    with patch("core.config.CONFIG_PATH", config_path):
        from core.config import load_config

        cfg = load_config()
    assert cfg["active_model"] == "anthropic/claude-3-5-sonnet-20241022"


def test_save_config_round_trip(tmp_path: Path):
    """save_config() then load_config() returns the same values."""
    config_path = tmp_path / "config.yaml"
    with patch("core.config.CONFIG_PATH", config_path):
        from core.config import load_config, save_config

        original = load_config()
        original["active_model"] = "ollama/llama3.2"
        save_config(original)
        reloaded = load_config()

    assert reloaded["active_model"] == "ollama/llama3.2"


def test_save_env_creates_file(tmp_path: Path):
    """save_env() writes key=value pairs to .env."""
    env_path = tmp_path / ".env"
    with patch("core.config.ENV_PATH", env_path):
        from core.config import save_env

        save_env({"OPENAI_API_KEY": "sk-test"})

    content = env_path.read_text()
    assert "OPENAI_API_KEY=sk-test" in content


def test_save_env_preserves_existing_keys(tmp_path: Path):
    """save_env() does not clobber keys it wasn't asked to update."""
    env_path = tmp_path / ".env"
    env_path.write_text("ANTHROPIC_API_KEY=existing\n")
    with patch("core.config.ENV_PATH", env_path):
        from core.config import save_env

        save_env({"OPENAI_API_KEY": "new-oai"})

    content = env_path.read_text()
    assert "ANTHROPIC_API_KEY=existing" in content
    assert "OPENAI_API_KEY=new-oai" in content
