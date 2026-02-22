"""tests/test_docker_browser.py — unit tests for core/docker_browser.py

All subprocess calls are mocked; Docker is NOT required to run these tests.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

# ── is_docker_available ──────────────────────────────────────────────────


@patch("core.docker_browser._run")
def test_is_docker_available_true(mock_run):
    """is_docker_available() returns True when docker info succeeds."""
    mock_run.return_value = MagicMock(returncode=0)
    from core.docker_browser import is_docker_available

    assert is_docker_available() is True
    mock_run.assert_called_once_with(["info"], timeout=10)


@patch("core.docker_browser._run")
def test_is_docker_available_false(mock_run):
    """is_docker_available() returns False when docker info fails."""
    mock_run.return_value = MagicMock(returncode=1)
    from core.docker_browser import is_docker_available

    assert is_docker_available() is False


@patch("core.docker_browser._run", side_effect=FileNotFoundError)
def test_is_docker_available_no_binary(mock_run):
    """is_docker_available() returns False when docker binary is missing."""
    from core.docker_browser import is_docker_available

    assert is_docker_available() is False


@patch("core.docker_browser._run", side_effect=subprocess.TimeoutExpired("docker", 10))
def test_is_docker_available_timeout(mock_run):
    """is_docker_available() returns False when docker info times out."""
    from core.docker_browser import is_docker_available

    assert is_docker_available() is False


# ── get_browser_status ───────────────────────────────────────────────────


@patch("core.docker_browser._run")
def test_get_status_running(mock_run):
    """get_browser_status() reports running when container is up."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="true|running\n",
    )
    from core.docker_browser import get_browser_status

    status = get_browser_status()
    assert status["running"] is True
    assert status["status"] == "running"
    assert "localhost" in status["url"]


@patch("core.docker_browser._run")
def test_get_status_stopped(mock_run):
    """get_browser_status() reports stopped when container is exited."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="false|exited\n",
    )
    from core.docker_browser import get_browser_status

    status = get_browser_status()
    assert status["running"] is False
    assert status["status"] == "exited"
    assert status["url"] == ""


@patch("core.docker_browser._run")
def test_get_status_not_created(mock_run):
    """get_browser_status() reports 'not created' when no container exists."""
    mock_run.return_value = MagicMock(
        returncode=1,
        stderr="No such object",
    )
    from core.docker_browser import get_browser_status

    status = get_browser_status()
    assert status["running"] is False
    assert status["status"] == "not created"


# ── start_browser ────────────────────────────────────────────────────────


@patch("core.docker_browser.time")
@patch("core.docker_browser._run")
def test_start_browser_success(mock_run, mock_time):
    """start_browser() returns success when container starts."""
    # Call sequence: get_browser_status (inspect) -> rm -> pull -> run
    mock_run.side_effect = [
        MagicMock(returncode=1, stderr="No such object"),  # inspect → not found
        MagicMock(returncode=0),  # rm -f
        MagicMock(returncode=0),  # pull
        MagicMock(returncode=0, stdout="abc123def456\n"),  # run
    ]
    from core.docker_browser import start_browser

    result = start_browser()
    assert result["success"] is True
    assert "localhost" in result["url"]


@patch("core.docker_browser._run")
def test_start_browser_already_running(mock_run):
    """start_browser() returns success without re-creating when already running."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="true|running\n",
    )
    from core.docker_browser import start_browser

    result = start_browser()
    assert result["success"] is True
    assert "already running" in result["message"].lower()


@patch("core.docker_browser._run")
def test_start_browser_pull_failure(mock_run):
    """start_browser() reports failure when image pull fails."""
    mock_run.side_effect = [
        MagicMock(returncode=1, stderr="No such object"),  # inspect
        MagicMock(returncode=0),  # rm -f
        MagicMock(returncode=1, stderr="network error"),  # pull fails
    ]
    from core.docker_browser import start_browser

    result = start_browser()
    assert result["success"] is False
    assert "pull" in result["message"].lower()


# ── stop_browser ─────────────────────────────────────────────────────────


@patch("core.docker_browser._run")
def test_stop_browser_success(mock_run):
    """stop_browser() returns success after stop+rm."""
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="true|running\n"),  # inspect
        MagicMock(returncode=0),  # stop
        MagicMock(returncode=0),  # rm
    ]
    from core.docker_browser import stop_browser

    result = stop_browser()
    assert result["success"] is True


@patch("core.docker_browser._run")
def test_stop_browser_not_created(mock_run):
    """stop_browser() returns success when no container exists."""
    mock_run.return_value = MagicMock(
        returncode=1,
        stderr="No such object",
    )
    from core.docker_browser import stop_browser

    result = stop_browser()
    assert result["success"] is True
    assert "no browser" in result["message"].lower()
