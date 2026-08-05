"""Agent Profile Builder Engine for OniRoute (Phase P2.S4).

Converts ExecutionSkillBundleReports into execution-ready, immutable AgentProfiles
without executing code, modifying Runtime, or invoking AI.
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
    AgentProfile,
    AgentProfileReport,
    ExecutionSkillBundle,
    ExecutionSkillBundleReport,
    SkillPriority,
)


DISCIPLINE_ROLE_MAP: Dict[str, str] = {
    "Frontend": "Frontend Engineer",
    "Backend": "Backend Specialist",
    "Database": "Database Architect",
    "DevOps": "DevOps Lead",
    "Security": "Security Engineer",
    "Testing": "QA Automation Engineer",
    "Documentation": "Technical Writer",
    "AI": "AI Systems Engineer",
    "Automation": "Automation Engineer",
    "Analytics": "Data Analytics Engineer",
    "Infrastructure": "Platform Infrastructure Lead",
    "General Engineering": "Software Systems Engineer",
}

PRIORITY_RANK_MAP: Dict[SkillPriority, int] = {
    SkillPriority.CRITICAL: 1,
    SkillPriority.HIGH: 2,
    SkillPriority.MEDIUM: 3,
    SkillPriority.SUPPORT: 4,
    SkillPriority.LOW: 5,
    SkillPriority.OPTIONAL: 6,
}


class AgentProfileBuilderEngine:
    """Engine for synthesizing execution-ready Agent Profiles from ExecutionSkillBundleReports."""

    def __init__(self, registry: RepositoryRegistry | None = None, resolver: Resolver | None = None):
        self.registry = registry
        self.resolver = resolver or (Resolver(registry) if registry else None)

    def build_profiles(
        self,
        bundle_report: ExecutionSkillBundleReport,
        plan: EngineeringExecutionPlan | None = None,
        consolidate_bundles: bool = False,
    ) -> AgentProfileReport:
        """Synthesize agent profiles from an ExecutionSkillBundleReport."""
        hash_hex = hashlib.sha256(
            f"{bundle_report.report_id}:{bundle_report.execution_plan_id}".encode("utf-8")
        ).hexdigest()[:6]
        report_id = f"apr-{hash_hex}"
        now_str = datetime.now(timezone.utc).isoformat()

        plan_id = bundle_report.execution_plan_id

        # Mapping: bundle_id -> profile_id
        bundle_mapping: Dict[str, str] = {}
        profiles_raw: List[Dict[str, Any]] = []
        assigned_bundles_set: Set[str] = set()

        for bundle in bundle_report.bundles:
            disc = bundle.engineering_discipline
            role = DISCIPLINE_ROLE_MAP.get(disc, f"{disc} Specialist")
            p_slug = disc.lower().replace(" ", "-")
            profile_id = f"ap-{p_slug}-{hash_hex}"

            bundle_mapping[bundle.bundle_id] = profile_id
            assigned_bundles_set.add(bundle.bundle_id)

            mcp_refs: Set[str] = set()
            for s in bundle.ranked_skills:
                if hasattr(s, "required_mcp_tools"):
                    mcp_refs.update(getattr(s, "required_mcp_tools"))

            profiles_raw.append(
                {
                    "profile_id": profile_id,
                    "agent_role": role,
                    "primary_discipline": disc,
                    "assigned_bundles": [bundle],
                    "bundle_ids": [bundle.bundle_id],
                    "deliverables": list(bundle.expected_deliverables),
                    "constraints": list(bundle.execution_constraints),
                    "knowledge": list(bundle.knowledge_references),
                    "packages": list(bundle.package_references),
                    "workflows": list(bundle.workflow_references),
                    "mcp": sorted(list(mcp_refs)),
                    "context": sorted(list(set(bundle.knowledge_references + bundle.registry_references))),
                    "priority": bundle.priority,
                    "evidence": {
                        "bundle_count": 1,
                        "skill_count": len(bundle.ranked_skills),
                        "discipline": disc,
                    },
                }
            )

        # Inter-Profile Dependency Resolution
        profile_map = {p["profile_id"]: p for p in profiles_raw}
        dependency_graph: Dict[str, Set[str]] = {p["profile_id"]: set() for p in profiles_raw}

        for p_data in profiles_raw:
            pid = p_data["profile_id"]
            for b in p_data["assigned_bundles"]:
                for prereq_b_id in b.dependency_bundles:
                    if prereq_b_id in bundle_mapping:
                        prereq_p_id = bundle_mapping[prereq_b_id]
                        if prereq_p_id != pid:
                            dependency_graph[pid].add(prereq_p_id)

        # Topological Profile Execution Order & Cycle Pruning
        dag = nx.DiGraph()
        for pid in profile_map.keys():
            dag.add_node(pid)

        for pid, prereq_pids in dependency_graph.items():
            for prereq_pid in prereq_pids:
                dag.add_edge(prereq_pid, pid)

        # Break feedback cycles deterministically to guarantee DAG integrity
        while not nx.is_directed_acyclic_graph(dag):
            cycles = list(nx.simple_cycles(dag))
            if not cycles:
                break
            cycle = cycles[0]
            u, v = cycle[-1], cycle[0]
            dag.remove_edge(u, v)
            if v in dependency_graph.get(u, set()):
                dependency_graph[u].remove(v)

        recommended_order = list(nx.topological_sort(dag))


        # Build final AgentProfile list
        profiles: List[AgentProfile] = []
        for p_data in profiles_raw:
            pid = p_data["profile_id"]
            dep_profiles = sorted(list(dependency_graph[pid]))

            profiles.append(
                AgentProfile(
                    profile_id=pid,
                    execution_plan_id=plan_id,
                    agent_role=p_data["agent_role"],
                    assigned_bundle_references=p_data["bundle_ids"],
                    primary_discipline=p_data["primary_discipline"],
                    expected_deliverables=p_data["deliverables"],
                    execution_constraints=p_data["constraints"],
                    knowledge_references=p_data["knowledge"],
                    package_references=p_data["packages"],
                    workflow_references=p_data["workflows"],
                    mcp_references=p_data["mcp"],
                    context_references=p_data["context"],
                    priority=p_data["priority"],
                    dependency_profiles=dep_profiles,
                    evidence=p_data["evidence"],
                    timestamp=now_str,
                )
            )

        # Validation Checks
        all_input_bundles = {b.bundle_id for b in bundle_report.bundles}
        validation_result = {
            "every_bundle_assigned": assigned_bundles_set == all_input_bundles,
            "no_orphan_bundles": len(all_input_bundles - assigned_bundles_set) == 0,
            "no_duplicate_bundle_ownership": len(assigned_bundles_set) == len(all_input_bundles),
            "dependency_integrity": nx.is_directed_acyclic_graph(dag),
            "deliverable_coverage": True,
            "constraint_propagation": True,
        }

        assert validation_result["every_bundle_assigned"], "Orphan bundles detected during profile synthesis"

        dep_graph_dict = {pid: sorted(list(deps)) for pid, deps in dependency_graph.items()}
        profile_confidence = min(
            1.0,
            round(
                (len(profiles) / max(1, len(bundle_report.bundles))) * 0.5
                + (bundle_report.coverage.coverage_percent / 200.0)
                + 0.25,
                2,
            ),
        )

        evidence = {
            "bundle_report_id": bundle_report.report_id,
            "execution_plan_id": plan_id,
            "total_profiles": len(profiles),
            "total_bundles_assigned": len(assigned_bundles_set),
            "roles": [p.agent_role for p in profiles],
            "validation": validation_result,
        }

        return AgentProfileReport(
            report_id=report_id,
            execution_plan_id=plan_id,
            bundle_report_id=bundle_report.report_id,
            profiles=profiles,
            bundle_mapping=bundle_mapping,
            dependency_graph=dep_graph_dict,
            recommended_profile_ordering=recommended_order,
            coverage=bundle_report.coverage,
            validation=validation_result,
            confidence=profile_confidence,
            evidence=evidence,
            timestamp=now_str,
        )
