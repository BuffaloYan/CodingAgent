"""
ui/workspace_tab.py
Mini IDE: clickable file tree on left, tabbed editor + multi-format preview on right.
Supports: HTML (live JS), images, markdown, CSV/TSV, PDF, video, audio.
"""

from __future__ import annotations

import csv
import io
import threading
import time
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import gradio as gr
import markdown as md_lib

from core.projects import get_active_project, project_tree


# ── Local static file server ──────────────────────────────────────────

_server_thread: threading.Thread | None = None
_server_port: int = 18862


def _start_file_server(directory: Path, port: int = 18862) -> int:
    """Start a local HTTP server serving *directory*. Returns port."""
    global _server_thread, _server_port
    _server_port = port
    if _server_thread and _server_thread.is_alive():
        return port
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    httpd = HTTPServer(("127.0.0.1", port), handler)
    httpd.timeout = 0.5
    _server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    _server_thread.start()
    return port


# ── Preview format detection ──────────────────────────────────────────

_HTML_EXTS = {".html", ".htm"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp"}
_MARKDOWN_EXTS = {".md", ".markdown"}
_CSV_EXTS = {".csv", ".tsv"}
_PDF_EXTS = {".pdf"}
_VIDEO_EXTS = {".mp4", ".webm", ".mov"}
_AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}

_ALL_PREVIEWABLE = _HTML_EXTS | _IMAGE_EXTS | _MARKDOWN_EXTS | _CSV_EXTS | _PDF_EXTS | _VIDEO_EXTS | _AUDIO_EXTS


def _is_previewable(path: str) -> bool:
    return Path(path).suffix.lower() in _ALL_PREVIEWABLE


