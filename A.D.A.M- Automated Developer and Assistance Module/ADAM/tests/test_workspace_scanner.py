"""Tests for repository scanner and project analyzer."""
import os
import tempfile
from pathlib import Path

import pytest

from ADAM.workspace.analyzer import ProjectAnalyzer
from ADAM.workspace.scanner import RepositoryScanner
from ADAM.core.exceptions import WorkspaceError


@pytest.fixture()
def py_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'demo'\n")
    (tmp_path / "main.py").write_text("print('hello')\n")
    return tmp_path


@pytest.fixture()
def ts_project(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "demo"}')
    (tmp_path / "app.ts").write_text("console.log('hi');\n")
    return tmp_path


def test_scanner_detects_python(py_project):
    scanner = RepositoryScanner(str(py_project))
    result = scanner.scan()
    assert "Python" in result["languages"]
    assert "pyproject.toml" in result["dependency_files"]


def test_scanner_detects_typescript(ts_project):
    scanner = RepositoryScanner(str(ts_project))
    result = scanner.scan()
    assert "TypeScript" in result["languages"]
    assert "package.json" in result["dependency_files"]


def test_analyzer_counts(py_project):
    analyzer = ProjectAnalyzer()
    result = analyzer.analyze(str(py_project))
    assert result["file_count"] >= 2
    assert result["directory_count"] >= 0
    assert result["project_size_bytes"] > 0


def test_scanner_invalid_path():
    with pytest.raises(WorkspaceError):
        RepositoryScanner("C:/nonexistent/path/xyz")
