import os
from pathlib import Path
from pydantic import BaseModel, Field
from tools.base import Tool, ToolInvocation, ToolResult, ToolKind

class ListDirParams(BaseModel):
    path: str = Field(".", description="The relative directory path to map.")
    depth: int = Field(2, description="Maximum directory depth to recursively explore (1-5).")

class ListDirTool(Tool):
    name = "list_dir"
    description = "List all files and subdirectories within a specific local directory tree to understand code architecture. Ignores hidden folders like .git and node_modules."
    kind = ToolKind.READ
    schema = ListDirParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ListDirParams(**invocation.params)
        base_path = (invocation.cwd / params.path).resolve()
        
        if not base_path.exists() or not base_path.is_dir():
            return ToolResult.error_result(f"Directory '{params.path}' does not exist.")

        if not base_path.is_relative_to(invocation.cwd):
            return ToolResult.error_result("Cannot access directory outside project scope.")

        depth_limit = max(1, min(5, params.depth))
        ignore_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".pytest_cache"}
        
        output = [f"📦 {base_path.name}/"]
        
        def walk_dir(current_path: Path, current_depth: int):
            if current_depth >= depth_limit:
                return
                
            try:
                entries = sorted(list(current_path.iterdir()), key=lambda e: (not e.is_dir(), e.name))
                for entry in entries:
                    if entry.name in ignore_dirs or (entry.name.startswith(".") and entry.name != ".env"):
                        continue
                    
                    indent = "    " * current_depth + "├── "
                    if entry.is_dir():
                        output.append(f"{indent}📁 {entry.name}/")
                        walk_dir(entry, current_depth + 1)
                    else:
                        output.append(f"{indent}📄 {entry.name}")
            except Exception as e:
                output.append(f"    " * current_depth + f"⚠️ Permission Denied: {e}")

        walk_dir(base_path, 0)
        
        return ToolResult.success_result("\n".join(output))
