"""Workspace Intelligence engine for OniRoute (Phase P1.I2).

Declaratively analyzes workspace characteristics, manifest files, git status,
build tools, package managers, and engine safety boundaries without AST parsing
or deep source code inspection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .discovery import WorkspaceResolver
from .engine import EngineResolver
from .models import ProjectMetadata, ProjectType, ValidationState, WorkspaceMetadata
from .project import ProjectDetector
from .validation import WorkspaceValidator


class WorkspaceState(str, Enum):
    """Canonical Workspace operational states."""
    EMPTY = "EMPTY"
    NEW_PROJECT = "NEW_PROJECT"
    EXISTING_PROJECT = "EXISTING_PROJECT"
    MONOREPO = "MONOREPO"
    UNKNOWN = "UNKNOWN"


class WorkspaceContext(BaseModel):
    """Immutable Workspace Context representing resolved workspace intelligence.

    Produced by WorkspaceIntelligence without scanning application code,
    parsing ASTs, or executing build tools.
    """

    model_config = ConfigDict(frozen=True)

    workspace_id: str = Field(description="Unique workspace identifier")
    workspace_root: Path = Field(description="Resolved workspace root path")
    repository_root: Path = Field(description="Resolved repository root path")
    engine_root: Path = Field(description="Resolved read-only engine root path")
    project_type: ProjectType = Field(default=ProjectType.UNKNOWN, description="Detected project type")
    primary_language: str = Field(default="Unknown", description="Primary programming language")
    framework_hint: str | None = Field(default=None, description="Detected framework hint")
    build_tool: str | None = Field(default=None, description="Detected build tool")
    package_manager: str | None = Field(default=None, description="Detected package manager")
    git_available: bool = Field(default=False, description="True if git repository is detected")
    workspace_state: WorkspaceState = Field(default=WorkspaceState.UNKNOWN, description="Workspace state")
    detected_manifests: List[str] = Field(default_factory=list, description="Paths of detected manifest files")
    has_oniroute_dir: bool = Field(default=False, description="True if .oniroute directory exists")
    read_only_validation: bool = Field(default=True, description="True if engine read-only assertion passes")
    validation: ValidationState = Field(default_factory=ValidationState, description="Workspace validation state")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Categorized workspace discovery evidence")


class WorkspaceIntelligence:
    """Workspace Intelligence analyzer.

    Reuses existing WorkspaceResolver, ProjectDetector, EngineResolver, and
    WorkspaceValidator components to assemble immutable WorkspaceContext records.
    """

    def __init__(
        self,
        workspace_resolver: WorkspaceResolver | None = None,
        project_detector: ProjectDetector | None = None,
        validator: WorkspaceValidator | None = None,
        engine_resolver: EngineResolver | None = None,
    ) -> None:
        self.engine_resolver = engine_resolver or EngineResolver()
        self.project_detector = project_detector or ProjectDetector()
        self.validator = validator or WorkspaceValidator()
        self.workspace_resolver = (
            workspace_resolver
            or WorkspaceResolver(
                engine_resolver=self.engine_resolver,
                project_detector=self.project_detector,
                validator=self.validator,
            )
        )

    def analyze_workspace(
        self,
        cwd: Path,
        explicit_workspace: Path | None = None,
    ) -> WorkspaceContext:
        """Analyze workspace environment and produce an immutable WorkspaceContext."""
        abs_cwd = cwd.resolve()
        ws_meta = self.workspace_resolver.resolve_workspace(cwd=abs_cwd, explicit_path=explicit_workspace)
        ws_root = ws_meta.workspace_root
        eng_root = ws_meta.engine_root

        # 1. Detect Git Repository Root
        repo_root, git_available = self._detect_git_repository(ws_root)

        # 2. Detect Manifest Files strictly
        manifests = self._detect_manifests(ws_root)

        # 3. Detect Project Metadata via ProjectDetector
        proj_meta = self.project_detector.detect_project(ws_root)

        # 4. Detect Build Tool & Package Manager
        build_tool, pkg_manager = self._detect_build_and_package_managers(ws_root, manifests)

        # 5. Detect Primary Language & Framework Hint
        primary_lang, framework_hint = self._detect_language_and_framework(proj_meta, manifests, ws_root)

        # 6. Determine Workspace State
        ws_state = self._determine_workspace_state(ws_root, manifests, proj_meta)

        # 7. Check for .oniroute directory
        has_oniroute = (ws_root / ".oniroute").is_dir()

        # 8. Perform Boundary Validation
        val_state = self.validator.validate(ws_root, eng_root, proj_meta)
        read_only_valid = eng_root.resolve() != ws_root.resolve()

        now_str = datetime.now(timezone.utc).isoformat()
        ws_id = f"ws-{abs(hash(str(ws_root))) % 1000000:06d}"

        evidence = {
            "discovery_method": str(ws_meta.discovery_method),
            "discovery_source": ws_meta.discovery_source,
            "manifest_count": len(manifests),
            "git_root": str(repo_root) if git_available else None,
            "is_empty": proj_meta.is_empty,
        }

        return WorkspaceContext(
            workspace_id=ws_id,
            workspace_root=ws_root,
            repository_root=repo_root,
            engine_root=eng_root,
            project_type=proj_meta.project_type,
            primary_language=primary_lang,
            framework_hint=framework_hint,
            build_tool=build_tool,
            package_manager=pkg_manager,
            git_available=git_available,
            workspace_state=ws_state,
            detected_manifests=[m.name for m in manifests],
            has_oniroute_dir=has_oniroute,
            read_only_validation=read_only_valid,
            validation=val_state,
            timestamp=now_str,
            evidence=evidence,
        )

    def _detect_git_repository(self, start_root: Path) -> Tuple[Path, bool]:
        """Climb directories to locate .git marker."""
        curr = start_root.resolve()
        visited: set[Path] = set()
        while curr not in visited:
            visited.add(curr)
            if (curr / ".git").exists():
                return curr, True
            if curr.parent == curr:
                break
            curr = curr.parent
        return start_root, False

    def _detect_manifests(self, root: Path) -> List[Path]:
        """Declaratively list known project manifest files in workspace root."""
        manifest_names = (
            "package.json",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            "Pipfile",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "composer.json",
            "pubspec.yaml",
            "pnpm-workspace.yaml",
            "lerna.json",
            "turbo.json",
            "nx.json",
        )
        found: List[Path] = []
        if not root.exists() or not root.is_dir():
            return found

        for name in manifest_names:
            p = root / name
            if p.is_file():
                found.append(p)

        try:
            for ext in ("*.csproj", "*.fsproj", "*.sln", "global.json"):
                for m in root.glob(ext):
                    if m.is_file() and m not in found:
                        found.append(m)
        except OSError:
            pass

        return found

    def _detect_build_and_package_managers(
        self, root: Path, manifests: List[Path]
    ) -> Tuple[str | None, str | None]:
        manifest_names = {m.name for m in manifests}

        # JavaScript / Node lockfiles
        if (root / "pnpm-lock.yaml").is_file() or (root / "pnpm-workspace.yaml").is_file():
            return "pnpm", "pnpm"
        if (root / "yarn.lock").is_file():
            return "yarn", "yarn"
        if (root / "bun.lockb").is_file() or (root / "bun.lock").is_file():
            return "bun", "bun"
        if "package.json" in manifest_names:
            return "npm", "npm"

        # Python lockfiles & managers
        if (root / "uv.lock").is_file():
            return "uv", "uv"
        if (root / "poetry.lock").is_file():
            return "poetry", "poetry"
        if any(name in manifest_names for name in ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile")):
            return "pip", "pip"

        # Rust
        if "Cargo.toml" in manifest_names:
            return "cargo", "cargo"

        # Go
        if "go.mod" in manifest_names:
            return "go", "go"

        # Java
        if "pom.xml" in manifest_names:
            return "maven", "maven"
        if "build.gradle" in manifest_names or "build.gradle.kts" in manifest_names:
            return "gradle", "gradle"

        # Flutter / Dart
        if "pubspec.yaml" in manifest_names:
            return "flutter", "pub"

        # .NET
        if any(name.endswith((".csproj", ".fsproj", ".sln")) or name == "global.json" for name in manifest_names):
            return "dotnet", "dotnet"

        # PHP
        if "composer.json" in manifest_names:
            return "composer", "composer"

        return None, None

    def _detect_language_and_framework(
        self, proj_meta: ProjectMetadata, manifests: List[Path], root: Path
    ) -> Tuple[str, str | None]:
        pt = proj_meta.project_type
        if pt == ProjectType.PYTHON:
            return "Python", None
        elif pt == ProjectType.NODE:
            return "JavaScript/TypeScript", "Node.js"
        elif pt == ProjectType.REACT:
            return "TypeScript/JavaScript", "React"
        elif pt == ProjectType.NEXTJS:
            return "TypeScript/JavaScript", "Next.js"
        elif pt == ProjectType.VUE:
            return "TypeScript/JavaScript", "Vue"
        elif pt == ProjectType.ANGULAR:
            return "TypeScript/JavaScript", "Angular"
        elif pt == ProjectType.REACT_NATIVE:
            return "TypeScript/JavaScript", "React Native"
        elif pt == ProjectType.GO:
            return "Go", None
        elif pt == ProjectType.RUST:
            return "Rust", None
        elif pt == ProjectType.JAVA:
            return "Java", None
        elif pt == ProjectType.DOTNET:
            return "C#", ".NET"
        elif pt == ProjectType.FLUTTER:
            return "Dart", "Flutter"

        manifest_names = {m.name for m in manifests}
        if "composer.json" in manifest_names:
            return "PHP", None
        if "pyproject.toml" in manifest_names or "requirements.txt" in manifest_names:
            return "Python", None
        if "package.json" in manifest_names:
            return "JavaScript/TypeScript", None

        return "Unknown", None

    def _determine_workspace_state(
        self, root: Path, manifests: List[Path], proj_meta: ProjectMetadata
    ) -> WorkspaceState:
        if proj_meta.is_empty:
            return WorkspaceState.EMPTY

        # Check explicit monorepo configuration files
        monorepo_files = {"pnpm-workspace.yaml", "lerna.json", "turbo.json", "nx.json"}
        manifest_names = {m.name for m in manifests}
        if any(f in manifest_names for f in monorepo_files):
            return WorkspaceState.MONOREPO

        # Check Cargo.toml workspace
        cargo_toml = root / "Cargo.toml"
        if cargo_toml.is_file():
            try:
                if "[workspace]" in cargo_toml.read_text(encoding="utf-8"):
                    return WorkspaceState.MONOREPO
            except Exception:
                pass

        # Check package.json workspaces
        pkg_json = root / "package.json"
        if pkg_json.is_file():
            try:
                content = pkg_json.read_text(encoding="utf-8")
                if '"workspaces"' in content:
                    return WorkspaceState.MONOREPO
            except Exception:
                pass

        # Check multiple subprojects in apps/ or packages/
        if (root / "packages").is_dir() or (root / "apps").is_dir():
            sub_manifests = list(root.glob("packages/*/package.json")) + list(root.glob("apps/*/package.json"))
            if len(sub_manifests) > 1:
                return WorkspaceState.MONOREPO

        if len(manifests) > 0:
            src_dirs = ("src", "lib", "app", "pages", "cmd", "pkg", "runtime", "cli")
            has_src = any((root / d).is_dir() for d in src_dirs)
            if has_src:
                return WorkspaceState.EXISTING_PROJECT
            return WorkspaceState.NEW_PROJECT

        return WorkspaceState.UNKNOWN
