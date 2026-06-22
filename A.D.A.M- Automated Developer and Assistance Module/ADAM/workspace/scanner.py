"""Repository and dependency file detection."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ADAM.core.exceptions import WorkspaceError


LANGUAGE_FILES = {
    "Python": ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile"],
    "JavaScript": ["package.json"],
    "TypeScript": ["package.json", "tsconfig.json"],
    "Rust": ["Cargo.toml"],
    "Go": ["go.mod"],
    "Java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "C#": ["*.csproj", "*.sln"],
}

EXTENSION_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".cs": "C#",
}

FRAMEWORK_MANIFESTS = {
    "package.json": ["react", "vue", "angular", "next", "svelte", "express", "fastify"],
    "pyproject.toml": ["django", "flask", "fastapi", "pydantic"],
    "requirements.txt": ["pandas", "numpy", "pytest"],
    "Cargo.toml": ["rocket", "actix", "axum"],
    "pom.xml": ["spring"],
    ".csproj": [".net", "aspnet"],
}


class RepositoryScanner:
    """Scan a workspace folder for languages and dependency files."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        if not self.root.exists():
            raise WorkspaceError(f"Path does not exist: {root}")

    def scan(self) -> dict[str, Any]:
        """Run detection and return a structured result."""
        languages = self._detect_languages()
        dep_files = self._detect_dependency_files()
        frameworks = self._detect_frameworks(dep_files)
        size = self._compute_size()
        counts = self._compute_counts()

        return {
            "languages": sorted(languages),
            "dependency_files": sorted(dep_files),
            "frameworks": sorted(frameworks),
            "project_size_bytes": size,
            "file_count": counts["files"],
            "directory_count": counts["dirs"],
        }

    def _detect_languages(self) -> set[str]:
        found: set[str] = set()
        for _dirpath, _dirnames, filenames in os.walk(self.root):
            for filename in filenames:
                ext = Path(filename).suffix.lower()
                lang = EXTENSION_LANGUAGE.get(ext)
                if lang:
                    found.add(lang)
        return found

    def _detect_dependency_files(self) -> set[str]:
        found: set[str] = set()
        for _dirpath, _dirnames, filenames in os.walk(self.root):
            for filename in filenames:
                if filename in [
                    "pyproject.toml",
                    "requirements.txt",
                    "setup.py",
                    "Pipfile",
                    "package.json",
                    "Cargo.toml",
                    "go.mod",
                    "pom.xml",
                    "build.gradle",
                    "build.gradle.kts",
                    "tsconfig.json",
                ]:
                    found.add(filename)
                elif filename.endswith(".csproj") or filename.endswith(".sln"):
                    found.add(filename)
        return found

    def _detect_frameworks(self, dep_files: set[str]) -> set[str]:
        frameworks: set[str] = set()
        manifest_paths: list[Path] = []
        for dep in dep_files:
            for root, _dirs, files in os.walk(self.root):
                if dep in files:
                    manifest_paths.append(Path(root) / dep)
                    break

        for manifest_path in manifest_paths:
            try:
                text = manifest_path.read_text(encoding="utf-8", errors="ignore").lower()
                for _framework, markers in FRAMEWORK_MANIFESTS.items():
                    if any(marker.lower() in text for marker in markers):
                        frameworks.add(markers[0])
            except Exception:
                continue
        return frameworks

    def _compute_size(self) -> int:
        total = 0
        for dirpath, _dirnames, filenames in os.walk(self.root):
            for f in filenames:
                fp = Path(dirpath) / f
                try:
                    total += fp.stat().st_size
                except OSError:
                    continue
        return total

    def _compute_counts(self) -> dict[str, int]:
        files = 0
        dirs = 0
        for _dirpath, dirnames, filenames in os.walk(self.root):
            dirs += len(dirnames)
            files += len(filenames)
        return {"files": files, "dirs": dirs}
