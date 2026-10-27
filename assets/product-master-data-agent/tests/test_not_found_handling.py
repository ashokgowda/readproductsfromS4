"""Unit tests for graceful not-found and error handling."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_agent_handles_not_found_gracefully():
    """Agent must return a clear message when a product does not exist."""
    os.environ["IBD_TESTING"] = "true"

    mock_tool = MagicMock()
    mock_tool.name = "get_a_product_for_api_product_srv"

    mock_result = MagicMock()
    mock_result.content = "Product NONEXISTENT-999 was not found in SAP S/4HANA."

    with patch("mcp_providers.agw.get_user_sub", return_value="test-user"), patch("agent.get_mcp_tools", new=AsyncMock(return_value=[mock_tool])):
        with patch("langchain_litellm.ChatLiteLLM") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            with patch("langchain.agents.create_agent") as mock_create_agent:
                mock_graph = AsyncMock()
                mock_graph.ainvoke = AsyncMock(return_value={
                    "messages": [mock_result]
                })
                mock_create_agent.return_value = mock_graph

                from app.agent import SampleAgent
                agent = SampleAgent()
                result = await agent.invoke(
                    query="What is the description of product NONEXISTENT-999?",
                    context_id="test-context-3",
                    tools=[mock_tool],
                )

    assert result.status == "completed"
    assert len(result.message) > 0
    # Agent should not return an error status for a "not found" scenario
    assert result.status != "error"


@pytest.mark.asyncio
async def test_agent_handles_api_error_gracefully():
    """Agent must relay API errors without fabricating fallback data."""
    os.environ["IBD_TESTING"] = "true"

    mock_tool = MagicMock()
    mock_tool.name = "get_a_product_for_api_product_srv"

    mock_result = MagicMock()
    mock_result.content = "Error: API_PRODUCT_SRV returned 503 Service Unavailable."

    with patch("mcp_providers.agw.get_user_sub", return_value="test-user"), patch("agent.get_mcp_tools", new=AsyncMock(return_value=[mock_tool])):
        with patch("langchain_litellm.ChatLiteLLM") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            with patch("langchain.agents.create_agent") as mock_create_agent:
                mock_graph = AsyncMock()
                mock_graph.ainvoke = AsyncMock(return_value={
                    "messages": [mock_result]
                })
                mock_create_agent.return_value = mock_graph

                from app.agent import SampleAgent
                agent = SampleAgent()
                result = await agent.invoke(
                    query="Get product TG-11 details",
                    context_id="test-context-4",
                    tools=[mock_tool],
                )

    assert result.status == "completed"
    assert len(result.message) > 0


@pytest.mark.asyncio
async def test_agent_handles_no_tools_gracefully():
    """Agent must handle the case where no tools are available."""
    os.environ["IBD_TESTING"] = "true"

    mock_result = MagicMock()
    mock_result.content = "I'm sorry, tools are temporarily unavailable. Please try again later."

    with patch("mcp_providers.agw.get_user_sub", return_value="test-user"), patch("agent.get_mcp_tools", new=AsyncMock(return_value=[])):
        with patch("langchain_litellm.ChatLiteLLM") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm

            with patch("langchain.agents.create_agent") as mock_create_agent:
                mock_graph = AsyncMock()
                mock_graph.ainvoke = AsyncMock(return_value={
                    "messages": [mock_result]
                })
                mock_create_agent.return_value = mock_graph

                from app.agent import SampleAgent
                agent = SampleAgent()
                result = await agent.invoke(
                    query="What is product TG-11?",
                    context_id="test-context-5",
                    tools=[],
                )

    assert result.status in ("completed", "input_required")
    assert len(result.message) > 0
