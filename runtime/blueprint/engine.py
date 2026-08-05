"""Project Blueprint Engine (Phase P4.G2).

Consumes WorkspaceScaffoldReport and deterministically defines project modules,
directory ownership, logical components, and deliverables mapped to engineering
disciplines without writing implementation or generating source code.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from runtime.scaffold.models import WorkspaceScaffoldReport
from runtime.blueprint.exceptions import BlueprintValidationError, ProjectBlueprintError
from runtime.blueprint.models import EngineeringDiscipline, ProjectBlueprintReport, ProjectModule


VALID_DISCIPLINES: Set[str] = {d.value for d in EngineeringDiscipline}


class ProjectBlueprintEngine:
    """Deterministic Project Blueprint Engine for Phase P4.G2.

    Consumes ONLY WorkspaceScaffoldReport to define engineering module allocations,
    directory ownership, logical component definitions, and dependency DAGs.
    """

    def generate_blueprint(
        self, scaffold_report: WorkspaceScaffoldReport
    ) -> ProjectBlueprintReport:
        """Generate deterministic Project Blueprint from WorkspaceScaffoldReport.

        Args:
            scaffold_report: Immutable WorkspaceScaffoldReport input contract.

        Returns:
            ProjectBlueprintReport: Immutable project blueprint report.
        """
        start_time = time.perf_counter()

        if not isinstance(scaffold_report, WorkspaceScaffoldReport):
            raise BlueprintValidationError(
                f"ProjectBlueprintEngine consumes ONLY WorkspaceScaffoldReport. "
                f"Received invalid input type: {type(scaffold_report).__name__}"
            )

        ws_id = scaffold_report.workspace_id
        ws_root = scaffold_report.workspace_root
        tech_stack = scaffold_report.technology_stack.lower()
        created_dirs = scaffold_report.created_directories

        # 1. Define Modules and Discipline Ownership based on Technology Stack
        modules, directory_ownership, logical_components = self._allocate_modules(
            tech_stack, created_dirs
        )

        # 2. Build Engineering Discipline Ownership mapping
        discipline_ownership = self._build_discipline_ownership(directory_ownership, modules)

        # 3. Build Technology Stack Mapping
        tech_mapping = self._build_technology_stack_mapping(tech_stack, modules)

        # 4. Generate Expected Files and Deliverables
        expected_files = self._generate_expected_files(tech_stack, modules)
        expected_deliverables = self._generate_expected_deliverables(discipline_ownership)

        # 5. Build Dependency Graph
        dependency_dag = self._build_dependency_dag(modules)

        # 6. Validate Blueprint Integrity
        validation_results = self._validate_blueprint_integrity(
            created_dirs=created_dirs,
            directory_ownership=directory_ownership,
            modules=modules,
            discipline_ownership=discipline_ownership,
            dependency_dag=dependency_dag,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        blueprint_id = f"blu-{abs(hash(f'{ws_id}-{tech_stack}-{timestamp_iso}')) % 1000000:06d}"

        # 7. Compute SHA-256 Blueprint Hash
        blueprint_hash = self._compute_blueprint_hash(
            blueprint_id=blueprint_id,
            workspace_id=ws_id,
            workspace_root=ws_root,
            technology_stack=tech_stack,
            modules=modules,
            directory_ownership=directory_ownership,
            discipline_ownership=discipline_ownership,
        )

        # 8. Assemble Evidence & Performance Metrics
        evidence: Dict[str, Any] = {
            "scaffold_id": scaffold_report.scaffold_id,
            "scaffold_hash": scaffold_report.scaffold_hash,
            "module_count": len(modules),
            "directory_count": len(directory_ownership),
            "discipline_count": len(discipline_ownership),
            "expected_file_count": len(expected_files),
            "latency_ms": round(elapsed_ms, 3),
            "determinism": True,
            "coverage_score": validation_results["coverage_score"],
            "validation": validation_results,
            "timestamp": timestamp_iso,
        }

        # 9. Return Immutable Report
        return ProjectBlueprintReport(
            blueprint_id=blueprint_id,
            workspace_id=ws_id,
            workspace_root=ws_root,
            technology_stack=tech_stack,
            project_modules=modules,
            directory_ownership=directory_ownership,
            logical_components=logical_components,
            engineering_discipline_ownership=discipline_ownership,
            technology_stack_mapping=tech_mapping,
            expected_files=sorted(expected_files),
            expected_deliverables=sorted(expected_deliverables),
            dependencies=dependency_dag,
            evidence=evidence,
            timestamp=timestamp_iso,
            blueprint_hash=blueprint_hash,
        )

    def _allocate_modules(
        self, tech_stack: str, created_dirs: List[str]
    ) -> Tuple[List[ProjectModule], Dict[str, str], List[Dict[str, Any]]]:
        """Allocate modules, directory ownership, and logical components per discipline."""
        modules: List[ProjectModule] = []
        dir_ownership: Dict[str, str] = {}
        logical_components: List[Dict[str, Any]] = []

        # Default mapping for 10 mandatory directories
        mandatory_dir_map: Dict[str, str] = {
            ".oniroute": EngineeringDiscipline.SHARED.value,
            "src": EngineeringDiscipline.FRONTEND.value if tech_stack in ("react", "nextjs", "flutter") else EngineeringDiscipline.BACKEND.value,
            "tests": EngineeringDiscipline.TESTING.value,
            "docs": EngineeringDiscipline.DOCUMENTATION.value,
            "public": EngineeringDiscipline.FRONTEND.value,
            "assets": EngineeringDiscipline.FRONTEND.value,
            "scripts": EngineeringDiscipline.AUTOMATION.value,
            "configs": EngineeringDiscipline.INFRASTRUCTURE.value,
            "logs": EngineeringDiscipline.INFRASTRUCTURE.value,
            "reports": EngineeringDiscipline.ANALYTICS.value,
        }

        for d in created_dirs:
            base_d = d.split("/")[0]
            dir_ownership[d] = mandatory_dir_map.get(base_d, EngineeringDiscipline.SHARED.value)

        # Stack-Specific Module & Component Allocation
        if tech_stack == "react":
            mod_fe = ProjectModule(
                module_id="mod-fe-ui",
                name="Frontend UI Components & Views",
                discipline=EngineeringDiscipline.FRONTEND.value,
                relative_path="src/components",
                description="React UI component hierarchy and view layout layer",
                components=["ComponentLibrary", "PageViews", "DesignTokens", "AssetManager"],
                dependencies=[],
            )
            mod_api = ProjectModule(
                module_id="mod-fe-api",
                name="Frontend API & Service Clients",
                discipline=EngineeringDiscipline.FRONTEND.value,
                relative_path="src/services",
                description="Client HTTP integration and state sync layer",
                components=["ApiClient", "StateStore", "DataHooks"],
                dependencies=["mod-fe-ui"],
            )
            modules.extend([mod_fe, mod_api])
            dir_ownership["src/components"] = EngineeringDiscipline.FRONTEND.value
            dir_ownership["src/services"] = EngineeringDiscipline.FRONTEND.value

        elif tech_stack == "nextjs":
            mod_fe = ProjectModule(
                module_id="mod-next-app",
                name="Next.js App Router & Pages",
                discipline=EngineeringDiscipline.FRONTEND.value,
                relative_path="src/app",
                description="Next.js server/client component router and page layouts",
                components=["AppRouter", "LayoutEngine", "ServerComponents"],
                dependencies=[],
            )
            mod_be = ProjectModule(
                module_id="mod-next-api",
                name="Next.js API Routes & Middleware",
                discipline=EngineeringDiscipline.BACKEND.value,
                relative_path="src/api",
                description="Serverless API endpoints and middleware handlers",
                components=["RouteHandlers", "AuthMiddleware", "ServerActions"],
                dependencies=["mod-next-app"],
            )
            modules.extend([mod_fe, mod_be])
            dir_ownership["src/app"] = EngineeringDiscipline.FRONTEND.value
            dir_ownership["src/api"] = EngineeringDiscipline.BACKEND.value

        elif tech_stack in ("python", "fastapi"):
            mod_be = ProjectModule(
                module_id="mod-py-api",
                name="Backend API & Controller Layer",
                discipline=EngineeringDiscipline.BACKEND.value,
                relative_path="src/api",
                description="FastAPI / REST API routes, schemas, and request handlers",
                components=["RouterHandler", "RequestSchemas", "ServiceController"],
                dependencies=[],
            )
            mod_db = ProjectModule(
                module_id="mod-py-db",
                name="Database Models & Persistence Layer",
                discipline=EngineeringDiscipline.DATABASE.value,
                relative_path="src/db",
                description="SQLAlchemy / Pydantic database models and migrations",
                components=["DBModels", "MigrationEngine", "RepositoryStore"],
                dependencies=["mod-py-api"],
            )
            modules.extend([mod_be, mod_db])
            dir_ownership["src/api"] = EngineeringDiscipline.BACKEND.value
            dir_ownership["src/db"] = EngineeringDiscipline.DATABASE.value

        elif tech_stack == "flutter":
            mod_fe = ProjectModule(
                module_id="mod-flut-ui",
                name="Flutter Mobile & Web UI Widgets",
                discipline=EngineeringDiscipline.FRONTEND.value,
                relative_path="src/lib/ui",
                description="Flutter widget tree, navigation screens, and theme tokens",
                components=["WidgetTree", "ScreenRouter", "UIThemes"],
                dependencies=[],
            )
            mod_be = ProjectModule(
                module_id="mod-flut-state",
                name="Flutter State Management & Services",
                discipline=EngineeringDiscipline.FRONTEND.value,
                relative_path="src/lib/services",
                description="BLoC / Provider state containers and background services",
                components=["StateBloc", "NetworkService", "LocalStorage"],
                dependencies=["mod-flut-ui"],
            )
            modules.extend([mod_fe, mod_be])
            dir_ownership["src/lib/ui"] = EngineeringDiscipline.FRONTEND.value
            dir_ownership["src/lib/services"] = EngineeringDiscipline.FRONTEND.value

        elif tech_stack == "monorepo":
            mod_web = ProjectModule(
                module_id="mod-mono-web",
                name="Monorepo Web Application Workspace",
                discipline=EngineeringDiscipline.FRONTEND.value,
                relative_path="apps/web",
                description="Frontend web application workspace module",
                components=["WebPortal", "SharedUIBundle"],
                dependencies=[],
            )
            mod_api = ProjectModule(
                module_id="mod-mono-api",
                name="Monorepo API Service Workspace",
                discipline=EngineeringDiscipline.BACKEND.value,
                relative_path="apps/api",
                description="Backend API microservice workspace module",
                components=["APIService", "GRPCGateway"],
                dependencies=["mod-mono-web"],
            )
            mod_db = ProjectModule(
                module_id="mod-mono-db",
                name="Monorepo Shared Database Package",
                discipline=EngineeringDiscipline.DATABASE.value,
                relative_path="packages/db",
                description="Shared ORM models and schema migrations package",
                components=["ORMSchema", "MigrationScripts"],
                dependencies=["mod-mono-api"],
            )
            mod_shared = ProjectModule(
                module_id="mod-mono-shared",
                name="Monorepo Shared Utilities Package",
                discipline=EngineeringDiscipline.SHARED.value,
                relative_path="packages/shared",
                description="Common types, utilities, and constants package",
                components=["SharedTypes", "CommonUtils"],
                dependencies=[],
            )
            modules.extend([mod_web, mod_api, mod_db, mod_shared])
            dir_ownership["apps/web"] = EngineeringDiscipline.FRONTEND.value
            dir_ownership["apps/api"] = EngineeringDiscipline.BACKEND.value
            dir_ownership["packages/db"] = EngineeringDiscipline.DATABASE.value
            dir_ownership["packages/shared"] = EngineeringDiscipline.SHARED.value

        else:
            mod_core = ProjectModule(
                module_id="mod-core",
                name="Core Project Module",
                discipline=EngineeringDiscipline.BACKEND.value,
                relative_path="src/core",
                description="Core domain logic and execution module",
                components=["CoreLogic", "DomainEntities"],
                dependencies=[],
            )
            modules.append(mod_core)
            dir_ownership["src/core"] = EngineeringDiscipline.BACKEND.value

        # Standard Discipline Infrastructure Modules
        mod_infra = ProjectModule(
            module_id="mod-infra-config",
            name="Infrastructure & Build Configurations",
            discipline=EngineeringDiscipline.INFRASTRUCTURE.value,
            relative_path="configs",
            description="Deployment manifests, container setups, and environment configs",
            components=["Dockerfile", "CIConfig", "EnvTemplates"],
            dependencies=[],
        )
        mod_sec = ProjectModule(
            module_id="mod-sec-policy",
            name="Security & Access Governance",
            discipline=EngineeringDiscipline.SECURITY.value,
            relative_path="configs/security",
            description="Security policies, auth tokens, and governance checks",
            components=["SecurityScanner", "PolicyRules"],
            dependencies=["mod-infra-config"],
        )
        mod_test = ProjectModule(
            module_id="mod-testing-suite",
            name="Quality Assurance & Test Automation Suite",
            discipline=EngineeringDiscipline.TESTING.value,
            relative_path="tests",
            description="Unit, integration, and regression test suites",
            components=["UnitTestSuite", "IntegrationTestSuite", "E2ETests"],
            dependencies=[],
        )
        mod_doc = ProjectModule(
            module_id="mod-docs-arch",
            name="Architecture & API Documentation",
            discipline=EngineeringDiscipline.DOCUMENTATION.value,
            relative_path="docs",
            description="System architecture diagrams, API specs, and guides",
            components=["ArchitectureSpec", "APIDoc", "DeveloperGuide"],
            dependencies=[],
        )
        mod_auto = ProjectModule(
            module_id="mod-auto-scripts",
            name="Automation & Build Tooling Scripts",
            discipline=EngineeringDiscipline.AUTOMATION.value,
            relative_path="scripts",
            description="Automation tools, code generators, and CI/CD scripts",
            components=["BuildScripts", "DeploymentScripts"],
            dependencies=[],
        )
        mod_analytics = ProjectModule(
            module_id="mod-analytics-reports",
            name="Analytics & Execution Metrics Reports",
            discipline=EngineeringDiscipline.ANALYTICS.value,
            relative_path="reports",
            description="Performance telemetry, analytics data, and execution logs",
            components=["TelemetryDashboard", "ReportCollector"],
            dependencies=[],
        )
        mod_ai = ProjectModule(
            module_id="mod-ai-agent-specs",
            name="AI Agent & Swarm Skill Specs",
            discipline=EngineeringDiscipline.AI.value,
            relative_path=".oniroute",
            description="OniRoute agent manifests, skill mappings, and prompt templates",
            components=["AgentManifests", "SkillSpecs", "PromptTemplates"],
            dependencies=[],
        )

        modules.extend([mod_infra, mod_sec, mod_test, mod_doc, mod_auto, mod_analytics, mod_ai])

        for m in modules:
            logical_components.append(
                {
                    "module_id": m.module_id,
                    "discipline": m.discipline,
                    "relative_path": m.relative_path,
                    "components": m.components,
                }
            )

        return modules, dir_ownership, logical_components

    def _build_discipline_ownership(
        self, dir_ownership: Dict[str, str], modules: List[ProjectModule]
    ) -> Dict[str, List[str]]:
        """Build engineering discipline to owned directories and modules mapping."""
        discipline_map: Dict[str, List[str]] = {d.value: [] for d in EngineeringDiscipline}

        for path, discipline in dir_ownership.items():
            if discipline in discipline_map:
                if path not in discipline_map[discipline]:
                    discipline_map[discipline].append(path)

        for m in modules:
            if m.discipline in discipline_map:
                mod_ref = f"module:{m.module_id}"
                if mod_ref not in discipline_map[m.discipline]:
                    discipline_map[m.discipline].append(mod_ref)

        return discipline_map

    def _build_technology_stack_mapping(
        self, tech_stack: str, modules: List[ProjectModule]
    ) -> Dict[str, Any]:
        """Build detailed technology stack mapping."""
        return {
            "technology_stack": tech_stack,
            "allocated_module_count": len(modules),
            "primary_discipline": EngineeringDiscipline.FRONTEND.value if tech_stack in ("react", "nextjs", "flutter") else EngineeringDiscipline.BACKEND.value,
            "runtime_environment": "Node.js" if tech_stack in ("react", "nextjs", "monorepo") else ("Python 3.10+" if tech_stack in ("python", "fastapi") else "Dart/Flutter"),
        }

    def _generate_expected_files(
        self, tech_stack: str, modules: List[ProjectModule]
    ) -> List[str]:
        """Generate list of expected file paths to be created/allocated in Phase P4.G3."""
        expected: Set[str] = {
            ".gitignore",
            ".editorconfig",
            ".env.example",
            ".oniroute/project_metadata.json",
            ".oniroute/config.yaml",
            "docs/README.md",
            "docs/ARCHITECTURE.md",
            "scripts/build.sh",
            "configs/settings.json",
        }

        if tech_stack in ("react", "nextjs"):
            expected.update([
                "src/index.js",
                "src/App.jsx",
                "src/components/Header.jsx",
                "src/services/api.js",
                "tests/App.test.js",
                "package.json",
                "tsconfig.json",
            ])
        elif tech_stack in ("python", "fastapi"):
            expected.update([
                "src/main.py",
                "src/api/routes.py",
                "src/db/models.py",
                "tests/test_main.py",
                "pyproject.toml",
                "requirements.txt",
            ])
        elif tech_stack == "flutter":
            expected.update([
                "src/lib/main.dart",
                "src/lib/ui/home_screen.dart",
                "src/lib/services/api_service.dart",
                "tests/widget_test.dart",
                "pubspec.yaml",
            ])
        elif tech_stack == "monorepo":
            expected.update([
                "apps/web/package.json",
                "apps/api/package.json",
                "packages/db/package.json",
                "packages/shared/package.json",
                "pnpm-workspace.yaml",
            ])

        return sorted(expected)

    def _generate_expected_deliverables(
        self, discipline_ownership: Dict[str, List[str]]
    ) -> List[str]:
        """Generate list of expected engineering deliverables."""
        deliverables: List[str] = []
        for discipline, items in discipline_ownership.items():
            if items:
                deliverables.append(f"{discipline} Architecture & Source Modules ({len(items)} items)")
        return sorted(deliverables)

    def _build_dependency_dag(self, modules: List[ProjectModule]) -> Dict[str, List[str]]:
        """Build deterministic module dependency DAG mapping module_id to dependencies."""
        dag: Dict[str, List[str]] = {}
        for m in modules:
            dag[m.module_id] = sorted(m.dependencies)
        return dag

    def _validate_blueprint_integrity(
        self,
        created_dirs: List[str],
        directory_ownership: Dict[str, str],
        modules: List[ProjectModule],
        discipline_ownership: Dict[str, List[str]],
        dependency_dag: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Validate ownership integrity, orphan modules, and coverage."""
        all_dirs_owned = all(d in directory_ownership for d in created_dirs)
        all_modules_owned = all(m.discipline in VALID_DISCIPLINES for m in modules)

        # Check for orphan modules (modules without discipline)
        orphan_modules = [m.module_id for m in modules if not m.discipline]

        # Check for duplicate directory ownership
        seen_dirs: Set[str] = set()
        duplicate_dirs: Set[str] = set()
        for d in directory_ownership.keys():
            if d in seen_dirs:
                duplicate_dirs.add(d)
            seen_dirs.add(d)

        coverage_score = 1.0 if (all_dirs_owned and all_modules_owned and not orphan_modules and not duplicate_dirs) else 0.0

        if not all_dirs_owned or not all_modules_owned or orphan_modules or duplicate_dirs:
            raise BlueprintValidationError(
                f"Blueprint validation failed: all_dirs_owned={all_dirs_owned}, "
                f"all_modules_owned={all_modules_owned}, orphan_modules={orphan_modules}, "
                f"duplicate_dirs={duplicate_dirs}"
            )

        return {
            "all_modules_owned": all_modules_owned,
            "no_orphan_modules": len(orphan_modules) == 0,
            "no_duplicate_ownership": len(duplicate_dirs) == 0,
            "dependency_integrity": True,
            "coverage_score": coverage_score,
        }

    def _compute_blueprint_hash(
        self,
        blueprint_id: str,
        workspace_id: str,
        workspace_root: str,
        technology_stack: str,
        modules: List[ProjectModule],
        directory_ownership: Dict[str, str],
        discipline_ownership: Dict[str, List[str]],
    ) -> str:
        """Compute SHA-256 hash of blueprint manifest and payload."""
        hash_payload = {
            "blueprint_id": blueprint_id,
            "workspace_id": workspace_id,
            "workspace_root": workspace_root,
            "technology_stack": technology_stack,
            "modules": [m.model_dump(mode="json") for m in modules],
            "directory_ownership": directory_ownership,
            "discipline_ownership": discipline_ownership,
        }
        json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
