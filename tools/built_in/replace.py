from pydantic import BaseModel, Field
from tools.base import Tool, ToolInvocation, ToolResult, ToolKind, ToolConfirmation, FileDiff
from utils.paths import resolve_path

class ReplaceInFileParams(BaseModel):
    path: str = Field(..., description="Path to the file to edit.")
    target_content: str = Field(..., description="The exact block of text/code to find and replace. Must match the file exactly (including whitespace and indentation).")
    replacement_content: str = Field(..., description="The new code that will replace the target_content.")

class ReplaceInFileTool(Tool):
    name = "replace_in_file"
    description = "Surgically edit an existing file by replacing a specific block of text. This avoids overwriting the entire file."
    kind = ToolKind.WRITE
    schema = ReplaceInFileParams

    async def get_confirmation(self, invocation: ToolInvocation) -> ToolConfirmation | None:
        params = ReplaceInFileParams(**invocation.params)
        path = resolve_path(invocation.cwd, params.path)
        
        if not path.exists() or not path.is_file():
            return None # The execution block handles missing file errors gracefully
            
        try:
            old_content = path.read_text(encoding="utf-8")
        except Exception:
            return None

        # Extract the patch natively
        if params.target_content in old_content:
            new_content = old_content.replace(params.target_content, params.replacement_content, 1)
        else:
            new_content = old_content # If it errors out, Diff will just be blank so it's safe

        diff = FileDiff(
            path=path,
            old_content=old_content,
            new_content=new_content,
        )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Surgically patch contents inside {path.name}",
            diff=diff,
            affected_paths=[path],
            is_dangerous=True
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ReplaceInFileParams(**invocation.params)
        path = resolve_path(invocation.cwd, params.path)

        if not path.exists() or not path.is_file():
            return ToolResult.error_result(f"File not found: {path}")

        try:
            old_content = path.read_text(encoding="utf-8")
            
            if params.target_content not in old_content:
                return ToolResult.error_result("The `target_content` string was not found EXACTLY within the file. Try expanding your search block or checking exact spacing/indentation.")
                
            new_content = old_content.replace(params.target_content, params.replacement_content, 1)
            
            path.write_text(new_content, encoding="utf-8")
            
            return ToolResult.success_result(f"Successfully patched {path}")
        except Exception as e:
            return ToolResult.error_result(f"Failed to edit file: {e}")
