# Docker-Based Proxy Browser Tab

Add a **🌐 Browser** tab to the Gradio UI that provides a fully functional web browser (Chrome) running inside a Docker container, streamed to the UI via KasmVNC's built-in noVNC web client.

This unlocks two capabilities:
1. **Proxy browsing** — Remote users can access any website (Gmail, etc.) through the host machine's network
2. **Future extensibility** — The Docker management layer can be reused by the coding agent to run user applications in containers

## User Review Required

> [!IMPORTANT]
> **Docker Desktop required** — The host machine (macOS or Windows) must have Docker Desktop installed and running. The implementation will detect this and show a helpful error if Docker is unavailable.

> [!WARNING]
> **Security consideration** — This gives remote Gradio users a full Chrome browser on the host network. Anyone with access to the Gradio UI can browse the web as if they were on the host machine. Consider access-controlling the Gradio app itself (e.g., `--auth` flag or VPN).

---

## Proposed Changes

### Core Module — Docker Browser Management

#### [NEW] [docker_browser.py](file:///Users/wyan/projects/learn/agent-by-claude/core/docker_browser.py)

A self-contained module for managing the KasmVNC Chrome Docker container. Uses the `docker` Python SDK (or `subprocess` calling the `docker` CLI for zero-dependency simplicity).

**Approach: Use `subprocess` + `docker` CLI** (avoids adding `docker` Python package as a dependency).

Key functions:
- `is_docker_available() -> bool` — Check if Docker daemon is reachable
- `start_browser(port=6901, password="changeme") -> dict` — Pull & run `kasmweb/chrome:1.16.1` mapping port 6901
- `stop_browser() -> bool` — Stop & remove the container
- `get_browser_status() -> dict` — Return `{"running": bool, "port": int, "url": str}`
- `get_browser_url() -> str` — Return the KasmVNC URL for iframe embedding

Container config:
- Image: `kasmweb/chrome:1.16.1` (stable, ~800MB, includes Chrome + KasmVNC)
- Port: `6901:6901` (KasmVNC HTTPS web interface)
- Environment: `VNC_PW` for password, `KASM_PORT` for internal port
- Shared memory: `--shm-size=512m` (Chrome needs this)
- Container name: `agent-browser` (fixed name for easy management)

---

### UI Tab — Browser Tab

#### [NEW] [browser_tab.py](file:///Users/wyan/projects/learn/agent-by-claude/ui/browser_tab.py)

A new Gradio tab with:
- **Start/Stop controls** — Buttons to launch or teardown the Docker browser container
- **Status indicator** — Shows if the container is running, starting, or stopped
- **Embedded browser** — A `gr.HTML()` component with an iframe pointing to the KasmVNC URL (`https://localhost:6901`)
- **Password display** — Shows the VNC password so the user can log in on first use (KasmVNC has a simple login page)

Layout:
```
┌───────────────────────────────────────────────┐
│  🌐 Docker Browser                            │
│                                               │
│  [▶ Start Browser]  [⏹ Stop]  Status: 🟢 Running │
│  Password: changeme                           │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │                                         │  │
│  │   (KasmVNC iframe — full Chrome)        │  │
│  │                                         │  │
│  └─────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘
```

---

### App Wiring

#### [MODIFY] [app.py](file:///Users/wyan/projects/learn/agent-by-claude/ui/app.py)

- Import `build_browser_tab` from `ui.browser_tab`
- Add a `🌐 Browser` tab in the tab bar (after Workspace, before Projects)

---

### Configuration

#### [MODIFY] [.env.example](file:///Users/wyan/projects/learn/agent-by-claude/.env.example)

Add optional browser config variables:
```
# Docker Browser (proxy browser tab)
BROWSER_VNC_PASSWORD=changeme
BROWSER_PORT=6901
```

---

### Build Targets

#### [MODIFY] [Makefile](file:///Users/wyan/projects/learn/agent-by-claude/Makefile)

Add convenience targets:
```makefile
browser-start:  ## Pull image & start browser container
browser-stop:   ## Stop & remove browser container
browser-status: ## Show container status
```

---

## Verification Plan

### Automated Tests

#### [NEW] [test_docker_browser.py](file:///Users/wyan/projects/learn/agent-by-claude/tests/test_docker_browser.py)

Unit tests for the core module, **mocking `subprocess` calls** so Docker is not actually required to run tests:

- `test_is_docker_available_true` — mock `docker info` returning success
- `test_is_docker_available_false` — mock `docker info` returning failure
- `test_start_browser_success` — mock `docker run` returning container ID
- `test_start_browser_already_running` — mock showing container already exists
- `test_stop_browser_success` — mock `docker stop` + `docker rm`
- `test_get_status_running` — mock `docker inspect` returning running state
- `test_get_status_not_running` — mock `docker inspect` returning no container

Run with:
```bash
make test
# or specifically:
.venv/bin/pytest tests/test_docker_browser.py -v
```

### Manual Verification

> [!NOTE]
> This requires Docker Desktop to be installed and running on the host machine.

1. Start the Gradio app: `make run`
2. Navigate to the **🌐 Browser** tab
3. Click **▶ Start Browser** — should show "Starting..." then "🟢 Running" after ~10-30s (first run pulls the image)
4. The iframe should load the KasmVNC login page
5. Enter the password shown in the UI to access Chrome
6. Browse to `gmail.com` — should fully function (login, compose, etc.)
7. Click **⏹ Stop** — container should stop, iframe should show a message
8. Verify `docker ps` shows no `agent-browser` container after stopping
