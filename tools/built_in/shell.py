import asyncio
from pydantic import BaseModel, Field
from tools.base import Tool, ToolInvocation, ToolResult, ToolKind

class ShellParams(BaseModel):
    command: str = Field(..., description="The bash/shell command to execute. Use this whenever you need to explore directories (ls), read paths, search files, or execute operations.")

class ShellTool(Tool):
    name = "shell"
    description = "Run a terminal command in the background. Use this whenever you need to understand the file system, list folders, or run code. Features a 30-second timeout for safety."
    kind = ToolKind.SHELL
    schema = ShellParams
    
    TIMEOUT_SECONDS = 30.0

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ShellParams(**invocation.params)
        
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
                # If the command takes too long, kill it to prevent freezing the agent!
                process.kill()
                stdout, stderr = await process.communicate()
                return ToolResult.error_result(
                    f"Command completely timed out after {self.TIMEOUT_SECONDS} seconds and was killed.",
                    output=stdout.decode('utf-8', errors='replace') if stdout else ""
                )

            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            output = stdout_str.strip()
            if stderr_str.strip():
                if output:
                    output += "\n--- STDERR ---\n" + stderr_str.strip()
                else:
                    output = stderr_str.strip()
                    
            if process.returncode == 0:
                if not output:
                    output = "Command executed successfully with no output."
                return ToolResult.success_result(output, exit_code=process.returncode)
            else:
                return ToolResult.error_result(
                    f"Command failed with exit code {process.returncode}", 
                    output=output, 
                    exit_code=process.returncode
                )
                
        except Exception as e:
            return ToolResult.error_result(f"Failed to start shell process: {e}")
