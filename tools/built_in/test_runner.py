"""
RunTestsTool — auto-detects and runs the project's test suite / linter.

The agent calls this tool after any code change to verify correctness.
If tests fail, the output is fed back to the agent so it can self-correct.
"""

from __future__ import annotations
import asyncio
import json
from pathlib import Path
from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolResult, ToolKind


class RunTestsParams(BaseModel):
    command: str | None = Field(
        default=None,
        description=(
            "The exact shell command to run (e.g. 'pytest -x', 'npm test', 'make test'). "
            "If omitted, Neural Claude auto-detects the correct runner from your project files."
        ),
    )


class RunTestsTool(Tool):
    """Auto-detect and run the project test suite or linter, returning PASSED/FAILED status."""

    name = "run_tests"
    description = (
        "Run the project's tests or linter and return the result. "
        "ALWAYS call this after writing or modifying any code file. "
        "If the result is FAILED, read the errors, fix the code, then call run_tests again. "
        "Repeat until PASSED (max 3 iterations). Never declare 'done' until tests pass."
    )
    kind = ToolKind.SHELL
    schema = RunTestsParams

    TIMEOUT = 120.0   # 2 minutes max
    MAX_OUTPUT = 6000  # characters to feed back to the LLM

    # ------------------------------------------------------------------ #
    # Auto-detection                                                       #
    # ------------------------------------------------------------------ #

    def _detect_command(self, cwd: Path) -> str | None:
        """Scan the project directory and return the best test command."""

        # 1. AGENTS.md override — look for `test_command: <cmd>` line
        for agents_md in cwd.rglob("AGENTS.md"):
            for line in agents_md.read_text(errors="ignore").splitlines():
                stripped = line.strip()
                if stripped.lower().startswith("test_command:"):
                    cmd = stripped.split(":", 1)[1].strip()
                    if cmd:
                        return cmd

        # 2. Python — pytest (check pyproject.toml, pytest.ini, setup.cfg)
        has_pytest_config = (
            (cwd / "pytest.ini").exists()
            or (cwd / "setup.cfg").exists()
            or self._toml_has_section(cwd / "pyproject.toml", "tool.pytest")
            or self._toml_has_section(cwd / "pyproject.toml", "tool.pytest.ini_options")
        )
        if has_pytest_config:
            return "pytest -x --tb=short -q"

        # 3. Python — ruff linter
        has_ruff = (
            (cwd / ".ruff.toml").exists()
            or self._toml_has_section(cwd / "pyproject.toml", "tool.ruff")
        )
        if has_ruff:
            return "ruff check ."

        # 4. JavaScript / Node — npm test
        pkg = cwd / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                if "test" in data.get("scripts", {}):
                    return "npm test"
            except Exception:
                pass

        # 5. Makefile with a 'test' target
        makefile = cwd / "Makefile"
        if makefile.exists():
            content = makefile.read_text(errors="ignore")
            if "\ntest:" in content or content.startswith("test:"):
                return "make test"

        # 6. Legacy Python — bare pytest discovery
        if any((cwd / f).exists() for f in ("setup.py", "setup.cfg")):
            return "python -m pytest -x --tb=short -q"

        # 7. Check if any test files exist and fall back to pytest
        if list(cwd.rglob("test_*.py")) or list(cwd.rglob("*_test.py")):
            return "pytest -x --tb=short -q"

        return None

    @staticmethod
    def _toml_has_section(path: Path, section: str) -> bool:
        """Return True if the TOML file contains the given [section] header."""
        if not path.exists():
            return False
        try:
            content = path.read_text(encoding="utf-8")
            return f"[{section}]" in content
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Execution                                                            #
    # ------------------------------------------------------------------ #

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Detect test runner, execute it, return structured pass/fail output."""
        params = RunTestsParams(**invocation.params)
        cwd = invocation.cwd

        # Resolve command
        command = params.command or self._detect_command(cwd)

        if not command:
            return ToolResult.success_result(
                "STATUS: NO_TESTS\n"
                "No test runner detected. To enable auto-testing add a `test_command:` "
                "line to your AGENTS.md, or configure pytest / npm test / make test."
            )

        # Run it
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return ToolResult.error_result(
                    f"STATUS: ERROR\nCOMMAND: {command}\nTest run timed out after {self.TIMEOUT}s."
                )
        except Exception as e:
            return ToolResult.error_result(
                f"STATUS: ERROR\nCOMMAND: {command}\nFailed to start process: {e}"
            )

        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        combined = stdout_str
        if stderr_str:
            combined = (combined + "\n" + stderr_str).strip() if combined else stderr_str

        # Trim to keep tokens manageable
        if len(combined) > self.MAX_OUTPUT:
            half = self.MAX_OUTPUT // 2
            combined = (
                combined[:half]
                + f"\n\n... [{len(combined) - self.MAX_OUTPUT} chars truncated] ...\n\n"
                + combined[-half:]
            )

        passed = proc.returncode == 0
        status = "PASSED" if passed else "FAILED"

        report = (
            f"STATUS: {status}\n"
            f"COMMAND: {command}\n"
            f"EXIT CODE: {proc.returncode}\n"
            f"OUTPUT:\n{combined or '(no output)'}"
        )

        if passed:
            return ToolResult.success_result(report, exit_code=proc.returncode)
        else:
            return ToolResult.error_result(report, output=combined, exit_code=proc.returncode)
