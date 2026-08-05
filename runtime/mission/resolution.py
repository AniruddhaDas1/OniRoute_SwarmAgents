"""Mission Resolution component for OniRoute Mission Orchestrator (ACR-004 Phase O3).

Mission Resolution transforms a canonical MissionRequest into a fully validated Mission.

It orchestrates existing framework engines:
- Workspace Manager & Project Detector (Workspace & Project Analysis)
- Repository Loader & Resolver (Repository Analysis)
- Context Engine & ICOE Optimization Engine (Context Resolution)
- Knowledge Resolution (Knowledge Sources, Packages, Mappings)
- Constraint Resolution (Operational & Policy Constraints)
- Mission Validation (Immutable Mission & Evidence)

It MUST NOT perform:
- Planning
- Workflow generation
- Agent selection
- Skill selection
- Model selection / UMAL invocation
- Swarm execution
- AI invocation
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.context.builder import ContextBuilder
from runtime.loader import RepositoryLoader
from runtime.optimization import OptimizationEngine, OptimizationRequest
from runtime.resolver import Resolver
from runtime.workspace import ProjectDetector, ProjectType, WorkspaceManager

from .contracts import MissionResolverContract
from .evidence import MissionEvidence
from .exceptions import InvalidMissionStateError, MissionResolutionError, MissionValidationError
from .models import (
    Mission,
    MissionConstraints,
    MissionContext,
    MissionDeliverables,
    MissionReport,
    MissionRequest,
    MissionRequirements,
    MissionStatus,
)
from .states import MissionState, can_transition


class MissionResolver(MissionResolverContract):
    """Concrete Mission Resolver orchestrating framework engines to produce a validated Mission."""

    def __init__(self, workspace_manager: WorkspaceManager | None = None) -> None:
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.project_detector = ProjectDetector()

    def resolve_mission(
        self,
        request: MissionRequest,
        workspace_manager: WorkspaceManager | None = None,
    ) -> Mission:
        """Transform a canonical MissionRequest into a fully validated Mission."""
        wm = workspace_manager or self.workspace_manager

        # Initial evidence log
        evidence = MissionEvidence()

        # 1. Workspace Analysis
        ws_evidence, ws_ctx = self._analyze_workspace(request, wm)
        evidence = evidence.record_stage("workspace", ws_evidence)

        # 2. Project Analysis
        proj_evidence, proj_meta = self._analyze_project(ws_ctx)
        evidence = evidence.record_stage("project", proj_evidence)

        # 3. Repository Analysis
        repo_evidence, registry, resolver = self._analyze_repository(ws_ctx.workspace_root)
        evidence = evidence.record_stage("repository", repo_evidence)

        # 4. Context Resolution
        ctx_evidence, icoe_evidence, mission_ctx = self._resolve_context(
            request, ws_ctx, registry
        )
        evidence = evidence.record_stage("context", ctx_evidence)
        evidence = evidence.record_stage("optimization", icoe_evidence)

        # 5. Knowledge Resolution
        know_evidence = self._resolve_knowledge(registry, resolver)
        evidence = evidence.record_stage("knowledge", know_evidence)

        # 6. Constraint Resolution
        const_evidence, constraints = self._resolve_constraints(
            request, ws_ctx, proj_meta
        )
        evidence = evidence.record_stage("constraints", const_evidence)

        # 7. Requirements & Deliverables Resolution
        req_evidence, requirements, deliverables = self._resolve_requirements(request)
        evidence = evidence.record_stage("requirements", req_evidence)

        # 8. Mission Validation & Assembly
        status = MissionStatus(current_state=request.mission_state or MissionState.RECEIVED)
        mission, val_evidence = self._validate_and_assemble(
            request=request,
            requirements=requirements,
            constraints=constraints,
            deliverables=deliverables,
            context=mission_ctx,
            evidence=evidence,
            initial_status=status,
        )

        return mission

    def _analyze_workspace(
        self, request: MissionRequest, wm: WorkspaceManager
    ) -> tuple[dict[str, Any], Any]:
        """Perform Workspace Analysis using frozen Workspace APIs."""
        ws_root = request.workspace or Path.cwd()
        ws_ctx = wm.create_context(cwd=ws_root, explicit_workspace=request.workspace)

        evidence = {
            "workspace_root": str(ws_ctx.workspace_root),
            "engine_root": str(ws_ctx.engine_root),
            "project_type": ws_ctx.project_type.value if hasattr(ws_ctx.project_type, "value") else str(ws_ctx.project_type),
            "discovery_method": ws_ctx.discovery_method.name if hasattr(ws_ctx.discovery_method, "name") else str(ws_ctx.discovery_source),
            "validation_status": ws_ctx.validation_status.value if hasattr(ws_ctx.validation_status, "value") else str(ws_ctx.validation_status),
            "read_only_engine_confirmed": ws_ctx.is_engine_read_only() or (ws_ctx.workspace_root.resolve() == ws_ctx.engine_root.resolve()),
            "has_git": (ws_ctx.workspace_root / ".git").exists(),
            "storage_initialized": ws_ctx.workspace_metadata is not None,
            "workspace_metadata_attached": request.workspace_metadata is not None,
        }

        return evidence, ws_ctx

    def _analyze_project(self, ws_ctx: Any) -> tuple[dict[str, Any], Any]:
        """Perform Project Analysis using ProjectDetector without executing build tools."""
        proj_meta = ws_ctx.project_metadata or self.project_detector.detect_project(ws_ctx.workspace_root)

        ptype = proj_meta.project_type
        ptype_str = ptype.value if hasattr(ptype, "value") else str(ptype)

        language = self._infer_language(ptype)
        build_system = self._infer_build_system(ptype)
        package_manager = self._infer_package_manager(ptype)

        evidence = {
            "project_id": proj_meta.project_id,
            "project_name": proj_meta.name,
            "project_type": ptype_str,
            "language": language,
            "framework": ptype_str if ptype_str not in ("python", "node", "unknown", "empty") else "none",
            "build_system": build_system,
            "package_manager": package_manager,
            "manifest_path": str(proj_meta.manifest_path) if proj_meta.manifest_path else None,
            "framework_version": proj_meta.framework_version,
            "language_version": proj_meta.language_version,
            "is_empty": proj_meta.is_empty,
            "repository_layout": "manifest-based" if proj_meta.manifest_path else ("empty" if proj_meta.is_empty else "flat"),
            "attributes": proj_meta.attributes,
        }

        return evidence, proj_meta

    def _infer_language(self, ptype: ProjectType | str) -> str:
        pt = ptype.value if hasattr(ptype, "value") else str(ptype)
        if pt == "python":
            return "Python"
        elif pt in ("node", "react", "nextjs", "vue", "angular", "react_native"):
            return "JavaScript/TypeScript"
        elif pt == "go":
            return "Go"
        elif pt == "rust":
            return "Rust"
        elif pt == "java":
            return "Java"
        elif pt == "flutter":
            return "Dart"
        elif pt == "dotnet":
            return "C#/.NET"
        return "Unknown"

    def _infer_build_system(self, ptype: ProjectType | str) -> str:
        pt = ptype.value if hasattr(ptype, "value") else str(ptype)
        if pt in ("node", "react", "nextjs", "vue", "angular", "react_native"):
            return "npm/yarn/pnpm"
        elif pt == "rust":
            return "cargo"
        elif pt == "go":
            return "go build"
        elif pt == "java":
            return "maven/gradle"
        elif pt == "python":
            return "pip/setuptools/poetry"
        elif pt == "flutter":
            return "flutter"
        elif pt == "dotnet":
            return "dotnet build"
        return "none"

    def _infer_package_manager(self, ptype: ProjectType | str) -> str:
        pt = ptype.value if hasattr(ptype, "value") else str(ptype)
        if pt in ("node", "react", "nextjs", "vue", "angular", "react_native"):
            return "npm"
        elif pt == "rust":
            return "cargo"
        elif pt == "go":
            return "go modules"
        elif pt == "python":
            return "pip"
        elif pt == "flutter":
            return "pub"
        elif pt == "java":
            return "maven/gradle"
        elif pt == "dotnet":
            return "nuget"
        return "none"

    def _analyze_repository(self, ws_root: Path) -> tuple[dict[str, Any], Any | None, Any | None]:
        """Perform Repository Analysis using Context Engine and RepositoryLoader."""
        registry = None
        resolver = None
        symbol_count = 0
        statistics = {}

        if ws_root.exists() and ws_root.is_dir():
            try:
                registry = RepositoryLoader(ws_root).load()
                resolver = Resolver(registry)
                statistics = registry.statistics()
                symbol_count = len(registry.agents) + len(registry.skills) + len(registry.workflows)
            except Exception:
                # If ws_root is an external directory without OniRoute registry files, registry will be empty
                pass

        config_dir = ws_root / "config"
        config_files = [f.name for f in config_dir.glob("*.yaml")] if config_dir.is_dir() else []

        doc_files = []
        for doc_name in ("README.md", "AGENTS.md", "CHANGELOG.md", "LICENSE", "NOTICE"):
            if (ws_root / doc_name).is_file():
                doc_files.append(doc_name)
        if (ws_root / "docs").is_dir():
            doc_files.append("docs/")

        evidence = {
            "root": str(ws_root),
            "statistics": statistics,
            "symbols_count": symbol_count,
            "configuration_files": config_files,
            "documentation_files": doc_files,
            "has_oniroute_storage": (ws_root / ".oniroute").exists(),
            "no_planning": True,
        }

        return evidence, registry, resolver

    def _resolve_context(
        self, request: MissionRequest, ws_ctx: Any, registry: Any | None
    ) -> tuple[dict[str, Any], dict[str, Any], MissionContext]:
        """Perform Context Resolution and pass payload through ICOE optimization."""
        mission_ctx = MissionContext(
            workspace_id=f"ws-{abs(hash(str(ws_ctx.workspace_root))) % 1000000:06d}",
            workspace_root=ws_ctx.workspace_root,
            engine_root=ws_ctx.engine_root,
            project_type=ws_ctx.project_type.value if hasattr(ws_ctx.project_type, "value") else str(ws_ctx.project_type),
            read_only_engine_confirmed=ws_ctx.is_engine_read_only() or (ws_ctx.workspace_root.resolve() == ws_ctx.engine_root.resolve()),
        )

        ctx_snapshot = {
            "workspace_id": mission_ctx.workspace_id,
            "workspace_root": str(mission_ctx.workspace_root),
            "engine_root": str(mission_ctx.engine_root),
            "project_type": mission_ctx.project_type,
            "request_command": request.normalized_command,
            "request_parameters": request.parameters,
        }

        if registry:
            ctx_builder = ContextBuilder(registry)
            repo_ctx = ctx_builder.repository()
            ctx_snapshot["repository_stats"] = repo_ctx.data.get("statistics", {})

        # Pass through ICOE (Context Optimization Engine)
        opt_engine = OptimizationEngine()
        opt_result = opt_engine.optimize(
            OptimizationRequest(
                source=ctx_snapshot,
                budget=8000,
                protected=frozenset(["workspace_id", "project_type"]),
                metadata={"request_id": f"opt-{request.mission_id}"},
            )
        )

        icoe_report_dict = opt_result.report.model_dump(mode="python")

        ctx_evidence = {
            "mission_context": mission_ctx.model_dump(mode="python"),
            "snapshot_keys": list(ctx_snapshot.keys()),
            "read_only_confirmed": mission_ctx.read_only_engine_confirmed,
        }

        return ctx_evidence, icoe_report_dict, mission_ctx

    def _resolve_knowledge(self, registry: Any | None, resolver: Any | None) -> dict[str, Any]:
        """Perform Knowledge Resolution over knowledge sources, packages, and mappings.

        MUST NOT select skills or agents.
        """
        ks_list = list(registry.knowledge_sources.keys()) if registry else []
        pkg_list = list(registry.packages.keys()) if registry else []
        map_list = list(registry.mappings.keys()) if registry else []

        evidence = {
            "knowledge_sources": ks_list,
            "packages": pkg_list,
            "mappings": map_list,
            "knowledge_sources_count": len(ks_list),
            "packages_count": len(pkg_list),
            "mappings_count": len(map_list),
            "skills_selected": False,  # Explicit boundary assertion
            "agents_selected": False,  # Explicit boundary assertion
        }

        return evidence

    def _resolve_constraints(
        self, request: MissionRequest, ws_ctx: Any, proj_meta: Any
    ) -> tuple[dict[str, Any], MissionConstraints]:
        """Perform Constraint Resolution based on parameters, workspace, and technology boundaries."""
        params = request.parameters or {}

        max_budget = params.get("max_budget_usd")
        timeout_sec = params.get("timeout_seconds", 300)
        allowed_prov = params.get("allowed_providers", [])
        local_only = params.get("local_only", False)
        require_approval = params.get("require_human_approval", False)

        constraints = MissionConstraints(
            max_budget_usd=max_budget,
            timeout_seconds=timeout_sec,
            allowed_providers=allowed_prov,
            local_only=local_only,
            require_human_approval=require_approval,
        )

        evidence = {
            "workspace_constraints": {
                "read_only_engine": ws_ctx.is_engine_read_only(),
                "storage_available": ws_ctx.workspace_metadata is not None,
            },
            "technology_constraints": {
                "project_type": proj_meta.project_type.value if hasattr(proj_meta.project_type, "value") else str(proj_meta.project_type),
                "is_empty": proj_meta.is_empty,
            },
            "user_constraints": {
                "max_budget_usd": max_budget,
                "timeout_seconds": timeout_sec,
                "allowed_providers": allowed_prov,
                "local_only": local_only,
                "require_human_approval": require_approval,
            },
            "resolved_constraints": constraints.model_dump(mode="python"),
        }

        return evidence, constraints

    def _resolve_requirements(
        self, request: MissionRequest
    ) -> tuple[dict[str, Any], MissionRequirements, MissionDeliverables]:
        """Extract requirements and deliverables from user request intent."""
        cmd = request.normalized_command.lower()

        if any(w in cmd for w in ("create", "build", "generate", "make", "add", "new")):
            intent = "create"
        elif any(w in cmd for w in ("refactor", "rewrite", "clean", "structure", "optimize")):
            intent = "refactor"
        elif any(w in cmd for w in ("fix", "debug", "resolve", "patch", "repair")):
            intent = "fix"
        elif any(w in cmd for w in ("review", "check", "inspect", "audit", "analyze")):
            intent = "review"
        else:
            intent = "general"

        func_reqs = [
            f"Fulfill request: '{request.normalized_command}'",
            f"Target intent: {intent}",
        ]
        non_func_reqs = [
            "Maintain provider independence",
            "Enforce read-only engine safety",
            "Record immutable stage evidence",
        ]

        target_artifacts = ["SOURCE_CODE", "DOCUMENTATION", "REPORT"]

        requirements = MissionRequirements(
            intent_category=intent,
            primary_goal=request.normalized_command,
            functional_requirements=func_reqs,
            non_functional_requirements=non_func_reqs,
            target_artifacts=target_artifacts,
        )

        deliverables = MissionDeliverables(
            expected_categories=target_artifacts,
            target_paths=[],
            output_summary=f"Expected deliverables for mission '{request.mission_id}'",
        )

        evidence = {
            "intent_category": intent,
            "primary_goal": request.normalized_command,
            "functional_requirements_count": len(func_reqs),
            "non_functional_requirements_count": len(non_func_reqs),
            "target_artifacts": target_artifacts,
        }

        return evidence, requirements, deliverables

    def _validate_and_assemble(
        self,
        request: MissionRequest,
        requirements: MissionRequirements,
        constraints: MissionConstraints,
        deliverables: MissionDeliverables,
        context: MissionContext,
        evidence: MissionEvidence,
        initial_status: MissionStatus,
    ) -> tuple[Mission, dict[str, Any]]:
        """Validate state machine progression and assemble immutable Mission."""
        # 1. State machine transitions: RECEIVED -> PARSED -> RESOLVED -> VALIDATED
        current = initial_status.current_state

        state_history = list(initial_status.state_history)
        now_str = datetime.now(timezone.utc).isoformat()

        def transition_to(target: MissionState, reason: str) -> MissionState:
            nonlocal current
            if not can_transition(current, target):
                raise InvalidMissionStateError(
                    f"Cannot transition mission from '{current}' to '{target}' state."
                )
            state_history.append(
                {
                    "from_state": current.value if hasattr(current, "value") else str(current),
                    "to_state": target.value if hasattr(target, "value") else str(target),
                    "reason": reason,
                    "timestamp": now_str,
                }
            )
            return target

        if current == MissionState.RECEIVED:
            current = transition_to(MissionState.PARSED, "Intake request parsed")
        if current == MissionState.PARSED:
            current = transition_to(MissionState.RESOLVED, "Framework engines resolved")
        if current == MissionState.RESOLVED:
            current = transition_to(MissionState.VALIDATED, "Mission contracts validated")

        status = MissionStatus(
            current_state=current,
            state_history=state_history,
            current_step="Mission Resolution Complete",
            progress_percentage=100.0,
            started_at=initial_status.started_at,
            updated_at=now_str,
        )

        # 2. Validation checks
        if not requirements.primary_goal:
            raise MissionValidationError("Mission requirements missing primary goal.")

        if not context.read_only_engine_confirmed:
            raise MissionValidationError("Engine read-only safety assertion failed.")

        val_evidence = {
            "validated": True,
            "final_state": current.value if hasattr(current, "value") else str(current),
            "state_transitions_count": len(state_history),
            "no_planning": True,
            "no_workflows": True,
            "no_agent_selection": True,
            "no_skill_selection": True,
            "no_model_selection": True,
            "no_execution": True,
        }

        final_evidence = evidence.record_stage("validation", val_evidence)

        # 3. Report generation
        report = MissionReport(
            mission_id=request.mission_id,
            title=f"Mission Resolution: {requirements.primary_goal[:50]}",
            summary=(
                f"Mission '{request.mission_id}' successfully resolved and validated "
                f"for workspace '{context.workspace_root}' (Project type: '{context.project_type}')."
            ),
            evidence_summary={
                "workspace": bool(final_evidence.workspace),
                "project": bool(final_evidence.project),
                "repository": bool(final_evidence.repository),
                "context": bool(final_evidence.context),
                "optimization": bool(final_evidence.optimization),
                "knowledge": bool(final_evidence.knowledge),
                "constraints": bool(final_evidence.constraints),
                "requirements": bool(final_evidence.requirements),
                "validation": bool(final_evidence.validation),
            },
        )

        mission = Mission(
            mission_id=request.mission_id,
            name=f"Mission: {requirements.primary_goal[:50]}",
            request=request,
            requirements=requirements,
            constraints=constraints,
            deliverables=deliverables,
            context=context,
            evidence=final_evidence,
            status=status,
            result=None,  # No execution outcome yet
            report=report,
        )

        return mission, val_evidence
