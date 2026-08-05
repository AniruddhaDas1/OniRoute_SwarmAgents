"""Skill Ranking Engine for OniRoute (Phase P2.S2).

Determines which discovered skills are most valuable for an EngineeringExecutionPlan
using a deterministic, multi-factor scoring model and graph-based dependency ordering.
Operates without prompt parsing, repository scanning, or AI invocation.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

import networkx as nx

from runtime.core_models import MetadataRecord, RepositoryRegistry
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan, RepositoryStrategy

from .models import (
    DependencyChain,
    DiscoveredSkill,
    RankedSkill,
    RankedSkillReport,
    SkillPriority,
    SkillSelectionReport,
)


class SkillRankingEngine:
    """Engine for deterministic skill ranking (Phase P2.S2).

    Calculates weighted scores across 7 deterministic scoring factors, assigns priority
    levels, evaluates graph dependency chains, and produces an immutable RankedSkillReport.
    """

    def __init__(self, registry: RepositoryRegistry | None = None, resolver: Resolver | None = None):
        self.registry = registry
        self.resolver = resolver or (Resolver(registry) if registry else None)

    def rank_skills(
        self,
        selection_report: SkillSelectionReport,
        plan: EngineeringExecutionPlan | None = None,
    ) -> RankedSkillReport:
        """Rank skills from a SkillSelectionReport deterministically."""
        hash_hex = hashlib.sha256(
            f"{selection_report.report_id}:{selection_report.execution_plan_id}".encode("utf-8")
        ).hexdigest()[:6]
        report_id = f"rsr-{hash_hex}"
        now_str = datetime.now(timezone.utc).isoformat()

        # Extract target context from plan (if provided) or selection report evidence
        if plan is not None:
            disciplines = {d.lower() for d in plan.required_disciplines}
            deliverables = {d.lower() for d in plan.required_deliverables}
            tech_stack = {t.lower() for t in plan.technology_stack}
            constraints = {c.lower() for c in plan.known_constraints}
            strategy_val = (
                plan.repository_strategy.value
                if hasattr(plan.repository_strategy, "value")
                else str(plan.repository_strategy)
            )
            plan_id = plan.plan_id
        else:
            evidence = selection_report.evidence or {}
            disciplines = {s.lower() for s in selection_report.coverage.required_skills}
            deliverables = set()
            tech_stack = set()
            constraints = set()
            strategy_val = str(evidence.get("repository_strategy", "FEATURE_ADDITION"))
            plan_id = selection_report.execution_plan_id

        discovered_skills = selection_report.discovered_skills
        discovered_ids = {s.skill_id for s in discovered_skills}

        # 1. Dependency and Relationship Analysis
        dependency_map: Dict[str, Set[str]] = {s.skill_id: set() for s in discovered_skills}
        workflow_refs_map: Dict[str, Set[str]] = {s.skill_id: set() for s in discovered_skills}
        is_official_map: Dict[str, bool] = {}

        for ds in discovered_skills:
            sid = ds.skill_id
            rec = self.registry.skills.get(sid) if self.registry else None
            data = rec.data if rec else {}

            # Official vs Community determination
            authorship = str(data.get("authorship", "")).lower()
            is_official = (
                authorship == "official"
                or data.get("official") is True
                or sid.startswith("official.")
                or "/official/" in str(ds.path).lower()
                or (rec is not None and "official" in str(rec.path).lower())
            )
            is_official_map[sid] = is_official

            # Explicit prerequisites / skill dependencies
            raw_deps = data.get("dependencies") or data.get("prerequisites") or data.get("compatible_skills") or []
            if isinstance(raw_deps, str):
                raw_deps = [raw_deps]
            for dep in raw_deps:
                dep_str = str(dep)
                if dep_str in discovered_ids and dep_str != sid:
                    dependency_map[sid].add(dep_str)

            # Check resolver relationships if present
            if self.resolver:
                rel_skills = self.resolver.related(sid, "related_skill") + self.resolver.related(sid, "dependency")
                for rs in rel_skills:
                    if rs.id in discovered_ids and rs.id != sid:
                        dependency_map[sid].add(rs.id)

                rel_wfs = self.resolver.related(sid, "compatible_workflow")
                for rw in rel_wfs:
                    workflow_refs_map[sid].add(rw.id)

            # Workflow references in raw data
            wfs = data.get("workflows") or data.get("compatible_workflows") or []
            if isinstance(wfs, str):
                wfs = [wfs]
            for w in wfs:
                workflow_refs_map[sid].add(str(w))

        # Count dependents (how many skills depend on skill X)
        dependents_map: Dict[str, Set[str]] = {s.skill_id: set() for s in discovered_skills}
        for sid, prereqs in dependency_map.items():
            for p in prereqs:
                if p in dependents_map:
                    dependents_map[p].add(sid)

        # 2. Multi-Factor Scoring
        scored_skills: List[Tuple[DiscoveredSkill, float, Dict[str, float], str]] = []

        for ds in discovered_skills:
            sid = ds.skill_id
            rec = self.registry.skills.get(sid) if self.registry else None
            data = rec.data if rec else {}
            cat = ds.category.lower()
            tags = {t.lower() for t in ds.tags}
            name = ds.name.lower()

            # Factor 1: Execution Priority (Max 15.0)
            if any(k in cat or k in sid for k in ("foundation", "platform", "architecture", "engineering")):
                exec_priority_score = 15.0
            elif any(k in cat or k in sid for k in ("framework", "language", "database", "security")):
                exec_priority_score = 12.0
            elif any(k in cat or k in sid for k in ("testing", "deployment", "ai")):
                exec_priority_score = 10.0
            else:
                exec_priority_score = 8.0

            # Factor 2: Discipline Match (Max 20.0)
            if any(d in cat or any(d in t for t in tags) or d in sid for d in disciplines):
                discipline_score = 20.0
            elif "software engineering" in disciplines or "foundation" in cat:
                discipline_score = 15.0
            else:
                discipline_score = 8.0

            # Factor 3: Deliverable Match (Max 15.0)
            if deliverables and any(any(deliv_part in sid or deliv_part in name or any(deliv_part in t for t in tags) for deliv_part in d.split()) for d in deliverables):
                deliverable_score = 15.0
            elif deliverables and any(d in cat for d in deliverables):
                deliverable_score = 10.0
            else:
                deliverable_score = 5.0

            # Factor 4: Technology Match (Max 15.0)
            if tech_stack and any(t in sid or t in name or t in tags for t in tech_stack):
                tech_score = 15.0
            elif tech_stack and any(t in cat for t in tech_stack):
                tech_score = 10.0
            else:
                tech_score = 5.0

            # Factor 5: Dependency Weight (Max 15.0)
            num_dependents = len(dependents_map[sid])
            if num_dependents >= 2:
                dep_weight_score = 15.0
            elif num_dependents == 1:
                dep_weight_score = 10.0
            else:
                dep_weight_score = 5.0

            # Factor 6: Registry Trust (Max 10.0)
            trust_score = 10.0 if is_official_map[sid] else 6.0

            # Factor 7: Skill Completeness (Max 10.0)
            k_complete = 3.5 if (not ds.required_knowledge or (self.registry and all(k in self.registry.knowledge_sources for k in ds.required_knowledge))) else 2.0
            p_complete = 3.5 if (not ds.required_packages or (self.registry and all(p in self.registry.packages for p in ds.required_packages))) else 2.0
            w_complete = 3.0 if len(workflow_refs_map[sid]) > 0 else 1.5
            completeness_score = round(k_complete + p_complete + w_complete, 2)

            total_score = min(
                100.0,
                round(
                    exec_priority_score
                    + discipline_score
                    + deliverable_score
                    + tech_score
                    + dep_weight_score
                    + trust_score
                    + completeness_score,
                    2,
                ),
            )

            score_breakdown = {
                "execution_priority": exec_priority_score,
                "discipline_match": discipline_score,
                "deliverable_match": deliverable_score,
                "technology_match": tech_score,
                "dependency_weight": dep_weight_score,
                "registry_trust": trust_score,
                "skill_completeness": completeness_score,
            }

            reason_parts = []
            if discipline_score >= 15.0:
                reason_parts.append("High discipline alignment")
            if tech_score >= 10.0:
                reason_parts.append("Matched technology stack")
            if dep_weight_score >= 10.0:
                reason_parts.append(f"Prerequisite for {num_dependents} dependent skills")
            if trust_score == 10.0:
                reason_parts.append("Official registry skill")

            ranking_reason = "; ".join(reason_parts) if reason_parts else "Discovered skill requirement match"

            scored_skills.append((ds, total_score, score_breakdown, ranking_reason))

        # 3. Priority Level Assignment & Ranking Sort
        priority_rank_map = {
            SkillPriority.CRITICAL: 1,
            SkillPriority.HIGH: 2,
            SkillPriority.MEDIUM: 3,
            SkillPriority.SUPPORT: 4,
            SkillPriority.LOW: 5,
            SkillPriority.OPTIONAL: 6,
        }

        unranked_skills: List[Tuple[SkillPriority, float, DiscoveredSkill, Dict[str, float], str]] = []

        for ds, score, breakdown, reason in scored_skills:
            sid = ds.skill_id
            cat = ds.category.lower()
            num_deps = len(dependents_map[sid])

            if score >= 85.0 or "foundation" in cat or "platform" in cat:
                prio = SkillPriority.CRITICAL
            elif score >= 70.0 or (breakdown["technology_match"] >= 10.0 and breakdown["discipline_match"] >= 15.0):
                prio = SkillPriority.HIGH
            elif num_deps >= 1 and score < 70.0:
                prio = SkillPriority.SUPPORT
            elif score >= 55.0:
                prio = SkillPriority.MEDIUM
            elif score >= 40.0:
                prio = SkillPriority.LOW
            else:
                prio = SkillPriority.OPTIONAL

            unranked_skills.append((prio, score, ds, breakdown, reason))

        # Sort deterministically by: priority_rank ascending, total_score descending, skill_id ascending
        unranked_skills.sort(key=lambda x: (priority_rank_map[x[0]], -x[1], x[2].skill_id))

        # 4. Dependency Chains and Topological Ordering
        dag = nx.DiGraph()
        for ds in discovered_skills:
            dag.add_node(ds.skill_id)

        for sid, prereqs in dependency_map.items():
            for p in prereqs:
                dag.add_edge(p, sid)

        # Recommended execution order via topological sort or rank fallback
        if nx.is_directed_acyclic_graph(dag):
            topo_layers = list(nx.topological_sort(dag))
            recommended_order = topo_layers
        else:
            # Fallback if graph contains cycles: sort strictly by rank
            recommended_order = [item[2].skill_id for item in unranked_skills]

        dependency_chains: List[DependencyChain] = []
        blocking_skills: List[str] = []
        independent_skills: List[str] = []

        for prio, score, ds, breakdown, reason in unranked_skills:
            sid = ds.skill_id
            prereqs = sorted(list(dependency_map[sid]))
            blocking = sorted(list(dependents_map[sid]))
            is_blocking = len(blocking) > 0
            is_independent = len(prereqs) == 0 and len(blocking) == 0

            if is_blocking:
                blocking_skills.append(sid)
            if is_independent:
                independent_skills.append(sid)

            dependency_chains.append(
                DependencyChain(
                    skill_id=sid,
                    prerequisites=prereqs,
                    blocking=blocking,
                    is_blocking=is_blocking,
                    is_independent=is_independent,
                )
            )

        # Construct final RankedSkill list
        ranked_skills: List[RankedSkill] = []
        priority_groups: Dict[str, List[str]] = {p.value: [] for p in SkillPriority}
        all_k_refs: Set[str] = set()
        all_p_refs: Set[str] = set()
        all_w_refs: Set[str] = set()

        for idx, (prio, score, ds, breakdown, reason) in enumerate(unranked_skills):
            rank = idx + 1
            sid = ds.skill_id
            prereqs = sorted(list(dependency_map[sid]))
            w_refs = sorted(list(workflow_refs_map[sid]))

            priority_groups[prio.value].append(sid)
            all_k_refs.update(ds.required_knowledge)
            all_p_refs.update(ds.required_packages)
            all_w_refs.update(w_refs)

            ranked_skills.append(
                RankedSkill(
                    skill_id=sid,
                    name=ds.name,
                    display_name=ds.display_name,
                    category=ds.category,
                    rank=rank,
                    priority=prio,
                    score=score,
                    ranking_reason=reason,
                    score_breakdown=breakdown,
                    dependencies=prereqs,
                    knowledge_references=ds.required_knowledge,
                    package_references=ds.required_packages,
                    workflow_references=w_refs,
                    path=ds.path,
                    is_official=is_official_map[sid],
                )
            )

        # Clean empty priority groups
        priority_groups = {k: v for k, v in priority_groups.items() if v}

        avg_score = (
            sum(s.score for s in ranked_skills) / len(ranked_skills) if ranked_skills else 0.0
        )
        ranking_confidence = min(
            1.0,
            round(
                (avg_score / 100.0) * 0.5 + (selection_report.coverage.coverage_percent / 200.0) + 0.25,
                2,
            ),
        )

        evidence = {
            "selection_report_id": selection_report.report_id,
            "execution_plan_id": plan_id,
            "total_ranked_skills": len(ranked_skills),
            "priority_counts": {k: len(v) for k, v in priority_groups.items()},
            "blocking_skills_count": len(blocking_skills),
            "independent_skills_count": len(independent_skills),
            "official_skills_count": sum(1 for s in ranked_skills if s.is_official),
            "is_dag": nx.is_directed_acyclic_graph(dag),
        }

        return RankedSkillReport(
            report_id=report_id,
            selection_report_id=selection_report.report_id,
            execution_plan_id=plan_id,
            ranked_skills=ranked_skills,
            priority_groups=priority_groups,
            dependency_chains=dependency_chains,
            recommended_execution_order=recommended_order,
            blocking_skills=sorted(blocking_skills),
            independent_skills=sorted(independent_skills),
            knowledge_references=sorted(list(all_k_refs)),
            package_references=sorted(list(all_p_refs)),
            workflow_references=sorted(list(all_w_refs)),
            coverage=selection_report.coverage,
            confidence=ranking_confidence,
            evidence=evidence,
            timestamp=now_str,
        )
