import os
import re
from pathlib import Path
from pydantic import BaseModel, Field
from tools.base import Tool, ToolInvocation, ToolResult, ToolKind

class GrepParams(BaseModel):
    query: str = Field(..., description="The string or regex pattern to search for.")
    path: str = Field(".", description="The relative directory to search in recursively.")
    include: str = Field(None, description="Optional extension filter (e.g., '.py')")

class GrepTool(Tool):
    name = "grep_search"
    description = "Perform a fast recursive text/regex search across multiple files to find functions, classes, or code logic."
    kind = ToolKind.READ
    schema = GrepParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = GrepParams(**invocation.params)
        base_path = (invocation.cwd / params.path).resolve()
        
        if not base_path.exists():
            return ToolResult.error_result(f"Path '{params.path}' does not exist.")

        if not base_path.is_relative_to(invocation.cwd):
            return ToolResult.error_result("Cannot search outside project scope.")

        try:
            pattern = re.compile(params.query, re.IGNORECASE)
        except re.error as e:
            return ToolResult.error_result(f"Invalid regex pattern: {e}")

        ignore_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
        results = []
        match_count = 0
        file_count = 0
        
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            
            for file in files:
                if file.startswith("."): continue
                if params.include and not file.endswith(params.include): continue
                
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    file_match = False
                    for i, line in enumerate(lines, 1):
                        if pattern.search(line):
                            if not file_match:
                                rel_p = file_path.relative_to(invocation.cwd)
                                results.append(f"\n🔍 **{rel_p}**")
                                file_match = True
                                file_count += 1
                                
                            results.append(f"  Line {i}: {line.strip()[:150]}")
                            match_count += 1
                            if match_count >= 100:
                                results.append("\n⚠️ Truncated: Reached 100 match display limit.")
                                return ToolResult.success_result("\n".join(results))
                except UnicodeDecodeError:
                    continue  # Ignore binary
                except Exception:
                    continue
                    
        if match_count == 0:
            return ToolResult.success_result(f"No matches found for '{params.query}'.")
            
        return ToolResult.success_result(f"Found {match_count} matches across {file_count} files:\n" + "\n".join(results))
