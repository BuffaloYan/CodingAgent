"""
tests/test_env_loading.py
Diagnostic tests for .env loading and API key availability.
Run with: make test  (or .venv/bin/pytest tests/test_env_loading.py -v)
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).parent.parent


def test_env_file_exists():
    """The .env file must exist at the repo root."""
    env_path = REPO_ROOT / ".env"
    assert env_path.exists(), (
        f".env not found at {env_path}. "
        "Copy .env.example to .env and fill in your API keys."
    )


def test_google_api_key_in_env_file():
    """GOOGLE_API_KEY must be present and non-empty in .env."""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return  # covered by test_env_file_exists

    content = env_path.read_text()
    lines = {
        k.strip(): v.strip()
        for line in content.splitlines()
        if not line.startswith("#") and "=" in line
        for k, _, v in [line.partition("=")]
    }

    assert "GOOGLE_API_KEY" in lines, (
        "GOOGLE_API_KEY line is missing from .env. "
        "Add: GOOGLE_API_KEY=your_key_here"
    )
    assert lines["GOOGLE_API_KEY"], (
        "GOOGLE_API_KEY is in .env but the value is empty. "
        "Set it to your actual Google API key."
    )


def test_load_dotenv_sets_google_key():
    """load_dotenv(override=True) must expose GOOGLE_API_KEY in os.environ."""
    from dotenv import load_dotenv
    from core.config import ENV_PATH

    # Temporarily remove from env to test loading from scratch
    original = os.environ.pop("GOOGLE_API_KEY", None)
    try:
        load_dotenv(ENV_PATH, override=True)
        key = os.environ.get("GOOGLE_API_KEY", "")
        assert key, (
            "GOOGLE_API_KEY is not set after load_dotenv. "
            "Check that .env contains: GOOGLE_API_KEY=your_key_here"
        )
    finally:
        # Restore original env state
        if original is not None:
            os.environ["GOOGLE_API_KEY"] = original
        elif "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]


def test_all_expected_keys_present_in_env_example():
    """The .env.example template should list all expected keys."""
    example_path = REPO_ROOT / ".env.example"
    assert example_path.exists(), ".env.example missing from repo root"
    content = example_path.read_text()
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        assert key in content, f"{key} missing from .env.example"
