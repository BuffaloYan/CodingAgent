"""
core/config.py
Load and save config.yaml. Also bootstraps .env via python-dotenv.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
ENV_PATH = REPO_ROOT / ".env"
WORKSPACE_ROOT = REPO_ROOT / "workspace"

# Load .env into os.environ at import time (.env always wins over shell env)
load_dotenv(ENV_PATH, override=True)

# ── Defaults ───────────────────────────────────────────────────────────
_DEFAULTS: dict = {
    "active_model": "openai/gpt-4o",
    "models": [
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "anthropic/claude-3-5-sonnet-20241022",
        "anthropic/claude-3-haiku-20240307",
        "google_genai/gemini-2.0-flash",
        "ollama/llama3.2",
    ],
    "active_project": "",
}


def load_config() -> dict:
    """Return merged config (defaults ← config.yaml)."""
    cfg = dict(_DEFAULTS)
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            on_disk = yaml.safe_load(f) or {}
        cfg.update({k: v for k, v in on_disk.items() if v is not None})
    return cfg


def save_config(cfg: dict) -> None:
    """Persist *cfg* to config.yaml."""
    with CONFIG_PATH.open("w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, allow_unicode=True)


def save_env(keys: dict[str, str]) -> None:
    """
    Write *keys* to .env (only non-empty values are written).
    Existing keys that are not in *keys* are preserved.
    """
    existing: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()

    existing.update({k: v for k, v in keys.items() if v})

    lines = ["# Managed by agent-by-claude — do not commit this file\n"]
    for k, v in existing.items():
        lines.append(f"{k}={v}\n")

    ENV_PATH.write_text("".join(lines))
    # Reload into os.environ
    load_dotenv(ENV_PATH, override=True)


def get_env_keys() -> dict[str, str]:
    """Return current API-key env vars (masked values for display)."""
    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
    }
