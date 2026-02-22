"""
ui/download_tab.py
Download individual files or the entire project as a ZIP.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import gradio as gr

from core.projects import get_active_project, project_tree


def build_download_tab() -> None:
    """Render the Download tab."""

    def get_file_choices():
        project = get_active_project()
        if not project:
            return []
        items = project_tree(project)
        return [i["path"] for i in items if not i["is_dir"]]

    def download_single(relative_path: str):
        project = get_active_project()
        if not project or not relative_path:
            return None, "⚠️ No file selected."
        full_path = project / relative_path
        if not full_path.is_file():
            return None, f"❌ File not found: {relative_path}"
        return str(full_path), f"✅ Downloading `{relative_path}`"

    def download_zip():
        project = get_active_project()
        if not project:
            return None, "⚠️ No project selected."

        zip_path = Path(f"/tmp/{project.name}.zip")
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in project.rglob("*"):
                    if f.is_file() and not any(p.startswith(".") for p in f.parts):
                        zf.write(f, f.relative_to(project))
            size_kb = zip_path.stat().st_size // 1024
            return str(zip_path), f"✅ Created `{project.name}.zip` ({size_kb} KB)"
        except Exception as e:
            return None, f"❌ {e}"

    def refresh_choices():
        choices = get_file_choices()
        return gr.update(choices=choices, value=None)

    # ── Layout ─────────────────────────────────────────────────────────

    with gr.Column():
        gr.Markdown("## 📥 Download")

        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh file list", size="sm")

        gr.Markdown("### Download a single file")
        with gr.Row():
            file_picker = gr.Dropdown(
                label="Select file",
                choices=get_file_choices(),
                interactive=True,
                scale=4,
            )
            single_btn = gr.Button("Download", variant="secondary", scale=1)

        single_output = gr.File(label="Download", visible=False)
        single_status = gr.Markdown("")

        gr.Markdown("---")
        gr.Markdown("### Download entire project as ZIP")
        zip_btn = gr.Button("📦 Download ZIP", variant="primary")
        zip_output = gr.File(label="ZIP", visible=False)
        zip_status = gr.Markdown("")

    # ── Events ─────────────────────────────────────────────────────────

    def do_single(path: str):
        file_path, msg = download_single(path)
        visible = file_path is not None
        return gr.update(value=file_path, visible=visible), msg

    def do_zip():
        zip_path, msg = download_zip()
        visible = zip_path is not None
        return gr.update(value=zip_path, visible=visible), msg

    refresh_btn.click(refresh_choices, outputs=[file_picker])
    single_btn.click(do_single, inputs=[file_picker], outputs=[single_output, single_status])
    zip_btn.click(do_zip, outputs=[zip_output, zip_status])
