"""
agent/agent.py
LangGraph ReAct agent with streaming support for Gradio.
"""

from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from agent.models import build_model
from agent.tools import make_tools

# ── System prompt ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert AI coding assistant helping the user work on a software project.

You have access to these tools (all sandboxed to the project directory):
- read_file: Read a file
- write_file: Write/update a file
- list_directory: List directory contents
- create_directory: Create a directory
- delete_file: Delete a file
- search_code: Search for text across files
- run_shell: Run shell commands (build, test, install, etc.)
- screenshot_html: Open a local HTML file in a headless browser and save a screenshot
- browse_url: Visit a URL, take a screenshot, and extract page text (great for smoke testing)
- get_page_content: Fetch a URL's rendered HTML (handles JavaScript)

CRITICAL RULES — follow these strictly:
1. **Narrate every step.** Before calling a tool, explain IN TEXT what you are about to do and why.
   Example: "Let me check the project structure first." then call list_directory.
2. **No redundant tool calls.** Never call the same tool with the same arguments twice in one session.
   If you already ran `list_directory .`, do not run it again — use what you already know.
3. **Stop when done.** After completing the task, write a clear TEXT summary of what you did.
   Do NOT keep calling tools after the task is complete.
4. **Be concise.** Show key results, not wall-of-text logs.
5. **Think before acting.** Plan your approach in text before using any tool.
"""


# ── Agent factory + cache ───────────────────────────────────────────────

# Cache key: (model_id, str(project_root))  →  compiled agent graph
_agent_cache: dict[tuple[str, str], object] = {}
_cache_key: tuple[str, str] | None = None


def create_agent(model_id: str, project_root: Path, max_steps: int = 30):
    """Build a compiled LangGraph ReAct agent for the given model and project."""
    llm = build_model(model_id)
    tools = make_tools(project_root)
    graph = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
    # Set recursion limit at compile time so astream() doesn't need a config,
    # which would trigger LangGraph's remote-routing code path.
    return graph.with_config({"recursion_limit": max_steps})


def get_agent(model_id: str, project_root: Path, max_steps: int = 30):
    """Return a cached agent, creating a new one only when model or project changes."""
    global _cache_key
    key = (model_id, str(project_root))
    if key != _cache_key or key not in _agent_cache:
        _agent_cache.clear()  # drop old entry to avoid memory buildup
        _agent_cache[key] = create_agent(model_id, project_root, max_steps)
        _cache_key = key
    return _agent_cache[key]


def invalidate_agent_cache() -> None:
    """Force the next get_agent() call to build a fresh agent."""
    global _cache_key
    _agent_cache.clear()
    _cache_key = None


# ── Streaming helper ────────────────────────────────────────────────────

def _extract_text(content) -> str:
    """Safely coerce LangChain message content to a plain string.

    content can be:
      - str   (most models)
      - list  (multi-part blocks, e.g. [{"type": "text", "text": "…"}, …])
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content) if content else ""


async def stream_response(
    agent,
    history: list[dict],
    user_message: str,
    recursion_limit: int = 30,
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Stream agent response chunks.

    Yields (chunk_type, content) where chunk_type is:
      "text"       — regular assistant text
      "tool_call"  — tool invocation (name + args)
      "tool_result"— tool output
    """
    # Convert Gradio messages format → LangChain messages
    lc_messages = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    lc_messages.append(HumanMessage(content=user_message))

    step = 0
    try:
        async for event in agent.astream(
            {"messages": lc_messages},
            stream_mode="messages",
        ):
            msg, metadata = event if isinstance(event, tuple) else (event, {})

            if isinstance(msg, AIMessage):
                text = _extract_text(msg.content)
                if text:
                    yield ("text", text)
                # Tool call announcements — emit a step label first
                for tc in (msg.tool_calls if hasattr(msg, "tool_calls") and msg.tool_calls else []):
                    step += 1
                    name = tc.get("name", "unknown_tool")
                    args = tc.get("args", {})
                    yield ("step", f"Step {step} — `{name}`")
                    yield ("tool_call", f"**🔧 {name}**\n```json\n{args}\n```")

            elif isinstance(msg, ToolMessage):
                content = _extract_text(msg.content)
                if len(content) > 2000:
                    content = content[:2000] + "\n… (truncated)"
                yield ("tool_result", content)

    except Exception as e:
        err = str(e)
        if "recursion" in err.lower() or "graphrecursion" in type(e).__name__.lower():
            yield ("text", f"\n\n⚠️ Agent reached the step limit ({recursion_limit} steps) and stopped. Try a more specific request.")
        else:
            raise


