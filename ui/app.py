"""
ui/app.py
Top-Down FastAPI application — mounts Gradio and handles custom proxy routes.
Run with: python -m ui.app
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import gradio as gr

# Use modern websockets API for version 15.0.1
from websockets.asyncio.client import connect as ws_connect

from core.config import load_config
from core.projects import get_active_project_name
from ui.browser_tab import build_browser_tab
from ui.chat_tab import build_chat_tab
from ui.download_tab import build_download_tab
from ui.project_tab import build_project_tab
from ui.settings_tab import build_settings_tab
from ui.workspace_tab import build_workspace_tab

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ── App Definition ───────────────────────────────────────────────────────

app = FastAPI(title="Remote Coding Agent")

# Add CORS middleware to allow the Gradio tunnel origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── CSS ─────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
/* ── Theme Variables ── */
:root {
    /* Default (Dark) */
    --bg-page: #0f111a;
    --bg-panel: #1e1e2e;
    --bg-header: linear-gradient(135deg, #1e1e2e 0%, #313244 100%);
    --bg-btn: #313244;
    --bg-btn-hover: #45475a;
    --border-color: #45475a;
    --border-hover: #89b4fa;
    --text-primary: #cdd6f4;
    --text-secondary: #a6adc8;
}

[data-theme="light"] {
    --bg-page: #f4f5f7;
    --bg-panel: #ffffff;
    --bg-header: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    --bg-btn: #e9ecef;
    --bg-btn-hover: #dee2e6;
    --border-color: #dee2e6;
    --border-hover: #adb5bd;
    --text-primary: #212529;
    --text-secondary: #6c757d;
}

[data-theme="grey"] {
    --bg-page: #343a40;
    --bg-panel: #495057;
    --bg-header: linear-gradient(135deg, #495057 0%, #6c757d 100%);
    --bg-btn: #6c757d;
    --bg-btn-hover: #adb5bd;
    --border-color: #adb5bd;
    --border-hover: #ced4da;
    --text-primary: #f8f9fa;
    --text-secondary: #e9ecef;
}

/* ── Global ── */
body {
    background-color: var(--bg-page) !important;
    transition: background-color 0.3s;
}

.gradio-container {
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace !important;
    width: 1024px !important;
    max-width: 95vw !important;
    margin: 40px auto !important;
    border: 1px solid var(--border-color);
    border-radius: 12px;
    overflow: hidden !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    background: var(--bg-panel);
    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
}

.gradio-container.maximized {
    width: 100vw !important;
    max-width: 100vw !important;
    height: 100vh !important;
    margin: 0 !important;
    border-radius: 0;
    border: none;
}

/* ── Header ── */
#app-header {
    background: var(--bg-header);
    padding: 16px 24px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* ── Maximize Button ── */
.window-controls {
    display: flex;
    gap: 8px;
    margin-left: auto;
}

.win-btn {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    border: 1px solid var(--border-color);
    background: var(--bg-btn);
    color: var(--text-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 14px;
    user-select: none;
}

.win-btn:hover {
    background: var(--bg-btn-hover);
    border-color: var(--border-hover);
}

.theme-select {
    background: var(--bg-btn);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 0 8px;
    height: 28px;
    font-family: monospace;
    font-size: 13px;
    cursor: pointer;
    outline: none;
    transition: all 0.2s;
}

.theme-select:hover {
    background: var(--bg-btn-hover);
    border-color: var(--border-hover);
}
"""

CUSTOM_JS = """
function toggleMaximize() {
    const container = document.querySelector('.gradio-container');
    const btn = document.querySelector('.maximize-btn');
    if (!container || !btn) return;

    if (container.classList.contains('maximized')) {
        container.classList.remove('maximized');
        btn.innerHTML = '[&lt;&gt;]';
        btn.title = 'Maximize';
    } else {
        container.classList.add('maximized');
        btn.innerHTML = '[&gt;&lt;]';
        btn.title = 'Restore';
    }
}

function handleThemeChange(e) {
    const theme = e.target.value;
    applyTheme(theme);
}

function applyTheme(theme) {
    // Save to local storage
    localStorage.setItem('ide-theme', theme);
    const select = document.getElementById('theme-select');
    if(select) select.value = theme;

    let effectiveTheme = theme;
    if (theme === 'system') {
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        effectiveTheme = prefersDark ? 'dark' : 'light';
    }

    document.documentElement.setAttribute('data-theme', theme);

    if (effectiveTheme === 'light') {
        document.body.classList.remove('dark');
        document.body.classList.add('light'); // Gradio might use this occasionally
    } else {
        document.body.classList.remove('light');
        document.body.classList.add('dark');
    }
}

// On load
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('ide-theme') || 'dark';
    applyTheme(savedTheme);
});
"""

