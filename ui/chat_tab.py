"""
ui/chat_tab.py
Chat tab: streaming chat with dynamic provider → model dropdowns.
Models are fetched live from each provider's API on launch and provider switch.
"""

from __future__ import annotations

import gradio as gr

from agent.agent import get_agent, stream_response
from agent.model_discovery import PROVIDERS, fetch_models
from core.config import load_config
from core.projects import get_active_project, get_active_project_name


def _parse_model_id(model_id: str) -> tuple[str, str]:
    if "/" in model_id:
        provider, _, model = model_id.partition("/")
        return provider, model
    return "openai", model_id


def build_chat_tab() -> None:
    """Render the Chat tab with live provider → model dropdowns."""

    cfg = load_config()
    default_model_id = cfg.get("active_model", "openai/gpt-4o")
    default_provider, default_model = _parse_model_id(default_model_id)

    # Fetch models for the default provider at launch
    initial_models = fetch_models(default_provider)
    initial_model = default_model if default_model in initial_models else (initial_models[0] if initial_models else "")

    with gr.Column():
        status_bar = gr.Markdown(
            "**No project selected.** Go to Projects tab to set one up.",
            elem_id="chat-status",
        )

        # ── Provider + Model selectors ───────────────────────────────────
        with gr.Row():
            provider_dropdown = gr.Dropdown(
                label="Provider",
                choices=PROVIDERS,
                value=default_provider,
                interactive=True,
                scale=1,
            )
            model_dropdown = gr.Dropdown(
                label="Model",
                choices=initial_models,
                value=initial_model,
                allow_custom_value=True,
                interactive=True,
                scale=3,
            )
            refresh_models_btn = gr.Button("⟳", size="sm", scale=0, elem_id="refresh-models-btn")

        chatbot = gr.Chatbot(
            label="Agent",
            buttons=["copy"],
            layout="bubble",
            height=500,
            elem_id="chatbot",
            avatar_images=(None, "https://api.dicebear.com/9.x/bottts/svg?seed=agent"),
        )

        with gr.Row():
            msg_box = gr.Textbox(
                placeholder="Ask the agent to write code, read files, run tests…",
                show_label=False,
                scale=9,
                autofocus=True,
                elem_id="chat-input",
            )
            send_btn = gr.Button("Send", variant="primary", scale=1)

        clear_btn = gr.Button("🗑️ Clear Chat", size="sm")

    # ── Helpers ────────────────────────────────────────────────────────

    def save_model_selection(provider: str, model: str) -> None:
        """Persist active_model to config.yaml silently."""
        if provider and model:
            from core.config import save_config, load_config
            cfg = load_config()
            cfg["active_model"] = f"{provider}/{model}"
            save_config(cfg)

    def on_provider_change(provider: str):
        """Fetch live models then update the model dropdown."""
        models = fetch_models(provider)
        first = models[0] if models else ""
        return gr.update(choices=models, value=first)

    def get_status(provider: str, model: str) -> str:
        name = get_active_project_name()
        model_id = f"{provider}/{model}" if model else provider
        if name:
            return f"📁 **Project:** `{name}` &nbsp;|&nbsp; 🤖 **Model:** `{model_id}`"
        return "⚠️ **No project selected.** Go to the Projects tab to create or switch projects."

    def user_msg(user_input: str, history: list[dict]):
        history = history or []
        history.append({"role": "user", "content": user_input})
        return "", history

    async def bot_respond(history: list[dict], provider: str, model: str):
        """Stream agent response using the selected provider/model."""
        project_path = get_active_project()
        if not project_path:
            history.append({
                "role": "assistant",
                "content": "⚠️ Please select a project first (Projects tab).",
            })
            yield history
            return

        if not model:
            history.append({"role": "assistant", "content": "⚠️ Please select a model."})
            yield history
            return

        model_id = f"{provider}/{model}"
        try:
            agent = get_agent(model_id, project_path)
        except Exception as e:
            history.append({"role": "assistant", "content": f"❌ Failed to create agent: {e}"})
            yield history
            return

        user_input = next(
            (m["content"] for m in reversed(history) if m["role"] == "user"), ""
        )
        prior_history = history[:-1]

        # ── Streaming state ─────────────────────────────────────────
        assistant_text = ""   # final narrative text from model
        tool_block = ""       # accumulated collapsible tool call/result blocks
        step_count = 0
        current_step = ""     # label of the currently-running tool

        WORKING_ANIMATION = (
            '<div style="display:inline-flex;align-items:center;gap:6px;'
            'padding:6px 14px;background:linear-gradient(135deg,#1e293b,#334155);'
            'border-radius:8px;font-size:0.9rem;color:#93c5fd;margin-bottom:8px;">'
            '<span style="display:inline-block;animation:pulse 1.4s ease-in-out infinite;">●</span>'
            '<span style="display:inline-block;animation:pulse 1.4s ease-in-out 0.2s infinite;">●</span>'
            '<span style="display:inline-block;animation:pulse 1.4s ease-in-out 0.4s infinite;">●</span>'
            '&nbsp; <b>{label}</b>'
            '</div>'
            '<style>@keyframes pulse{{0%,100%{{opacity:.3}}50%{{opacity:1}}}}</style>'
        )

        def _render(*, working: bool) -> str:
            """Build the bubble content with animated progress or completion banner."""
            parts = []
            if working:
                label = current_step or "Starting"
                parts.append(WORKING_ANIMATION.format(label=label))
            if assistant_text:
                parts.append(assistant_text)
            if tool_block:
                parts.append(tool_block)
            if not working and parts:
                # Clear completion footer
                parts.append("\n\n---\n*What else can I help you with?* 🚀")
            return "\n\n".join(parts) if parts else WORKING_ANIMATION.format(label="Starting")

        # Seed the bubble immediately so the user sees the animation
        history.append({"role": "assistant", "content": WORKING_ANIMATION.format(label="Starting")})
        yield history

        try:
            async for chunk_type, content in stream_response(agent, prior_history, user_input):
                if chunk_type == "text":
                    assistant_text += content

                elif chunk_type == "step":
                    step_count += 1
                    current_step = content  # e.g. "Step 2 — `list_directory`"

                elif chunk_type == "tool_call":
                    tool_block += (
                        f"\n\n<details><summary>🔧 Tool call</summary>\n\n{content}\n\n</details>"
                    )

                elif chunk_type == "tool_result":
                    tool_block += (
                        f"\n\n<details><summary>📤 Result</summary>\n\n```\n{content}\n```\n\n</details>"
                    )

                history[-1] = {"role": "assistant", "content": _render(working=True)}
                yield history

        except Exception as e:
            history[-1] = {"role": "assistant", "content": f"❌ Error: {e}"}
            yield history
            return

        # ── Final message ────────────────────────────────────────────
        if not assistant_text.strip():
            if step_count > 0:
                assistant_text = f"✅ **Done** — completed {step_count} step{'s' if step_count != 1 else ''}."
            else:
                assistant_text = "✅ **Done.**"

        history[-1] = {"role": "assistant", "content": _render(working=False)}
        yield history

    # ── Wire events ────────────────────────────────────────────────────

    # Update status bar + save when model changes
    model_dropdown.change(
        get_status,
        inputs=[provider_dropdown, model_dropdown],
        outputs=[status_bar],
    ).then(
        save_model_selection,
        inputs=[provider_dropdown, model_dropdown],
        outputs=None,
    )

    # After provider change: refresh models, then save the new selection
    provider_dropdown.change(
        on_provider_change,
        inputs=[provider_dropdown],
        outputs=[model_dropdown],
    ).then(
        get_status,
        inputs=[provider_dropdown, model_dropdown],
        outputs=[status_bar],
    )

    # Manual ⟳ button — re-fetch models for current provider (no save needed)
    refresh_models_btn.click(
        on_provider_change,
        inputs=[provider_dropdown],
        outputs=[model_dropdown],
    )

    msg_box.submit(user_msg, [msg_box, chatbot], [msg_box, chatbot], queue=False).then(
        bot_respond, [chatbot, provider_dropdown, model_dropdown], chatbot
    )
    send_btn.click(user_msg, [msg_box, chatbot], [msg_box, chatbot], queue=False).then(
        bot_respond, [chatbot, provider_dropdown, model_dropdown], chatbot
    )
    clear_btn.click(lambda: [], None, chatbot)

    # Populate status on load
    status_bar.value = get_status(default_provider, initial_model)
