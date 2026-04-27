"""
MCPTool — a dynamic Tool wrapper around a remote MCP server tool.

Each tool discovered from an MCP server is wrapped in one of these
so the existing ToolRegistry can treat it like any built-in tool.
"""

from __future__ import annotations
from typing import Any, TYPE_CHECKING
from tools.base import Tool, ToolKind, ToolInvocation, ToolResult

if TYPE_CHECKING:
    from tools.mcp_client import MCPManager


class MCPTool(Tool):
    """Wraps a single MCP server tool so it can live in the ToolRegistry."""

    kind = ToolKind.MCP

    def __init__(self, tool_meta: dict[str, Any], manager: "MCPManager"):
        """
        Args:
            tool_meta: dict with keys name, original_name, description, input_schema, server
            manager:   the MCPManager that owns the server connection
        """
        self.name = tool_meta["name"]              # prefixed: "server__toolname"
        self.description = tool_meta["description"]
        self._original_name = tool_meta["original_name"]
        self._input_schema = tool_meta["input_schema"]
        self._manager = manager

    @property
    def schema(self) -> dict[str, Any]:
        """
        Return the tool's JSON schema in OpenAI function-calling format.
        MCP servers already supply jsonschema for their tools.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._input_schema,
        }

    def to_openai_schema(self) -> dict[str, Any]:
        """Override to directly use the MCP-provided jsonschema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._input_schema,
        }

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """MCP servers validate their own params; skip local validation."""
        return []

    def is_mutating(self, params: dict[str, Any]) -> bool:
        # Treat all MCP tools as mutating to ensure the user gets confirmation
        return True

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Forward the call to the MCP server via MCPManager."""
        output = await self._manager.call_tool(self.name, invocation.params)
        if output.lower().startswith("error"):
            return ToolResult.error_result(output)
        return ToolResult.success_result(output)
