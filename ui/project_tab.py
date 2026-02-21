"""
ui/project_tab.py
Project management tab: list, create, and switch projects inside workspace/.
"""

from __future__ import annotations

import gradio as gr

from core.projects import (
    create_project,
    get_active_project_name,
    list_projects,
    set_active_project,
)


def build_project_tab() -> None:
    """Render the Projects tab UI."""

    def refresh_projects():
        projects = list_projects()
        active = get_active_project_name()
        choices = projects if projects else []
        value = active if active in choices else (choices[0] if choices else None)
        return gr.update(choices=choices, value=value), _status(active)

    def _status(active: str) -> str:
        if active:
            return f"✅ Active project: **{active}**"
        return "⚠️ No project selected."

    with gr.Column():
        gr.Markdown("## 📂 Projects")
        gr.Markdown(
            "All projects live inside the `workspace/` folder. "
            "Create a new one or switch between existing ones."
        )

        active_label = gr.Markdown(_status(get_active_project_name()))

        with gr.Row():
            project_dropdown = gr.Dropdown(
                label="Select project",
                choices=list_projects(),
                value=get_active_project_name() or None,
                interactive=True,
                scale=3,
            )
            switch_btn = gr.Button("Switch →", variant="primary", scale=1)

        gr.Markdown("---")
        gr.Markdown("### ➕ Create new project")

        with gr.Row():
            new_name = gr.Textbox(
                label="Project name",
                placeholder="e.g. my-awesome-app",
                scale=3,
            )
            create_btn = gr.Button("Create", variant="secondary", scale=1)

        result_msg = gr.Markdown("")

    # ── Events ─────────────────────────────────────────────────────────

    def do_switch(name: str):
        if not name:
            return _status(""), gr.update(), "⚠️ Please select a project first."
        try:
            set_active_project(name)
            dd, _ = refresh_projects()
            return _status(name), dd, f"✅ Switched to **{name}**"
        except Exception as e:
            return _status(get_active_project_name()), gr.update(), f"❌ {e}"

    def do_create(name: str):
        name = name.strip()
        if not name:
            return _status(get_active_project_name()), gr.update(), "⚠️ Please enter a project name."
        try:
            create_project(name)
            dd, status = refresh_projects()
            return status, dd, f"✅ Created and switched to **{name}**"
        except Exception as e:
            return _status(get_active_project_name()), gr.update(), f"❌ {e}"

    switch_btn.click(
        do_switch,
        inputs=[project_dropdown],
        outputs=[active_label, project_dropdown, result_msg],
    )
    create_btn.click(
        do_create,
        inputs=[new_name],
        outputs=[active_label, project_dropdown, result_msg],
    )
    new_name.submit(
        do_create,
        inputs=[new_name],
        outputs=[active_label, project_dropdown, result_msg],
    )
