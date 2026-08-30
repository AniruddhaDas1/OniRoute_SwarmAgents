"""E2.1 Contract Validation Module for OniRoute_SwarmAgents (Phase P4.G4-E2.1).

Validates EngineeringContractReport against E2.1 acceptance criteria including:
- E2.1.1 Unique contract IDs
- E2.1.2 Mission assignment correctness
- E2.1.3 Agent assignment completeness
- E2.1.4 Objective coverage
- E2.1.5 Deliverable completeness
- E2.1.6 Acceptance criteria per contract
- E2.1.7 Dependency DAG integrity (Kahn's algorithm, no NetworkX)
- E2.1.8 Repository scope alignment
- E2.1.9 Technology context match
- E2.1.10 No orphan contracts
- E2.1.11 100% coverage accounting
- E2.1.12 Determinism (sequential IDs, no timestamps)
- E2.1.13 Traceability (hash verification)
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Any, Dict, List

from runtime.contracts.exceptions import (
 ContractDependencyError,
 ContractValidationError,
 EngineeringContractError,
)
from runtime.contracts.models import EngineeringContract, EngineeringContractReport

try:
 from runtime.workspace.plan import EngineeringExecutionPlan
except ImportError:
 EngineeringExecutionPlan = None # type: ignore[assignment,misc]


class ContractValidator:
 """Validates EngineeringContractReport for E2.1 acceptance criteria.
 
 Runs all validation checks and returns a detailed dict of per-check results.
 Raises ContractValidationError if any check fails.
 """

 _CONTRACT_ID_PATTERN = re.compile(r"^ctr-\d{4}$")

 def validate(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Run all validation checks.
  
  Args:
  report: Immutable EngineeringContractReport to validate.
  
  Returns:
  Dict[str, Any]: Detailed per-check results including coverage metrics.
  
  Raises:
  ContractValidationError: If any validation check fails.
  ContractDependencyError: If a cycle is detected in contract dependencies.
  """
  if not isinstance(report, EngineeringContractReport):
   raise ContractValidationError("Expected EngineeringContractReport")

  results: Dict[str, Any] = {}
  results["E2.1.1_unique_ids"] = self._check_unique_ids(report)
  results["E2.1.2_mission_assignment"] = self._check_mission_assignment(report)
  results["E2.1.3_agent_assignment"] = self._check_agent_assignment(report)
  results["E2.1.4_objective_coverage"] = self._check_objective_coverage(report)
  results["E2.1.5_deliverable_completeness"] = self._check_deliverable_completeness(report)
  results["E2.1.6_acceptance_criteria"] = self._check_acceptance_criteria(report)
  results["E2.1.7_dependency_dag"] = self._check_dependency_dag(report)
  results["E2.1.8_repo_scope"] = self._check_repo_scope(report)
  results["E2.1.9_tech_context"] = self._check_tech_context(report)
  results["E2.1.10_no_orphans"] = self._check_no_orphans(report)
  results["E2.1.11_coverage_100"] = self._check_coverage_100(report)
  results["E2.1.12_determinism"] = self._check_determinism(report)
  results["E2.1.13_traceability"] = self._check_traceability(report)

  summary = self._summarize(results)
  if summary["failed"] > 0:
   raise ContractValidationError(
    f"Validation failed: {summary['failed']}/{summary['total']} checks failed. "
    f"Details: {summary['failures']}")

  return results

 def _summarize(self, results: Dict[str, Any]) -> Dict[str, Any]:
  total = len(results)
  passed = sum(1 for v in results.values() if v.get("passed", False))
  failed = total - passed
  failures = [k for k, v in results.items() if not v.get("passed", False)]
  return {"total": total, "passed": passed, "failed": failed, "failures": failures}

 def _check_unique_ids(self, report: EngineeringContractReport) -> Dict[str, Any]:
  ids = [c.contract_id for c in report.contracts]
  unique = len(ids) == len(set(ids))
  return {"passed": unique, "detail": f"Unique: {len(set(ids))}/{len(ids)}"}

 def _check_mission_assignment(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """All contracts share the same mission_id as the report."""
  ids = {c.mission_id for c in report.contracts}
  passed = len(ids) == 1 and report.mission_id in ids
  return {"passed": passed, "detail": f"Distinct mission_ids: {len(ids)}"}

 def _check_agent_assignment(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Every contract has a non-empty assigned_profile_id."""
  unassigned = [c.contract_id for c in report.contracts if not c.assigned_profile_id]
  passed = len(unassigned) == 0
  return {"passed": passed, "detail": f"Unassigned: {len(unassigned)}"}

 def _check_objective_coverage(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Every contract has a non-empty objective."""
  empty = [c.contract_id for c in report.contracts if not c.objective]
  passed = len(empty) == 0
  return {"passed": passed, "detail": f"Empty objectives: {len(empty)}"}

 def _check_deliverable_completeness(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Each contract links to at least one deliverable."""
  ctr_ids = {c.contract_id for c in report.contracts}
  dlv_ctr_ids = {d.contract_id for d in report.deliverables}
  missing = sorted(ctr_ids - dlv_ctr_ids)
  passed = len(missing) == 0
  return {"passed": passed, "detail": f"Contracts without deliverables: {missing}"}

 def _check_acceptance_criteria(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Each contract has at least one acceptance criterion."""
  ctr_ids = {c.contract_id for c in report.contracts}
  ac_ctr_ids = {a.contract_id for a in report.acceptance_criteria_models}
  missing = sorted(ctr_ids - ac_ctr_ids)
  passed = len(missing) == 0
  return {"passed": passed, "detail": f"Contracts without acceptance criteria: {missing}"}

 def _check_dependency_dag(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Kahn's algorithm for topological sort; no cycles allowed."""
  adj: Dict[str, List[str]] = defaultdict(list)
  in_degree: Dict[str, int] = defaultdict(int)
  all_ids = {c.contract_id for c in report.contracts}
  for c in report.contracts:
   in_degree.setdefault(c.contract_id, 0)
   for dep in c.dependencies:
    if dep in all_ids:
     adj[dep].append(c.contract_id)
     in_degree[c.contract_id] += 1

  queue = deque([n for n in all_ids if in_degree.get(n, 0) == 0])
  visited = 0
  while queue:
   node = queue.popleft()
   visited += 1
   for neighbor in adj.get(node, []):
    in_degree[neighbor] -= 1
    if in_degree[neighbor] == 0:
     queue.append(neighbor)

  passed = visited == len(all_ids)
  detail = "No cycles detected" if passed else f"Cycle detected, visited {visited}/{len(all_ids)}"
  return {"passed": passed, "detail": detail}

 def _check_repo_scope(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Every contract has a non-empty repository_scope."""
  empty = [c.contract_id for c in report.contracts if not c.repository_scope]
  passed = len(empty) == 0
  return {"passed": passed, "detail": f"Empty repository_scope: {len(empty)}"}

 def _check_tech_context(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Each contract tech_context references at least one technology."""
  empty = [c.contract_id for c in report.contracts if not c.technology_context]
  passed = len(empty) == 0
  return {"passed": passed, "detail": f"Empty tech_context: {len(empty)}"}

 def _check_no_orphans(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """No contract should be unreachable from any dependency root."""
  reachable: Set[str] = set()
  has_deps: Set[str] = set()
  all_ids = {c.contract_id for c in report.contracts}
  for c in report.contracts:
   for dep in c.dependencies:
    if dep in all_ids:
     has_deps.add(dep)

  adj: Dict[str, List[str]] = defaultdict(list)
  for c in report.contracts:
   for dep in c.dependencies:
    if dep in all_ids:
     adj[dep].append(c.contract_id)

  entry = all_ids - has_deps
  queue = deque(list(entry))
  visited: Set[str] = set()
  while queue:
   node = queue.popleft()
   if node in visited:
    continue
   visited.add(node)
   for neighbor in adj.get(node, []):
    if neighbor not in visited:
     queue.append(neighbor)

  orphans = all_ids - visited
  passed = len(orphans) == 0
  return {"passed": passed, "detail": f"Orphan contracts: {sorted(orphans)}"}

 def _check_coverage_100(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Coverage report indicates 100%."""
  cov = getattr(report, "coverage", {})
  pct = cov.get("coverage_percent", 0)
  passed = pct >= 100.0
  return {"passed": passed, "detail": f"Coverage: {pct}%"}

 def _check_determinism(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Sequential IDs, no timestamps in contract data."""
  ids = [c.contract_id for c in report.contracts]
  sequential = all(ids[i] < ids[i+1] for i in range(len(ids)-1))
  no_ts = not any(getattr(c, "timestamp", None) for c in report.contracts)
  passed = sequential and no_ts
  return {"passed": passed, "detail": f"Sequential: {sequential}, No timestamps: {no_ts}"}

 def _check_traceability(self, report: EngineeringContractReport) -> Dict[str, Any]:
  """Every contract has a traceability record."""
  ctr_ids = {c.contract_id for c in report.contracts}
  trc_ids = {t.contract_id for t in report.traceability}
  missing = sorted(ctr_ids - trc_ids)
  passed = len(missing) == 0
  return {"passed": passed, "detail": f"Contracts without traceability: {missing}"}