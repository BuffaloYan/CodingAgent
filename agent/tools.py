"""
agent/tools.py
LangChain @tool decorated functions that operate on the active project.
All file paths are sandboxed to the project root.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from langchain_core.tools import tool


# ── Sandbox helpers ─────────────────────────────────────────────────────

def _resolve(project_root: Path, relative_path: str) -> Path:
    """
    Resolve *relative_path* inside *project_root*.
    Raises PermissionError if the resolved path escapes the root.
    """
    resolved = (project_root / relative_path).resolve()
    if not str(resolved).startswith(str(project_root.resolve())):
        raise PermissionError(
            f"Access denied: '{relative_path}' is outside the project root."
        )
    return resolved


# ── Tool factory ────────────────────────────────────────────────────────

def make_tools(project_root: Path) -> list:
    """Return a list of LangChain tools bound to *project_root*."""

    @tool
    def read_file(path: str) -> str:
        """Read and return the contents of a file in the project. path is relative to the project root."""
        target = _resolve(project_root, path)
        if not target.exists():
            return f"ERROR: File not found: {path}"
        if not target.is_file():
            return f"ERROR: Not a file: {path}"
        try:
            return target.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"ERROR reading file: {e}"

    @tool
    def write_file(path: str, content: str) -> str:
        """Write content to a file in the project (creates parent dirs as needed). path is relative to project root."""
        try:
            target = _resolve(project_root, path)
        except PermissionError as e:
            return f"ERROR: {e}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"OK: Wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"ERROR writing file: {e}"

    @tool
    def list_directory(path: str = ".") -> str:
        """List files and directories at the given path (relative to project root). Defaults to project root."""
        target = _resolve(project_root, path)
        if not target.exists():
            return f"ERROR: Path not found: {path}"
        if not target.is_dir():
            return f"ERROR: Not a directory: {path}"
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = []
        for entry in entries:
            prefix = "📄" if entry.is_file() else "📁"
            lines.append(f"{prefix} {entry.name}")
        return "\n".join(lines) if lines else "(empty directory)"

    @tool
    def create_directory(path: str) -> str:
        """Create a directory (and any missing parents) in the project. path is relative to project root."""
        target = _resolve(project_root, path)
        try:
            target.mkdir(parents=True, exist_ok=True)
            return f"OK: Created directory {path}"
        except Exception as e:
            return f"ERROR: {e}"

    @tool
    def delete_file(path: str) -> str:
        """Delete a file from the project. path is relative to project root. Directories are NOT deleted."""
        target = _resolve(project_root, path)
        if not target.exists():
            return f"ERROR: File not found: {path}"
        if not target.is_file():
            return f"ERROR: '{path}' is a directory; only files can be deleted."
        try:
            target.unlink()
            return f"OK: Deleted {path}"
        except Exception as e:
            return f"ERROR: {e}"

    @tool
    def search_code(query: str, path: str = ".") -> str:
        """Search for a text pattern in files under path (relative to project root). Returns matching lines."""
        target = _resolve(project_root, path)
        if not target.exists():
            return f"ERROR: Path not found: {path}"
        matches = []
        search_files = [target] if target.is_file() else list(target.rglob("*"))
        for f in search_files:
            if not f.is_file():
                continue
            try:
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if query.lower() in line.lower():
                        rel = f.relative_to(project_root)
                        matches.append(f"{rel}:{i}: {line.rstrip()}")
            except Exception:
                continue
        if not matches:
            return f"No matches for '{query}'"
        return "\n".join(matches[:200])  # cap at 200 lines

    @tool
    def run_shell(command: str) -> str:
        """
        Run a shell command in the project root directory.
        Returns combined stdout+stderr. Timeout: 60 seconds.
        WARNING: This executes arbitrary code. Use responsibly.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout + result.stderr
            return output.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 60 seconds."
        except Exception as e:
            return f"ERROR: {e}"

    tools = [read_file, write_file, list_directory, create_directory, delete_file, search_code, run_shell]

    # Add browser tools if playwright is available
    try:
        from agent.browser_tool import make_browser_tools
        tools.extend(make_browser_tools(project_root))
    except ImportError:
        pass  # playwright not installed — skip browser tools

    return tools
