"""
agent/model_discovery.py
Dynamically fetch available models from each provider's API.
Falls back to a curated static list when the API is unavailable.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Always reload .env so keys set after startup are picked up
_ENV_PATH = Path(__file__).parent.parent / ".env"


def _reload_env() -> None:
    load_dotenv(_ENV_PATH, override=True)


# ── Static fallbacks (used when API is unavailable) ────────────────────

_FALLBACK: dict[str, list[str]] = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": [
        "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
        "claude-3-haiku-20240307", "claude-3-opus-20240229",
    ],
    "google_genai": [
        "gemini-3-flash-preview", "gemini-2.5-flash",
        "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-flash-latest",
    ],
    "ollama": ["llama3.2", "llama3.1", "mistral", "codellama"],
}


# ── Per-provider fetchers ───────────────────────────────────────────────

def fetch_openai_models() -> list[str]:
    _reload_env()
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        models = [
            m.id for m in client.models.list()
            if "gpt" in m.id and "realtime" not in m.id and "audio" not in m.id
        ]
        return sorted(models, reverse=True) or _FALLBACK["openai"]
    except Exception:
        return _FALLBACK["openai"]


def fetch_anthropic_models() -> list[str]:
    _reload_env()
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        models = [m.id for m in client.models.list(limit=50)]
        return models or _FALLBACK["anthropic"]
    except Exception:
        return _FALLBACK["anthropic"]


def fetch_google_models() -> list[str]:
    _reload_env()
    try:
        from google import genai
        client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        models = []
        for m in client.models.list():
            name = m.name  # format: "models/gemini-2.0-flash"
            if not name.startswith("models/"):
                continue
            short = name[len("models/"):]
            # Only keep text generation models (skip tts, image-gen, audio, etc.)
            skip_keywords = ["tts", "image", "audio", "embedding", "aqa", "vision"]
            if any(k in short for k in skip_keywords):
                continue
            models.append(short)
        return models or _FALLBACK["google_genai"]
    except Exception:
        return _FALLBACK["google_genai"]


def fetch_ollama_models() -> list[str]:
    try:
        import ollama
        models = [m.model for m in ollama.list().models]
        # Strip the ":latest" tag for cleaner display
        models = [m.replace(":latest", "") for m in models]
        return models or _FALLBACK["ollama"]
    except Exception:
        return _FALLBACK["ollama"]


# ── Public API ──────────────────────────────────────────────────────────

FETCHERS = {
    "openai": fetch_openai_models,
    "anthropic": fetch_anthropic_models,
    "google_genai": fetch_google_models,
    "ollama": fetch_ollama_models,
}

PROVIDERS = list(FETCHERS.keys())


def fetch_models(provider: str) -> list[str]:
    """Return live model list for *provider*, falling back to static list."""
    fetcher = FETCHERS.get(provider)
    if fetcher is None:
        return []
    return fetcher()
