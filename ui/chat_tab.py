"""
ui/chat_tab.py
Chat tab: streaming chat with dynamic provider → model dropdowns.
Models are fetched live from each provider's API on launch and provider switch.
"""

from __future__ import annotations

import gradio as gr

from agent.agent import get_agent, stream_response
from core.config import load_config
from core.projects import get_active_project, get_active_project_name


def _parse_model_id(model_id: str) -> tuple[str, str]:
    if "/" in model_id:
        provider, _, model = model_id.partition("/")
        return provider, model
    return "openai", model_id


def build_chat_tab() -> gr.Dropdown:
    """Render the Chat tab using the curated model list from config."""

    cfg = load_config()
    model_list = cfg.get("models", [])
    default_model_id = cfg.get("active_model", "openai/gpt-4o")
    if default_model_id not in model_list and model_list:
        default_model_id = model_list[0]

    with gr.Column():
        status_bar = gr.Markdown(
            "**No project selected.** Go to Projects tab to set one up.",
            elem_id="chat-status",
        )

        # ── Curated Model selector ───────────────────────────────────
        with gr.Row():
            model_dropdown = gr.Dropdown(
                label="Model",
                choices=model_list,
                value=default_model_id,
                allow_custom_value=False,
                interactive=True,
                scale=4,
            )

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

    def save_model_selection(model_id: str) -> None:
        """Persist active_model to config.yaml silently."""
        if model_id:
            from core.config import save_config, load_config
            cfg = load_config()
            cfg["active_model"] = model_id
            save_config(cfg)

    def get_status(model_id: str) -> str:
        name = get_active_project_name()
        if name:
            return f"📁 **Project:** `{name}` &nbsp;|&nbsp; 🤖 **Model:** `{model_id}`"
        return "⚠️ **No project selected.** Go to the Projects tab to create or switch projects."

    def user_msg(user_input: str, history: list[dict]):
        history = history or []
        history.append({"role": "user", "content": user_input})
        return "", history

    async def bot_respond(history: list[dict], model_id: str):
        """Stream agent response using the selected model."""
        project_path = get_active_project()
        if not project_path:
            history.append({
                "role": "assistant",
                "content": "⚠️ Please select a project first (Projects tab).",
            })
            yield history
            return

        if not model_id:
            history.append({"role": "assistant", "content": "⚠️ Please select a model."})
            yield history
            return

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
            '<span style="display:inline-block;animation:pulse 1.4s ease-in-out infinite;">'
            '●</span>'
            '<span style="display:inline-block;animation:pulse 1.4s ease-in-out 0.2s infinite;">'
            '●</span>'
            '<span style="display:inline-block;animation:pulse 1.4s ease-in-out 0.4s infinite;">'
            '●</span>'
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
                    summary = "📤 Result"
                    tool_block += (
                        f"\n\n<details><summary>{summary}</summary>\n\n"
                        f"```\n{content}\n```\n\n</details>"
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
                s = "s" if step_count != 1 else ""
                assistant_text = f"✅ **Done** — completed {step_count} step{s}."
            else:
                assistant_text = "✅ **Done.**"

        history[-1] = {"role": "assistant", "content": _render(working=False)}
        yield history

    # ── Wire events ────────────────────────────────────────────────────

    # Update status bar + save when model changes
    model_dropdown.change(
        get_status,
        inputs=[model_dropdown],
        outputs=[status_bar],
    ).then(
        save_model_selection,
        inputs=[model_dropdown],
        outputs=None,
    )

    msg_box.submit(user_msg, [msg_box, chatbot], [msg_box, chatbot], queue=False).then(
        bot_respond, [chatbot, model_dropdown], chatbot
    )
    send_btn.click(user_msg, [msg_box, chatbot], [msg_box, chatbot], queue=False).then(
        bot_respond, [chatbot, model_dropdown], chatbot
    )
    clear_btn.click(lambda: [], None, chatbot)

    # Populate status on load
    status_bar.value = get_status(default_model_id)

    return model_dropdown
