import os
from pydantic import BaseModel, Field
from tools.base import Tool, ToolInvocation, ToolResult, ToolKind, ToolConfirmation, FileDiff
from utils.paths import resolve_path

class WriteFileParams(BaseModel):
    path: str = Field(..., description="Path to the file to write (relative to working directory or absolute)")
    content: str = Field(..., description="The content to write to the file. Will completely overwrite the file.")

class WriteFileTool(Tool):
    name = "write_file"
    description = "Create or overwrite a text file. If the file exists, it will be completely overwritten with the new content."
    kind = ToolKind.WRITE
    schema = WriteFileParams

    async def get_confirmation(self, invocation: ToolInvocation) -> ToolConfirmation | None:
        params = WriteFileParams(**invocation.params)
        path = resolve_path(invocation.cwd, params.path)
        
        old_content = ""
        is_new_file = True
        
        if path.exists() and path.is_file():
            try:
                old_content = path.read_text(encoding="utf-8")
                is_new_file = False
            except Exception:
                old_content = "[Binary or unreadable file]"

        diff = FileDiff(
            path=path,
            old_content=old_content,
            new_content=params.content,
            is_new_file=is_new_file
        )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Write completely new content to {path.name}",
            diff=diff,
            affected_paths=[path],
            is_dangerous=True
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = WriteFileParams(**invocation.params)
        path = resolve_path(invocation.cwd, params.path)

        old_content = ""
        is_new_file = True
        
        if path.exists() and path.is_file():
            try:
                old_content = path.read_text(encoding="utf-8")
                is_new_file = False
            except Exception:
                old_content = "[Binary or unreadable file]"

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(params.content, encoding="utf-8")
            
            diff = FileDiff(
                path=path,
                old_content=old_content,
                new_content=params.content,
                is_new_file=is_new_file
            )
            
            return ToolResult.success_result(f"Successfully wrote {len(params.content)} characters to {path}", diff=diff)
        except Exception as e:
            return ToolResult.error_result(f"Failed to write file: {e}")
