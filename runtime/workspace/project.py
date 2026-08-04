"""Declarative Project Detection engine for OniRoute (ACR-003 Phase W2).

Recognizes project types and metadata using manifest files without executing build tools.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ProjectMetadata, ProjectType


class ProjectDetector:
    """Declarative project metadata and project type detector."""

    def detect_project(self, workspace_root: Path) -> ProjectMetadata:
        """Detect project type and assemble ProjectMetadata from manifest files strictly."""
        ws_root = workspace_root.resolve()
        project_id = f"proj-{abs(hash(str(ws_root))) % 1000000:06d}"
        name = ws_root.name

        if not ws_root.exists() or not ws_root.is_dir():
            return ProjectMetadata(
                project_id=project_id,
                name=name,
                project_type=ProjectType.UNKNOWN,
                root_path=ws_root,
                is_empty=True,
            )

        # Check if empty workspace
        if self._is_empty(ws_root):
            return ProjectMetadata(
                project_id=project_id,
                name=name,
                project_type=ProjectType.EMPTY,
                root_path=ws_root,
                is_empty=True,
            )

        # Perform manifest-based classification
        proj_type, manifest_path, extracted_name, framework_ver, lang_ver, attrs = self._classify_project(ws_root)
        final_name = extracted_name or name

        return ProjectMetadata(
            project_id=project_id,
            name=final_name,
            project_type=proj_type,
            root_path=ws_root,
            framework_version=framework_ver,
            language_version=lang_ver,
            manifest_path=manifest_path,
            is_empty=False,
            attributes=attrs,
        )

    def _is_empty(self, root: Path) -> bool:
        """Determine if directory contains no user files or subdirectories."""
        try:
            items = [item for item in root.iterdir() if item.name not in (".DS_Store", ".git", ".idea", ".vscode")]
            return len(items) == 0
        except OSError:
            return False

    def _classify_project(
        self, root: Path
    ) -> tuple[ProjectType, Path | None, str | None, str | None, str | None, dict[str, Any]]:
        """Declaratively inspect manifest files in priority order."""
        attrs: dict[str, Any] = {}

        # 1. Flutter check (pubspec.yaml)
        pubspec = root / "pubspec.yaml"
        if pubspec.is_file():
            name, sdk_ver = self._parse_pubspec(pubspec)
            return ProjectType.FLUTTER, pubspec, name, None, sdk_ver, attrs

        # 2. Rust check (Cargo.toml)
        cargo = root / "Cargo.toml"
        if cargo.is_file():
            name, rust_ver = self._parse_cargo(cargo)
            return ProjectType.RUST, cargo, name, None, rust_ver, attrs

        # 3. Go check (go.mod)
        gomod = root / "go.mod"
        if gomod.is_file():
            name, go_ver = self._parse_gomod(gomod)
            return ProjectType.GO, gomod, name, None, go_ver, attrs

        # 4. Java check (pom.xml, build.gradle, build.gradle.kts)
        pom = root / "pom.xml"
        if pom.is_file():
            name = self._parse_pom(pom)
            return ProjectType.JAVA, pom, name, None, None, attrs
        gradle = root / "build.gradle"
        if gradle.is_file():
            return ProjectType.JAVA, gradle, root.name, None, None, attrs
        gradle_kts = root / "build.gradle.kts"
        if gradle_kts.is_file():
            return ProjectType.JAVA, gradle_kts, root.name, None, None, attrs

        # 5. .NET check (*.csproj, *.fsproj, *.sln, global.json)
        dotnet_manifest = self._find_dotnet_manifest(root)
        if dotnet_manifest:
            return ProjectType.DOTNET, dotnet_manifest, dotnet_manifest.stem, None, None, attrs

        # 6. JavaScript / Node / Frontend frameworks (package.json, angular.json, next.config, etc.)
        pkg_json = root / "package.json"
        angular_json = root / "angular.json"
        vue_config = root / "vue.config.js"
        vue_config_ts = root / "vue.config.ts"
        next_configs = [root / f"next.config.{ext}" for ext in ("js", "mjs", "ts", "cjs")]

        pkg_data = self._parse_json(pkg_json) if pkg_json.is_file() else {}
        deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
        pkg_name = pkg_data.get("name")
        node_ver = pkg_data.get("engines", {}).get("node")

        # Next.js
        if any(cfg.is_file() for cfg in next_configs) or "next" in deps:
            manifest = next((cfg for cfg in next_configs if cfg.is_file()), pkg_json)
            return ProjectType.NEXTJS, manifest, pkg_name, deps.get("next"), node_ver, attrs

        # React Native
        if "react-native" in deps:
            return ProjectType.REACT_NATIVE, pkg_json, pkg_name, deps.get("react-native"), node_ver, attrs

        # Angular
        if angular_json.is_file() or "@angular/core" in deps:
            manifest = angular_json if angular_json.is_file() else pkg_json
            return ProjectType.ANGULAR, manifest, pkg_name, deps.get("@angular/core"), node_ver, attrs

        # Vue
        if vue_config.is_file() or vue_config_ts.is_file() or "vue" in deps:
            manifest = vue_config if vue_config.is_file() else (vue_config_ts if vue_config_ts.is_file() else pkg_json)
            return ProjectType.VUE, manifest, pkg_name, deps.get("vue"), node_ver, attrs

        # React
        if "react" in deps:
            return ProjectType.REACT, pkg_json, pkg_name, deps.get("react"), node_ver, attrs

        # General Node.js
        if pkg_json.is_file():
            return ProjectType.NODE, pkg_json, pkg_name, None, node_ver, attrs

        # 7. Python check (pyproject.toml, setup.py, setup.cfg, requirements.txt, Pipfile)
        pyproject = root / "pyproject.toml"
        setup_py = root / "setup.py"
        setup_cfg = root / "setup.cfg"
        reqs = root / "requirements.txt"
        pipfile = root / "Pipfile"

        if pyproject.is_file():
            py_name, py_ver = self._parse_pyproject(pyproject)
            return ProjectType.PYTHON, pyproject, py_name, None, py_ver, attrs
        if setup_py.is_file():
            return ProjectType.PYTHON, setup_py, root.name, None, None, attrs
        if setup_cfg.is_file():
            return ProjectType.PYTHON, setup_cfg, root.name, None, None, attrs
        if reqs.is_file():
            return ProjectType.PYTHON, reqs, root.name, None, None, attrs
        if pipfile.is_file():
            return ProjectType.PYTHON, pipfile, root.name, None, None, attrs

        return ProjectType.UNKNOWN, None, root.name, None, None, attrs

    def _parse_json(self, path: Path) -> dict[str, Any]:
        """Safely parse JSON file."""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _find_dotnet_manifest(self, root: Path) -> Path | None:
        """Locate .NET manifest file."""
        try:
            for ext in ("*.csproj", "*.fsproj", "*.sln", "global.json"):
                matches = list(root.glob(ext))
                if matches:
                    return matches[0]
        except OSError:
            pass
        return None

    def _parse_pyproject(self, path: Path) -> tuple[str | None, str | None]:
        """Basic pyproject.toml reader without heavy external dependencies."""
        try:
            content = path.read_text(encoding="utf-8")
            name, python_ver = None, None
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("name ="):
                    name = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("requires-python ="):
                    python_ver = line.split("=", 1)[1].strip().strip('"').strip("'")
            return name, python_ver
        except Exception:
            return None, None

    def _parse_cargo(self, path: Path) -> tuple[str | None, str | None]:
        """Basic Cargo.toml reader."""
        try:
            content = path.read_text(encoding="utf-8")
            name, rust_edition = None, None
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("name =") and name is None:
                    name = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("edition ="):
                    rust_edition = line.split("=", 1)[1].strip().strip('"').strip("'")
            return name, rust_edition
        except Exception:
            return None, None

    def _parse_gomod(self, path: Path) -> tuple[str | None, str | None]:
        """Basic go.mod reader."""
        try:
            content = path.read_text(encoding="utf-8")
            mod_name, go_ver = None, None
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("module "):
                    mod_name = line.split(maxsplit=1)[1].strip()
                elif line.startswith("go "):
                    go_ver = line.split(maxsplit=1)[1].strip()
            return mod_name, go_ver
        except Exception:
            return None, None

    def _parse_pubspec(self, path: Path) -> tuple[str | None, str | None]:
        """Basic pubspec.yaml reader."""
        try:
            content = path.read_text(encoding="utf-8")
            name, sdk = None, None
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("sdk:"):
                    sdk = line.split(":", 1)[1].strip().strip('"').strip("'")
            return name, sdk
        except Exception:
            return None, None

    def _parse_pom(self, path: Path) -> str | None:
        """Basic pom.xml text reader."""
        try:
            content = path.read_text(encoding="utf-8")
            if "<artifactId>" in content:
                part = content.split("<artifactId>", 1)[1].split("</artifactId>", 1)[0]
                return part.strip()
        except Exception:
            pass
        return None
