"""
Loads AGENTS.md files from the project directory tree.

Per spec:
- Walks from CWD up toward the filesystem root collecting AGENTS.md files.
- Root-level files are appended first; more-deeply-nested files override.
- Returns a merged string ready to be injected into the system prompt.
"""

from pathlib import Path


def load_agents_md(cwd: Path) -> str:
    """
    Collect all AGENTS.md files in scope:
    - Every directory from filesystem root down to `cwd` (inclusive).
    Returns the merged content, or an empty string if none found.
    """
    # Build path chain from root → cwd so outer files come first (lower priority)
    chain: list[Path] = []
    current = cwd.resolve()
    while True:
        chain.append(current)
        parent = current.parent
        if parent == current:  # reached filesystem root
            break
        current = parent
    chain.reverse()  # root → cwd order

    blocks: list[str] = []
    for directory in chain:
        agents_file = directory / "AGENTS.md"
        if agents_file.exists() and agents_file.is_file():
            try:
                content = agents_file.read_text(encoding="utf-8").strip()
                if content:
                    rel_path = agents_file.relative_to(cwd) if directory != cwd else Path("AGENTS.md")
                    blocks.append(f"### From `{rel_path}`\n\n{content}")
            except Exception:
                pass  # skip unreadable files silently

    if not blocks:
        return ""

    header = (
        "# Project Instructions (AGENTS.md)\n\n"
        "The following instructions were loaded from AGENTS.md files in this project. "
        "More deeply nested files take precedence over outer ones.\n\n"
    )
    return header + "\n\n---\n\n".join(blocks)
