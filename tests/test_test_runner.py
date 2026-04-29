"""
Tests for RunTestsTool._detect_command.

These tests create fake project structures in a temporary directory and verify
that the auto-detector picks the right test command without running anything.
"""

import json
import pytest
from pathlib import Path

from tools.built_in.test_runner import RunTestsTool


@pytest.fixture
def tool():
    """Return a RunTestsTool instance (no config needed for detection)."""
    from unittest.mock import MagicMock
    return RunTestsTool(config=MagicMock())


class TestAutoDetection:

    def test_no_config_returns_none(self, tmp_path, tool):
        result = tool._detect_command(tmp_path)
        assert result is None

    def test_detects_pytest_via_pytest_ini(self, tmp_path, tool):
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        cmd = tool._detect_command(tmp_path)
        assert cmd is not None
        assert "pytest" in cmd

    def test_detects_pytest_via_pyproject_toml(self, tmp_path, tool):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\ntestpaths = ['tests']\n"
        )
        cmd = tool._detect_command(tmp_path)
        assert cmd is not None
        assert "pytest" in cmd

    def test_detects_ruff_via_pyproject_toml(self, tmp_path, tool):
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
        cmd = tool._detect_command(tmp_path)
        assert cmd is not None
        assert "ruff" in cmd

    def test_detects_ruff_via_ruff_toml(self, tmp_path, tool):
        (tmp_path / ".ruff.toml").write_text("line-length = 88\n")
        cmd = tool._detect_command(tmp_path)
        assert cmd is not None
        assert "ruff" in cmd

    def test_detects_npm_test(self, tmp_path, tool):
        pkg = {"scripts": {"test": "jest", "build": "webpack"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        cmd = tool._detect_command(tmp_path)
        assert cmd == "npm test"

    def test_skips_npm_if_no_test_script(self, tmp_path, tool):
        pkg = {"scripts": {"build": "webpack"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        cmd = tool._detect_command(tmp_path)
        assert cmd is None

    def test_detects_makefile_test_target(self, tmp_path, tool):
        (tmp_path / "Makefile").write_text("build:\n\techo build\n\ntest:\n\tpytest\n")
        cmd = tool._detect_command(tmp_path)
        assert cmd == "make test"

    def test_detects_legacy_setup_py(self, tmp_path, tool):
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()\n")
        cmd = tool._detect_command(tmp_path)
        assert cmd is not None
        assert "pytest" in cmd

    def test_detects_test_files_directly(self, tmp_path, tool):
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_something.py").write_text("def test_pass(): pass\n")
        cmd = tool._detect_command(tmp_path)
        assert cmd is not None
        assert "pytest" in cmd

    def test_agents_md_override_wins(self, tmp_path, tool):
        # Even if pytest.ini exists, AGENTS.md override takes priority
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        (tmp_path / "AGENTS.md").write_text(
            "# Rules\ntest_command: make custom-test\n"
        )
        cmd = tool._detect_command(tmp_path)
        assert cmd == "make custom-test"

    def test_agents_md_override_case_insensitive(self, tmp_path, tool):
        (tmp_path / "AGENTS.md").write_text("TEST_COMMAND: npm run test:ci\n")
        cmd = tool._detect_command(tmp_path)
        assert cmd == "npm run test:ci"


class TestTomlHasSection:

    def test_section_present(self, tmp_path, tool):
        f = tmp_path / "pyproject.toml"
        f.write_text("[tool.pytest.ini_options]\n")
        assert tool._toml_has_section(f, "tool.pytest.ini_options") is True

    def test_section_absent(self, tmp_path, tool):
        f = tmp_path / "pyproject.toml"
        f.write_text("[build-system]\n")
        assert tool._toml_has_section(f, "tool.pytest") is False

    def test_file_missing(self, tmp_path, tool):
        f = tmp_path / "nonexistent.toml"
        assert tool._toml_has_section(f, "tool.pytest") is False
