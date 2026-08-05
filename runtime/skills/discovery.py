"""Skill Discovery Engine for OniRoute (Phase P2.S1).

Determines required skills from an EngineeringExecutionPlan via repository registry lookup
without prompt parsing, code execution, or AI invocation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

from runtime.core_models import MetadataRecord, RepositoryRegistry
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan, RepositoryStrategy

from .models import DiscoveredSkill, SkillCoverage, SkillSelectionReport


class SkillDiscoveryEngine:
    """Engine for automatic skill discovery from EngineeringExecutionPlan.

    Discovers required skills across 12 canonical categories using ONLY
    the declarative attributes of EngineeringExecutionPlan and RepositoryRegistry.
    Performs registry lookup without AI invocation or prompt parsing.
    """

    def __init__(self, registry: RepositoryRegistry, resolver: Resolver | None = None):
        self.registry = registry
        self.resolver = resolver or Resolver(registry)

    def discover_skills(self, plan: EngineeringExecutionPlan) -> SkillSelectionReport:
        """Discover skills required to execute the given EngineeringExecutionPlan."""
        now_str = datetime.now(timezone.utc).isoformat()
        hash_id = abs(hash(f"{plan.plan_id}:{plan.timestamp}")) % 1000000
        report_id = f"ssr-{hash_id:06d}"

        # Collect target requirements from plan sources ONLY
        disciplines = {d.lower() for d in plan.required_disciplines}
        deliverables = {d.lower() for d in plan.required_deliverables}
        tech_stack = {t.lower() for t in plan.technology_stack}
        constraints = {c.lower() for c in plan.known_constraints}
        strategy_val = plan.repository_strategy.value if hasattr(plan.repository_strategy, "value") else str(plan.repository_strategy)

        discovered_dict: Dict[str, Tuple[MetadataRecord, str, str]] = {}
        discovery_reasons: Dict[str, List[str]] = {}
        category_map: Dict[str, List[str]] = {
            "Engineering Skills": [],
            "Framework Skills": [],
            "Language Skills": [],
            "Testing Skills": [],
            "Security Skills": [],
            "Deployment Skills": [],
            "Database Skills": [],
            "AI Skills": [],
            "Documentation Skills": [],
            "Automation Skills": [],
            "Repository Skills": [],
            "MCP Skills": [],
        }

        all_skill_records = list(self.registry.skills.values())

        def _add_match(record: MetadataRecord, cat_name: str, reason: str):
            sid = record.id
            if sid not in discovered_dict:
                discovered_dict[sid] = (record, cat_name, reason)
            if sid not in discovery_reasons:
                discovery_reasons[sid] = []
            if reason not in discovery_reasons[sid]:
                discovery_reasons[sid].append(reason)
            if sid not in category_map[cat_name]:
                category_map[cat_name].append(sid)

        for rec in all_skill_records:
            data = rec.data
            rec_id = rec.id.lower()
            rec_cat = str(data.get("category", "")).lower()
            rec_tags = {str(t).lower() for t in data.get("tags", [])}
            rec_name = str(data.get("name", "")).lower()

            # Rule 1: Engineering Skills
            if rec_cat in ("foundation", "platform", "general engineering") or any(t in rec_tags for t in ("architecture", "design", "patterns", "engineering")) or "software engineering" in disciplines:
                _add_match(rec, "Engineering Skills", f"Matched engineering domain or foundation category ({rec.data.get('category', 'Engineering')})")

            # Rule 2: Framework Skills
            fw_keywords = ("react", "next", "vue", "angular", "fastapi", "django", "express", "flutter", "spring", "nestjs", "tailwind", "shadcn", "laravel", "svelte")
            matched_fw = [fw for fw in fw_keywords if fw in tech_stack or any(fw in d for d in deliverables) or any(fw in c for c in constraints)]
            if matched_fw and (any(fw in rec_id or fw in rec_tags or fw in rec_name for fw in matched_fw) or (rec_cat in ("frontend", "backend") and any(d in ("user interface pages", "rest api endpoints", "ui components") for d in deliverables))):
                _add_match(rec, "Framework Skills", f"Matched framework technology stack ({', '.join(matched_fw)})")

            # Rule 3: Language Skills
            lang_keywords = ("typescript", "javascript", "python", "dart", "go", "rust", "java", "c++", "swift", "kotlin", "sql", "html", "css")
            matched_lang = [l for l in lang_keywords if l in tech_stack or any(l in c for c in constraints)]
            if matched_lang and (any(l in rec_id or l in rec_tags or l in rec_name for l in matched_lang) or ("sql" in matched_lang and "sql" in rec_id)):
                _add_match(rec, "Language Skills", f"Matched programming language stack ({', '.join(matched_lang)})")

            # Rule 4: Testing Skills
            if "qa" in disciplines or any("test" in d for d in deliverables) or any(t in tech_stack for t in ("jest", "pytest", "cypress", "playwright")) or "test" in plan.project_goal.lower():
                if rec_cat == "testing" or any(t in rec_tags for t in ("testing", "qa", "jest", "pytest")) or "testing" in rec_id:
                    _add_match(rec, "Testing Skills", "Matched QA discipline and test suite deliverables")

            # Rule 5: Security Skills
            if "security" in disciplines or any("auth" in d for d in deliverables) or any(s in tech_stack or any(s in c for c in constraints) for s in ("auth", "oauth", "jwt", "encryption", "security", "secrets", "threat")):
                if rec_cat == "security" or any(t in rec_tags for t in ("security", "authentication", "authorization", "encryption", "secrets-management")) or "security" in rec_id or "auth" in rec_id:
                    _add_match(rec, "Security Skills", "Matched Security discipline, authentication, or access control requirements")

            # Rule 6: Deployment Skills
            if any(d in disciplines for d in ("devops", "infrastructure")) or any("deploy" in d or "container" in d for d in deliverables) or any(t in tech_stack for t in ("docker", "kubernetes", "aws", "gcp", "azure", "vercel", "netlify", "ci/cd")):
                if rec_cat in ("devops", "deployment") or any(t in rec_tags for t in ("devops", "ci", "cd", "cloud", "docker", "infrastructure")) or "devops" in rec_id or "cloud" in rec_id:
                    _add_match(rec, "Deployment Skills", "Matched DevOps discipline, containerization, or cloud deployment deliverables")

            # Rule 7: Database Skills
            if "database" in disciplines or any("database" in d for d in deliverables) or any(db in tech_stack or any(db in c for c in constraints) for db in ("postgresql", "mysql", "mongodb", "sqlite", "supabase", "redis", "prisma", "orm", "sql")):
                if rec_cat == "database" or any(t in rec_tags for t in ("database", "sql", "data-modeling", "schema-design")) or "database" in rec_id or "sql" in rec_id:
                    _add_match(rec, "Database Skills", "Matched Database discipline, schema deliverables, or database technology stack")

            # Rule 8: AI Skills
            if "ai" in disciplines or any("ai" in d for d in deliverables) or any(ai in tech_stack for ai in ("openai", "gemini", "anthropic", "llm", "agent", "ai", "rag")):
                if rec_cat in ("ai", "ai") or any(t in rec_tags for t in ("ai", "agent", "prompt")) or "ai" in rec_id or "agent" in rec_id:
                    _add_match(rec, "AI Skills", "Matched AI discipline, LLM integration, or prompt engineering requirements")

            # Rule 9: Documentation Skills
            if "documentation" in disciplines or any("doc" in d for d in deliverables) or strategy_val == RepositoryStrategy.DOCUMENTATION.value:
                if rec_cat in ("documentation", "presentation") or any(t in rec_tags for t in ("documentation", "docs")) or "doc" in rec_id or "presentation" in rec_id:
                    _add_match(rec, "Documentation Skills", "Matched Documentation discipline and technical documentation deliverables")

            # Rule 10: Automation Skills
            if "automation" in disciplines or plan.project_type.lower() in ("cli tool", "automation") or "automation" in tech_stack:
                if rec_cat == "automation" or any(t in rec_tags for t in ("automation", "cli", "background-jobs")) or "jobs" in rec_id:
                    _add_match(rec, "Automation Skills", "Matched Automation discipline or CLI project type")

            # Rule 11: Repository Skills
            if strategy_val in (RepositoryStrategy.REFACTOR_EXISTING.value, RepositoryStrategy.EXTEND_EXISTING.value, RepositoryStrategy.FEATURE_ADDITION.value, RepositoryStrategy.BUG_FIX.value):
                if rec_cat == "platform" or any(t in rec_tags for t in ("versioning", "migration", "integration", "refactoring")) or "versioning" in rec_id or "migration" in rec_id or "integration" in rec_id:
                    _add_match(rec, "Repository Skills", f"Matched repository strategy ({strategy_val}) and maintenance requirements")

            # Rule 12: MCP Skills
            if any(m in constraints for m in ("mcp", "tooling", "context")) or any("ai" in d for d in deliverables) or rec_cat in ("ai", "foundation"):
                if any(t in rec_tags for t in ("tool-calling", "context-optimization", "mcp")) or "tool-calling" in rec_id or "context-optimization" in rec_id:
                    _add_match(rec, "MCP Skills", "Matched tool calling and MCP integration capabilities")

        discovered_skills_list: List[DiscoveredSkill] = []
        consolidated_knowledge: Set[str] = set()
        consolidated_packages: Set[str] = set()
        consolidated_mcp_tools: Set[str] = set()

        for sid, (rec, primary_cat, reason) in discovered_dict.items():
            data = rec.data

            k_sources = data.get("knowledge_sources") or data.get("consumes_context") or []
            if isinstance(k_sources, str):
                k_sources = [k_sources]
            k_list = [str(k) for k in k_sources]
            rel_k = [r.id for r in self.resolver.related(sid, "knowledge_source")]
            all_k = sorted(list(set(k_list + rel_k)))
            consolidated_knowledge.update(all_k)

            pkgs = data.get("packages") or data.get("dependencies") or []
            if isinstance(pkgs, str):
                pkgs = [pkgs]
            p_list = [str(p) for p in pkgs]
            rel_p = [r.id for r in self.resolver.related(sid, "package")]
            all_p = sorted(list(set(p_list + rel_p)))
            consolidated_packages.update(all_p)

            tools = data.get("required_tools") or data.get("optional_tools") or data.get("mcp_tools") or []
            if isinstance(tools, str):
                tools = [tools]
            t_list = [str(t) for t in tools]
            consolidated_mcp_tools.update(t_list)

            discovered_skills_list.append(
                DiscoveredSkill(
                    skill_id=rec.id,
                    name=str(data.get("name") or rec.id),
                    display_name=str(data.get("display_name") or data.get("name") or rec.id),
                    category=str(data.get("category") or primary_cat),
                    tags=[str(t) for t in data.get("tags", [])],
                    discovery_reason="; ".join(discovery_reasons.get(rec.id, [reason])),
                    required_knowledge=all_k,
                    required_packages=all_p,
                    required_mcp_tools=t_list,
                    path=str(rec.path),
                )
            )

        expected_domains: List[str] = []
        for d in plan.required_disciplines:
            expected_domains.append(d)
        for t in plan.technology_stack:
            expected_domains.append(t)

        missing_skills: List[str] = []
        for expected in expected_domains:
            exp_low = expected.lower()
            found = any(
                exp_low in ds.skill_id.lower() or exp_low in ds.name.lower() or exp_low in ds.category.lower() or any(exp_low in tag.lower() for tag in ds.tags)
                for ds in discovered_skills_list
            )
            if not found:
                missing_skills.append(expected)

        total_req_count = max(1, len(expected_domains))
        covered_count = len(expected_domains) - len(missing_skills)
        coverage_percent = round(100.0 * max(0.0, covered_count) / total_req_count, 2)

        coverage = SkillCoverage(
            required_skills=sorted(list(set(expected_domains))),
            discovered_skills=[ds.skill_id for ds in discovered_skills_list],
            missing_skills=sorted(list(set(missing_skills))),
            coverage_percent=coverage_percent,
            registry_hits=len(discovered_skills_list),
        )

        confidence = 0.95 if coverage_percent >= 80.0 else round(0.5 + (coverage_percent / 200.0), 2)

        evidence = {
            "execution_plan_id": plan.plan_id,
            "project_type": plan.project_type,
            "repository_strategy": strategy_val,
            "disciplines_count": len(plan.required_disciplines),
            "deliverables_count": len(plan.required_deliverables),
            "technology_stack_count": len(plan.technology_stack),
            "total_registry_skills": len(self.registry.skills),
        }

        return SkillSelectionReport(
            report_id=report_id,
            execution_plan_id=plan.plan_id,
            discovered_skills=discovered_skills_list,
            discovery_reasons=discovery_reasons,
            skill_categories={k: v for k, v in category_map.items() if v},
            required_knowledge=sorted(list(consolidated_knowledge)),
            required_packages=sorted(list(consolidated_packages)),
            required_mcp_tools=sorted(list(consolidated_mcp_tools)),
            coverage=coverage,
            confidence=confidence,
            evidence=evidence,
            timestamp=now_str,
        )
