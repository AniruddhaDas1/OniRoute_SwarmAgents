"""Natural Language Router Engine for Phase P6.D1.

Accepts arbitrary natural language requests ("oniroute build real estate website",
"oniroute create SaaS CRM", "oniroute fix ...") and automatically orchestrates
Intent Analysis, Workspace/Repository Intelligence, Mission Planning, Skill Intelligence,
Swarm Initialization, Project Assembly, and Autonomous Engineering without requiring
manual workflow selection, skill selection, agent selection, or model selection.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from runtime.allocation import ImplementationAllocationEngine
from runtime.assembly import ProjectAssemblyCertificationEngine
from runtime.blueprint import ProjectBlueprintEngine
from runtime.contracts import EngineeringContractEngine
from runtime.engineering import AutonomousEngineeringCertificationEngine, EngineeringWorkerEngine
from runtime.healing import RepairPlanner, SelfHealingEngine
from runtime.intent import IntentAnalyzer
from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.review import QualityGateEngine
from runtime.router.exceptions import RouterError, RouterExecutionError
from runtime.router.models import RouterExecutionResult, SmartDefaults
from runtime.scaffold import WorkspaceScaffoldEngine
from runtime.skills import AgentProfileBuilderEngine, SkillBundlingEngine, SkillDiscoveryEngine, SkillRankingEngine
from runtime.deployment import MissionDeploymentPlanner
from runtime.swarm import SwarmInitializationEngine

from runtime.validation import AcceptanceEngine, VerificationEngine
from runtime.workspace.intelligence import WorkspaceIntelligence
from runtime.workspace.repository import RepositoryIntelligence
from runtime.workspace.plan import EngineeringPlanGenerator



class NaturalLanguageRouter:
    """Public Natural Language Router for Phase P6.D1."""

    def __init__(self, confidence_threshold: float = 0.6) -> None:
        """Initialize NaturalLanguageRouter.

        Args:
            confidence_threshold: Threshold below which user interaction is solicited.
        """
        self.confidence_threshold = confidence_threshold
        self.intent_analyzer = IntentAnalyzer()
        self.workspace_intelligence = WorkspaceIntelligence()
        self.repository_intelligence = RepositoryIntelligence()

    def route_and_execute(
        self,
        request_text: str,
        workspace_path: Optional[Path] = None,
        prompt_callback: Optional[Callable[[str, List[str]], str]] = None,
    ) -> RouterExecutionResult:
        """Route natural language request and execute the full end-to-end pipeline automatically.

        Args:
            request_text: Natural language user request (e.g. "build a real estate website").
            workspace_path: Optional target workspace path. Defaults to Path.cwd().
            prompt_callback: Optional callback for asking clarification questions when confidence < threshold.

        Returns:
            RouterExecutionResult: Immutable end-to-end execution summary contract.
        """
        start_time = time.perf_counter()

        if not request_text or not request_text.strip():
            raise RouterExecutionError("Request text cannot be empty.")

        ws_path = (workspace_path or Path.cwd()).resolve()

        # 1. Intent Analysis
        intent_report = self.intent_analyzer.analyze(request_text)

        # Prompt user ONLY if confidence is below defined threshold
        if intent_report.confidence_score < self.confidence_threshold and prompt_callback is not None:
            question = f"Could you clarify the primary domain or requirement for '{request_text}'?"
            options = ["Web Application", "REST API Backend", "CLI Tool", "Full-Stack SaaS"]
            user_choice = prompt_callback(question, options)
            request_text = f"{request_text} ({user_choice})"
            intent_report = self.intent_analyzer.analyze(request_text)

        # 2. Workspace & Repository Intelligence
        ws_context = self.workspace_intelligence.analyze_workspace(cwd=ws_path, explicit_workspace=ws_path)
        repo_context = self.repository_intelligence.analyze_repository(ws_context)

        # 3. Resolve Smart Defaults
        smart_defaults = self._resolve_smart_defaults(intent_report, request_text)

        # 4. Mission Planning
        plan_gen = EngineeringPlanGenerator()
        exec_plan = plan_gen.generate_plan(intent_report, ws_context, repo_context)

        # 5. Skill Intelligence
        registry = RepositoryLoader(ws_path if (ws_path / ".oniroute").exists() else Path.cwd()).load()
        resolver = Resolver(registry)

        discovery_engine = SkillDiscoveryEngine(registry, resolver)
        ranking_engine = SkillRankingEngine(registry, resolver)
        bundling_engine = SkillBundlingEngine(registry, resolver)
        builder_engine = AgentProfileBuilderEngine(registry, resolver)
        deployment_planner = MissionDeploymentPlanner()

        sel_report = discovery_engine.discover_skills(exec_plan)
        rnk_report = ranking_engine.rank_skills(sel_report, exec_plan)
        bnd_report = bundling_engine.bundle_skills(rnk_report, exec_plan, sel_report)
        prf_report = builder_engine.build_profiles(bnd_report, exec_plan)
        deployment_plan = deployment_planner.create_deployment_plan(exec_plan, prf_report)

        # 6. Swarm Initialization (P3)
        init_engine = SwarmInitializationEngine()
        snapshot = init_engine.initialize_swarm(deployment_plan)

        # 7. Project Assembly Pipeline (P4)
        scaffold_engine = WorkspaceScaffoldEngine()
        scaffold_report = scaffold_engine.scaffold_workspace(snapshot, workspace_override=ws_path)

        blueprint_engine = ProjectBlueprintEngine()
        blueprint_report = blueprint_engine.generate_blueprint(scaffold_report)

        allocation_engine = ImplementationAllocationEngine()
        allocation_report = allocation_engine.allocate_implementation(blueprint_report)

        contract_engine = EngineeringContractEngine()
        contract_report = contract_engine.generate_contracts(allocation_report)

        assembly_cert_engine = ProjectAssemblyCertificationEngine()
        assembly_cert_report = assembly_cert_engine.certify_assembly(
            target_workspace_dir=ws_path
        )

        # 8. Autonomous Engineering Pipeline (P5)
        worker_engine = EngineeringWorkerEngine()
        eng_results = worker_engine.execute_all_contracts(contract_report)

        gate_engine = QualityGateEngine()
        quality_reports = gate_engine.review_all_results(eng_results, contract_report)

        planner = RepairPlanner()
        healing_engine = SelfHealingEngine()
        updated_results = []
        result_map = {r.result_id: r for r in eng_results}
        for q_rep in quality_reports:
            repair_plan = planner.create_repair_plan(q_rep)
            orig_res = result_map.get(q_rep.engineering_result_id, eng_results[0])
            upd_res = healing_engine.apply_repairs(repair_plan, orig_res, str(ws_path))
            updated_results.append(upd_res)

        vrf_engine = VerificationEngine()
        verifications = vrf_engine.verify_all_results(updated_results, str(ws_path))

        acpt_engine = AcceptanceEngine()
        acceptance_reports = acpt_engine.evaluate_all_acceptances(verifications)

        cert_engine = AutonomousEngineeringCertificationEngine()
        certification_report = cert_engine.certify_engineering_pipeline(
            acceptance_reports=acceptance_reports,
            verification_results=verifications,
            updated_results=updated_results,
            quality_reports=quality_reports,
            engineering_results=eng_results,
            contract_report=contract_report,
        )

        end_latency_ms = (time.perf_counter() - start_time) * 1000.0
        exec_id = f"nlr-{abs(hash(f'{request_text}-{end_latency_ms}')) % 1000000:06d}"

        total_created = sum(len(e.created_files) for e in eng_results)
        total_modified = sum(len(e.modified_files) for e in eng_results)
        avg_quality = round(sum(q.architecture_score + q.security_score for q in quality_reports) / (2.0 * len(quality_reports)), 2) if quality_reports else 9.5
        production_ready = certification_report.production_readiness

        return RouterExecutionResult(
            router_execution_id=exec_id,
            request_text=request_text,
            primary_intent=intent_report.primary_intent,
            mission_id=snapshot.mission_id,
            confidence_score=intent_report.confidence_score,
            smart_defaults=smart_defaults,
            execution_snapshot=snapshot,
            scaffold_report=scaffold_report,
            blueprint_report=blueprint_report,
            allocation_report=allocation_report,
            contract_report=contract_report,
            assembly_certification_report=assembly_cert_report,
            engineering_results=eng_results,
            quality_reports=quality_reports,
            updated_results=updated_results,
            verifications=verifications,
            acceptance_reports=acceptance_reports,
            certification_report=certification_report,
            total_files_created=total_created,
            total_files_modified=total_modified,
            quality_score=avg_quality,
            production_ready=production_ready,
            end_to_end_latency_ms=round(end_latency_ms, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _resolve_smart_defaults(self, intent_report: Any, request_text: str) -> SmartDefaults:
        """Automatically derive smart defaults based on parsed intent and request text."""
        req_lower = request_text.lower()

        if "fastapi" in req_lower or "python" in req_lower or "backend" in req_lower:
            proj_type = "python"
            tech_stack = "Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy + PostgreSQL"
            framework = "FastAPI"
            db = "PostgreSQL"
            auth = "OAuth2 + JWT"
            deploy = "Docker Container / AWS ECS"
            test_fw = "pytest"
            pkg_mgr = "pip / poetry"
            standards = "PEP8 + Black + Ruff"
        elif "go" in req_lower or "gin" in req_lower or "microservice" in req_lower:
            proj_type = "go"
            tech_stack = "Go 1.22 + Gin Gonic + GORM + PostgreSQL"
            framework = "Gin Gonic"
            db = "PostgreSQL"
            auth = "JWT"
            deploy = "Docker Container / Kubernetes"
            test_fw = "testing / testify"
            pkg_mgr = "go mod"
            standards = "Standard Go + staticcheck"
        elif "rust" in req_lower or "cli" in req_lower:
            proj_type = "rust"
            tech_stack = "Rust 2021 + Axum / Clap + Tokio + SQLite"
            framework = "Axum / Clap"
            db = "SQLite / PostgreSQL"
            auth = "JWT"
            deploy = "Binary Release / Docker"
            test_fw = "cargo test"
            pkg_mgr = "cargo"
            standards = "rustfmt + clippy"
        elif "real estate" in req_lower or "saas" in req_lower or "crm" in req_lower or "website" in req_lower or "app" in req_lower:
            proj_type = "typescript"
            tech_stack = "Next.js 14 + React + Tailwind CSS + TypeScript + PostgreSQL"
            framework = "Next.js"
            db = "PostgreSQL"
            auth = "NextAuth.js / JWT"
            deploy = "Vercel / Docker Container"
            test_fw = "Vitest + Playwright"
            pkg_mgr = "npm"
            standards = "ESLint + Prettier + Strict TypeScript"

        else:
            proj_type = getattr(intent_report, "extracted_domain", "typescript")
            tech_stack = "Modern Full-Stack Architecture (TypeScript + React + Node.js + PostgreSQL)"
            framework = "Next.js / Node.js"
            db = "PostgreSQL"
            auth = "JWT / OAuth2"
            deploy = "Docker Container"
            test_fw = "pytest / Vitest"
            pkg_mgr = "npm"
            standards = "Standard Clean Code Guidelines"

        return SmartDefaults(
            project_type=proj_type,
            technology_stack=tech_stack,
            framework=framework,
            database=db,
            authentication=auth,
            deployment_target=deploy,
            testing_framework=test_fw,
            package_manager=pkg_mgr,
            coding_standards=standards,
            llm_provider="oniroute-local-engine",
            mcp_tools=["BridgeForce", "StitchMCP", "Chrome DevTools", "Firebase MCP"],
            review_strategy="cross-agent-5-profile-review",
            healing_strategy="automated-self-healing",
            verification_strategy="deterministic-build-test-coverage",
        )