# ── Proxy Logic ──────────────────────────────────────────────────────────

def inject_vnc_proxy(app: FastAPI):
    """Inject the /vnc routes into a FastAPI app instance."""
    
    # We use a fresh path to avoid any Gradio route collisions or browser caching
    PROXY_ROOT = "/vnc"
    
    @app.websocket(PROXY_ROOT + "/websockify")
    async def vnc_proxy_ws(websocket: WebSocket):
        # Log the attempt to help debugging
        logger.info(f"WebSocket attempt from {websocket.client} path {websocket.url.path}")
        
        # Negotiate subprotocols (e.g., 'binary')
        requested_protocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
        requested_protocols = [p.strip() for p in requested_protocols if p.strip()]
        
        # Prefer 'binary' if requested by noVNC
        subprotocol = None
        if "binary" in requested_protocols:
            subprotocol = "binary"
        
        await websocket.accept(subprotocol=subprotocol)
        
        try:
            # Connect to the local Firefox container
            # We must forward the same subprotocol to the upstream.
            # Host/Origin headers are omitted as they cause 400 rejections 
            # with websockify when manually injected.
            conn_subprotocols = [subprotocol] if subprotocol else None
            
            async with ws_connect(
                "ws://127.0.0.1:5800/websockify",
                subprotocols=conn_subprotocols
            ) as target_ws:
                logger.info("Successfully connected to upstream vnc-websockify")
                
                async def forward_to_target():
                    try:
                        while True:
                            data = await websocket.receive_bytes()
                            await target_ws.send(data)
                    except Exception:
                        pass
                
                async def forward_to_client():
                    try:
                        while True:
                            data = await target_ws.recv()
                            if isinstance(data, str):
                                await websocket.send_text(data)
                            else:
                                await websocket.send_bytes(data)
                    except Exception:
                        pass
                
                await asyncio.gather(forward_to_target(), forward_to_client())
        except Exception as e:
            logger.error(f"WebSocket Proxy session error: {e}")
            try:
                await websocket.close()
            except Exception:
                pass

    @app.api_route(PROXY_ROOT + "/hello", methods=["GET"])
    async def proxy_hello():
        return {"status": "ok", "message": "VNC Proxy is active"}

    @app.api_route(PROXY_ROOT + "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    @app.api_route(PROXY_ROOT, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    async def vnc_proxy_all(request: Request, path: str = ""):
        target_path = path if path else ""
        target_url = f"http://127.0.0.1:5800/{target_path}"
        if request.query_params:
            target_url += f"?{request.query_params}"
            
        async with httpx.AsyncClient() as client_httpx:
            try:
                method = request.method
                content = await request.body()
                headers = dict(request.headers)
                headers["host"] = "127.0.0.1:5800"
                
                resp = await client_httpx.request(
                    method=method, url=target_url, content=content,
                    headers=headers, follow_redirects=True, timeout=15.0
                )
                
                excluded = ["content-encoding", "content-length", "transfer-encoding", "connection"]
                out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
                
                return Response(
                    content=resp.content, status_code=resp.status_code, headers=out_headers
                )
            except Exception as e:
                logger.error(f"Proxy error for {method} {target_url}: {e}")
                return Response(content=f"Proxy error: {e}", status_code=502)

    logger.info(f"Injecting vnc_proxy routes under {PROXY_ROOT}")


def inject_workspace_preview(app: FastAPI):
    """Serve files from the active project for preview."""
    from core.projects import get_active_project

    @app.get("/workspace_preview/{file_path:path}")
    async def workspace_preview(file_path: str):
        project_dir = get_active_project()
        if not project_dir:
            raise HTTPException(status_code=404, detail="No active project")
        full_path = project_dir / file_path
        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        # Ensure the file is inside the project directory (security)
        try:
            full_path.relative_to(project_dir)
        except ValueError:
            raise HTTPException(status_code=403, detail="Forbidden")
        return FileResponse(full_path)

    logger.info("Injecting workspace_preview route")


# ── Gradio Setup ─────────────────────────────────────────────────────────

def build_gradio_blocks() -> gr.Blocks:
    cfg = load_config()
    # Note: css is moved to launch() in Gradio 6
    with gr.Blocks() as blocks:
        model_state = gr.State(cfg.get("active_model", "openai/gpt-4o"))
        # gr.State() is enough, we don't need project_state if unused here
        gr.State(get_active_project_name())

        with gr.Row(elem_id="app-header"):
            gr.HTML("""
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <div style="display: flex; flex-direction: column;">
                        <h1 style="color: var(--text-primary); margin: 0; font-size: 1.4rem;">🤖 Remote Coding Agent</h1>
                        <p style="color: var(--text-secondary); margin: 2px 0 0 0; font-size: 0.8rem;">Your remote AI coding assistant — powered by LangGraph & FastAPI</p>
                    </div>
                    <div class="window-controls">
                        <select id="theme-select" class="theme-select" onchange="handleThemeChange(event)" title="Theme">
                            <option value="dark">Dark</option>
                            <option value="grey">Grey</option>
                            <option value="light">Light</option>
                            <option value="system">System</option>
                        </select>
                        <div class="win-btn maximize-btn" onclick="toggleMaximize()" title="Maximize" style="font-family: monospace; width: auto; padding: 0 6px;">[&lt;&gt;]</div>
                    </div>
                </div>
            """)

        with gr.Tabs() as tabs:
            with gr.Tab("💬 Chat") as chat_tab:
                chat_dropdown = build_chat_tab()
            with gr.Tab("🗂️ Workspace"):
                build_workspace_tab()
            with gr.Tab("🌐 Browser"):
                build_browser_tab()
            with gr.Tab("📂 Projects"):
                build_project_tab()
            with gr.Tab("📥 Download"):
                build_download_tab()
            with gr.Tab("⚙️ Settings") as settings_tab:
                settings_dropdown, settings_checkbox = build_settings_tab(model_state)

        def sync_models():
            c = load_config()
            models = c.get("models", [])
            act = c.get("active_model", "")
            if act not in models and models:
                act = models[0]
            return [
                gr.update(choices=models, value=act),
                gr.update(choices=models, value=act),
                gr.update(choices=models, value=models)
            ]

        # Sync states when app loads or users switch between the active model UI tabs
        blocks.load(sync_models, None, [chat_dropdown, settings_dropdown, settings_checkbox])
        chat_tab.select(sync_models, None, [chat_dropdown, settings_dropdown, settings_checkbox])
        settings_tab.select(sync_models, None, [chat_dropdown, settings_dropdown, settings_checkbox])

    return blocks

# ── Launch ───────────────────────────────────────────────────────────────

def main():
    # Inject routes before mounting Gradio
    inject_vnc_proxy(app)
    inject_workspace_preview(app)
    
    blocks = build_gradio_blocks()

    # Load auth from env
    auth_user = os.getenv("GRADIO_AUTH_USER")
    auth_password = os.getenv("GRADIO_AUTH_PASSWORD")
    auth = (auth_user, auth_password) if auth_user and auth_password else None

    # Mount Gradio onto FastAPI at root
    gr.mount_gradio_app(app, blocks, path="/", auth=auth, css=CUSTOM_CSS, js=CUSTOM_JS)
    
    port = int(os.environ.get("GRADIO_SERVER_PORT", "7862"))
    
    # Enable Gradio sharing manually — this creates a public *.gradio.live URL
    try:
        share_url = gr.networking.setup_tunnel(
            local_host="127.0.0.1",
            local_port=port,
            share_token=blocks.share_token,
            share_server_address=None,
            share_server_tls_certificate=None
        )
        print(f"\n* Running on public URL: {share_url}")
        print(f"* This share link expires in 72 hours.\n")
    except Exception as e:
        logger.warning(f"Could not create Gradio share link: {e}")

    logger.info(f"Starting FastAPI + Gradio on port {port}...")
    
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()
