"""Execution Skill Bundling Engine for OniRoute (Phase P2.S3).

Groups ranked skills from a RankedSkillReport into cohesive, discipline-aligned
ExecutionSkillBundles without prompt parsing, repository scanning, or AI invocation.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

import networkx as nx

from runtime.core_models import RepositoryRegistry
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan

from .models import (
    ExecutionSkillBundle,
    ExecutionSkillBundleReport,
    RankedSkill,
    RankedSkillReport,
    SkillPriority,
    SkillSelectionReport,
)


CANONICAL_DISCIPLINES: List[str] = [
    "Frontend",
    "Backend",
    "Database",
    "DevOps",
    "Security",
    "Testing",
    "Documentation",
    "AI",
    "Automation",
    "Infrastructure",
    "Analytics",
    "General Engineering",
]

PRIORITY_RANK_MAP: Dict[SkillPriority, int] = {
    SkillPriority.CRITICAL: 1,
    SkillPriority.HIGH: 2,
    SkillPriority.MEDIUM: 3,
    SkillPriority.SUPPORT: 4,
    SkillPriority.LOW: 5,
    SkillPriority.OPTIONAL: 6,
}


def classify_skill_discipline(skill: RankedSkill) -> str:
    """Classify a RankedSkill into a canonical engineering discipline."""
    cat = skill.category.lower()
    sid = skill.skill_id.lower()
    name = skill.name.lower()

    if any(k in cat or k in sid or k in name for k in ("frontend", "ui", "react", "vue", "angular", "presentation", "form", "responsive", "routing", "state-management", "tailwind", "shadcn", "css", "html", "style", "component-design", "ui-patterns")):
        return "Frontend"

    if any(k in cat or k in sid or k in name for k in ("backend", "api", "fastapi", "django", "express", "spring", "nestjs", "rest", "graphql", "microservice", "business-logic", "service-design", "resilience", "integration-patterns", "api-versioning", "background-jobs")):
        return "Backend"

    if any(k in cat or k in sid or k in name for k in ("database", "sql", "postgresql", "mysql", "mongodb", "sqlite", "orm", "prisma", "schema-design", "migration", "data-modeling")):
        return "Database"

    if any(k in cat or k in sid or k in name for k in ("devops", "deployment", "docker", "kubernetes", "ci/cd", "continuous-integration", "cloud", "aws", "gcp", "azure", "container")):
        return "DevOps"

    if any(k in cat or k in sid or k in name for k in ("security", "auth", "authentication", "authorization", "encryption", "secrets")):
        return "Security"

    if any(k in cat or k in sid or k in name for k in ("testing", "qa", "jest", "pytest", "cypress", "playwright", "test")):
        return "Testing"

    if any(k in cat or k in sid or k in name for k in ("ai", "llm", "agent", "prompt", "openai", "gemini", "anthropic", "rag", "tool-calling", "context-optimization")):
        return "AI"

    if any(k in cat or k in sid or k in name for k in ("documentation", "docs", "executive-communication", "technical-storytelling")):
        return "Documentation"

    if any(k in cat or k in sid or k in name for k in ("automation", "cli", "script")):
        return "Automation"

    if any(k in cat or k in sid or k in name for k in ("analytics", "observability", "logging", "telemetry")):
        return "Analytics"

    if any(k in cat or k in sid or k in name for k in ("infrastructure", "platform", "scalability", "vendor-neutral", "technology-evaluation")):
        return "Infrastructure"

    return "General Engineering"


class SkillBundlingEngine:
    """Engine for execution skill bundling (Phase P2.S3)."""

    def __init__(self, registry: RepositoryRegistry | None = None, resolver: Resolver | None = None):
        self.registry = registry
        self.resolver = resolver or (Resolver(registry) if registry else None)

    def bundle_skills(
        self,
        ranked_report: RankedSkillReport,
        plan: EngineeringExecutionPlan | None = None,
        selection_report: SkillSelectionReport | None = None,
    ) -> ExecutionSkillBundleReport:
        """Group ranked skills into execution-ready ExecutionSkillBundles."""
        hash_hex = hashlib.sha256(
            f"{ranked_report.report_id}:{ranked_report.execution_plan_id}".encode("utf-8")
        ).hexdigest()[:6]
        report_id = f"esbr-{hash_hex}"
        now_str = datetime.now(timezone.utc).isoformat()

        plan_id = ranked_report.execution_plan_id
        plan_deliverables = plan.required_deliverables if plan else []
        plan_constraints = plan.known_constraints if plan else []

        # 1. Group Ranked Skills by Discipline
        discipline_skills: Dict[str, List[RankedSkill]] = {}
        skill_to_bundle_id: Dict[str, str] = {}
        discipline_bundle_id_map: Dict[str, str] = {}

        for skill in ranked_report.ranked_skills:
            disc = classify_skill_discipline(skill)
            if disc not in discipline_skills:
                discipline_skills[disc] = []
                disc_slug = disc.lower().replace(" ", "-")
                discipline_bundle_id_map[disc] = f"esb-{disc_slug}-{hash_hex}"

            discipline_skills[disc].append(skill)
            skill_to_bundle_id[skill.skill_id] = discipline_bundle_id_map[disc]

        # 2. Build Bundles
        bundles: List[ExecutionSkillBundle] = []
        all_skill_ids = set()

        for disc, skills in discipline_skills.items():
            b_id = discipline_bundle_id_map[disc]
            all_k_refs: Set[str] = set()
            all_p_refs: Set[str] = set()
            all_w_refs: Set[str] = set()
            reg_refs: List[str] = []
            highest_prio = SkillPriority.OPTIONAL

            for s in skills:
                all_skill_ids.add(s.skill_id)
                reg_refs.append(s.skill_id)
                all_k_refs.update(s.knowledge_references)
                all_p_refs.update(s.package_references)
                all_w_refs.update(s.workflow_references)

                # Determine highest priority in bundle
                if PRIORITY_RANK_MAP[s.priority] < PRIORITY_RANK_MAP[highest_prio]:
                    highest_prio = s.priority

            # Filter relevant deliverables and constraints for this discipline
            matching_deliverables = [
                d for d in plan_deliverables
                if any(part in d.lower() for part in (disc.lower(), *[s.name.lower() for s in skills]))
            ]
            if not matching_deliverables:
                matching_deliverables = [f"{disc} Engineering Deliverables"]

            disc_constraints = [
                c for c in plan_constraints
                if any(part in c.lower() for part in (disc.lower(), *[s.name.lower() for s in skills]))
            ]

            # Calculate bundle coverage
            avg_skill_score = sum(s.score for s in skills) / len(skills) if skills else 0.0
            bundle_cov = round(min(100.0, avg_skill_score), 2)

            bundle_evidence = {
                "discipline": disc,
                "skill_count": len(skills),
                "official_skills_count": sum(1 for s in skills if s.is_official),
                "highest_priority": highest_prio.value,
            }

            bundles.append(
                ExecutionSkillBundle(
                    bundle_id=b_id,
                    name=f"{disc} Engineering Bundle",
                    engineering_discipline=disc,
                    ranked_skills=skills,
                    knowledge_references=sorted(list(all_k_refs)),
                    package_references=sorted(list(all_p_refs)),
                    workflow_references=sorted(list(all_w_refs)),
                    registry_references=reg_refs,
                    execution_constraints=disc_constraints,
                    expected_deliverables=matching_deliverables,
                    dependency_bundles=[],  # Filled in step 3
                    priority=highest_prio,
                    coverage=bundle_cov,
                    evidence=bundle_evidence,
                    timestamp=now_str,
                )
            )

        # 3. Inter-Bundle Dependency Resolution
        bundle_map = {b.bundle_id: b for b in bundles}
        bundle_deps_map: Dict[str, Set[str]] = {b.bundle_id: set() for b in bundles}

        for b in bundles:
            for skill in b.ranked_skills:
                for dep_sid in skill.dependencies:
                    if dep_sid in skill_to_bundle_id:
                        prereq_bundle_id = skill_to_bundle_id[dep_sid]
                        if prereq_bundle_id != b.bundle_id:
                            bundle_deps_map[b.bundle_id].add(prereq_bundle_id)

        # Reconstruct updated bundles with populated dependency_bundles
        updated_bundles: List[ExecutionSkillBundle] = []
        for b in bundles:
            deps_list = sorted(list(bundle_deps_map[b.bundle_id]))
            updated_bundles.append(
                ExecutionSkillBundle(
                    bundle_id=b.bundle_id,
                    name=b.name,
                    engineering_discipline=b.engineering_discipline,
                    ranked_skills=b.ranked_skills,
                    knowledge_references=b.knowledge_references,
                    package_references=b.package_references,
                    workflow_references=b.workflow_references,
                    registry_references=b.registry_references,
                    execution_constraints=b.execution_constraints,
                    expected_deliverables=b.expected_deliverables,
                    dependency_bundles=deps_list,
                    priority=b.priority,
                    coverage=b.coverage,
                    evidence=b.evidence,
                    timestamp=b.timestamp,
                )
            )

        # 4. Topological Bundle Execution Ordering
        dag = nx.DiGraph()
        for b in updated_bundles:
            dag.add_node(b.bundle_id)

        for b_id, prereq_ids in bundle_deps_map.items():
            for p_id in prereq_ids:
                dag.add_edge(p_id, b_id)

        if nx.is_directed_acyclic_graph(dag):
            bundle_ordering = list(nx.topological_sort(dag))
        else:
            # Fallback sort by priority rank if cyclic
            bundle_ordering = [
                b.bundle_id for b in sorted(updated_bundles, key=lambda x: (PRIORITY_RANK_MAP[x.priority], x.bundle_id))
            ]

        # 5. Validation Check
        total_bundled_skills = sum(len(b.ranked_skills) for b in updated_bundles)
        assert total_bundled_skills == len(ranked_report.ranked_skills), (
            f"Orphan or duplicate skill mismatch: bundled {total_bundled_skills} skills, "
            f"expected {len(ranked_report.ranked_skills)}"
        )
        assert len(all_skill_ids) == len(ranked_report.ranked_skills), "Duplicate skill detected across bundles"

        # 6. Final Report Assembly
        bundle_deps_dict = {b.bundle_id: b.dependency_bundles for b in updated_bundles}
        bundling_confidence = min(
            1.0,
            round(
                (sum(b.coverage for b in updated_bundles) / (len(updated_bundles) * 100.0)) * 0.5
                + (ranked_report.coverage.coverage_percent / 200.0)
                + 0.25,
                2,
            ),
        ) if updated_bundles else 0.5

        evidence = {
            "ranked_report_id": ranked_report.report_id,
            "selection_report_id": ranked_report.selection_report_id,
            "execution_plan_id": plan_id,
            "total_bundles": len(updated_bundles),
            "total_bundled_skills": total_bundled_skills,
            "disciplines": [b.engineering_discipline for b in updated_bundles],
            "validation": {
                "no_orphan_skills": True,
                "no_duplicate_skills": True,
                "bundle_dependency_integrity": nx.is_directed_acyclic_graph(dag),
            },
        }

        return ExecutionSkillBundleReport(
            report_id=report_id,
            execution_plan_id=plan_id,
            ranked_report_id=ranked_report.report_id,
            selection_report_id=ranked_report.selection_report_id,
            bundles=updated_bundles,
            bundle_ordering=bundle_ordering,
            bundle_dependencies=bundle_deps_dict,
            coverage=ranked_report.coverage,
            confidence=bundling_confidence,
            evidence=evidence,
            timestamp=now_str,
        )
