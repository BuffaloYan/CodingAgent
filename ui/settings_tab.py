"""
ui/settings_tab.py
Model selection + API key management.
"""

from __future__ import annotations

import gradio as gr

from core.config import get_env_keys, load_config, save_config, save_env


def build_settings_tab(model_state: gr.State) -> None:
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
        gr.Markdown("### 🤖 Model")
        gr.Markdown(
            "Format: `provider/model-name`. Provider must be one of: "
            "`openai`, `anthropic`, `google_genai`, `ollama`."
        )
        with gr.Row():
            model_dropdown = gr.Dropdown(
                label="Active model",
                choices=model_list,
                value=current_model,
                allow_custom_value=True,
                interactive=True,
                scale=4,
            )
            save_model_btn = gr.Button("Save model", variant="primary", scale=1)

        gr.Markdown("#### ➕ Add a model to the list")
        with gr.Row():
            new_model_box = gr.Textbox(
                label="Model ID",
                placeholder="e.g. openai/gpt-4-turbo",
                scale=4,
            )
            add_model_btn = gr.Button("Add", scale=1)

        model_status = gr.Markdown("")

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

    def do_save_model(model_id: str):
        if not model_id:
            return "⚠️ Please select or enter a model ID.", gr.update(), model_id
        cfg = load_config()
        cfg["active_model"] = model_id
        save_config(cfg)
        return f"✅ Active model set to `{model_id}`", gr.update(value=model_id), model_id

    def do_add_model(new_id: str, current_choices: list):
        new_id = new_id.strip()
        if not new_id:
            return gr.update(), "⚠️ Enter a model ID."
        cfg = load_config()
        models = cfg.get("models", [])
        if new_id not in models:
            models.append(new_id)
            cfg["models"] = models
            save_config(cfg)
        return gr.update(choices=models, value=new_id), f"✅ Added `{new_id}` to model list."

    def do_save_keys(oai: str, ant: str, goog: str, g_user: str, g_pass: str):
        save_env({
            "OPENAI_API_KEY": oai,
            "ANTHROPIC_API_KEY": ant,
            "GOOGLE_API_KEY": goog,
            "GRADIO_AUTH_USER": g_user,
            "GRADIO_AUTH_PASSWORD": g_pass,
        })
        return "✅ Settings saved to `.env` (Restart app to apply auth changes)"

    save_model_btn.click(
        do_save_model,
        inputs=[model_dropdown],
        outputs=[model_status, model_dropdown, model_state],
    )
    add_model_btn.click(
        do_add_model,
        inputs=[new_model_box, model_dropdown],
        outputs=[model_dropdown, model_status],
    )
    save_keys_btn.click(
        do_save_keys,
        inputs=[openai_key, anthropic_key, google_key, gradio_auth_user, gradio_auth_password],
        outputs=[keys_status],
    )
