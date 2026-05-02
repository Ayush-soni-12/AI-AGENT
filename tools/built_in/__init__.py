from tools.built_in.read_file import ReadFileTool
from tools.built_in.shell import ShellTool
from tools.built_in.write_file import WriteFileTool
from tools.built_in.memory import MemoryTool
from tools.built_in.replace import ReplaceInFileTool
from tools.built_in.list_dir import ListDirTool
from tools.built_in.grep_search import GrepTool
from tools.built_in.web_search import WebSearchTool
from tools.built_in.test_runner import RunTestsTool
from tools.built_in.screenshot import BrowserActionTool
from tools.built_in.artifact import ArtifactTool

__all__ = [
    "ReadFileTool",
    "ShellTool",
    "WriteFileTool",
    "MemoryTool",
    "ReplaceInFileTool",
    "ListDirTool",
    "GrepTool",
    "WebSearchTool",
    "RunTestsTool",
    "BrowserActionTool",
    "ArtifactTool",
]


def get_all_builtin_tools() -> list[type]:
    return [
        ReadFileTool,
        ShellTool,
        WriteFileTool,
        MemoryTool,
        ReplaceInFileTool,
        ListDirTool,
        GrepTool,
        WebSearchTool,
        RunTestsTool,
        BrowserActionTool,
        ArtifactTool,
    ]