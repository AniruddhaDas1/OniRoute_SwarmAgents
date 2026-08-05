"""Deterministic Capability Resolver for OniRoute Organization Builder (ACR-005 Phase S2).

Transforms a frozen ExecutionRequest into a validated CapabilityReport by analyzing mission
requirements, workspace context, and repository registries (Agent, Skill, Knowledge, Package, Workflow).

Performs NO agent allocation, NO role assignment, NO workflow execution, and NO AI invocation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.loader import RepositoryLoader
from runtime.mission.models import ExecutionRequest
from runtime.resolver import Resolver

from .capability import (
    Capability,
    CapabilityConstraint,
    CapabilityEvidence,
    CapabilityGroup,
    CapabilityPriority,
    CapabilityReport,
    CapabilityRequirement,
)
from .capability_validator import CapabilityValidator
from .contracts import CapabilityAnalyzerContract


class CapabilityResolver(CapabilityAnalyzerContract):
    """Deterministic Capability Resolver engine."""

    def __init__(self, repository_root: Path | str | None = None) -> None:
        self.repository_root = Path(repository_root).resolve() if repository_root else Path.cwd()
        self._loader: RepositoryLoader | None = None
        self._resolver: Resolver | None = None

    def _get_resolver(self) -> Resolver:
        if self._resolver is None:
            self._loader = RepositoryLoader(self.repository_root)
            registry = self._loader.load()
            self._resolver = Resolver(registry)
        return self._resolver

    def analyze_capabilities(self, execution_request: ExecutionRequest) -> CapabilityReport:
        """Alias for resolve_capabilities satisfying CapabilityAnalyzerContract."""
        return self.resolve_capabilities(execution_request)

    def resolve_capabilities(
        self, execution_request: ExecutionRequest, repository_root: Path | str | None = None
    ) -> CapabilityReport:
        """Transform an ExecutionRequest into a validated CapabilityReport."""
        root = Path(repository_root).resolve() if repository_root else self.repository_root
        resolver = Resolver(RepositoryLoader(root).load()) if repository_root else self._get_resolver()

        mission = execution_request.mission
        reqs = mission.requirements
        constraints = mission.constraints
        context = mission.context

        # Data structures to collect
        resolved_caps: list[Capability] = []
        requirements_list: list[CapabilityRequirement] = []
        constraints_list: list[CapabilityConstraint] = []
        evidence_list: list[CapabilityEvidence] = []
        groups_list: list[CapabilityGroup] = []

        # Track created cap IDs to avoid duplicates
        seen_cap_ids: set[str] = set()

        # Build base constraints from mission constraints
        base_constraint = CapabilityConstraint(
            constraint_id=f"cst-mission-{mission.mission_id}",
            capability_id="global",
            local_only=constraints.local_only,
            allowed_providers=constraints.allowed_providers,
            max_duration_seconds=constraints.timeout_seconds,
            custom_rules={"max_budget_usd": constraints.max_budget_usd},
        )
        constraints_list.append(base_constraint)

        # Domain mapping rules based on intent, primary goal, and requirements
        search_terms: list[tuple[str, str, str]] = []  # (text, source, default_priority)

        # 1. Primary goal
        search_terms.append((reqs.primary_goal, "primary_goal", "CRITICAL"))

        # 2. Functional requirements
        for freq in reqs.functional_requirements:
            search_terms.append((freq, "functional_requirement", "HIGH"))

        # 3. Non-functional requirements
        for nfreq in reqs.non_functional_requirements:
            search_terms.append((nfreq, "non_functional_requirement", "MEDIUM"))

        # 4. Mandatory baseline engineering capabilities
        baseline_domains = [
            ("cap-architecture-design", "Architecture Design & Systems Decomposition", "architecture", "Core architectural specification", CapabilityPriority.CRITICAL),
            ("cap-documentation-spec", "Technical Documentation & Deliverables", "documentation", "API and technical docs generation", CapabilityPriority.MEDIUM),
        ]

        for cap_id, cap_name, domain, desc, priority in baseline_domains:
            if cap_id not in seen_cap_ids:
                seen_cap_ids.add(cap_id)
                # Find matching skills & knowledge from registry
                skills = [s.id for s in resolver.search_by_category(domain)] or [s.id for s in resolver.search(domain)]
                know = [k.id for k in resolver.registry.knowledge_sources.values() if domain in str(k.data.get("domain", "")).lower()]

                cap = Capability(
                    capability_id=cap_id,
                    name=cap_name,
                    domain=domain,
                    description=desc,
                    priority=priority,
                    confidence=1.0,
                    required_skills=skills[:5],
                    required_knowledge=know[:5],
                )
                resolved_caps.append(cap)

                # Add requirement
                req_obj = CapabilityRequirement(
                    requirement_id=f"capreq-{cap_id}",
                    mission_id=mission.mission_id,
                    capability_id=cap_id,
                    priority=priority,
                    source_requirement="Baseline engineering requirement",
                    constraints=[base_constraint],
                )
                requirements_list.append(req_obj)

                # Add evidence
                ev_obj = CapabilityEvidence(
                    evidence_id=f"ev-{cap_id}",
                    capability_id=cap_id,
                    source_stage="capability_resolution",
                    asserted_by="CapabilityResolver",
                    provenance_details={"rule": "baseline_engineering", "domain": domain},
                )
                evidence_list.append(ev_obj)

        # 5. Extract domain capabilities from search terms
        domain_keywords = {
            "frontend": ["frontend", "ui", "ux", "react", "page", "web", "html", "css", "component", "view", "presentation"],
            "backend": ["backend", "api", "rest", "service", "fastapi", "python", "endpoint", "server", "logic"],
            "database": ["database", "db", "sql", "postgres", "data", "query", "schema", "store", "table"],
            "security": ["security", "auth", "audit", "permission", "crypto", "authz", "jwt", "login", "vulnerability"],
            "testing": ["test", "testing", "unit", "integration", "assert", "coverage", "pytest"],
            "qa": ["qa", "quality", "verification", "compliance", "validation"],
            "devops": ["devops", "ci", "cd", "docker", "pipeline", "deploy", "container"],
            "infrastructure": ["infrastructure", "cloud", "aws", "gcp", "iac", "terraform", "platform"],
            "research": ["research", "benchmark", "analysis", "study", "evaluation"],
            "ai": ["ai", "ml", "prompt", "llm", "model", "rag", "agent"],
            "mobile": ["mobile", "ios", "android", "swift", "kotlin", "app"],
            "analytics": ["analytics", "metrics", "telemetry", "tracking", "log"],
            "automation": ["automation", "script", "cron", "workflow", "trigger"],
        }

        for text, source, default_priority_str in search_terms:
            text_lower = text.lower()
            matched_domains: list[str] = []

            for dom, keywords in domain_keywords.items():
                if any(kw in text_lower for kw in keywords):
                    matched_domains.append(dom)

            if not matched_domains:
                # Extensible custom or general domain fallback
                matched_domains.append(reqs.intent_category if reqs.intent_category != "general" else "backend")

            for dom in matched_domains:
                cap_id = f"cap-{dom}-{len(resolved_caps) + 1:02d}"
                if cap_id in seen_cap_ids:
                    continue
                seen_cap_ids.add(cap_id)

                prio = CapabilityPriority(default_priority_str.lower())
                skills = [s.id for s in resolver.search(dom)]
                know = [k.id for k in resolver.registry.knowledge_sources.values() if dom in str(k.data.get("domain", "")).lower()]
                packages = [p.id for p in resolver.registry.packages.values() if dom in str(p.data.get("name", "")).lower()]
                workflows = [w.id for w in resolver.registry.workflows.values() if dom in str(w.data.get("category", "")).lower()]

                # Setup capability dependencies
                dependencies: list[str] = []
                if dom == "frontend":
                    dependencies.extend([c.capability_id for c in resolved_caps if c.domain in ("architecture", "backend")])
                elif dom == "backend":
                    dependencies.extend([c.capability_id for c in resolved_caps if c.domain in ("architecture", "database")])
                elif dom in ("security", "testing", "qa"):
                    dependencies.extend([c.capability_id for c in resolved_caps if c.domain in ("backend", "frontend")])

                cap = Capability(
                    capability_id=cap_id,
                    name=f"{dom.capitalize()} Capability ({text[:30]})",
                    domain=dom,
                    description=f"Capability resolved for requirement: '{text}'",
                    priority=prio,
                    confidence=0.95,
                    dependencies=dependencies,
                    required_skills=skills[:5],
                    required_knowledge=know[:5],
                    required_packages=packages[:5],
                    required_workflows=workflows[:5],
                )
                resolved_caps.append(cap)

                # Requirement
                req_obj = CapabilityRequirement(
                    requirement_id=f"capreq-{cap_id}",
                    mission_id=mission.mission_id,
                    capability_id=cap_id,
                    priority=prio,
                    source_requirement=text,
                    constraints=[base_constraint],
                )
                requirements_list.append(req_obj)

                # Evidence
                ev_obj = CapabilityEvidence(
                    evidence_id=f"ev-{cap_id}",
                    capability_id=cap_id,
                    source_stage="capability_resolution",
                    asserted_by="CapabilityResolver",
                    provenance_details={
                        "source_requirement": text,
                        "source_type": source,
                        "matched_domain": dom,
                        "registry_matches_count": len(skills) + len(know) + len(packages),
                    },
                )
                evidence_list.append(ev_obj)

        # 6. Group capabilities by domain into CapabilityGroups
        domain_groups: dict[str, list[Capability]] = {}
        for cap in resolved_caps:
            domain_groups.setdefault(cap.domain, []).append(cap)

        for dom, caps in domain_groups.items():
            grp = CapabilityGroup(
                group_id=f"capgrp-{dom}",
                name=f"{dom.capitalize()} Capability Group",
                domain=dom,
                description=f"Group of {len(caps)} capabilities for domain '{dom}'",
                capabilities=caps,
            )
            groups_list.append(grp)

        # 7. Validate capability set
        validator = CapabilityValidator()
        coverage_summary, readiness_summary = validator.validate_capability_set(
            capabilities=resolved_caps,
            requirements=requirements_list,
            constraints=constraints_list,
            evidence_list=evidence_list,
        )

        # 8. Build summaries
        priority_map = {cap.capability_id: cap.priority.value for cap in resolved_caps}
        dependency_map = {cap.capability_id: cap.dependencies for cap in resolved_caps}

        return CapabilityReport(
            report_id=f"rep-cap-{mission.mission_id}",
            mission_id=mission.mission_id,
            total_capabilities_analyzed=len(resolved_caps),
            capabilities=resolved_caps,
            groups=groups_list,
            requirements=requirements_list,
            evidence=evidence_list,
            capability_priorities=priority_map,
            capability_constraints=constraints_list,
            dependency_summary=dependency_map,
            coverage_summary=coverage_summary,
            readiness=readiness_summary,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
