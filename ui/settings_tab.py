"""
ui/settings_tab.py
Model selection + API key management.
"""

from __future__ import annotations

import gradio as gr

from agent.model_discovery import PROVIDERS, fetch_models
from core.config import get_env_keys, load_config, save_config, save_env


import gradio as gr

from agent.model_discovery import PROVIDERS, fetch_models
from core.config import get_env_keys, load_config, save_config, save_env

# ── Module-level Handlers for Testability ─────────────────────────────────────

def do_save_model(model_id: str):
    if not model_id:
        return "⚠️ Please select a model ID.", gr.update(), model_id
    cfg = load_config()
    cfg["active_model"] = model_id
    save_config(cfg)
    return f"✅ Active model set to `{model_id}`", gr.update(value=model_id), model_id

def do_remove_unchecked(checked_models: list[str]):
    cfg = load_config()
    cfg["models"] = checked_models
    active = cfg.get("active_model")
    if active not in checked_models and checked_models:
        cfg["active_model"] = checked_models[0]
    save_config(cfg)
    return (
        gr.update(choices=checked_models, value=checked_models),
        gr.update(choices=checked_models, value=cfg.get("active_model", "")),
        f"✅ Kept {len(checked_models)} models."
    )

def do_browse_provider(provider: str):
    models = fetch_models(provider)
    if not models:
        return gr.update(choices=["No models found"], value="")
    return gr.update(choices=models, value=models[0])

def do_add_browsed(provider: str, model: str, current_checked: list[str]):
    if not provider or not model or model == "No models found":
        return gr.update(), gr.update(), "⚠️ Please select a valid provider and model."
    model_id = f"{provider}/{model}"
    cfg = load_config()
    models = cfg.get("models", [])
    if model_id not in models:
        models.append(model_id)
        cfg["models"] = models
        save_config(cfg)
        current_checked.append(model_id)
    return (
        gr.update(choices=models, value=current_checked),
        gr.update(choices=models),
        f"✅ Added `{model_id}` to selected list."
    )

def do_add_custom(new_id: str, current_checked: list[str]):
    new_id = new_id.strip()
    if not new_id or "/" not in new_id:
        return gr.update(), gr.update(), "⚠️ Enter a valid model ID (provider/model)."
    cfg = load_config()
    models = cfg.get("models", [])
    if new_id not in models:
        models.append(new_id)
        cfg["models"] = models
        save_config(cfg)
        current_checked.append(new_id)
    return (
        gr.update(choices=models, value=current_checked),
        gr.update(choices=models),
        f"✅ Added custom `{new_id}` to selected list.",
        gr.update(value="")
    )

def do_save_keys(oai: str, ant: str, goog: str, g_user: str, g_pass: str):
    save_env({
        "OPENAI_API_KEY": oai,
        "ANTHROPIC_API_KEY": ant,
        "GOOGLE_API_KEY": goog,
        "GRADIO_AUTH_USER": g_user,
        "GRADIO_AUTH_PASSWORD": g_pass,
    })
    return "✅ Settings saved to `.env` (Restart app to apply changes)"

# ── UI Builder ───────────────────────────────────────────────────────────────

