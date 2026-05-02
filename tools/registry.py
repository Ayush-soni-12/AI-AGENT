from tools.base import Tool,ToolResult,ToolInvocation
import logging
from typing import Any
from pathlib import Path
from tools.built_in import get_all_builtin_tools


logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools : dict[str,Tool] = {}

    def register(self,tool:Tool) -> None:
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} is already registered. Overwriting.")
        self._tools[tool.name] = tool
        logger.info(f"Tool {tool.name} registered")

    
    def unregister(self,tool_name:str) -> bool:
        if tool_name  in self._tools:
            del self._tools[tool_name]
            return True
        return False

    def get(self,name:str) -> Tool | None:
        if name in self._tools:
            return self._tools[name]
        logger.error(f"Tool {name} not found")
        return None

    def get_tools(self)-> list[Tool]:
        tools : list[Tool]  = []

        for tool in self._tools.values():
            tools.append(tool)

        return tools
    
    def get_schema(self):
        return [tool.to_openai_schema() for tool in self.get_tools()]

        

    async def invoke(self, name: str, params: dict[str, Any], cwd: Path | None, agent: Any = None):
        tool = self.get(name)

        if tool is None:
            return ToolResult.error_result(f"Tool {name} not found",metadata={'tool_name':name})

        validataton_error  = tool.validate_params(params)
        if validataton_error:
            return ToolResult.error_result(f"Validation error: {validataton_error}",metadata={'tool_name':name})


        invocation = ToolInvocation(params=params, cwd=cwd or Path.cwd(), agent=agent)

        try:
            result = await tool.execute(invocation)
            return result
        except Exception as e:
            return ToolResult.error_result(f"Error executing tool {name}: {e}",metadata={'tool_name':name})
        
        
from config.config import ConfigManager

def create_tool_registry(mcp_manager=None) -> ToolRegistry:
    """Create and populate the tool registry.

    Args:
        mcp_manager: optional MCPManager whose discovered tools will be
                     registered alongside the built-in tools.
    """
    registry = ToolRegistry()
    config = ConfigManager()

    for tool_class in get_all_builtin_tools():
        registry.register(tool_class(config))

    if mcp_manager is not None:
        from tools.mcp_tool import MCPTool
        for tool_meta in mcp_manager.get_all_tools():
            registry.register(MCPTool(tool_meta, mcp_manager))

    return registry