"""Repository Intelligence engine for OniRoute (Phase P1.I3).

Declaratively inspects repository file structure, directory topology, entry points,
configuration, tests, documentation, and assets without parsing ASTs, executing code,
or analyzing business logic.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .intelligence import WorkspaceContext
from .models import ProjectType


DEFAULT_IGNORED_DIRS: Set[str] = {
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
    "coverage",
    ".cache",
    ".git",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".next",
    "__pycache__",
    ".egg-info",
    ".oniroute",
    "bin",
    "obj",
    ".gradle",
    ".dart_tool",
    "out",
}


class RepositoryContext(BaseModel):
    """Immutable Repository Context representing extracted repository intelligence.

    Produced by RepositoryIntelligence via declarative structural scanning
    without AST parsing, code execution, or business logic analysis.
    """

    model_config = ConfigDict(frozen=True)

    repository_id: str = Field(description="Unique repository context identifier")
    repository_root: Path = Field(description="Resolved repository root path")
    directory_topology: Dict[str, List[str]] = Field(default_factory=dict, description="Structural mapping of main directories and top children")
    project_layout: str = Field(default="standard", description="Detected project layout pattern (flat, src_layout, monorepo, etc.)")
    detected_roots: Dict[str, str | None] = Field(default_factory=dict, description="Detected specialized directory roots (source_root, test_root, etc.)")
    entry_points: List[str] = Field(default_factory=list, description="Detected main application entry points")
    configuration_files: List[str] = Field(default_factory=list, description="Detected configuration files")
    documentation_files: List[str] = Field(default_factory=list, description="Detected documentation files")
    test_presence: bool = Field(default=False, description="True if test files or test directories exist")
    test_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of test roots and file counts")
    asset_summary: Dict[str, int] = Field(default_factory=dict, description="Count summary of static media and asset files")
    infrastructure_summary: List[str] = Field(default_factory=list, description="Detected infrastructure and deployment files")
    ignored_paths: List[str] = Field(default_factory=list, description="List of standard ignored directory names")
    repository_size: Dict[str, int] = Field(default_factory=dict, description="File count, directory count, and total byte size")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Categorized repository discovery evidence")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")


class RepositoryIntelligence:
    """Repository Intelligence analyzer.

    Inspects file tree topology, classifies files, identifies entry points,
    and returns an immutable RepositoryContext.
    """

    def analyze_repository(
        self,
        workspace_context: WorkspaceContext,
        max_scan_depth: int = 5,
    ) -> RepositoryContext:
        """Analyze repository structure using resolved WorkspaceContext."""
        repo_root = workspace_context.repository_root.resolve()
        now_str = datetime.now(timezone.utc).isoformat()
        repo_id = f"repo-{abs(hash(str(repo_root))) % 1000000:06d}"

        # 1. Scan filesystem tree (skipping ignored directories)
        file_tree, stats = self._scan_file_tree(repo_root, max_depth=max_scan_depth)

        # 2. Build directory topology
        topology = self._build_directory_topology(repo_root, file_tree)

        # 3. Detect specialized roots
        roots = self._detect_roots(repo_root, file_tree)

        # 4. Determine project layout
        layout = self._determine_project_layout(repo_root, roots, workspace_context)

        # 5. Classify files & entry points
        classified = self._classify_repository_files(repo_root, file_tree)

        # 6. Detect entry points
        entry_points = self._detect_entry_points(repo_root, file_tree, classified["source"])

        # 7. Summarize tests, assets, and infrastructure
        test_summary = self._summarize_tests(roots, classified["tests"])
        asset_summary = self._summarize_assets(classified["assets"])

        evidence = {
            "project_type": str(workspace_context.project_type),
            "primary_language": workspace_context.primary_language,
            "workspace_state": str(workspace_context.workspace_state),
            "detected_manifests": workspace_context.detected_manifests,
        }

        return RepositoryContext(
            repository_id=repo_id,
            repository_root=repo_root,
            directory_topology=topology,
            project_layout=layout,
            detected_roots=roots,
            entry_points=entry_points,
            configuration_files=sorted(classified["config"]),
            documentation_files=sorted(classified["documentation"]),
            test_presence=len(classified["tests"]) > 0 or roots.get("test_root") is not None,
            test_summary=test_summary,
            asset_summary=asset_summary,
            infrastructure_summary=sorted(classified["infrastructure"]),
            ignored_paths=sorted(list(DEFAULT_IGNORED_DIRS)),
            repository_size=stats,
            evidence=evidence,
            timestamp=now_str,
        )

    def _scan_file_tree(
        self, repo_root: Path, max_depth: int = 5
    ) -> tuple[List[Path], Dict[str, int]]:
        """Walk repository files cleanly skipping ignored directories."""
        all_files: List[Path] = []
        dir_count = 0
        file_count = 0
        total_size = 0

        if not repo_root.exists() or not repo_root.is_dir():
            return [], {"file_count": 0, "directory_count": 0, "total_size_bytes": 0}

        try:
            for root, dirs, files in os.walk(repo_root):
                # Prune ignored directories
                dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORED_DIRS and not d.startswith(".")]
                curr_path = Path(root)

                # Check depth
                try:
                    rel_depth = len(curr_path.relative_to(repo_root).parts)
                except ValueError:
                    rel_depth = 0

                if rel_depth > max_depth:
                    dirs[:] = []
                    continue

                dir_count += len(dirs)

                for file_name in files:
                    if file_name.startswith(".DS_Store"):
                        continue
                    file_path = curr_path / file_name
                    all_files.append(file_path)
                    file_count += 1
                    try:
                        total_size += file_path.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass

        stats = {
            "file_count": file_count,
            "directory_count": dir_count,
            "total_size_bytes": total_size,
        }
        return all_files, stats

    def _build_directory_topology(
        self, repo_root: Path, file_tree: List[Path]
    ) -> Dict[str, List[str]]:
        """Build top-level directory topology mapping."""
        topology: Dict[str, List[str]] = {}
        if not repo_root.exists():
            return topology

        try:
            top_items = sorted([p for p in repo_root.iterdir() if p.name not in DEFAULT_IGNORED_DIRS and not p.name.startswith(".")])
            for item in top_items:
                if item.is_dir():
                    children = [c.name for c in item.iterdir() if c.name not in DEFAULT_IGNORED_DIRS and not c.name.startswith(".")][:10]
                    topology[item.name] = children
                else:
                    if "." not in topology:
                        topology["."] = []
                    topology["."].append(item.name)
        except OSError:
            pass

        return topology

    def _detect_roots(self, repo_root: Path, file_tree: List[Path]) -> Dict[str, str | None]:
        """Detect specialized directory roots."""
        roots: Dict[str, str | None] = {
            "application_root": str(repo_root),
            "source_root": None,
            "api_root": None,
            "component_root": None,
            "test_root": None,
            "asset_root": None,
            "configuration_root": None,
            "documentation_root": None,
            "scripts_root": None,
            "infrastructure_root": None,
        }

        # Source Root candidates
        for src_candidate in ("src", "lib", "app", "pkg", "cmd", "packages"):
            p = repo_root / src_candidate
            if p.is_dir():
                roots["source_root"] = str(p)
                break
        if roots["source_root"] is None:
            roots["source_root"] = str(repo_root)

        # API Root candidates
        for api_candidate in ("api", "routes", "controllers", "handlers", "endpoints", "graphql"):
            for base in (repo_root, repo_root / "src", repo_root / "app", repo_root / "lib"):
                p = base / api_candidate
                if p.is_dir():
                    roots["api_root"] = str(p)
                    break
            if roots["api_root"]:
                break

        # Component Root candidates
        for comp_candidate in ("components", "views", "ui", "widgets"):
            for base in (repo_root, repo_root / "src", repo_root / "app"):
                p = base / comp_candidate
                if p.is_dir():
                    roots["component_root"] = str(p)
                    break
            if roots["component_root"]:
                break

        # Test Root candidates
        for test_candidate in ("tests", "test", "spec", "__tests__"):
            p = repo_root / test_candidate
            if p.is_dir():
                roots["test_root"] = str(p)
                break

        # Asset Root candidates
        for asset_candidate in ("assets", "public", "static", "images", "media"):
            p = repo_root / asset_candidate
            if p.is_dir():
                roots["asset_root"] = str(p)
                break

        # Config Root candidates
        for cfg_candidate in ("config", "configs", ".config"):
            p = repo_root / cfg_candidate
            if p.is_dir():
                roots["configuration_root"] = str(p)
                break
        if roots["configuration_root"] is None:
            roots["configuration_root"] = str(repo_root)

        # Doc Root candidates
        for doc_candidate in ("docs", "doc", "documentation", "wiki"):
            p = repo_root / doc_candidate
            if p.is_dir():
                roots["documentation_root"] = str(p)
                break

        # Scripts Root candidates
        for script_candidate in ("scripts", "bin", "tools"):
            p = repo_root / script_candidate
            if p.is_dir():
                roots["scripts_root"] = str(p)
                break

        # Infrastructure Root candidates
        for infra_candidate in ("infra", "infrastructure", "k8s", "docker", "terraform", "deploy"):
            p = repo_root / infra_candidate
            if p.is_dir():
                roots["infrastructure_root"] = str(p)
                break

        return roots

    def _determine_project_layout(
        self, repo_root: Path, roots: Dict[str, str | None], ws_ctx: WorkspaceContext
    ) -> str:
        if ws_ctx.workspace_state.value == "MONOREPO":
            return "monorepo"

        src_root = roots.get("source_root")
        if src_root and src_root != str(repo_root):
            return "src_layout"

        return "flat_layout"

    def _classify_repository_files(
        self, repo_root: Path, file_tree: List[Path]
    ) -> Dict[str, List[str]]:
        classified: Dict[str, List[str]] = {
            "source": [],
            "config": [],
            "documentation": [],
            "assets": [],
            "tests": [],
            "infrastructure": [],
            "database": [],
            "generated": [],
            "unknown": [],
        }

        source_exts = {
            ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".cs",
            ".dart", ".php", ".c", ".cpp", ".h", ".hpp", ".rb", ".swift", ".html", ".css", ".scss"
        }
        config_names = {
            "package.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
            "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts",
            "composer.json", "pubspec.yaml", "pnpm-workspace.yaml", "lerna.json", "turbo.json",
            "nx.json", "tsconfig.json", "jsconfig.json", "Makefile", "CMakeLists.txt"
        }
        config_exts = {".json", ".toml", ".yaml", ".yml", ".ini", ".env", ".cfg", ".xml", ".properties", ".csproj", ".fsproj", ".sln"}
        doc_names = {"README.md", "README", "CHANGELOG.md", "LICENSE", "NOTICE", "CONTRIBUTING.md", "AGENTS.md"}
        doc_exts = {".md", ".rst", ".txt"}
        asset_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".mp3", ".mp4", ".pdf", ".ttf", ".woff", ".woff2"}
        infra_names = {"Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Procfile", "Containerfile"}
        infra_exts = {".tf", ".k8s.yaml"}

        for p in file_tree:
            try:
                rel_path = str(p.relative_to(repo_root))
            except ValueError:
                rel_path = p.name

            name = p.name
            ext = p.suffix.lower()

            # Test check
            if "test" in name.lower() or "spec" in name.lower() or "/tests/" in rel_path or "/test/" in rel_path or "/__tests__/" in rel_path:
                classified["tests"].append(rel_path)
                continue

            # Infrastructure check
            if name in infra_names or ext in infra_exts or ".github/workflows" in rel_path:
                classified["infrastructure"].append(rel_path)
                continue

            # Documentation check
            if name in doc_names or ext in doc_exts or rel_path.startswith("docs/"):
                classified["documentation"].append(rel_path)
                continue

            # Configuration check
            if name in config_names or ext in config_exts or name.startswith(".env"):
                classified["config"].append(rel_path)
                continue

            # Asset check
            if ext in asset_exts or rel_path.startswith("assets/") or rel_path.startswith("public/"):
                classified["assets"].append(rel_path)
                continue

            # Database check
            if ext == ".sql" or ext == ".prisma" or "migrations/" in rel_path or "alembic/" in rel_path:
                classified["database"].append(rel_path)
                continue

            # Source check
            if ext in source_exts:
                classified["source"].append(rel_path)
                continue

            classified["unknown"].append(rel_path)

        return classified

    def _detect_entry_points(
        self, repo_root: Path, file_tree: List[Path], source_files: List[str]
    ) -> List[str]:
        entry_points: List[str] = []
        known_entries = (
            "main.py", "manage.py", "app.py", "wsgi.py", "asgi.py", "cli.py", "__main__.py",
            "index.ts", "index.js", "main.ts", "main.js", "server.ts", "server.js", "app.ts", "app.js",
            "main.go", "Program.cs", "main.rs", "lib.rs", "Application.java", "Main.java",
            "next.config.js", "next.config.mjs", "next.config.ts", "vite.config.ts", "vite.config.js",
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "README.md", "LICENSE"
        )

        for name in known_entries:
            for p in file_tree:
                if p.name == name or str(p.relative_to(repo_root)) == name:
                    rel = str(p.relative_to(repo_root))
                    if rel not in entry_points:
                        entry_points.append(rel)

        # Check cmd/*/main.go
        for p in file_tree:
            if "cmd/" in str(p) and p.name == "main.go":
                rel = str(p.relative_to(repo_root))
                if rel not in entry_points:
                    entry_points.append(rel)

        return sorted(entry_points)

    def _summarize_tests(
        self, roots: Dict[str, str | None], test_files: List[str]
    ) -> Dict[str, Any]:
        return {
            "has_tests": len(test_files) > 0 or roots.get("test_root") is not None,
            "test_root": roots.get("test_root"),
            "test_file_count": len(test_files),
        }

    def _summarize_assets(self, asset_files: List[str]) -> Dict[str, int]:
        summary: Dict[str, int] = {"total_assets": len(asset_files)}
        for f in asset_files:
            ext = Path(f).suffix.lower() or "other"
            summary[ext] = summary.get(ext, 0) + 1
        return summary
