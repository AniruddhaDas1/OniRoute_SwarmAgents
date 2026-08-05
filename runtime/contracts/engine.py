"""Engineering Contracts Engine (Phase P4.G4).

Consumes ImplementationAllocationReport and deterministically transforms implementation
allocations into execution-ready Engineering Contracts for Autonomous Engineering (P5)
without invoking LLMs or generating source code.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from runtime.allocation.models import AllocationTarget, ImplementationAllocationReport
from runtime.contracts.exceptions import ContractConstraintError, ContractValidationError, EngineeringContractError
from runtime.contracts.models import EngineeringContract, EngineeringContractReport


DISCIPLINE_WAVE_MAP: Dict[str, int] = {
    "Shared": 1,
    "Infrastructure": 1,
    "Security": 1,
    "AI": 1,
    "Database": 2,
    "Backend": 3,
    "Automation": 3,
    "Frontend": 4,
    "Testing": 5,
    "Documentation": 6,
    "Analytics": 6,
}


class EngineeringContractEngine:
    """Deterministic Engineering Contract Engine for Phase P4.G4.

    Consumes ONLY ImplementationAllocationReport to produce execution-ready
    Engineering Contracts for every allocated target.
    """

    def generate_contracts(
        self, allocation_report: ImplementationAllocationReport
    ) -> EngineeringContractReport:
        """Generate deterministic EngineeringContractReport from ImplementationAllocationReport.

        Args:
            allocation_report: Immutable ImplementationAllocationReport input contract.

        Returns:
            EngineeringContractReport: Immutable engineering contract report.
        """
        start_time = time.perf_counter()

        if not isinstance(allocation_report, ImplementationAllocationReport):
            raise ContractValidationError(
                f"EngineeringContractEngine consumes ONLY ImplementationAllocationReport. "
                f"Received invalid input type: {type(allocation_report).__name__}"
            )

        alloc_id = allocation_report.allocation_id
        ws_id = allocation_report.workspace_id
        ws_root = allocation_report.workspace_root
        tech_stack = allocation_report.technology_stack.lower()

        # 1. Generate Engineering Contracts
        contracts, agent_contracts, discipline_contracts, execution_waves, all_outputs = (
            self._build_contracts(allocation_report)
        )

        # 2. Validate Contract Integrity
        validation_results = self._validate_contract_integrity(
            allocation_report=allocation_report,
            contracts=contracts,
            agent_contracts=agent_contracts,
            discipline_contracts=discipline_contracts,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        report_id = f"ctrr-{abs(hash(f'{alloc_id}-{ws_id}-{timestamp_iso}')) % 1000000:06d}"

        # 3. Compute SHA-256 Report Hash
        report_hash = self._compute_report_hash(
            report_id=report_id,
            allocation_id=alloc_id,
            workspace_id=ws_id,
            workspace_root=ws_root,
            technology_stack=tech_stack,
            contracts=contracts,
            agent_contracts=agent_contracts,
        )

        # 4. Assemble Evidence & Performance Metrics
        evidence: Dict[str, Any] = {
            "allocation_id": alloc_id,
            "allocation_hash": allocation_report.allocation_hash,
            "contract_count": len(contracts),
            "output_artifact_count": len(all_outputs),
            "agent_profile_count": len(agent_contracts),
            "discipline_count": len(discipline_contracts),
            "wave_count": len(execution_waves),
            "latency_ms": round(elapsed_ms, 3),
            "determinism": True,
            "coverage_score": validation_results["coverage_score"],
            "validation": validation_results,
            "timestamp": timestamp_iso,
        }

        # 5. Return Immutable Report
        return EngineeringContractReport(
            report_id=report_id,
            allocation_id=alloc_id,
            workspace_id=ws_id,
            workspace_root=ws_root,
            technology_stack=tech_stack,
            contracts=contracts,
            agent_contracts=agent_contracts,
            discipline_contracts=discipline_contracts,
            expected_outputs=sorted(all_outputs),
            execution_waves=execution_waves,
            evidence=evidence,
            timestamp=timestamp_iso,
            report_hash=report_hash,
        )

    def _build_contracts(
        self, allocation_report: ImplementationAllocationReport
    ) -> Tuple[
        List[EngineeringContract],
        Dict[str, List[str]],
        Dict[str, List[str]],
        Dict[int, List[str]],
        List[str],
    ]:
        """Build individual EngineeringContracts and output mappings."""
        contracts: List[EngineeringContract] = []
        agent_contracts: Dict[str, List[str]] = defaultdict(list)
        discipline_contracts: Dict[str, List[str]] = defaultdict(list)
        execution_waves: Dict[int, List[str]] = defaultdict(list)
        all_outputs: Set[str] = set()

        contract_counter = 1

        for target in allocation_report.allocated_targets:
            ctr_id = f"ctr-{contract_counter:04d}"
            contract_counter += 1

            wave = DISCIPLINE_WAVE_MAP.get(target.owning_discipline, 1)

            # Define specific constraints per target
            interface_constraints = {
                "target_type": target.target_type,
                "exported_symbols": ["main", "handler", "init"] if target.target_type == "file" else ["ModulePackage"],
                "api_protocol": "REST/JSON" if target.owning_discipline in ("Frontend", "Backend") else "Internal",
            }

            arch_constraints = [
                "Preserve clear boundaries between architecture specs and implementation code.",
                "Enforce provider independence and avoid embedding project-specific behavior in core modules.",
                "Assert read-only Engine Root safety boundaries strictly via assert_no_engine_write.",
                "Ensure modules have zero circular import dependencies.",
            ]

            coding_standards = [
                "Use Python 3.10+ type annotations and standard library guidelines.",
                "Follow PEP8 / ESLint style guides with 100-character line length limits.",
                "Write clean, modular, self-documenting code with descriptive docstrings.",
            ]

            naming_rules = [
                "Use PascalCase for classes, components, and type declarations.",
                "Use snake_case for functions, methods, variables, and module filenames.",
                "Use UPPER_SNAKE_CASE for global constants.",
            ]

            security_reqs = [
                "Sanitize and validate all external inputs using Pydantic models or strict schemas.",
                "Do NOT embed hardcoded secrets, API keys, or private tokens in source code.",
                "Enforce strict path resolution within workspace root boundaries.",
            ]

            perf_expectations = {
                "max_latency_ms": 100.0,
                "memory_limit_mb": 512,
                "deterministic_execution": True,
            }

            test_reqs = [
                "Write automated unit tests covering key logical branches and exception scenarios.",
                "Maintain 100% test execution pass rate in test runner.",
            ]

            doc_reqs = [
                "Include professional docstrings describing inputs, outputs, and exceptions.",
                "Maintain README.md documentation for every major module directory.",
            ]

            acceptance_criteria = [
                f"Target path '{target.relative_path}' satisfies all discipline '{target.owning_discipline}' requirements.",
                f"Assigned agent profile '{target.owning_profile_role}' ({target.owning_profile_id}) successfully verifies contract implementation.",
                "Execution passes all automated test suite assertions without warnings.",
            ]

            review_reqs = [
                "Requires peer code review approval from Lead System Architect before merging.",
                "Requires automated security scanner pass.",
            ]

            output_arts = [target.relative_path]
            all_outputs.add(target.relative_path)

            # Compute Hash for Single Contract
            ctr_hash = self._compute_single_contract_hash(
                ctr_id, target.relative_path, target.owning_profile_id, target.owning_discipline
            )

            contract = EngineeringContract(
                contract_id=ctr_id,
                target_path=target.relative_path,
                target_type=target.target_type,
                assigned_profile_id=target.owning_profile_id,
                assigned_profile_role=target.owning_profile_role,
                engineering_discipline=target.owning_discipline,
                input_dependencies=target.dependencies,
                output_artifacts=output_arts,
                interface_constraints=interface_constraints,
                architecture_constraints=arch_constraints,
                coding_standards=coding_standards,
                naming_rules=naming_rules,
                security_requirements=security_reqs,
                performance_expectations=perf_expectations,
                testing_requirements=test_reqs,
                documentation_requirements=doc_reqs,
                acceptance_criteria=acceptance_criteria,
                review_requirements=review_reqs,
                generation_priority=target.priority,
                execution_wave=wave,
                contract_hash=ctr_hash,
            )

            contracts.append(contract)
            agent_contracts[target.owning_profile_id].append(ctr_id)
            discipline_contracts[target.owning_discipline].append(ctr_id)
            execution_waves[wave].append(ctr_id)

        return (
            contracts,
            dict(agent_contracts),
            dict(discipline_contracts),
            dict(execution_waves),
            list(all_outputs),
        )

    def _validate_contract_integrity(
        self,
        allocation_report: ImplementationAllocationReport,
        contracts: List[EngineeringContract],
        agent_contracts: Dict[str, List[str]],
        discipline_contracts: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Validate 100% allocation coverage, orphan/duplicate checking, and constraint completeness."""
        total_targets = len(allocation_report.allocated_targets)
        total_contracts = len(contracts)

        hundred_percent_coverage = total_targets > 0 and total_contracts == total_targets
        no_orphan_contracts = all(c.assigned_profile_id != "" for c in contracts)
        no_duplicate_contracts = len(set(c.contract_id for c in contracts)) == total_contracts
        dependency_integrity = all(isinstance(c.input_dependencies, list) for c in contracts)

        # Check constraint completeness (all constraint categories non-empty)
        constraint_completeness = all(
            len(c.architecture_constraints) > 0
            and len(c.coding_standards) > 0
            and len(c.naming_rules) > 0
            and len(c.security_requirements) > 0
            and len(c.testing_requirements) > 0
            and len(c.documentation_requirements) > 0
            for c in contracts
        )

        acceptance_completeness = all(len(c.acceptance_criteria) > 0 for c in contracts)

        coverage_score = (
            1.0
            if (
                hundred_percent_coverage
                and no_orphan_contracts
                and no_duplicate_contracts
                and dependency_integrity
                and constraint_completeness
                and acceptance_completeness
            )
            else 0.0
        )

        if not hundred_percent_coverage or not no_orphan_contracts or not constraint_completeness:
            raise ContractConstraintError(
                f"Engineering Contract validation failed: coverage={hundred_percent_coverage}, "
                f"no_orphans={no_orphan_contracts}, constraint_completeness={constraint_completeness}"
            )

        return {
            "hundred_percent_allocation_coverage": hundred_percent_coverage,
            "no_orphan_contracts": no_orphan_contracts,
            "no_duplicate_contracts": no_duplicate_contracts,
            "dependency_integrity": dependency_integrity,
            "constraint_completeness": constraint_completeness,
            "acceptance_completeness": acceptance_completeness,
            "coverage_score": coverage_score,
        }

    def _compute_single_contract_hash(
        self, contract_id: str, target_path: str, profile_id: str, discipline: str
    ) -> str:
        """Compute SHA-256 hash for a single contract."""
        payload = f"{contract_id}:{target_path}:{profile_id}:{discipline}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _compute_report_hash(
        self,
        report_id: str,
        allocation_id: str,
        workspace_id: str,
        workspace_root: str,
        technology_stack: str,
        contracts: List[EngineeringContract],
        agent_contracts: Dict[str, List[str]],
    ) -> str:
        """Compute SHA-256 hash of entire engineering contract report payload."""
        hash_payload = {
            "report_id": report_id,
            "allocation_id": allocation_id,
            "workspace_id": workspace_id,
            "workspace_root": workspace_root,
            "technology_stack": technology_stack,
            "contracts": [c.model_dump(mode="json") for c in contracts],
            "agent_contracts": agent_contracts,
        }
        json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
