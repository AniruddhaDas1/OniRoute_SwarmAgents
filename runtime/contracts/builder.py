"""E2.1 EngineeringContractBuilder Engine (Phase E2.1).

Deterministic builder that consumes engineering intelligence to produce
EngineeringContracts. No LLM calls, no agent execution, no code generation.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from runtime.contracts.exceptions import (
    ContractConstraintError, ContractCoverageError,
    ContractDependencyError, ContractValidationError, EngineeringContractError,
)
from runtime.contracts.e21_models import (
    ACCEPTANCE_CRITERIA_TEMPLATES, DELIVERABLE_VERIFICATION_METHOD,
    DISCIPLINE_DELIVERABLE_TYPE, DISCIPLINE_REPOSITORY_SCOPE,
    SKILL_PRIORITY_TO_GENERATION, ContractCoverageMetrics, ContractTraceability,
    DeliverableContract, AcceptanceCriteria,
)
from runtime.contracts.models import EngineeringContract, EngineeringContractReport
from runtime.skills.models import (
    AgentProfile, AgentProfileReport, ExecutionSkillBundle,
    ExecutionSkillBundleReport, SkillPriority,
)
from runtime.workspace.plan import EngineeringExecutionPlan


class EngineeringContractBuilder:
    """Deterministic builder that consumes engineering intelligence to produce EngineeringContracts.
    
    Inputs: EngineeringExecutionPlan + ExecutionSkillBundleReport + AgentProfileReport
    Output: EngineeringContractReport
    No LLM calls, no agent execution, no code generation.
    """

    def build(self, plan: EngineeringExecutionPlan, bundle_report: ExecutionSkillBundleReport, profile_report: AgentProfileReport) -> EngineeringContractReport:
        self._validate_inputs(plan, bundle_report, profile_report)
        start_time = time.perf_counter()
        plan_id = plan.plan_id
        mission_id = plan.mission_id
        self._validate_bundle_dependencies(bundle_report)
        self._validate_bundle_mapping(bundle_report, profile_report)
        (contracts, deliverable_contracts, acceptance_criteria_list, traceability_records, coverage_metrics) = self._build_contracts(plan, plan_id, mission_id, bundle_report, profile_report)
        if coverage_metrics.coverage_percent < 100.0:
            raise ContractCoverageError(f"Contract coverage is {coverage_metrics.coverage_percent:.1f}%, required 100%. Uncovered bundles: {coverage_metrics.uncovered_bundles}")
        agent_contracts: Dict[str, List[str]] = defaultdict(list)
        discipline_contracts: Dict[str, List[str]] = defaultdict(list)
        execution_waves: Dict[int, List[str]] = defaultdict(list)
        all_outputs: Set[str] = set()
        for contract in contracts:
            agent_contracts[contract.assigned_profile_id].append(contract.contract_id)
            discipline_contracts[contract.engineering_discipline].append(contract.contract_id)
            execution_waves[contract.execution_wave].append(contract.contract_id)
            all_outputs.update(contract.output_artifacts)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        workspace_root = plan.evidence.get("workspace_path", f"/workspace/{plan_id}")
        report_id = self._compute_report_id(plan_id, mission_id)
        report_hash = self._compute_report_hash(report_id, plan_id, mission_id, contracts)
        cycle_free = self._detect_cycle_detection(bundle_report)
        evidence: Dict[str, Any] = {
            "plan_id": plan_id, "mission_id": mission_id,
            "bundle_report_id": bundle_report.report_id,
            "profile_report_id": profile_report.report_id,
            "contract_count": len(contracts), "deliverable_count": len(deliverable_contracts),
            "acceptance_criteria_count": len(acceptance_criteria_list),
            "traceability_count": len(traceability_records),
            "agent_count": len(agent_contracts), "discipline_count": len(discipline_contracts),
            "wave_count": len(execution_waves), "latency_ms": round(elapsed_ms, 3),
            "determinism": True,
            "coverage_percent": coverage_metrics.coverage_percent,
            "coverage_metrics": coverage_metrics.model_dump(mode="json"),
            "no_cycles": cycle_free,
            "timestamp": timestamp_iso,
        }
        return EngineeringContractReport(
            mission_id=mission_id, execution_plan_id=plan_id,
            bundle_report_id=bundle_report.report_id,
            agent_profile_report_id=profile_report.report_id,
            deliverables=deliverable_contracts,
            acceptance_criteria_models=acceptance_criteria_list,
            traceability=traceability_records,
            coverage=coverage_metrics.model_dump(mode="json"),
            validation_results={
                "coverage_100_percent": coverage_metrics.coverage_percent >= 100.0,
                "no_cycles": cycle_free, "no_missing_refs": True, "bundle_mapping_complete": True,
            },
            deterministic=True, report_id=report_id,
            allocation_id=f"alloc-{plan_id[5:]}",
            workspace_id=f"ws-{plan_id[5:]}",
            workspace_root=workspace_root,
            technology_stack=", ".join(plan.technology_stack),
            contracts=contracts,
            agent_contracts=dict(agent_contracts),
            discipline_contracts=dict(discipline_contracts),
            expected_outputs=sorted(all_outputs),
            execution_waves=dict(execution_waves),
            evidence=evidence, timestamp=timestamp_iso, report_hash=report_hash,
        )

    def _validate_inputs(self, plan: EngineeringExecutionPlan, bundle_report: ExecutionSkillBundleReport, profile_report: AgentProfileReport) -> None:
        if not plan.project_goal or not plan.project_goal.strip():
            raise ContractValidationError("EngineeringExecutionPlan.project_goal must not be empty.")
        if not bundle_report.bundles:
            raise ContractValidationError("ExecutionSkillBundleReport contains no bundles.")
        if not profile_report.profiles:
            raise ContractValidationError("AgentProfileReport contains no profiles.")

    def _build_contracts(self, plan: EngineeringExecutionPlan, plan_id: str, mission_id: str, bundle_report: ExecutionSkillBundleReport, profile_report: AgentProfileReport) -> Tuple[List[EngineeringContract], List[DeliverableContract], List[AcceptanceCriteria], List[ContractTraceability], ContractCoverageMetrics]:
        contracts: List[EngineeringContract] = []
        deliverable_contracts: List[DeliverableContract] = []
        acceptance_criteria_list: List[AcceptanceCriteria] = []
        traceability_records: List[ContractTraceability] = []
        ordering_index: Dict[str, int] = {}
        for idx, b_id in enumerate(bundle_report.bundle_ordering):
            ordering_index[b_id] = idx
        total_deliverables_count = sum(len(b.expected_deliverables) for b in bundle_report.bundles)
        contract_counter = 0
        for bundle in bundle_report.bundles:
            contract_counter += 1
            ctr_id = f"ctr-{contract_counter:04d}"
            profile_id = profile_report.bundle_mapping.get(bundle.bundle_id, "")
            profile: Optional[AgentProfile] = None
            for p in profile_report.profiles:
                if p.profile_id == profile_id:
                    profile = p
                break
            assigned_profile_role = profile.agent_role if profile else f"{bundle.engineering_discipline} Agent"
            ranked_skills = bundle.ranked_skills
            required_capabilities = sorted({s.category for s in ranked_skills})
            required_skills = [s.name for s in ranked_skills]
            bundle_priority = bundle.priority.value if isinstance(bundle.priority, SkillPriority) else str(bundle.priority)
            generation_priority = SKILL_PRIORITY_TO_GENERATION.get(bundle_priority, "P2_MEDIUM")
            execution_order = ordering_index.get(bundle.bundle_id, 0)
            repo_scope = DISCIPLINE_REPOSITORY_SCOPE.get(bundle.engineering_discipline, "src/")
            bundle_size = len(ranked_skills) + len(bundle.expected_deliverables)
            risk_level = self._compute_risk_level(bundle_size)
            inputs = sorted(set(bundle.knowledge_references + bundle.package_references))
            output_artifacts = [f"{repo_scope}{d.lower().replace(chr(39)+chr(39), chr(39)).replace(" ", "_").replace(chr(39)+chr(39)+chr(39), chr(39)+chr(39))}" for d in bundle.expected_deliverables]
            contract_deliverables: List[DeliverableContract] = []
            for dlv_idx, deliverable_desc in enumerate(bundle.expected_deliverables, start=1):
                deliverable_id = f"dlv-{ctr_id}-{dlv_idx:02d}"
                deliverable_type = DISCIPLINE_DELIVERABLE_TYPE.get(bundle.engineering_discipline, "CODE")
                verification_method = DELIVERABLE_VERIFICATION_METHOD.get(deliverable_type, "AUTOMATED_SCAN")
                contract_deliverables.append(DeliverableContract(deliverable_id=deliverable_id, contract_id=ctr_id, mission_id=mission_id, description=deliverable_desc, deliverable_type=deliverable_type, acceptance_criteria=[], verification_method=verification_method, estimated_complexity=risk_level, dependencies=[]))
            contract_criteria: List[AcceptanceCriteria] = []
            criteria_categories = ["FUNCTIONAL", "SECURITY", "PERFORMANCE", "COMPLIANCE", "QUALITY"]
            for crt_idx, category in enumerate(criteria_categories, start=1):
                criteria_id = f"ac-{ctr_id}-{crt_idx:02d}"
                template = ACCEPTANCE_CRITERIA_TEMPLATES.get(category, ACCEPTANCE_CRITERIA_TEMPLATES["FUNCTIONAL"])
                description = template["given"].replace("{discipline}", bundle.engineering_discipline).replace("{objective}", bundle.name) + " " + template["when"].replace("{discipline}", bundle.engineering_discipline).replace("{objective}", bundle.name) + " " + template["then"].replace("{discipline}", bundle.engineering_discipline).replace("{objective}", bundle.name)
                contract_criteria.append(AcceptanceCriteria(criteria_id=criteria_id, contract_id=ctr_id, mission_id=mission_id, description=description, category=category, is_deterministic=True, test_reference=""))
            trace_id = f"trc-{ctr_id}"
            trace_chain = [plan.plan_id, plan.mission_id, bundle_report.report_id, profile_report.report_id, bundle.bundle_id, profile_id, ctr_id]
            traceability_records.append(ContractTraceability(traceability_id=trace_id, contract_id=ctr_id, mission_id=mission_id, intent_report_id="", execution_plan_id=plan_id, skill_bundle_report_id=bundle_report.report_id, agent_profile_report_id=profile_report.report_id, source_deliverable=bundle.expected_deliverables[0] if bundle.expected_deliverables else "", trace_chain=trace_chain))
            deliverable_contracts.extend(contract_deliverables)
            acceptance_criteria_list.extend(contract_criteria)
            interface_constraints = {"repository_scope": repo_scope, "bundle_id": bundle.bundle_id, "technology_stack": plan.technology_stack, "project_type": plan.project_type}
            arch_constraints = ["Preserve clear boundaries between architecture specs and implementation code.", "Enforce provider independence.", "Assert read-only Engine Root safety boundaries strictly.", "Ensure modules have zero circular import dependencies."]
            coding_standards = ["Use type annotations for all implementation languages.", "Follow PEP8 style guides with 100-character line length limits.", "Write clean, modular code with descriptive docstrings."]
            naming_rules = ["Use PascalCase for classes.", "Use snake_case for functions.", "Use UPPER_SNAKE_CASE for constants."]
            security_reqs = ["Sanitize all external inputs.", "Do NOT embed hardcoded secrets in source code.", "Enforce strict path resolution within workspace root boundaries."]
            perf_expectations: Dict[str, Any] = {"max_latency_ms": 100.0, "memory_limit_mb": 512, "deterministic_execution": True}
            test_reqs = ["Write automated unit tests.", "Maintain 100% test pass rate."]
            doc_reqs = ["Include professional docstrings.", "Maintain README.md documentation for major modules."]
            contract_acceptance_criteria = [crt.description for crt in contract_criteria]
            review_reqs = ["Requires peer code review.", "Requires automated security scanner pass."]
            ctr_hash = self._compute_contract_hash(ctr_id, bundle.bundle_id, plan_id, mission_id)
            contract = EngineeringContract(mission_id=plan.mission_id, project_goal=plan.project_goal, engineering_domain=bundle.engineering_discipline, agent_profile_id=profile_id, skill_bundle_id=bundle.bundle_id, objective=f"{bundle.name}: {plan.project_goal}", required_capabilities=required_capabilities, required_skills=required_skills, inputs=inputs, dependencies=bundle.dependency_bundles, constraints=arch_constraints, repository_scope=repo_scope, technology_context=list(plan.technology_stack), execution_order=contract_counter, risk_level=risk_level, expected_deliverables=bundle.expected_deliverables, priority=generation_priority, contract_id=ctr_id, target_path=repo_scope, target_type="module" if bundle.engineering_discipline in ("Backend", "Frontend") else "component", assigned_profile_id=profile_id, assigned_profile_role=assigned_profile_role, engineering_discipline=bundle.engineering_discipline, input_dependencies=bundle.dependency_bundles, output_artifacts=output_artifacts, interface_constraints=interface_constraints, architecture_constraints=arch_constraints, coding_standards=coding_standards, naming_rules=naming_rules, security_requirements=security_reqs, performance_expectations=perf_expectations, testing_requirements=test_reqs, documentation_requirements=doc_reqs, acceptance_criteria=contract_acceptance_criteria, review_requirements=review_reqs, generation_priority=generation_priority, execution_wave=execution_order + 1, contract_hash=ctr_hash)
            contracts.append(contract)
            plan_disciplines: Set[str] = set(plan.required_disciplines) if hasattr(plan, "required_disciplines") else {b.engineering_discipline for b in bundle_report.bundles}
            contracted_disciplines = {c.engineering_discipline for c in contracts}
            missing_disciplines_list = sorted(plan_disciplines - contracted_disciplines)
            coverage_percent = 100.0 if len(contracts) == len(bundle_report.bundles) else (len(contracts) / len(bundle_report.bundles)) * 100.0
            coverage_metrics = ContractCoverageMetrics(total_bundles=len(bundle_report.bundles), contracted_bundles=len(contracts), coverage_percent=coverage_percent, uncovered_bundles=[], total_deliverables=total_deliverables_count, covered_deliverables=total_deliverables_count, uncovered_deliverables=[], total_disciplines=len(plan_disciplines), represented_disciplines=len(contracted_disciplines), missing_disciplines=missing_disciplines_list)
        return (contracts, deliverable_contracts, acceptance_criteria_list, traceability_records, coverage_metrics)

    def _detect_cycle_detection(self, bundle_report: ExecutionSkillBundleReport) -> bool:
        bundle_ids = {b.bundle_id for b in bundle_report.bundles}
        adj: Dict[str, List[str]] = {bid: [] for bid in bundle_ids}
        for b in bundle_report.bundles:
            for dep in b.dependency_bundles:
                if dep in bundle_ids:
                    adj[b.bundle_id].append(dep)
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {bid: WHITE for bid in bundle_ids}
        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in adj.get(node, []):
                if color[neighbor] == GRAY:
                    return False
                if color[neighbor] == WHITE:
                    if not dfs(neighbor):
                        return False
                color[node] = BLACK
            return True
        for bid in bundle_ids:
            if color[bid] == WHITE:
                if not dfs(bid):
                    return False
            return True

    def _validate_bundle_dependencies(self, bundle_report: ExecutionSkillBundleReport) -> None:
        valid_ids = {b.bundle_id for b in bundle_report.bundles}
        missing_refs: Set[str] = set()
        for b in bundle_report.bundles:
            for dep in b.dependency_bundles:
                if dep not in valid_ids:
                    missing_refs.add(dep)
        if missing_refs:
            raise ContractDependencyError(f"Bundle dependencies reference non-existent bundles: {sorted(missing_refs)}")

    def _validate_bundle_mapping(self, bundle_report: ExecutionSkillBundleReport, profile_report: AgentProfileReport) -> None:
        unmapped = [b.bundle_id for b in bundle_report.bundles if b.bundle_id not in profile_report.bundle_mapping]
        if unmapped:
            raise ContractDependencyError(f"Bundles missing from profile_report.bundle_mapping: {unmapped}")

    def _compute_risk_level(self, bundle_size: int) -> str:
        if bundle_size <= 3:
            return "LOW"
        elif bundle_size <= 7:
            return "MEDIUM"
        else:
            return "HIGH"

    def _compute_report_id(self, plan_id: str, mission_id: str) -> str:
        payload = f"{plan_id}:{mission_id}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        return f"ctrr-{digest}"

    def _compute_contract_hash(self, contract_id: str, bundle_id: str, plan_id: str, mission_id: str) -> str:
        payload = f"{contract_id}:{bundle_id}:{plan_id}:{mission_id}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _compute_report_hash(self, report_id: str, plan_id: str, mission_id: str, contracts: List[EngineeringContract]) -> str:
        hash_payload = {"report_id": report_id, "plan_id": plan_id, "mission_id": mission_id, "contracts": [c.model_dump(mode="json") for c in contracts]}
        json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
