"""tests/test_agent.py — integration test for agent/agent.py using a mock LLM"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / "hello.py").write_text('print("hello")\n')
    return tmp_path


def _make_mock_agent():
    """Return a mock compiled LangGraph agent that streams a text chunk."""
    async def _fake_astream(*args, **kwargs):
        msg = AIMessage(content="Hello from agent!")
        yield (msg, {})

    mock_agent = MagicMock()
    mock_agent.invoke = MagicMock(return_value={"messages": [AIMessage(content="Done.")]})
    mock_agent.astream = _fake_astream
    return mock_agent


def test_create_agent_mock(project: Path):
    """create_agent() builds something with invoke/astream when we mock build_model."""
    from agent.agent import create_agent

    with patch("agent.agent.build_model", return_value=MagicMock()), \
         patch("agent.agent.create_react_agent", return_value=_make_mock_agent()):
        agent = create_agent("openai/gpt-4o", project)

    assert hasattr(agent, "invoke")
    assert hasattr(agent, "astream")


@pytest.mark.asyncio
async def test_stream_response_yields_text(project: Path):
    """stream_response() yields at least one chunk when we inject a mock agent."""
    from agent.agent import stream_response

    mock_agent = _make_mock_agent()

    chunks = []
    async for chunk_type, content in stream_response(mock_agent, [], "Say hello"):
        chunks.append((chunk_type, content))

    assert len(chunks) > 0
    types = {c[0] for c in chunks}
    assert "text" in types
