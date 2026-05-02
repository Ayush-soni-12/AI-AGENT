import asyncio
from pydantic import BaseModel, Field
from typing import Optional
from tools.base import Tool, ToolInvocation, ToolResult, ToolKind

class ShellParams(BaseModel):
    command: str = Field(..., description="The bash/shell command to execute.")
    background: bool = Field(False, description="Set to true to run this as a persistent background process (e.g. for dev servers).")
    process_id: Optional[str] = Field(None, description="A unique name for the background process (required if background=True).")

class ShellTool(Tool):
    name = "shell"
    description = (
        "Run a terminal command. By default, it waits for the command to finish (30s timeout). "
        "If background=True, it runs the command persistently and returns immediately. "
        "Use background=True for starting dev servers or watchers."
    )
    kind = ToolKind.SHELL
    schema = ShellParams
    
    TIMEOUT_SECONDS = 30.0

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ShellParams(**invocation.params)
        agent = getattr(invocation, 'agent', None)
        
        if params.background:
            if not params.process_id:
                return ToolResult.error_result("process_id is required for background tasks.")
            
            if not agent or not hasattr(agent, 'process_manager'):
                return ToolResult.error_result("Process manager not available in current context.")

            success = await agent.process_manager.start_process(
                params.process_id, 
                params.command, 
                str(invocation.cwd)
            )
            
            if success:
                return ToolResult.success_result(
                    f"Process '{params.process_id}' started in background.\nCommand: {params.command}\n"
                    "Logs will be streamed to the yellow log panel on the right."
                )
            else:
                return ToolResult.error_result(f"Failed to start background process '{params.process_id}'.")

        try:
            process = await asyncio.create_subprocess_shell(
                params.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=invocation.cwd,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                process.kill()
                stdout, stderr = await process.communicate()
                return ToolResult.error_result(
                    f"Command timed out after {self.TIMEOUT_SECONDS}s and was killed.",
                    output=stdout.decode('utf-8', errors='replace') if stdout else ""
                )

            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            output = (stdout_str + "\n" + stderr_str).strip()
            
            if process.returncode == 0:
                return ToolResult.success_result(output or "Success", exit_code=0)
            else:
                return ToolResult.error_result(f"Exit code {process.returncode}", output=output, exit_code=process.returncode)
                
        except Exception as e:
            return ToolResult.error_result(f"Error: {e}")

class GetLogsParams(BaseModel):
    process_id: str = Field(..., description="The unique name of the background process to read logs from.")

class GetLogsTool(Tool):
    name = "get_shell_logs"
    description = "Read the most recent logs from a background process started with 'shell(background=True)'."
    kind = ToolKind.READ
    schema = GetLogsParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = GetLogsParams(**invocation.params)
        agent = getattr(invocation, 'agent', None)
        if not agent or not hasattr(agent, 'process_manager'):
            return ToolResult.error_result("Process manager not available.")
            
        logs = agent.process_manager.get_logs(params.process_id)
        return ToolResult.success_result(logs)
