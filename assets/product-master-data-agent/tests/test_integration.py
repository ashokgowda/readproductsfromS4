"""Integration test: end-to-end agent flow with mocked LLM and MCP tools."""
import logging
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.tools import StructuredTool

# Ensure app/ is on sys.path so peer-level imports work (mirrors conftest add_agent_to_path)
_APP_PATH = str(Path(__file__).parents[1] / "app")
if _APP_PATH not in sys.path:
    sys.path.insert(0, _APP_PATH)

_USER_SUB_PATCH = patch("agent.get_user_sub", return_value="test-user")
_LLM_PATCH = patch("langchain_litellm.ChatLiteLLM")
_CREATE_AGENT_PATCH = patch("agent.create_agent")
_SUMMARIZATION_PATCH = patch("langchain.agents.middleware.SummarizationMiddleware")


def _make_tool(name: str) -> StructuredTool:
    """Create a real StructuredTool for testing (required by create_agent)."""
    return StructuredTool.from_function(
        func=lambda **kwargs: "mock result",
        name=name,
        description=f"Mock tool {name}",
    )


@pytest.mark.asyncio
async def test_end_to_end_product_query():
    """
    Simulated Sales Rep asks about a product.
    Agent selects the correct MCP tool and returns a formatted answer.
    All external systems (LLM, MCP) are mocked — runs offline.
    """
    os.environ["IBD_TESTING"] = "true"

    mock_tools = [
        _make_tool("get_a_product_for_api_product_srv"),
        _make_tool("get_a_productdescription_for_api_product_srv"),
        _make_tool("list_a_productclass_for_api_clfn_product_srv"),
    ]

    mock_final_message = MagicMock()
    mock_final_message.content = (
        "Product TG-11 (Notebook Basic 15) has a base unit of measure of EA (Each). "
        "It belongs to product group L001."
    )

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={"messages": [mock_final_message]})

    from agent import SampleAgent

    with _USER_SUB_PATCH, _LLM_PATCH, _SUMMARIZATION_PATCH, _CREATE_AGENT_PATCH as mock_create:
        mock_create.return_value = mock_graph

        with patch("agent.get_mcp_tools", new=AsyncMock(return_value=mock_tools)):
            agent = SampleAgent()
            result = await agent.invoke(
                query="What is the description and base unit of measure for product TG-11?",
                context_id="integration-test-1",
                tools=mock_tools,
            )

    assert result.status == "completed"
    assert len(result.message) > 0
    mock_graph.ainvoke.assert_called_once()
    call_args = mock_graph.ainvoke.call_args[0][0]
    assert "messages" in call_args


@pytest.mark.asyncio
async def test_stream_end_to_end():
    """Agent stream() must yield a processing chunk followed by the final response."""
    os.environ["IBD_TESTING"] = "true"

    mock_tools = [_make_tool("list_a_product_for_api_product_srv")]

    mock_final = MagicMock()
    mock_final.content = "Found 2 products matching 'notebook': TG-11, TG-12."

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={"messages": [mock_final]})

    from agent import SampleAgent

    with _USER_SUB_PATCH, _LLM_PATCH, _SUMMARIZATION_PATCH, _CREATE_AGENT_PATCH as mock_create:
        mock_create.return_value = mock_graph

        with patch("agent.get_mcp_tools", new=AsyncMock(return_value=mock_tools)):
            agent = SampleAgent()

            chunks = []
            async for chunk in agent.stream(
                query="Show me all notebook products",
                context_id="stream-test-1",
                tools=mock_tools,
            ):
                chunks.append(chunk)

    assert len(chunks) >= 2
    assert chunks[0]["is_task_complete"] is False
    assert chunks[-1]["is_task_complete"] is True
    assert len(chunks[-1]["content"]) > 0


@pytest.mark.asyncio
async def test_business_instrumentation_logs(caplog):
    """M1/M2/M3 milestones must be logged during agent execution."""
    os.environ["IBD_TESTING"] = "true"

    mock_tools = [_make_tool("get_a_product_for_api_product_srv")]

    mock_final = MagicMock()
    mock_final.content = "Product TG-11: Notebook Basic 15"

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={"messages": [mock_final]})

    from agent import SampleAgent

    with _USER_SUB_PATCH, _LLM_PATCH, _SUMMARIZATION_PATCH, _CREATE_AGENT_PATCH as mock_create:
        mock_create.return_value = mock_graph

        with patch("agent.get_mcp_tools", new=AsyncMock(return_value=mock_tools)):
            with caplog.at_level(logging.INFO, logger="agent"):
                agent = SampleAgent()
                await agent.invoke(
                    query="What is product TG-11?",
                    context_id="instrumentation-test",
                    tools=mock_tools,
                )

    log_text = caplog.text
    assert "M1.achieved" in log_text
    assert "M2" in log_text
    assert "M3" in log_text
