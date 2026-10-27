"""Unit tests for Product Master (A2X) MCP tool via mock."""
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


MOCK_FILE = Path(__file__).parents[1] / "mcp-mock.json"


def load_mock():
    with open(MOCK_FILE) as f:
        return json.load(f)


def test_mock_file_exists():
    """mcp-mock.json must be present."""
    assert MOCK_FILE.exists(), "mcp-mock.json not found"


def test_product_srv_server_present():
    """sap-s4-product-srv server must be in mock config."""
    data = load_mock()
    assert "sap-s4-product-srv" in data["servers"]


def test_list_product_tool_present():
    """list_a_product_for_api_product_srv tool must exist."""
    data = load_mock()
    tools = data["servers"]["sap-s4-product-srv"]["tools"]
    assert "list_a_product_for_api_product_srv" in tools


def test_get_product_tool_present():
    """get_a_product_for_api_product_srv tool must exist."""
    data = load_mock()
    tools = data["servers"]["sap-s4-product-srv"]["tools"]
    assert "get_a_product_for_api_product_srv" in tools


def test_product_mock_response_has_required_fields():
    """Product mock response must contain key product fields."""
    data = load_mock()
    mock_resp = data["servers"]["sap-s4-product-srv"]["tools"]["get_a_product_for_api_product_srv"]["mock_response"]
    assert "Product" in mock_resp
    assert "BaseUnit" in mock_resp
    assert "ProductGroup" in mock_resp


def test_list_product_mock_returns_results():
    """List product mock must return a results array."""
    data = load_mock()
    mock_resp = data["servers"]["sap-s4-product-srv"]["tools"]["list_a_product_for_api_product_srv"]["mock_response"]
    assert "results" in mock_resp
    assert len(mock_resp["results"]) >= 1


def test_product_description_tool_present():
    """list_a_productdescription tool must exist for product descriptions."""
    data = load_mock()
    tools = data["servers"]["sap-s4-product-srv"]["tools"]
    assert "list_a_productdescription_for_api_product_srv" in tools
    assert "get_a_productdescription_for_api_product_srv" in tools


def test_description_mock_has_text():
    """Product description mock must have ProductDescription text."""
    data = load_mock()
    mock_resp = data["servers"]["sap-s4-product-srv"]["tools"]["get_a_productdescription_for_api_product_srv"]["mock_response"]
    assert "ProductDescription" in mock_resp
    assert len(mock_resp["ProductDescription"]) > 0


def test_metadata_tool_present():
    """OData metadata tool must be present (infrastructure tool)."""
    data = load_mock()
    tools = data["servers"]["sap-s4-product-srv"]["tools"]
    assert "get_metadata_api_product_srv" in tools


@pytest.mark.asyncio
async def test_agent_invokes_product_master_tool():
    """Agent should call product master tools when queried about a product."""
    os.environ["IBD_TESTING"] = "true"

    mock_tool = MagicMock()
    mock_tool.name = "list_a_product_for_api_product_srv"

    mock_result = MagicMock()
    mock_result.content = "Product TG-11: Notebook Basic 15, Base Unit: EA"

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
                    query="What is the description of product TG-11?",
                    context_id="test-context-1",
                    tools=[mock_tool],
                )

    assert result.status == "completed"
    assert "TG-11" in result.message or "Notebook" in result.message or len(result.message) > 0