def _preview_tab_label(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in _HTML_EXTS:
        return "🌐 Preview"
    if ext in _IMAGE_EXTS:
        return "🖼️ Preview"
    if ext in _MARKDOWN_EXTS:
        return "📝 Preview"
    if ext in _CSV_EXTS:
        return "📊 Preview"
    if ext in _PDF_EXTS:
        return "📄 Preview"
    if ext in _VIDEO_EXTS:
        return "🎬 Preview"
    if ext in _AUDIO_EXTS:
        return "🔊 Preview"
    return "Preview"


# ── Preview builders ──────────────────────────────────────────────────

_PREVIEW_STYLE = (
    "width:100%;min-height:500px;border:1px solid #45475a;"
    "border-radius:8px;background:white;"
)


def _build_preview(relative_path: str, content: str, server_url: str) -> str:
    """Return an HTML string with the right preview for the file type."""
    ext = Path(relative_path).suffix.lower()
    cb = int(time.time() * 1000)  # cache-buster

    # ── HTML: iframe via HTTP server (full JS execution)
    if ext in _HTML_EXTS:
        url = f"{server_url}/{relative_path}?_={cb}"
        return f'<iframe src="{url}" style="{_PREVIEW_STYLE}height:550px;"></iframe>'

    # ── Images: <img> tag via HTTP server
    if ext in _IMAGE_EXTS:
        url = f"{server_url}/{relative_path}?_={cb}"
        return (
            f'<div style="padding:20px;text-align:center;background:#1e1e2e;'
            f'border-radius:8px;min-height:200px;">'
            f'<img src="{url}" style="max-width:100%;max-height:600px;'
            f'border-radius:6px;box-shadow:0 4px 20px rgba(0,0,0,0.3);" />'
            f'<p style="color:#a6adc8;margin-top:12px;font-size:0.85rem;">{relative_path}</p>'
            f'</div>'
        )

    # ── Markdown: render to HTML
    if ext in _MARKDOWN_EXTS:
        html = md_lib.markdown(
            content,
            extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br"],
        )
        return (
            f'<div style="padding:20px 28px;background:#1e1e2e;border-radius:8px;'
            f'color:#cdd6f4;font-family:system-ui,sans-serif;line-height:1.7;'
            f'max-height:600px;overflow-y:auto;">'
            f'<style>'
            f'  .md-preview h1,.md-preview h2,.md-preview h3 {{ color:#89b4fa; margin-top:1em; }}'
            f'  .md-preview code {{ background:#313244; padding:2px 6px; border-radius:4px; font-size:0.9em; }}'
            f'  .md-preview pre {{ background:#313244; padding:12px; border-radius:8px; overflow-x:auto; }}'
            f'  .md-preview pre code {{ background:none; padding:0; }}'
            f'  .md-preview table {{ border-collapse:collapse; width:100%; margin:1em 0; }}'
            f'  .md-preview th,.md-preview td {{ border:1px solid #45475a; padding:8px 12px; text-align:left; }}'
            f'  .md-preview th {{ background:#313244; }}'
            f'  .md-preview a {{ color:#89b4fa; }}'
            f'  .md-preview blockquote {{ border-left:3px solid #89b4fa; padding-left:12px; color:#a6adc8; }}'
            f'</style>'
            f'<div class="md-preview">{html}</div>'
            f'</div>'
        )

    # ── CSV / TSV: parse to styled HTML table
    if ext in _CSV_EXTS:
        delimiter = "\t" if ext == ".tsv" else ","
        try:
            reader = csv.reader(io.StringIO(content), delimiter=delimiter)
            rows = list(reader)
        except Exception:
            return f'<p style="color:red;">Error parsing {ext} file.</p>'

        if not rows:
            return '<p style="color:#888;">Empty file.</p>'

        # First row as header
        header = rows[0]
        body = rows[1:200]  # cap at 200 rows for performance

        th = "".join(f"<th>{cell}</th>" for cell in header)
        tbody = ""
        for row in body:
            td = "".join(f"<td>{cell}</td>" for cell in row)
            tbody += f"<tr>{td}</tr>"

        return (
            f'<div style="max-height:600px;overflow:auto;border-radius:8px;">'
            f'<table style="border-collapse:collapse;width:100%;font-size:0.85rem;'
            f'background:#1e1e2e;color:#cdd6f4;">'
            f'<thead style="position:sticky;top:0;background:#313244;">'
            f'<tr>{th}</tr></thead>'
            f'<tbody>{tbody}</tbody></table>'
            f'<style>'
            f'  table th, table td {{ border:1px solid #45475a; padding:6px 10px; text-align:left; }}'
            f'  table tr:hover {{ background:rgba(137,180,250,0.08); }}'
            f'</style>'
            f'</div>'
            + (f'<p style="color:#a6adc8;font-size:0.8rem;margin-top:6px;">'
               f'Showing {len(body)} of {len(rows)-1} rows</p>' if len(rows) > 201 else "")
        )

    # ── PDF: iframe embed
    if ext in _PDF_EXTS:
        url = f"{server_url}/{relative_path}?_={cb}"
        return f'<iframe src="{url}" style="{_PREVIEW_STYLE}height:600px;"></iframe>'

    # ── Video: HTML5 video player
    if ext in _VIDEO_EXTS:
        url = f"{server_url}/{relative_path}?_={cb}"
        return (
            f'<div style="padding:20px;text-align:center;background:#1e1e2e;border-radius:8px;">'
            f'<video controls style="max-width:100%;max-height:500px;border-radius:6px;">'
            f'<source src="{url}" type="video/{ext.lstrip(".")}">Your browser does not support video.</video>'
            f'<p style="color:#a6adc8;margin-top:12px;font-size:0.85rem;">{relative_path}</p>'
            f'</div>'
        )

    # ── Audio: HTML5 audio player
    if ext in _AUDIO_EXTS:
        url = f"{server_url}/{relative_path}?_={cb}"
        return (
            f'<div style="padding:30px;text-align:center;background:#1e1e2e;border-radius:8px;">'
            f'<p style="color:#cdd6f4;font-size:1.1rem;margin-bottom:16px;">🎵 {relative_path}</p>'
            f'<audio controls style="width:100%;max-width:500px;">'
            f'<source src="{url}" type="audio/{ext.lstrip(".")}">Your browser does not support audio.</audio>'
            f'</div>'
        )

    return '<p style="color:#888;">No preview available for this file type.</p>'


# ── Main builder ──────────────────────────────────────────────────────

def build_workspace_tab() -> None:
    """Render the mini-IDE workspace tab."""

    def _file_icon(name: str) -> str:
        ext = Path(name).suffix.lower()
        icons = {
            ".py": "🐍", ".js": "🟨", ".ts": "🔷", ".html": "🌐",
            ".css": "🎨", ".json": "📋", ".yaml": "📋", ".yml": "📋",
            ".md": "📝", ".txt": "📄", ".sh": "⚙️", ".toml": "⚙️",
            ".png": "🖼️", ".jpg": "🖼️", ".svg": "🖼️", ".gif": "🖼️",
            ".mp4": "🎬", ".mp3": "🔊", ".pdf": "📄", ".csv": "📊",
        }
        return icons.get(ext, "📄")

    def _detect_language(path: str) -> str | None:
        ext = Path(path).suffix.lower()
        return {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".html": "html", ".css": "css", ".json": "json",
            ".yaml": "yaml", ".yml": "yaml", ".sh": "shell",
            ".md": "markdown", ".toml": None, ".txt": None,
            ".rs": "c", ".go": None, ".java": None, ".cpp": "cpp",
        }.get(ext, None)

    def _build_file_choices(items: list[dict]) -> list[str]:
        choices = []
        for item in items:
            if item["is_dir"]:
                continue
            depth = item["path"].count("/")
            indent = "  " * depth
            icon = _file_icon(item["name"])
            choices.append(f"{indent}{icon} {item['path']}")
        return choices

    def _path_from_choice(choice: str) -> str:
        if not choice:
            return ""
        stripped = choice.strip()
        parts = stripped.split(" ", 1)
        return parts[1] if len(parts) > 1 else stripped

    def do_refresh():
        project = get_active_project()
        if not project:
            return gr.update(choices=[], value=None), "⚠️ No project"
        items = project_tree(project)
        choices = _build_file_choices(items)
        label = f"📁 **{project.name}**"
        return gr.update(choices=choices, value=None), label

    def open_file(choice: str):
        relative_path = _path_from_choice(choice)
        project = get_active_project()

        empty_result = (
            "", gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=False), "", "_Select a file to edit_",
            gr.update(visible=False), "",
        )

        if not project or not relative_path:
            return empty_result

        full_path = project / relative_path
        if not full_path.is_file():
            return empty_result

        # Read text content (skip for binary files)
        ext = full_path.suffix.lower()
        is_binary = ext in (_IMAGE_EXTS | _PDF_EXTS | _VIDEO_EXTS | _AUDIO_EXTS)
        content = ""
        if not is_binary:
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                content = f"Error reading file: {e}"

        lang = _detect_language(relative_path)
        previewable = _is_previewable(relative_path)

        # Build preview HTML
        preview = ""
        if previewable:
            _start_file_server(project, port=_server_port)
            server_url = f"http://127.0.0.1:{_server_port}"
            preview = _build_preview(relative_path, content, server_url)

        return (
            content,
            gr.update(visible=not is_binary, language=lang),
            gr.update(visible=not is_binary),
            gr.update(visible=previewable),
            preview,
            f"📄 **{relative_path}**",
            gr.update(visible=True),
            relative_path,
        )

    def save_file(relative_path: str, content: str):
        project = get_active_project()
        if not project or not relative_path:
            return "⚠️ No file selected."
        full_path = project / relative_path
        try:
            full_path.write_text(content, encoding="utf-8")
            return f"✅ Saved `{relative_path}`"
        except Exception as e:
            return f"❌ {e}"

    def refresh_preview(relative_path: str, content: str):
        if not _is_previewable(relative_path or ""):
            return ""
        project = get_active_project()
        if not project:
            return ""
        _start_file_server(project, port=_server_port)
        server_url = f"http://127.0.0.1:{_server_port}"
        return _build_preview(relative_path, content, server_url)

    # ── Layout ─────────────────────────────────────────────────────────

    with gr.Row():
        # ── LEFT PANEL ─────────────────────────────────────────────────
        with gr.Column(scale=1, min_width=240):
            with gr.Row():
                with gr.Column(scale=3):
                    project_label = gr.Markdown("⚠️ No project")
                refresh_btn = gr.Button("🔄", size="sm", scale=0)

            file_tree = gr.Radio(
                label="📂 Files",
                choices=[],
                interactive=True,
                elem_id="ide-file-tree",
            )

        # ── RIGHT PANEL ────────────────────────────────────────────────
        with gr.Column(scale=3):
            file_label = gr.Markdown("_Select a file to edit_")
            selected_file = gr.State("")

            with gr.Column(visible=False) as editor_section:
                with gr.Tabs():
                    with gr.Tab("📝 Editor"):
                        code_editor = gr.Code(
                            label="",
                            language=None,
                            interactive=True,
                            visible=False,
                            elem_id="code-editor",
                            lines=22,
                        )
                        with gr.Row():
                            save_btn = gr.Button("💾 Save", variant="primary", visible=False)
                            save_status = gr.Markdown("")

                    with gr.Tab("Preview", visible=False) as preview_tab:
                        preview_html = gr.HTML(
                            value="<p style='color:#888;padding:20px;'>Select a previewable file.</p>",
                            elem_id="ide-preview",
                        )
                        refresh_preview_btn = gr.Button("🔄 Refresh Preview", size="sm")

    # ── Events ─────────────────────────────────────────────────────────

    refresh_btn.click(do_refresh, outputs=[file_tree, project_label])

    file_tree.change(
        open_file,
        inputs=[file_tree],
        outputs=[
            code_editor, code_editor, save_btn,
            preview_tab, preview_html, file_label,
            editor_section, selected_file,
        ],
    )

    save_btn.click(
        save_file,
        inputs=[selected_file, code_editor],
        outputs=[save_status],
    ).then(
        refresh_preview,
        inputs=[selected_file, code_editor],
        outputs=[preview_html],
    )

    refresh_preview_btn.click(
        refresh_preview,
        inputs=[selected_file, code_editor],
        outputs=[preview_html],
    )

    # Auto-populate on load
    app_load = gr.Timer(value=1, active=True)
    app_load.tick(do_refresh, outputs=[file_tree, project_label]).then(
        lambda: gr.update(active=False), outputs=[app_load]
    )
