"""Data Contracts for Natural Language Router (Phase P6.D1)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SmartDefaults(BaseModel):
    """Immutable Smart Defaults contract automatically resolved by NaturalLanguageRouter."""

    model_config = ConfigDict(frozen=True)

    project_type: str = Field(..., description="Inferred project type (python, typescript, go, rust, java, etc.)")
    technology_stack: str = Field(..., description="Inferred tech stack (e.g. Next.js + React + Tailwind + PostgreSQL)")
    framework: str = Field(..., description="Primary web/backend framework (e.g. Next.js, FastAPI, Spring Boot)")
    database: str = Field(default="PostgreSQL", description="Primary database (PostgreSQL, SQLite, MongoDB, Redis)")
    authentication: str = Field(default="JWT / OAuth2", description="Authentication mechanism")
    deployment_target: str = Field(default="Docker Container / Cloud", description="Deployment infrastructure target")
    testing_framework: str = Field(default="pytest / Vitest", description="Testing framework")
    package_manager: str = Field(default="npm / pip", description="Package manager")
    coding_standards: str = Field(default="Standard PEP8 / ESLint", description="Coding standards")
    llm_provider: str = Field(default="oniroute-local-engine", description="LLM provider")
    mcp_tools: List[str] = Field(default_factory=lambda: ["BridgeForce", "StitchMCP", "Chrome DevTools"], description="MCP tool integrations")
    review_strategy: str = Field(default="cross-agent-5-profile-review", description="Quality Gate review strategy")
    healing_strategy: str = Field(default="automated-self-healing", description="Self-healing repair strategy")
    verification_strategy: str = Field(default="deterministic-build-test-coverage", description="Verification strategy")


class RouterExecutionResult(BaseModel):
    """Immutable result contract produced by NaturalLanguageRouter upon executing the complete pipeline."""

    model_config = ConfigDict(frozen=True)

    router_execution_id: str = Field(..., description="Unique router execution ID (nlr-xxxxxx)")
    request_text: str = Field(..., description="Raw natural language user request")
    primary_intent: str = Field(..., description="Extracted primary intent (build, create, fix, review, refactor, migrate)")
    mission_id: str = Field(..., description="Generated mission identifier")
    confidence_score: float = Field(..., description="Intent confidence score (0.0 to 1.0)")
    smart_defaults: SmartDefaults = Field(..., description="Resolved smart defaults configuration")
    execution_snapshot: Any = Field(..., description="Swarm execution snapshot (P3)")
    scaffold_report: Any = Field(..., description="Workspace scaffold report (P4.G1)")
    blueprint_report: Any = Field(..., description="Project blueprint report (P4.G2)")
    allocation_report: Any = Field(..., description="Implementation allocation report (P4.G3)")
    contract_report: Any = Field(..., description="Engineering contract report (P4.G4)")
    assembly_certification_report: Any = Field(..., description="Project assembly certification report (P4.G5)")
    engineering_results: List[Any] = Field(default_factory=list, description="Engineering worker results (P5.E1)")
    quality_reports: List[Any] = Field(default_factory=list, description="Quality Gate audit reports (P5.E2)")
    updated_results: List[Any] = Field(default_factory=list, description="Self-healing repaired results (P5.E3)")
    verifications: List[Any] = Field(default_factory=list, description="Verification results (P5.E4)")
    acceptance_reports: List[Any] = Field(default_factory=list, description="Acceptance reports (P5.E4)")
    certification_report: Any = Field(..., description="Engineering certification report (P5.E5)")
    total_files_created: int = Field(..., description="Total count of created project files")
    total_files_modified: int = Field(..., description="Total count of modified project files")
    quality_score: float = Field(..., description="Average architecture/quality score (0.0 to 10.0)")
    production_ready: bool = Field(..., description="True if complete pipeline passed validation and acceptance")
    end_to_end_latency_ms: float = Field(..., description="Total end-to-end pipeline latency in milliseconds")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
