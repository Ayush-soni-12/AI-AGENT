"""
Git utilities for Neural Claude's autonomous commit and PR features.
All functions are async and return plain strings for display in the TUI.
"""

from __future__ import annotations
import asyncio
from pathlib import Path


async def _run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode().strip(), stderr.decode().strip()


async def is_git_repo(cwd: Path) -> bool:
    """Return True if the current directory is inside a git repo."""
    code, _, _ = await _run_git(["rev-parse", "--git-dir"], cwd)
    return code == 0


async def get_staged_diff(cwd: Path) -> str:
    """Return the diff of currently staged changes."""
    _, diff, _ = await _run_git(["diff", "--cached"], cwd)
    return diff


async def get_unstaged_diff(cwd: Path) -> str:
    """Return the diff of all tracked but unstaged changes."""
    _, diff, _ = await _run_git(["diff"], cwd)
    return diff


async def get_untracked_files(cwd: Path) -> list[str]:
    """Return a list of untracked files."""
    _, out, _ = await _run_git(
        ["ls-files", "--others", "--exclude-standard"], cwd
    )
    return [f for f in out.splitlines() if f.strip()]


async def stage_all(cwd: Path) -> bool:
    """Run git add -A. Returns True on success."""
    code, _, _ = await _run_git(["add", "-A"], cwd)
    return code == 0


async def commit(message: str, cwd: Path) -> tuple[bool, str]:
    """Commit staged changes with message. Returns (success, output)."""
    code, out, err = await _run_git(["commit", "-m", message], cwd)
    return code == 0, out or err


async def get_current_branch(cwd: Path) -> str:
    """Return the name of the current branch."""
    _, branch, _ = await _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    return branch or "HEAD"


async def get_branch_diff_vs_main(cwd: Path, base: str = "main") -> str:
    """Return the combined diff of this branch vs base branch."""
    _, diff, _ = await _run_git(["diff", f"{base}...HEAD"], cwd)
    return diff


async def get_branch_commits(cwd: Path, base: str = "main") -> str:
    """Return one-line log of commits on this branch not in base."""
    _, log, _ = await _run_git(
        ["log", f"{base}..HEAD", "--oneline", "--no-decorate"], cwd
    )
    return log


async def has_gh_cli() -> bool:
    """Return True if the GitHub CLI (gh) is installed and authenticated."""
    proc = await asyncio.create_subprocess_exec(
        "gh", "auth", "status",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()
    return proc.returncode == 0


async def create_pr(title: str, body: str, cwd: Path) -> tuple[bool, str]:
    """Create a GitHub PR via gh CLI. Returns (success, output_or_url)."""
    proc = await asyncio.create_subprocess_exec(
        "gh", "pr", "create",
        "--title", title,
        "--body", body,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode().strip() or stderr.decode().strip()
    return proc.returncode == 0, out


async def generate_commit_message(diff: str, client) -> str:
    """Use the LLM to generate a conventional commit message from a diff.

    Args:
        diff:   The output of git diff --cached.
        client: An LLMClient instance.
    """
    from client.response import StreamEventType

    if not diff.strip():
        return ""

    # Truncate very large diffs to stay within token limits
    max_diff_chars = 12_000
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n... (diff truncated)"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Git commit message expert. "
                "Write a single commit message in the Conventional Commits format "
                "(feat/fix/refactor/docs/chore/test/style). "
                "Output ONLY the commit message — no explanation, no markdown fences, "
                "no extra text. Keep the subject line under 72 characters. "
                "If there are multiple logical changes, pick the most important type. "
                "Add a short bullet-point body after a blank line if the change is complex."
            ),
        },
        {
            "role": "user",
            "content": f"Generate a commit message for this diff:\n\n{diff}",
        },
    ]

    result = []
    async for event in client.chat_completion(messages, tools=None, stream=True):
        if event.type == StreamEventType.TEXT_DELTA and event.text_delta:
            result.append(event.text_delta.content)

    return "".join(result).strip()


async def generate_pr_description(commits: str, diff: str, branch: str, client) -> tuple[str, str]:
    """Use the LLM to generate a PR title + body from commits and diff.

    Args:
        commits: One-line git log of branch commits.
        diff:    Full diff vs main.
        branch:  Current branch name.
        client:  An LLMClient instance.

    Returns:
        (title, body) as strings.
    """
    from client.response import StreamEventType

    max_diff_chars = 10_000
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n... (diff truncated)"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior engineer writing GitHub Pull Request descriptions. "
                "Output JSON with exactly two keys: 'title' (string, under 72 chars) "
                "and 'body' (string, markdown formatted with ## sections). "
                "No other text outside the JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Branch: {branch}\n\n"
                f"Commits:\n{commits}\n\n"
                f"Diff:\n{diff}"
            ),
        },
    ]

    raw = []
    async for event in client.chat_completion(messages, tools=None, stream=True):
        if event.type == StreamEventType.TEXT_DELTA and event.text_delta:
            raw.append(event.text_delta.content)

    text = "".join(raw).strip()

    import json, re
    # Strip markdown fences if present
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text, flags=re.MULTILINE)

    try:
        data = json.loads(text)
        return data.get("title", branch), data.get("body", "")
    except Exception:
        # Fallback: first line = title, rest = body
        lines = text.splitlines()
        return lines[0] if lines else branch, "\n".join(lines[1:]) if len(lines) > 1 else text
