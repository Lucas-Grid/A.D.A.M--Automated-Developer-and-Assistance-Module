"""Project Analyzer: produce structured analysis from scanner output."""
from __future__ import annotations

from typing import Any

from ADAM.workspace.scanner import RepositoryScanner


class ProjectAnalyzer:
    """Transform raw scan results into analysis payloads."""

    def analyze(self, path: str) -> dict[str, Any]:
        """Analyze a workspace directory and return structured data."""
        scanner = RepositoryScanner(path)
        scan_result = scanner.scan()

        analysis = {
            "path": path,
            "languages": scan_result["languages"],
            "frameworks": scan_result["frameworks"],
            "dependency_files": scan_result["dependency_files"],
            "project_size_bytes": scan_result["project_size_bytes"],
            "file_count": scan_result["file_count"],
            "directory_count": scan_result["directory_count"],
        }
        return analysis
