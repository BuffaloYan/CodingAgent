"""
agent/models.py
LLM factory: build a LangChain chat model from a "provider/model-name" string.
API keys are read from environment variables (loaded from .env by core/config.py).
"""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


def build_model(model_id: str, temperature: float = 0.2) -> BaseChatModel:
    """
    Build a LangChain chat model from *model_id*.

    Format:  "<provider>/<model-name>"
    Examples:
      "openai/gpt-4o"
      "anthropic/claude-3-5-sonnet-20241022"
      "google_genai/gemini-3-flash"
      "ollama/llama3.2"

    API keys are picked up automatically from env vars:
      OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
    """
    # Reload .env every call so keys set after startup are picked up
    from core.config import ENV_PATH
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH, override=True)

    if "/" not in model_id:
        raise ValueError(
            f"model_id must be 'provider/model-name', got: {model_id!r}"
        )
    provider, model_name = model_id.split("/", 1)
    return init_chat_model(
        model=model_name,
        model_provider=provider,
        temperature=temperature,
    )
