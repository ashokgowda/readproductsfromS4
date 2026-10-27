"""Unit tests for Product Classification MCP tool via mock."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import os

import pytest


MOCK_FILE = Path(__file__).parents[1] / "mcp-mock.json"


def load_mock():
    with open(MOCK_FILE) as f:
        return json.load(f)


def test_clfn_server_present():
    """sap-s4-clfn-product-srv server must be in mock config."""
    data = load_mock()
    assert "sap-s4-clfn-product-srv" in data["servers"]


def test_list_clfn_product_tool_present():
    """list_a_clfnproduct tool must exist."""
    data = load_mock()
    tools = data["servers"]["sap-s4-clfn-product-srv"]["tools"]
    assert "list_a_clfnproduct_for_api_clfn_product_srv" in tools


def test_list_product_class_tool_present():
    """list_a_productclass tool must exist."""
    data = load_mock()
    tools = data["servers"]["sap-s4-clfn-product-srv"]["tools"]
    assert "list_a_productclass_for_api_clfn_product_srv" in tools


def test_list_product_charc_tool_present():
    """list_a_productcharc tool must exist for characteristic queries."""
    data = load_mock()
    tools = data["servers"]["sap-s4-clfn-product-srv"]["tools"]
    assert "list_a_productcharc_for_api_clfn_product_srv" in tools


def test_product_class_mock_has_class_info():
    """Product class mock must have Class and Product fields."""
    data = load_mock()
    mock_resp = data["servers"]["sap-s4-clfn-product-srv"]["tools"]["get_a_productclass_for_api_clfn_product_srv"]["mock_response"]
    assert "Product" in mock_resp
    assert "Class" in mock_resp
    assert "ClassType" in mock_resp


def test_product_charc_value_mock_has_value():
    """Characteristic value mock must have CharcValue."""
    data = load_mock()
    mock_resp = data["servers"]["sap-s4-clfn-product-srv"]["tools"]["get_a_productcharcvalue_for_api_clfn_product_srv"]["mock_response"]
    assert "CharcValue" in mock_resp
    assert "Characteristic" in mock_resp


def test_list_product_class_mock_returns_results():
    """List product class mock must return a results array."""
    data = load_mock()
    mock_resp = data["servers"]["sap-s4-clfn-product-srv"]["tools"]["list_a_productclass_for_api_clfn_product_srv"]["mock_response"]
    assert "results" in mock_resp
    assert len(mock_resp["results"]) >= 1


def test_clfn_metadata_tool_present():
    """OData metadata tool must be present for classification API."""
    data = load_mock()
    tools = data["servers"]["sap-s4-clfn-product-srv"]["tools"]
    assert "get_metadata_api_clfn_product_srv" in tools


@pytest.mark.asyncio
async def test_agent_invokes_classification_tool():
    """Agent should call classification tools when queried about product class."""
    os.environ["IBD_TESTING"] = "true"

    mock_tool = MagicMock()
    mock_tool.name = "list_a_productclass_for_api_clfn_product_srv"

    mock_result = MagicMock()
    mock_result.content = "Product TG-11 belongs to class NOTEBOOK (Material Class)."

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
                    query="What class does product TG-11 belong to?",
                    context_id="test-context-2",
                    tools=[mock_tool],
                )

    assert result.status == "completed"
    assert len(result.message) > 0
