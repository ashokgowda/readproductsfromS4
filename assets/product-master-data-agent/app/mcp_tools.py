"""MCP tools indirection layer.

This module is the single point through which the agent loads MCP tools.
In production, it fetches tools from the SAP Agent Gateway via the MCP providers.
In tests (IBD_TESTING=1), conftest.py monkey-patches get_mcp_tools to return
mock tools built from mcp-mock.json, so no real network calls are made.

Do NOT import directly from sap_cloud_sdk.agentgateway in agent code.
Always import from this module.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

logger = logging.getLogger(__name__)

_MCP_MOCK_PATH = Path(__file__).parents[1] / "mcp-mock.json"


def _build_mock_tools() -> list[BaseTool]:
    """Build StructuredTool instances from mcp-mock.json for offline testing."""
    if not _MCP_MOCK_PATH.exists():
        logger.warning("mcp-mock.json not found at %s — no tools available", _MCP_MOCK_PATH)
        return []

    with open(_MCP_MOCK_PATH) as f:
        mock_data: dict[str, Any] = json.load(f)

    tools: list[BaseTool] = []
    for server_slug, server in mock_data.get("servers", {}).items():
        for tool_name, tool_def in server.get("tools", {}).items():
            mock_response = tool_def.get("mock_response", {})

            def make_tool_fn(response: Any):
                def tool_fn(**kwargs: Any) -> str:
                    return json.dumps(response)
                return tool_fn

            tool = StructuredTool.from_function(
                func=make_tool_fn(mock_response),
                name=tool_name,
                description=tool_def.get("description", f"Mock tool {tool_name}"),
                args_schema=None,
            )
            tools.append(tool)

    logger.info("Loaded %d mock MCP tools from mcp-mock.json", len(tools))
    return tools


async def get_mcp_tools() -> list[BaseTool]:
    """Return MCP tools for the agent.

    In production (IBD_TESTING not set): fetches tools from the SAP Agent Gateway.
    In tests (IBD_TESTING=1): returns mock tools from mcp-mock.json.
    """
    if os.environ.get("IBD_TESTING"):
        return _build_mock_tools()

    # Production path: load from SAP Agent Gateway
    try:
        from sap_cloud_sdk.agentgateway import get_mcp_tools as _agw_get_tools  # type: ignore
        return await _agw_get_tools()
    except ImportError:
        logger.warning("sap_cloud_sdk.agentgateway not available — returning empty tool list")
        return []
