"""
ui/app.py
Main Gradio Blocks application — wires all tabs together.
Run with: python -m ui.app
"""

from __future__ import annotations

import gradio as gr

from core.config import load_config
from core.projects import get_active_project_name
from ui.chat_tab import build_chat_tab
from ui.download_tab import build_download_tab
from ui.project_tab import build_project_tab
from ui.settings_tab import build_settings_tab
from ui.workspace_tab import build_workspace_tab

# ── CSS ─────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
/* ── Global ── */
body, .gradio-container {
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace !important;
}

/* ── Header ── */
#app-header {
    background: linear-gradient(135deg, #1e1e2e 0%, #313244 100%);
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 16px;
    border: 1px solid #45475a;
}
#app-header h1 { color: #cdd6f4; margin: 0; font-size: 1.6rem; }
#app-header p  { color: #a6adc8; margin: 4px 0 0 0; font-size: 0.85rem; }

/* ── Chatbot ── */
#chatbot .message.assistant { background: #1e1e2e !important; }
#chatbot .message.user      { background: #313244 !important; }

/* ── Chat input ── */
#chat-input textarea {
    background: #1e1e2e !important;
    border: 1px solid #45475a !important;
    border-radius: 8px;
    color: #cdd6f4 !important;
}

/* ── Code editor ── */
#code-editor {
    border: 1px solid #45475a;
    border-radius: 8px;
}

/* ── File list ── */
#file-list { font-size: 0.82rem; }

/* ── Tab bar ── */
.tab-nav button {
    font-weight: 600;
    letter-spacing: 0.03em;
}

/* ── Status chips ── */
#chat-status {
    padding: 6px 12px;
    background: #1e1e2e;
    border-radius: 6px;
    border-left: 3px solid #89b4fa;
    font-size: 0.85rem;
    color: #cdd6f4;
}

/* ── Width constraint ── */
.gradio-container {
    min-width: 1024px !important;
    max-width: 66.67vw !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
"""


def build_app() -> gr.Blocks:
    cfg = load_config()

    with gr.Blocks() as app:

        # ── Shared state ────────────────────────────────────────────────
        model_state = gr.State(cfg.get("active_model", "openai/gpt-4o"))
        project_state = gr.State(get_active_project_name())

        # ── Header ──────────────────────────────────────────────────────
        with gr.Row(elem_id="app-header"):
            gr.HTML("""
                <h1>🤖Remote Coding Agent</h1>
                <p>Your remote AI coding assistant — powered by LangGraph &amp; Gradio 6</p>
            """)

        # ── Tabs ────────────────────────────────────────────────────────
        with gr.Tabs():
            with gr.Tab("💬 Chat"):
                build_chat_tab()

            with gr.Tab("🗂️ Workspace"):
                build_workspace_tab()

            with gr.Tab("📂 Projects"):
                build_project_tab()

            with gr.Tab("📥 Download"):
                build_download_tab()

            with gr.Tab("⚙️ Settings"):
                build_settings_tab(model_state)

    return app


def main():
    app = build_app()
    app.queue()
    app.launch(
        server_name="127.0.0.1",
        server_port=7862,
        inbrowser=True,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"],
        ),
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    main()
