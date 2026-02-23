import yaml
from pathlib import Path
from unittest.mock import patch
import pytest

from ui.settings_tab import (
    do_save_model,
    do_remove_unchecked,
    do_add_browsed,
    do_add_custom
)
from core.config import load_config

@pytest.fixture
def mock_config(tmp_path: Path):
    """Fixture to provide a mock config.yaml file and patch CONFIG_PATH."""
    config_path = tmp_path / "config.yaml"
    initial_data = {
        "active_model": "openai/gpt-4o",
        "models": ["openai/gpt-4o", "anthropic/claude-3-opus-20240229"]
    }
    with config_path.open("w") as f:
        yaml.safe_dump(initial_data, f)
        
    with patch("core.config.CONFIG_PATH", config_path):
        yield config_path

def test_do_save_model(mock_config):
    # Simulate saving a new active model
    msg, ui_update, new_id = do_save_model("anthropic/claude-3-opus-20240229")
    
    assert "✅" in msg
    assert new_id == "anthropic/claude-3-opus-20240229"
    
    # Verify disk persistence
    cfg = load_config()
    assert cfg["active_model"] == "anthropic/claude-3-opus-20240229"

def test_do_remove_unchecked(mock_config):
    # We uncheck 'anthropic/claude-3-opus-20240229' and keep only 'openai/gpt-4o'
    keep_models = ["openai/gpt-4o"]
    ui_checkbox, ui_dropdown, msg = do_remove_unchecked(keep_models)
    
    # check return values format
    assert ui_checkbox["choices"] == keep_models
    assert ui_dropdown["choices"] == keep_models
    assert ui_dropdown["value"] == "openai/gpt-4o"
    
    # Verify disk persistence
    cfg = load_config()
    assert cfg["models"] == keep_models
    assert cfg["active_model"] == "openai/gpt-4o"

def test_do_remove_active_model_fallback(mock_config):
    # If we remove the currently active model, it should fall back to first available
    keep_models = ["anthropic/claude-3-opus-20240229"]
    ui_checkbox, ui_dropdown, msg = do_remove_unchecked(keep_models)
    
    cfg = load_config()
    assert cfg["active_model"] == "anthropic/claude-3-opus-20240229"
    assert ui_dropdown["value"] == "anthropic/claude-3-opus-20240229"

def test_do_add_custom(mock_config):
    # User types a new model manually
    new_model = "google_genai/gemini-1.5-pro"
    current_checked = ["openai/gpt-4o", "anthropic/claude-3-opus-20240229"]
    
    ui_checkbox, ui_dropdown, msg, ui_textbox = do_add_custom(new_model, current_checked)
    
    cfg = load_config()
    assert new_model in cfg["models"]
    assert len(cfg["models"]) == 3
    
    assert new_model in ui_checkbox["choices"]
    assert new_model in ui_checkbox["value"]  # Automatically checked
    assert ui_textbox["value"] == ""          # text box cleared

def test_sync_models_logic(mock_config):
    """
    Test the sync_models logic that is inside app.py locally. 
    This is what makes the UI tabs refresh correctly from memory.
    """
    # 1. Simulate saving to disk from another tab
    do_add_custom("ollama/llama3", ["openai/gpt-4o", "anthropic/claude-3-opus-20240229"])
    
    # 2. Simulate what `sync_models()` in app.py does:
    cfg = load_config()
    models = cfg.get("models", [])
    act = cfg.get("active_model", "")
    
    assert "ollama/llama3" in models
    assert act == "openai/gpt-4o"
