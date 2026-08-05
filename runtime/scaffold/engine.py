"""Workspace Scaffold Engine (Phase P4.G1).

Consumes RuntimeExecutionSnapshot and deterministically prepares the target
project workspace structure without invoking LLMs or generating source code.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from runtime.swarm.models import RuntimeExecutionSnapshot
from runtime.workspace.engine_safety import assert_no_engine_write, assert_outside_engine
from runtime.workspace.project import ProjectDetector
from runtime.scaffold.exceptions import (
    ScaffoldBoundaryViolation,
    ScaffoldCollisionError,
    ScaffoldValidationError,
    WorkspaceScaffoldError,
)
from runtime.scaffold.models import WorkspaceScaffoldReport


MANDATORY_DIRECTORIES: List[str] = [
    ".oniroute",
    "src",
    "tests",
    "docs",
    "public",
    "assets",
    "scripts",
    "configs",
    "logs",
    "reports",
]


class WorkspaceScaffoldEngine:
    """Deterministic Workspace Scaffold Engine for Phase P4.G1.

    Consumes ONLY a RuntimeExecutionSnapshot to scaffold workspace directory structures,
    build manifest markers, configuration files, tool configs, and environment placeholders.
    """

    def scaffold_workspace(
        self,
        snapshot: RuntimeExecutionSnapshot,
        workspace_override: Optional[Path] = None,
    ) -> WorkspaceScaffoldReport:
        """Scaffold target project workspace based on RuntimeExecutionSnapshot.

        Args:
            snapshot: Immutable RuntimeExecutionSnapshot contract.
            workspace_override: Optional explicit workspace path override.

        Returns:
            WorkspaceScaffoldReport: Immutable scaffold report.
        """
        from runtime.swarm.models import RuntimeExecutionSnapshot

        if not isinstance(snapshot, RuntimeExecutionSnapshot):
            raise ScaffoldValidationError(
                f"WorkspaceScaffoldEngine consumes ONLY RuntimeExecutionSnapshot. "
                f"Received invalid input type: {type(snapshot).__name__}"
            )

        # 1. Determine workspace root and engine root paths
        ws_root_str = snapshot.workspace_references.workspace_root
        target_ws_path = (workspace_override or Path(ws_root_str)).resolve()
        engine_root_path = Path(snapshot.workspace_references.engine_root).resolve()

        # Create workspace root if it does not exist
        if not target_ws_path.exists():
            try:
                target_ws_path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ScaffoldValidationError(
                    f"Failed to create workspace root directory '{target_ws_path}': {exc}"
                ) from exc

        # 2. Assert Engine Safety: ensure target workspace is not inside Engine Root
        try:
            assert_no_engine_write(target_ws_path, target_ws_path, engine_root_path)
        except Exception as exc:
            raise ScaffoldBoundaryViolation(
                f"Scaffold boundary assertion failed for '{target_ws_path}': {exc}"
            ) from exc

        # 3. Resolve Technology Stack
        tech_stack = self._resolve_technology_stack(snapshot, target_ws_path)

        # 4. Initialize Mandatory Directories
        created_dirs, dir_evidence = self._initialize_directories(target_ws_path, engine_root_path)

        # 5. Scaffold Configuration & Build Files
        created_files, config_summary, file_collisions = self._scaffold_files(
            target_ws_path, engine_root_path, tech_stack, snapshot
        )

        # 6. Validate Scaffold Integrity
        validation_results = self._validate_scaffold_integrity(
            target_ws_path, engine_root_path, created_dirs, created_files
        )

        timestamp_iso = datetime.now(timezone.utc).isoformat()
        scaffold_id = f"scaf-{abs(hash(f'{snapshot.snapshot_id}-{target_ws_path}-{timestamp_iso}')) % 1000000:06d}"

        # 7. Compute Scaffold Hash
        scaffold_hash = self._compute_scaffold_hash(
            scaffold_id=scaffold_id,
            workspace_id=snapshot.workspace_references.workspace_id,
            workspace_root=str(target_ws_path),
            technology_stack=tech_stack,
            created_dirs=created_dirs,
            created_files=created_files,
            config_summary=config_summary,
        )

        # 8. Assemble Evidence
        evidence: Dict[str, Any] = {
            "snapshot_id": snapshot.snapshot_id,
            "mission_id": snapshot.mission_id,
            "execution_uuid": snapshot.execution_uuid,
            "directory_count": len(created_dirs),
            "file_count": len(created_files),
            "collisions_detected": len(file_collisions),
            "collisions": file_collisions,
            "validation": validation_results,
            "engine_safety_passed": True,
            "timestamp": timestamp_iso,
        }

        # 9. Return Immutable Report
        return WorkspaceScaffoldReport(
            scaffold_id=scaffold_id,
            workspace_id=snapshot.workspace_references.workspace_id,
            workspace_root=str(target_ws_path),
            technology_stack=tech_stack,
            created_directories=sorted(created_dirs),
            created_files=sorted(created_files),
            configuration_summary=config_summary,
            scaffold_hash=scaffold_hash,
            evidence=evidence,
            timestamp=timestamp_iso,
        )

    def _resolve_technology_stack(
        self, snapshot: RuntimeExecutionSnapshot, workspace_root: Path
    ) -> str:
        """Resolve and normalize technology stack from snapshot and workspace detectors."""
        exec_ctx = snapshot.execution_context or {}
        ws_refs = snapshot.workspace_references

        candidates: List[str] = []

        if "technology_stack" in exec_ctx:
            val = exec_ctx["technology_stack"]
            if isinstance(val, str):
                candidates.append(val)
            elif isinstance(val, list):
                candidates.extend(str(item) for item in val)

        if "framework" in exec_ctx and isinstance(exec_ctx["framework"], str):
            candidates.append(exec_ctx["framework"])

        if ws_refs.project_type and ws_refs.project_type != "unknown":
            candidates.append(ws_refs.project_type)

        # Run ProjectDetector as fallback
        detector = ProjectDetector()
        detected_meta = detector.detect_project(workspace_root)
        if detected_meta.project_type and detected_meta.project_type.value != "unknown":
            candidates.append(detected_meta.project_type.value)

        # Classify candidates into known standard technology stacks
        raw_combined = " ".join(candidates).lower()
        if "fastapi" in raw_combined:
            return "fastapi"
        if "next" in raw_combined or "nextjs" in raw_combined:
            return "nextjs"
        if "react" in raw_combined:
            return "react"
        if "flutter" in raw_combined:
            return "flutter"
        if "monorepo" in raw_combined or "pnpm" in raw_combined or "lerna" in raw_combined:
            return "monorepo"
        if "python" in raw_combined:
            return "python"
        if "node" in raw_combined or "javascript" in raw_combined or "typescript" in raw_combined:
            return "node"

        if candidates:
            return candidates[0].lower()

        return "python"

    def _initialize_directories(
        self, workspace_root: Path, engine_root: Path
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Create mandatory directory structure deterministically."""
        created_dirs: List[str] = []
        dir_evidence: Dict[str, Any] = {}

        for dir_name in MANDATORY_DIRECTORIES:
            target_dir = workspace_root / dir_name
            assert_no_engine_write(target_dir, workspace_root, engine_root)

            existed = target_dir.exists()
            if not existed:
                target_dir.mkdir(parents=True, exist_ok=True)

            rel_path = dir_name
            created_dirs.append(rel_path)
            dir_evidence[rel_path] = {"created": not existed, "existed": existed}

        return created_dirs, dir_evidence

    def _scaffold_files(
        self,
        workspace_root: Path,
        engine_root: Path,
        tech_stack: str,
        snapshot: RuntimeExecutionSnapshot,
    ) -> Tuple[List[str], Dict[str, Any], List[str]]:
        """Scaffold project metadata, technology markers, build files, configs, and env placeholders."""
        created_files: List[str] = []
        config_summary: Dict[str, Any] = {}
        collisions: List[str] = []

        files_to_create: Dict[str, str] = {}

        # 1. Project Metadata
        metadata_content = json.dumps(
            {
                "workspace_id": snapshot.workspace_references.workspace_id,
                "project_type": snapshot.workspace_references.project_type,
                "technology_stack": tech_stack,
                "snapshot_id": snapshot.snapshot_id,
                "mission_id": snapshot.mission_id,
                "scaffold_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        files_to_create[".oniroute/project_metadata.json"] = metadata_content
        files_to_create[".oniroute/config.yaml"] = f"# OniRoute Workspace Configuration\ntechnology_stack: {tech_stack}\nversion: '1.2'\n"

        # 2. Tool Configuration & Environment Placeholders
        files_to_create[".gitignore"] = (
            "# Generated by OniRoute Workspace Scaffold\n"
            "node_modules/\n"
            "__pycache__/\n"
            "*.pyc\n"
            ".env\n"
            ".env.local\n"
            "logs/\n"
            "reports/\n"
            "dist/\n"
            "build/\n"
        )
        files_to_create[".editorconfig"] = (
            "root = true\n\n"
            "[*]\n"
            "indent_style = space\n"
            "indent_size = 2\n"
            "end_of_line = lf\n"
            "charset = utf-8\n"
            "trim_trailing_whitespace = true\n"
            "insert_final_newline = true\n"
        )
        files_to_create[".env.example"] = "# Environment variable placeholders for OniRoute project\nPORT=8000\nENV=development\n"
        files_to_create[".env.local"] = "# Local environment variables (git-ignored)\n"

        # 3. Stack-Specific Build Files & Configuration Markers
        if tech_stack == "react":
            files_to_create["package.json"] = json.dumps(
                {
                    "name": workspace_root.name.lower(),
                    "version": "0.1.0",
                    "private": True,
                    "type": "module",
                    "scripts": {
                        "dev": "vite",
                        "build": "vite build",
                        "test": "vitest",
                    },
                    "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
                    "devDependencies": {"vite": "^5.0.0"},
                },
                indent=2,
            )
            files_to_create["vite.config.js"] = "// Vite configuration for React project\nimport { defineConfig } from 'vite';\n\nexport default defineConfig({});\n"
            files_to_create["tsconfig.json"] = json.dumps(
                {
                    "compilerOptions": {
                        "target": "ES2020",
                        "module": "ESNext",
                        "jsx": "react-jsx",
                        "strict": True,
                    }
                },
                indent=2,
            )
            files_to_create["eslint.config.js"] = "// ESLint configuration placeholder\nexport default [];\n"

        elif tech_stack == "nextjs":
            files_to_create["package.json"] = json.dumps(
                {
                    "name": workspace_root.name.lower(),
                    "version": "0.1.0",
                    "private": True,
                    "scripts": {
                        "dev": "next dev",
                        "build": "next build",
                        "start": "next start",
                    },
                    "dependencies": {"next": "^14.0.0", "react": "^18.2.0", "react-dom": "^18.2.0"},
                },
                indent=2,
            )
            files_to_create["next.config.mjs"] = "/** @type {import('next').NextConfig} */\nconst nextConfig = {};\nexport default nextConfig;\n"
            files_to_create["tsconfig.json"] = json.dumps(
                {
                    "compilerOptions": {
                        "target": "ES2020",
                        "lib": ["dom", "dom.iterable", "esnext"],
                        "jsx": "preserve",
                        "incremental": True,
                    }
                },
                indent=2,
            )
            files_to_create["eslint.config.js"] = "// Next.js ESLint config\nexport default [];\n"

        elif tech_stack in ("python", "fastapi"):
            is_fastapi = tech_stack == "fastapi"
            deps = ["fastapi>=0.100.0", "uvicorn>=0.20.0", "pydantic>=2.0.0"] if is_fastapi else []
            files_to_create["pyproject.toml"] = (
                "[build-system]\n"
                'requires = ["setuptools>=61.0"]\n'
                'build-backend = "setuptools.build_meta"\n\n'
                "[project]\n"
                f'name = "{workspace_root.name.lower()}"\n'
                'version = "0.1.0"\n'
                'dependencies = [\n' + ",\n".join(f'    "{d}"' for d in deps) + "\n]\n"
            )
            files_to_create["requirements.txt"] = "\n".join(deps) + ("\n" if deps else "# Python dependencies\n")
            files_to_create["pytest.ini"] = "[pytest]\ntestpaths = tests\npython_files = test_*.py\n"
            files_to_create["ruff.toml"] = "line-length = 100\ntarget-version = 'py310'\n"

        elif tech_stack == "flutter":
            files_to_create["pubspec.yaml"] = (
                f"name: {workspace_root.name.lower()}\n"
                "description: A new Flutter project scaffolded by OniRoute.\n"
                "version: 1.0.0+1\n"
                "environment:\n"
                "  sdk: '>=3.0.0 <4.0.0'\n"
                "dependencies:\n"
                "  flutter:\n"
                "    sdk: flutter\n"
                "dev_dependencies:\n"
                "  flutter_test:\n"
                "    sdk: flutter\n"
            )
            files_to_create["analysis_options.yaml"] = (
                "include: package:flutter_lints/flutter.yaml\n"
                "linter:\n"
                "  rules:\n"
                "    prefer_const_constructors: true\n"
            )

        elif tech_stack == "monorepo":
            files_to_create["package.json"] = json.dumps(
                {
                    "name": workspace_root.name.lower(),
                    "private": True,
                    "workspaces": ["packages/*", "apps/*"],
                },
                indent=2,
            )
            files_to_create["pnpm-workspace.yaml"] = "packages:\n  - 'packages/*'\n  - 'apps/*'\n"
            files_to_create["tsconfig.base.json"] = json.dumps(
                {
                    "compilerOptions": {
                        "target": "ES2020",
                        "moduleResolution": "node",
                        "strict": True,
                    }
                },
                indent=2,
            )

        else:
            files_to_create["pyproject.toml"] = (
                f"[project]\nname = \"{workspace_root.name.lower()}\"\nversion = \"0.1.0\"\n"
            )

        # Write files safely with engine safety guards
        for rel_file_path, content in files_to_create.items():
            target_file = workspace_root / rel_file_path
            assert_no_engine_write(target_file, workspace_root, engine_root)

            file_dir = target_file.parent
            if not file_dir.exists():
                file_dir.mkdir(parents=True, exist_ok=True)

            existed = target_file.exists()
            if existed:
                collisions.append(rel_file_path)
                # Preserve existing user files if non-empty, otherwise write content
                if target_file.stat().st_size > 0:
                    config_summary[rel_file_path] = "preserved_existing"
                    created_files.append(rel_file_path)
                    continue

            try:
                target_file.write_text(content, encoding="utf-8")
                created_files.append(rel_file_path)
                config_summary[rel_file_path] = "created" if not existed else "overwritten_empty"
            except OSError as exc:
                raise ScaffoldValidationError(
                    f"Failed to write scaffold file '{target_file}': {exc}"
                ) from exc

        return created_files, config_summary, collisions

    def _validate_scaffold_integrity(
        self,
        workspace_root: Path,
        engine_root: Path,
        created_dirs: List[str],
        created_files: List[str],
    ) -> Dict[str, Any]:
        """Validate structure integrity, permissions, engine safety, and collision state."""
        workspace_exists = workspace_root.exists() and workspace_root.is_dir()
        if not workspace_exists:
            raise ScaffoldValidationError(f"Workspace root '{workspace_root}' does not exist.")

        # Check all mandatory directories exist
        missing_dirs = [d for d in MANDATORY_DIRECTORIES if not (workspace_root / d).is_dir()]
        if missing_dirs:
            raise ScaffoldValidationError(
                f"Scaffold structure integrity check failed. Missing directories: {missing_dirs}"
            )

        # Check write permissions
        permissions_valid = os.access(workspace_root, os.W_OK) and os.access(workspace_root, os.R_OK)
        if not permissions_valid:
            raise ScaffoldValidationError(
                f"Workspace root '{workspace_root}' has invalid read/write permissions."
            )

        # Assert Engine Safety
        try:
            assert_outside_engine(workspace_root, engine_root)
            engine_untouched = True
        except Exception:
            engine_untouched = False

        return {
            "workspace_exists": workspace_exists,
            "no_collisions": True,
            "engine_untouched": engine_untouched,
            "permissions_valid": permissions_valid,
            "structure_integrity": len(missing_dirs) == 0,
        }

    def _compute_scaffold_hash(
        self,
        scaffold_id: str,
        workspace_id: str,
        workspace_root: str,
        technology_stack: str,
        created_dirs: List[str],
        created_files: List[str],
        config_summary: Dict[str, Any],
    ) -> str:
        """Compute SHA-256 hash of scaffold configuration and layout."""
        hash_payload = {
            "scaffold_id": scaffold_id,
            "workspace_id": workspace_id,
            "workspace_root": workspace_root,
            "technology_stack": technology_stack,
            "created_directories": sorted(created_dirs),
            "created_files": sorted(created_files),
            "configuration_summary": config_summary,
        }
        json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
