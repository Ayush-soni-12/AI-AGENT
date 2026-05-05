from typing import Any
import pathlib
import textwrap
from pydantic import BaseModel, Field

from tools.base import Tool, ToolResult, ToolInvocation, ToolKind, ToolConfirmation, FileDiff


class ArtifactParams(BaseModel):
    title: str = Field(..., description="The title of the artifact.")
    artifact_type: str = Field(..., description="Type of artifact: 'implementation_plan', 'walkthrough', 'roadmap', 'task', or 'other'.")
    summary: str = Field(..., description="A short summary of what this artifact contains.")
    content: str = Field(..., description="The Markdown content of the artifact.")


class ArtifactTool(Tool):
    name = "create_artifact"
    description = "Create a structured markdown artifact (like an implementation plan or walkthrough). Use this to plan out your work or summarize what you did. Implementation plans will pause and ask the user for approval."
    kind = ToolKind.WRITE
    schema = ArtifactParams

    def is_mutating(self, params: dict[str, Any]) -> bool:
        # We always want to show a confirmation screen for implementation plans!
        return True

    async def get_confirmation(self, invocation: ToolInvocation) -> ToolConfirmation | None:
        params = ArtifactParams(**invocation.params)
        
        # Require user approval for implementation plans AND roadmaps (since roadmaps define the whole project)
        if params.artifact_type not in ["implementation_plan", "roadmap"]:
            return None

        # Create a faux FileDiff so the UI can beautifully render the plan text!
        diff = FileDiff(
            path=pathlib.Path(f"ARTIFACT: {params.title}"),
            old_content="",
            new_content=params.content,
            is_new_file=True
        )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"📝 {params.artifact_type.replace('_', ' ').title()} Created: {params.title}\nPlease review the {params.artifact_type} before the AI proceeds.",
            diff=diff,
            affected_paths=[],
            is_dangerous=False
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ArtifactParams(**invocation.params)
        
        # Save artifacts to .agent_scratch/artifacts
        artifacts_dir = invocation.cwd / ".agent_scratch" / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up the title for a filename
        safe_title = "".join([c if c.isalnum() else "_" for c in params.title]).lower()
        filename = artifacts_dir / f"{params.artifact_type}_{safe_title}.md"
        
        # Format the artifact beautifully
        full_content = textwrap.dedent(f"""\
        # {params.title}
        
        **Type:** {params.artifact_type}
        **Summary:** {params.summary}
        
        ---
        
        {params.content}
        """)
        
        try:
            filename.write_text(full_content, encoding="utf-8")
            
            # If it's a plan, return a success message telling the agent to proceed
            if params.artifact_type == "implementation_plan":
                return ToolResult.success_result(
                    f"Implementation plan '{params.title}' created and APPROVED by the user.\n"
                    f"Saved to: {filename}\n"
                    "You may now proceed with executing the plan."
                )
            else:
                return ToolResult.success_result(
                    f"Artifact '{params.title}' successfully saved to: {filename}"
                )
                
        except Exception as e:
            return ToolResult.error_result(f"Failed to save artifact: {e}")
