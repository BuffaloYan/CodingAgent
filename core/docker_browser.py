"""
core/docker_browser.py
Manage a jlesage/firefox Docker container for the proxy browser tab.
Uses subprocess + docker CLI (no extra Python dependencies).
"""

from __future__ import annotations

import logging
import os
import subprocess
import time

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────────

CONTAINER_NAME = "agent-browser"
DEFAULT_IMAGE = "jlesage/firefox"
DEFAULT_PORT = int(os.getenv("BROWSER_PORT", "5800"))
DEFAULT_PASSWORD = os.getenv("BROWSER_VNC_PASSWORD", "")


# ── Helpers ──────────────────────────────────────────────────────────────

def _run(args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a docker CLI command and return the result."""
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ── Public API ───────────────────────────────────────────────────────────

def is_docker_available() -> bool:
    """Return True if the Docker daemon is reachable."""
    try:
        result = _run(["info"], timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_browser_status() -> dict:
    """
    Return the current status of the browser container.
    """
    info = {
        "running": False,
        "status": "stopped",
        "port": DEFAULT_PORT,
        "url": "",
        "image": DEFAULT_IMAGE,
    }

    try:
        result = _run([
            "inspect",
            "--format", '{{.State.Running}}|{{.State.Status}}',
            CONTAINER_NAME,
        ])
        if result.returncode != 0:
            info["status"] = "not created"
            return info

        parts = result.stdout.strip().split("|")
        is_running = parts[0].lower() == "true"
        state_str = parts[1] if len(parts) > 1 else "unknown"

        info["running"] = is_running
        info["status"] = state_str
        if is_running:
            # We now use the internal proxy at /vnc/ with a cache-buster
            info["url"] = f"/vnc/?t={int(time.time())}"

    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        info["status"] = f"error: {e}"

    return info


def start_browser(
    port: int | None = None,
    password: str | None = None,
    image: str | None = None,
) -> dict:
    """
    Start the jlesage/firefox container.
    """
    port = port or DEFAULT_PORT
    password = password if password is not None else DEFAULT_PASSWORD
    image = image or DEFAULT_IMAGE

    # Check if already running
    status = get_browser_status()
    if status["running"]:
        return {
            "success": True,
            "message": "Browser is already running.",
            "url": f"/vnc/?t={int(time.time())}",
        }

    # Remove any stopped container with the same name
    _run(["rm", "-f", CONTAINER_NAME])

    # Pull the image
    logger.info("Pulling Docker image %s...", image)
    pull = _run(["pull", image], timeout=300)
    if pull.returncode != 0:
        return {
            "success": False,
            "message": f"Failed to pull image: {pull.stderr.strip()}",
            "url": "",
        }

    # Run the container
    run_args = [
        "run", "-d",
        "--name", CONTAINER_NAME,
        "--shm-size=512m",
        "-p", f"127.0.0.1:{port}:5800",
    ]
    if password:
        run_args.extend(["-e", f"VNC_PASSWORD={password}"])
    run_args.append(image)

    run_result = _run(run_args)

    if run_result.returncode != 0:
        return {
            "success": False,
            "message": f"Failed to start container: {run_result.stderr.strip()}",
            "url": "",
        }

    container_id = run_result.stdout.strip()[:12]
    logger.info("Browser container %s started", container_id)
    time.sleep(3)

    return {
        "success": True,
        "message": f"Browser started (container {container_id}).",
        "url": f"/vnc/?t={int(time.time())}",
    }


def stop_browser() -> dict:
    """
    Stop and remove the browser container.
    """
    status = get_browser_status()
    if not status["running"] and status["status"] == "not created":
        return {"success": True, "message": "No browser container to stop."}

    _run(["stop", CONTAINER_NAME], timeout=30)
    rm_result = _run(["rm", "-f", CONTAINER_NAME], timeout=15)

    if rm_result.returncode != 0:
        return {
            "success": False,
            "message": f"Failed to remove container: {rm_result.stderr.strip()}",
        }

    logger.info("Browser container stopped and removed.")
    return {"success": True, "message": "Browser stopped."}
