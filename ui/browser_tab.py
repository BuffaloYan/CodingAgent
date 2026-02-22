"""
ui/browser_tab.py
Proxy browser tab — embeds a Firefox container via an internal FastAPI proxy.
Provides start/stop controls and Docker status display.
"""

from __future__ import annotations

import gradio as gr

from core.docker_browser import (
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    get_browser_status,
    is_docker_available,
    start_browser,
    stop_browser,
)

# ── Iframe builder ───────────────────────────────────────────────────────

def _browser_iframe(url: str) -> str:
    """Return an HTML iframe pointing at the internal proxy."""
    if not url:
        return _placeholder(
            "Browser is not running. Click <b>▶ Start Browser</b> to launch."
        )

    # Broken into smaller parts to satisfy E501
    container_style = (
        "width:100%;background:#11111b;border-radius:12px;"
        "padding:12px;border:1px solid #45475a;"
    )
    header_style = (
        "margin-bottom:12px;display:flex;justify-content:space-between;"
        "align-items:center;"
    )
    link_style = (
        "color:#89b4fa;font-size:0.9rem;text-decoration:none;"
        "background:#313244;padding:4px 12px;border-radius:6px;"
        "border:1px solid #45475a;"
    )
    iframe_style = (
        "width:100%;height:800px;border:none;border-radius:6px;"
        "background:#1e1e2e;display:block;"
    )

    return (
        f'<div style="{container_style}">'
        f'<div style="{header_style}">'
        f'<span style="color:#a6adc8;font-size:0.85rem;">🌐 <b>Firefox Desktop</b></span>'
        f'<a href="{url}" target="_blank" style="{link_style}">'
        f'↗ Open in New Tab</a>'
        f'</div>'
        f'<iframe src="{url}" style="{iframe_style}" '
        f'allow="clipboard-read; clipboard-write; autoplay"></iframe>'
        f'</div>'
    )


def _placeholder(msg: str) -> str:
    """Return styled placeholder HTML."""
    return (
        f'<div style="width:100%;height:700px;display:flex;align-items:center;'
        f'justify-content:center;background:#1e1e2e;border:1px solid #45475a;'
        f'border-radius:8px;color:#a6adc8;font-size:1.1rem;text-align:center;'
        f'padding:40px;">'
        f'<div>{msg}</div></div>'
    )


def _status_badge(running: bool, status_text: str) -> str:
    """Return a styled status markdown string."""
    if running:
        return f"🟢 **Running** — `{status_text}`"
    return f"🔴 **Stopped** — `{status_text}`"


# ── Tab builder ──────────────────────────────────────────────────────────

def build_browser_tab() -> None:
    """Render the proxy browser tab."""

    # ── Check Docker availability ────────────────────────────────
    docker_ok = is_docker_available()

    if not docker_ok:
        gr.Markdown(
            "## ⚠️ Docker Not Available\n\n"
            "The proxy browser requires **Docker Desktop** to be installed and running.\n\n"
            "Once Docker is running, restart the app."
        )
        return

    # ── Controls ─────────────────────────────────────────────────
    with gr.Row():
        with gr.Column(scale=1):
            start_btn = gr.Button("▶ Start Browser", variant="primary", size="sm")
        with gr.Column(scale=1):
            stop_btn = gr.Button("⏹ Stop Browser", variant="stop", size="sm")
        with gr.Column(scale=1):
            refresh_btn = gr.Button("🔄 Refresh", size="sm")
        with gr.Column(scale=3):
            status_md = gr.Markdown(
                value="🔴 **Stopped**",
                elem_id="browser-status",
            )

    # ── Password hint ────────────────────────────────────────────
    with gr.Accordion("🔑 Connection Info", open=False):
        pw_note = (
            f"- **VNC Password:** `{DEFAULT_PASSWORD}`\n"
            if DEFAULT_PASSWORD
            else "- **VNC Password:** _(none — open access)_\n"
        )
        note_text = (
            f"{pw_note}"
            f"- **Internal Port:** `{DEFAULT_PORT}`\n\n"
            "**Note:** For remote access via Gradio Share, the browser is "
            "automatically proxied through the same secure link."
        )
        gr.Markdown(note_text)

    # ── Browser iframe ───────────────────────────────────────────
    browser_html = gr.HTML(
        value=_placeholder("Click <b>▶ Start Browser</b> to launch Firefox."),
        elem_id="browser-frame",
    )

    # ── Event handlers ───────────────────────────────────────────

    def do_start():
        """Start the browser container."""
        yield "⏳ **Starting...**", _placeholder("⏳ Starting browser container...")
        result = start_browser()
        if result["success"]:
            yield _status_badge(True, "running"), _browser_iframe(result["url"])
        else:
            yield f"❌ **Error** — `{result['message']}`", gr.update()

    def do_stop():
        """Stop the browser container."""
        stop_browser()
        return _status_badge(False, "stopped"), _placeholder("Browser stopped.")

    def do_refresh():
        """Refresh the status display."""
        status = get_browser_status()
        badge = _status_badge(status["running"], status["status"])
        if status["running"]:
            return badge, _browser_iframe(status["url"])
        return badge, _placeholder("Browser is not running.")

    # ── Wire events ──────────────────────────────────────────────

    start_btn.click(do_start, outputs=[status_md, browser_html])
    stop_btn.click(do_stop, outputs=[status_md, browser_html])
    refresh_btn.click(do_refresh, outputs=[status_md, browser_html])
