"""
MCP Client — manages stdio connections to external MCP servers.

Each server is defined in ~/.config/neuralclaude/mcp_servers.json:
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"],
      "env": {}
    },
    {
      "name": "github",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"}
    }
  ]
}
"""

from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Config path for MCP servers
MCP_CONFIG_PATH = Path.home() / ".config" / "neuralclaude" / "mcp_servers.json"


class MCPServerConnection:
    """Represents a live stdio connection to one MCP server process."""

    def __init__(self, name: str, command: str, args: list[str], env: dict[str, str]):
        self.name = name
        self.command = command
        self.args = args
        self.env = env
        self._session = None
        self._tools: list[dict[str, Any]] = []
        self._connected = False

    async def connect(self) -> bool:
        """Start the MCP server process and initialise the session."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=self.env or None,
            )

            self._stdio_ctx = stdio_client(server_params)
            self._read, self._write = await self._stdio_ctx.__aenter__()

            self._session_ctx = ClientSession(self._read, self._write)
            self._session = await self._session_ctx.__aenter__()

            await self._session.initialize()
            await self._refresh_tools()
            self._connected = True
            logger.info(f"[MCP] Connected to '{self.name}' with {len(self._tools)} tools.")
            return True

        except Exception as e:
            logger.error(f"[MCP] Failed to connect to '{self.name}': {e}")
            self._connected = False
            return False

    async def _refresh_tools(self):
        """Fetch the tool list from the server."""
        if not self._session:
            return
        result = await self._session.list_tools()
        self._tools = [
            {
                "name": f"{self.name}__{t.name}",   # prefix to avoid name collisions
                "original_name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema or {"type": "object", "properties": {}},
                "server": self.name,
            }
            for t in result.tools
        ]

    async def call_tool(self, original_tool_name: str, params: dict[str, Any]) -> str:
        """Call a tool on this MCP server and return its text output."""
        if not self._session:
            return "Error: MCP server not connected."
        try:
            result = await self._session.call_tool(original_tool_name, params)
            parts = []
            for content in result.content:
                if hasattr(content, "text"):
                    parts.append(content.text)
                else:
                    parts.append(str(content))
            return "\n".join(parts) if parts else "(empty response)"
        except Exception as e:
            return f"Error calling MCP tool '{original_tool_name}': {e}"

    async def disconnect(self):
        """Cleanly shut down the server connection."""
        try:
            if hasattr(self, "_session_ctx") and self._session_ctx:
                await self._session_ctx.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            if hasattr(self, "_stdio_ctx") and self._stdio_ctx:
                await self._stdio_ctx.__aexit__(None, None, None)
        except Exception:
            pass
        self._connected = False

    @property
    def tools(self) -> list[dict[str, Any]]:
        return self._tools

    @property
    def is_connected(self) -> bool:
        return self._connected


class MCPManager:
    """Manages all configured MCP server connections."""

    def __init__(self):
        self._servers: dict[str, MCPServerConnection] = {}

    @staticmethod
    def load_config() -> list[dict]:
        """Read mcp_servers.json. Returns empty list if not found."""
        if not MCP_CONFIG_PATH.exists():
            return []
        try:
            data = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("servers", [])
        except Exception as e:
            logger.error(f"[MCP] Failed to read config: {e}")
            return []

    async def connect_all(self) -> int:
        """Connect to all configured servers. Returns count of successful connections."""
        configs = self.load_config()
        connected = 0
        tasks = []

        for cfg in configs:
            name = cfg.get("name", "unnamed")
            conn = MCPServerConnection(
                name=name,
                command=cfg.get("command", ""),
                args=cfg.get("args", []),
                env=cfg.get("env", {}),
            )
            self._servers[name] = conn
            tasks.append(conn.connect())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if r is True:
                connected += 1
        return connected

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Return all tools from all connected servers."""
        tools = []
        for server in self._servers.values():
            if server.is_connected:
                tools.extend(server.tools)
        return tools

    async def call_tool(self, prefixed_name: str, params: dict[str, Any]) -> str:
        """Route a tool call to the right server using the prefixed name."""
        parts = prefixed_name.split("__", 1)
        if len(parts) != 2:
            return f"Error: invalid MCP tool name format '{prefixed_name}'"
        server_name, original_name = parts
        server = self._servers.get(server_name)
        if not server or not server.is_connected:
            return f"Error: MCP server '{server_name}' is not connected."
        return await server.call_tool(original_name, params)

    async def disconnect_all(self):
        """Disconnect from all servers cleanly."""
        await asyncio.gather(*[s.disconnect() for s in self._servers.values()])

    def status(self) -> list[dict]:
        """Return connection status for all servers."""
        return [
            {
                "name": name,
                "connected": server.is_connected,
                "tools": len(server.tools),
            }
            for name, server in self._servers.items()
        ]
