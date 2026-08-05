"""Engineering Execution Plan engine for OniRoute (Phase P1.I4).

Converts IntentReport, WorkspaceContext, and RepositoryContext into a single
declarative EngineeringExecutionPlan for Swarm orchestration without code generation,
AI model invocation, or agent execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from runtime.intent.models import IntentReport
from .intelligence import WorkspaceContext, WorkspaceState
from .repository import RepositoryContext


class RepositoryStrategy(str, Enum):
    """Canonical repository modification strategies."""
    NEW_PROJECT = "NEW_PROJECT"
    EXTEND_EXISTING = "EXTEND_EXISTING"
    REFACTOR_EXISTING = "REFACTOR_EXISTING"
    FEATURE_ADDITION = "FEATURE_ADDITION"
    BUG_FIX = "BUG_FIX"
    DOCUMENTATION = "DOCUMENTATION"
    UNKNOWN = "UNKNOWN"


class EngineeringExecutionPlan(BaseModel):
    """Immutable Engineering Execution Plan.

    Consolidates IntentReport, WorkspaceContext, and RepositoryContext into a single
    declarative engineering blueprint for Swarm orchestration.
    """

    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(description="Unique execution plan identifier")
    mission_id: str = Field(description="Associated mission identifier")
    project_goal: str = Field(description="Primary project engineering goal")
    current_project_state: str = Field(description="Current workspace operational state")
    target_project_state: str = Field(description="Target project state post-execution")
    project_type: str = Field(description="Canonical project type")
    technology_stack: List[str] = Field(default_factory=list, description="Consolidated technology stack")
    repository_strategy: RepositoryStrategy = Field(default=RepositoryStrategy.UNKNOWN, description="Repository modification strategy")
    required_deliverables: List[str] = Field(default_factory=list, description="Planned engineering outputs and deliverables")
    required_disciplines: List[str] = Field(default_factory=list, description="Required engineering disciplines (Frontend, Backend, etc.)")
    high_level_milestones: List[Dict[str, Any]] = Field(default_factory=list, description="Ordered high-level execution milestones")
    known_constraints: List[str] = Field(default_factory=list, description="Architectural and functional constraints")
    risks: List[str] = Field(default_factory=list, description="Identified technical and architectural risks")
    missing_information: List[str] = Field(default_factory=list, description="Unresolved or missing requirements")
    success_criteria: List[str] = Field(default_factory=list, description="Measurable criteria for task completion")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Consolidated planning evidence")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")


class EngineeringPlanGenerator:
    """Engineering Execution Plan generator.

    Transforms IntentReport, WorkspaceContext, and RepositoryContext into an immutable
    EngineeringExecutionPlan without code generation, AI invocation, or agent execution.
    """

    def generate_plan(
        self,
        intent_report: IntentReport,
        workspace_context: WorkspaceContext,
        repository_context: RepositoryContext,
    ) -> EngineeringExecutionPlan:
        """Generate a declarative EngineeringExecutionPlan from intelligence contexts."""
        now_str = datetime.now(timezone.utc).isoformat()
        hash_id = abs(hash(f"{intent_report.intent_id}:{workspace_context.workspace_id}:{repository_context.repository_id}")) % 1000000
        plan_id = f"plan-{hash_id:06d}"
        mission_id = f"msn-{hash_id:06d}"

        # 1. Determine Repository Strategy
        strategy = self._determine_repository_strategy(intent_report, workspace_context, repository_context)

        # 2. Detect Required Disciplines
        disciplines = self._detect_required_disciplines(intent_report, workspace_context, repository_context)

        # 3. Plan Deliverables
        deliverables = self._plan_deliverables(intent_report, workspace_context, repository_context, disciplines)

        # 4. Generate High-Level Milestones
        milestones = self._generate_milestones(intent_report, strategy, deliverables)

        # 5. Assess Risks & Missing Information
        risks, missing_info = self._assess_risks_and_missing_info(intent_report, workspace_context, repository_context, deliverables)

        # 6. Define Success Criteria
        success_criteria = self._define_success_criteria(intent_report, deliverables)

        # 7. Consolidate Technology Stack
        tech_stack = sorted(list(set(intent_report.detected_technologies)))

        # 8. Target Project State
        ws_val = workspace_context.workspace_state.value if hasattr(workspace_context.workspace_state, 'value') else str(workspace_context.workspace_state)
        target_state = "COMPLETED_PROJECT" if strategy in (RepositoryStrategy.NEW_PROJECT, RepositoryStrategy.EXTEND_EXISTING) else "UPDATED_PROJECT"

        evidence = {
            "intent_confidence": intent_report.confidence_score,
            "workspace_state": ws_val,
            "project_layout": repository_context.project_layout,
            "detected_manifests": workspace_context.detected_manifests,
            "test_presence": repository_context.test_presence,
        }

        return EngineeringExecutionPlan(
            plan_id=plan_id,
            mission_id=mission_id,
            project_goal=intent_report.normalized_request,
            current_project_state=ws_val,
            target_project_state=target_state,
            project_type=str(workspace_context.project_type.value if hasattr(workspace_context.project_type, 'value') else workspace_context.project_type),
            technology_stack=tech_stack,
            repository_strategy=strategy,
            required_deliverables=deliverables,
            required_disciplines=disciplines,
            high_level_milestones=milestones,
            known_constraints=intent_report.detected_constraints,
            risks=risks,
            missing_information=missing_info,
            success_criteria=success_criteria,
            evidence=evidence,
            timestamp=now_str,
        )

    def _determine_repository_strategy(
        self,
        intent: IntentReport,
        workspace: WorkspaceContext,
        repo: RepositoryContext,
    ) -> RepositoryStrategy:
        pi = intent.primary_intent.lower()
        ws_state = workspace.workspace_state.value if hasattr(workspace.workspace_state, 'value') else str(workspace.workspace_state)
        normalized = intent.normalized_request.lower()

        if pi == "fix" or "bug" in normalized or "fix" in normalized:
            return RepositoryStrategy.BUG_FIX
        elif pi == "refactor" or "refactor" in normalized or "rewrite" in normalized:
            return RepositoryStrategy.REFACTOR_EXISTING
        elif pi in ("audit", "docs") or "doc" in normalized or "readme" in normalized:
            return RepositoryStrategy.DOCUMENTATION

        if ws_state in ("EMPTY", "NEW_PROJECT"):
            return RepositoryStrategy.NEW_PROJECT

        if ws_state in ("EXISTING_PROJECT", "MONOREPO"):
            if intent.detected_features or pi in ("create", "build", "add"):
                return RepositoryStrategy.FEATURE_ADDITION
            return RepositoryStrategy.EXTEND_EXISTING

        return RepositoryStrategy.UNKNOWN

    def _detect_required_disciplines(
        self,
        intent: IntentReport,
        workspace: WorkspaceContext,
        repo: RepositoryContext,
    ) -> List[str]:
        disciplines: Set[str] = set()

        all_techs = {t.lower() for t in intent.detected_technologies}
        app_type = intent.application_type.lower()
        category = intent.project_category.lower()

        # Frontend
        if any(t in all_techs for t in ("react", "next.js", "vue", "angular", "tailwind", "shadcn")) or "web" in app_type or category in ("website", "landing page", "dashboard", "portfolio", "e-commerce", "marketplace"):
            disciplines.add("Frontend")

        # Backend
        if any(t in all_techs for t in ("node.js", "python", "fastapi", "django", "laravel", "spring", "go", "rust", ".net", "express", "nestjs", "stripe", "paypal")) or "api" in app_type or category in ("api", "sdk", "crm", "erp") or "payment" in intent.normalized_request.lower() or "checkout" in intent.normalized_request.lower():
            disciplines.add("Backend")

        # Database
        if intent.detected_database or any(t in all_techs for t in ("supabase", "appwrite", "firebase", "postgresql", "mysql", "mongodb", "redis", "sqlite")) or category in ("crm", "erp", "e-commerce", "marketplace", "dashboard"):
            disciplines.add("Database")

        # DevOps & Infrastructure
        if intent.detected_cloud or any(t in all_techs for t in ("docker", "kubernetes", "aws", "gcp", "azure", "vercel", "netlify")) or repo.infrastructure_summary:
            disciplines.add("DevOps")
            disciplines.add("Infrastructure")

        # Security
        if intent.detected_authentication or "user_authentication" in intent.detected_features or any(t in all_techs for t in ("supabase auth", "firebase auth", "auth0", "clerk", "nextauth", "oauth", "jwt")):
            disciplines.add("Security")

        # QA / Testing
        if repo.test_presence or intent.primary_intent == "test" or "testing" in " ".join(intent.detected_features).lower():
            disciplines.add("QA")

        # Documentation
        if intent.primary_intent in ("audit", "docs") or repo.documentation_files or "documentation" in " ".join(intent.detected_features).lower():
            disciplines.add("Documentation")

        # Mobile
        if any(t in all_techs for t in ("flutter", "react native", "dart", "swift", "kotlin")) or "mobile" in app_type or category == "mobile app":
            disciplines.add("Mobile")

        # AI
        if any(t in all_techs for t in ("openai", "gemini", "anthropic")) or category == "ai agent":
            disciplines.add("AI")

        # Analytics
        if "analytics" in " ".join(intent.detected_features).lower() or category in ("dashboard", "analytics"):
            disciplines.add("Analytics")

        # Automation
        if category in ("automation", "cli tool") or "automation" in app_type:
            disciplines.add("Automation")

        if not disciplines:
            disciplines.add("Software Engineering")

        return sorted(list(disciplines))

    def _plan_deliverables(
        self,
        intent: IntentReport,
        workspace: WorkspaceContext,
        repo: RepositoryContext,
        disciplines: List[str],
    ) -> List[str]:
        deliverables: Set[str] = set()

        deliverables.add("Project Configuration")

        if "Frontend" in disciplines or intent.project_category in ("Website", "Landing Page", "Dashboard", "E-commerce", "Portfolio", "CRM"):
            deliverables.add("User Interface Pages")
            deliverables.add("UI Components")

        if "Backend" in disciplines or intent.project_category in ("API", "CRM", "ERP", "SDK"):
            deliverables.add("REST API Endpoints")
            deliverables.add("Business Logic Modules")

        if "Database" in disciplines or intent.detected_database:
            deliverables.add("Database Schema & Migrations")

        if "Security" in disciplines or intent.detected_authentication:
            deliverables.add("User Authentication & Authorization")

        if "DevOps" in disciplines or "Infrastructure" in disciplines or "Docker" in intent.detected_cloud:
            deliverables.add("Containerization & Deployment Scripts")

        if "QA" in disciplines or repo.test_presence:
            deliverables.add("Automated Test Suite")

        if "Documentation" in disciplines or repo.documentation_files or intent.primary_intent in ("audit", "docs"):
            deliverables.add("Technical & Architecture Documentation")

        if "Mobile" in disciplines:
            deliverables.add("Mobile Application Bundle")

        if "AI" in disciplines:
            deliverables.add("AI Model Integration & Prompts")

        return sorted(list(deliverables))

    def _generate_milestones(
        self,
        intent: IntentReport,
        strategy: RepositoryStrategy,
        deliverables: List[str],
    ) -> List[Dict[str, Any]]:
        milestones = [
            {
                "step": 1,
                "name": "Workspace & Environment Setup",
                "objective": "Initialize workspace dependencies, project configuration, and engine boundary validation.",
                "deliverables": ["Project Configuration"],
            },
            {
                "step": 2,
                "name": "Architecture & Data Foundation",
                "objective": "Establish data models, database schemas, and API contracts.",
                "deliverables": [d for d in deliverables if "Database" in d or "API" in d or "Business" in d],
            },
            {
                "step": 3,
                "name": "Feature Implementation",
                "objective": "Develop core user interface pages, components, and application logic.",
                "deliverables": [d for d in deliverables if "UI" in d or "Pages" in d or "Mobile" in d or "AI" in d],
            },
            {
                "step": 4,
                "name": "Security & Quality Assurance",
                "objective": "Integrate authentication, authorization, and automated test suites.",
                "deliverables": [d for d in deliverables if "Authentication" in d or "Test" in d],
            },
            {
                "step": 5,
                "name": "Deployment & Release Preparation",
                "objective": "Finalize documentation, deployment scripts, containerization, and release readiness.",
                "deliverables": [d for d in deliverables if "Deployment" in d or "Documentation" in d],
            },
        ]
        return milestones

    def _assess_risks_and_missing_info(
        self,
        intent: IntentReport,
        workspace: WorkspaceContext,
        repo: RepositoryContext,
        deliverables: List[str],
    ) -> Tuple[List[str], List[str]]:
        risks: List[str] = []
        missing_info: List[str] = list(intent.unknown_items)

        if intent.confidence_score < 0.80:
            risks.append(f"Intent confidence is low ({intent.confidence_score:.2f}). Requirements may require clarification.")

        if not workspace.read_only_validation:
            risks.append("Engine Root is not verified as read-only. Workspace boundary assertion required.")

        if "Database Schema & Migrations" in deliverables and not intent.detected_database:
            risks.append("Database deliverables expected but no explicit database engine specified. Defaulting to PostgreSQL.")

        return risks, missing_info

    def _define_success_criteria(
        self,
        intent: IntentReport,
        deliverables: List[str],
    ) -> List[str]:
        criteria = [
            "Project builds and compiles without syntax or dependency errors.",
            "All planned engineering deliverables pass validation checks.",
            "Automated test suite executes with 100% pass rate.",
            "Read-only Engine Root safety boundaries are preserved throughout execution.",
        ]
        return criteria