def build_settings_tab(model_state: gr.State) -> tuple[gr.Dropdown, gr.CheckboxGroup]:
    """Render the Settings tab."""

    def load_settings():
        cfg = load_config()
        keys = get_env_keys()
        return (
            cfg.get("active_model", "openai/gpt-4o"),
            cfg.get("models", []),
            keys.get("OPENAI_API_KEY", ""),
            keys.get("ANTHROPIC_API_KEY", ""),
            keys.get("GOOGLE_API_KEY", ""),
            keys.get("GRADIO_AUTH_USER", ""),
            keys.get("GRADIO_AUTH_PASSWORD", ""),
        )

    current_model, model_list, oai_key, ant_key, goog_key, g_user, g_pass = load_settings()

    with gr.Column():
        gr.Markdown("## ⚙️ Settings")

        # ── Model ──────────────────────────────────────────────────────
        gr.Markdown("### 🤖 Default Active Model")
        gr.Markdown("Choose the model that will be selected by default when you open the Chat.")
        with gr.Row():
            model_dropdown = gr.Dropdown(
                label="Active model",
                choices=model_list,
                value=current_model if current_model in model_list else (model_list[0] if model_list else ""),
                interactive=True,
                scale=4,
            )
            save_model_btn = gr.Button("Save Active Model", variant="primary", scale=1)

        model_status = gr.Markdown("")

        gr.Markdown("---")
        gr.Markdown("### 📋 Manage Selected Models")
        gr.Markdown("These models appear in your curated list in the Chat tab.")

        with gr.Row():
            selected_models_group = gr.CheckboxGroup(
                label="Currently Selected Models",
                choices=model_list,
                value=model_list,
                interactive=True,
            )
        remove_models_btn = gr.Button("🗑️ Remove Unchecked Models", size="sm")
        manage_status = gr.Markdown("")

        gr.Markdown("#### ➕ Add Models")
        with gr.Row():
            provider_dropdown = gr.Dropdown(
                label="1. Select Provider",
                choices=PROVIDERS,
                value=PROVIDERS[0] if PROVIDERS else None,
                interactive=True,
                scale=1,
            )
            available_models_dropdown = gr.Dropdown(
                label="2. Browse Available Models",
                choices=[],
                interactive=True,
                scale=3,
            )
            add_browsed_btn = gr.Button("Add to Selected", variant="primary", scale=1)

        gr.Markdown("#### Or Add Custom ID Manually")
        with gr.Row():
            new_model_box = gr.Textbox(
                label="Custom Model ID",
                placeholder="e.g. provider/model-name",
                scale=4,
            )
            add_custom_btn = gr.Button("Add Custom", scale=1)

        gr.Markdown("---")

        # ── API Keys ───────────────────────────────────────────────────
        gr.Markdown("### 🔑 API Keys")
        gr.Markdown(
            "Keys are saved to **`.env`** (never committed to git). "
            "Leave a field blank to keep the existing value."
        )

        with gr.Column():
            openai_key = gr.Textbox(
                label="OpenAI API Key",
                value=oai_key,
                type="password",
                placeholder="sk-…",
            )
            anthropic_key = gr.Textbox(
                label="Anthropic API Key",
                value=ant_key,
                type="password",
                placeholder="sk-ant-…",
            )
            google_key = gr.Textbox(
                label="Google API Key",
                value=goog_key,
                type="password",
                placeholder="AIza…",
            )
            gr.Markdown("#### Gradio App Authentication (Local & Public)")
            with gr.Row():
                gradio_auth_user = gr.Textbox(
                    label="Gradio Username",
                    value=g_user,
                    placeholder="admin",
                )
                gradio_auth_password = gr.Textbox(
                    label="Gradio Password",
                    value=g_pass,
                    type="password",
                    placeholder="choose-a-safe-password",
                )

        save_keys_btn = gr.Button("💾 Save Keys", variant="primary")
        keys_status = gr.Markdown("")

    # ── Events ─────────────────────────────────────────────────────────

    save_model_btn.click(
        do_save_model,
        inputs=[model_dropdown],
        outputs=[model_status, model_dropdown, model_state],
    )

    remove_models_btn.click(
        do_remove_unchecked,
        inputs=[selected_models_group],
        outputs=[selected_models_group, model_dropdown, manage_status]
    )

    provider_dropdown.change(
        do_browse_provider,
        inputs=[provider_dropdown],
        outputs=[available_models_dropdown]
    )

    add_browsed_btn.click(
        do_add_browsed,
        inputs=[provider_dropdown, available_models_dropdown, selected_models_group],
        outputs=[selected_models_group, model_dropdown, manage_status]
    )

    add_custom_btn.click(
        do_add_custom,
        inputs=[new_model_box, selected_models_group],
        outputs=[selected_models_group, model_dropdown, manage_status, new_model_box]
    )

    save_keys_btn.click(
        do_save_keys,
        inputs=[openai_key, anthropic_key, google_key, gradio_auth_user, gradio_auth_password],
        outputs=[keys_status],
    )

    # Fetch initial models for the default provider
    def _init_models():
        if PROVIDERS:
            return do_browse_provider(PROVIDERS[0])
        return gr.update()
    
    # We can't easily trigger this on load within Blocks cleanly without demo.load, 
    # but we can at least return a default empty list, and let the user change the dropdown
    # to trigger the fetch. Actually, gradio triggers `change` if we set a default value, 
    # but let's wire a `.load` if possible, not supported here directly.

    return model_dropdown, selected_models_group

