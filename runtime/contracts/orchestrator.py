"""E3.3 Artifact Execution Orchestrator.

Phase E3.3 — Artifact Execution Orchestration.

Orchestrates multi-artifact project execution through dependency-aware
scheduling, wave-based execution, and failure propagation using
existing E2 ArtifactExecutionPlan and E3.1 RealCodeGenerationEngine.

Architecture:
    ArtifactExecutionPlan
        ↓
    ArtifactExecutionOrchestrator
        ↓
    DependencyResolver (cycle detection, ordering)
        ↓
    WaveExecutor
        ↓
    RealCodeGenerationEngine
        ↓
    ExecutionReport
        ↓
    REAL MULTI-FILE PROJECT
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from runtime.contracts.e23_models import (
    ArtifactExecutionPlan,
    ArtifactExecutionUnit,
    ArtifactDependencyEdge,
    ArtifactDependencyGraph,
    ArtifactExecutionWave,
    GenerationStrategy,
)
from runtime.contracts.e33_models import (
    ArtifactExecutionStatus,
    ExecutionState,
    ExecutionStateTransition,
    WaveExecutionStatus,
    CycleDetectionResult,
    DependencyFailureInfo,
    ExecutionReport,
    ExecutionProgress,
    compute_execution_hash,
    compute_report_hash,
)


class DependencyCycleDetectedError(Exception):
    """Raised when a dependency cycle is detected in the plan."""
    pass


class ArtifactExecutionOrchestrator:
    """Orchestrates multi-artifact project execution.

    Consumes ArtifactExecutionPlan and orchestrates execution through
    the existing RealCodeGenerationEngine with dependency-aware scheduling,
    wave-based execution, and failure propagation.
    """

    def __init__(
        self,
        repository_root: str,
        generation_engine: Any,  # RealCodeGenerationEngine
        invocation_engine: Optional[Any] = None,  # InvocationEngine
    ):
        """Initialize the orchestrator.

        Args:
            repository_root: Absolute path to repository root
            generation_engine: RealCodeGenerationEngine instance
            invocation_engine: Optional InvocationEngine for LLM generation
        """
        self.repository_root = repository_root
        self.generation_engine = generation_engine
        self.invocation_engine = invocation_engine

        # Execution state tracking
        self._status_map: Dict[str, ArtifactExecutionStatus] = {}
        self._wave_results: List[WaveExecutionStatus] = []
        self._execution_start: Optional[float] = None

    def execute(self, plan: ArtifactExecutionPlan) -> ExecutionReport:
        """Execute all artifacts in the plan.

        Args:
            plan: ArtifactExecutionPlan from E2

        Returns:
            ExecutionReport with complete execution results

        Raises:
            DependencyCycleDetectedError: If dependency cycle is detected
        """
        start_time = time.time()
        self._execution_start = start_time
        execution_started = datetime.now(timezone.utc).isoformat()

        # Initialize status map
        self._initialize_statuses(plan)

        # Detect cycles
        cycle_result = self._detect_cycles(plan)
        if cycle_result.cycle_detected:
            return self._create_cycle_report(
                plan, cycle_result, execution_started, start_time
            )

        # Execute waves
        self._execute_waves(plan)

        # Build final report
        return self._build_report(plan, execution_started, start_time)

    def _initialize_statuses(self, plan: ArtifactExecutionPlan) -> None:
        """Initialize execution statuses for all units."""
        self._status_map.clear()
        self._wave_results.clear()

        for unit in plan.execution_units:
            dependencies = tuple(str(inp.source_artifact_id) for inp in unit.required_inputs)

            # Find dependents
            dependents = []
            for other_unit in plan.execution_units:
                for inp in other_unit.required_inputs:
                    if inp.source_artifact_id == unit.artifact_id:
                        dependents.append(other_unit.artifact_execution_id)
                        break

            status = ArtifactExecutionStatus(
                artifact_execution_id=unit.artifact_execution_id,
                artifact_id=unit.artifact_id,
                target_path=unit.target_path,
                state=ExecutionState.QUEUED,
                state_history=(),
                generation_strategy=unit.generation_strategy,
                execution_wave=unit.execution_wave,
                dependencies=dependencies,
                dependents=tuple(dependents),
                success=False,
                file_written=False,
                written_path="",
                content_hash="",
                strategy=unit.generation_strategy,
                errors=(),
                warnings=(),
                queued_at=datetime.now(timezone.utc).isoformat(),
                deterministic_hash="",
            )
            self._status_map[unit.artifact_execution_id] = status

    def _detect_cycles(self, plan: ArtifactExecutionPlan) -> CycleDetectionResult:
        """Detect cycles in the dependency graph."""
        # Build adjacency for cycle detection
        adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = defaultdict(int)

        all_ids = set()
        for unit in plan.execution_units:
            all_ids.add(unit.artifact_execution_id)
            in_degree[unit.artifact_execution_id] = 0

        for unit in plan.execution_units:
            for inp in unit.required_inputs:
                # Find source unit
                for src_unit in plan.execution_units:
                    if src_unit.artifact_id == inp.source_artifact_id:
                        adj[src_unit.artifact_execution_id].append(unit.artifact_execution_id)
                        in_degree[unit.artifact_execution_id] += 1
                        break

        # Kahn's algorithm for cycle detection
        queue = [n for n, d in in_degree.items() if d == 0]
        processed: Set[str] = set()

        while queue:
            node = queue.pop(0)
            processed.add(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(processed) != len(all_ids):
            # Cycle detected - find the cycle nodes
            cycle_ids = all_ids - processed
            cycle_path = tuple(sorted(cycle_ids))

            # Build cycle edges
            involved_edges = []
            for unit in plan.execution_units:
                if unit.artifact_execution_id in cycle_ids:
                    for inp in unit.required_inputs:
                        for src in plan.execution_units:
                            if src.artifact_id == inp.source_artifact_id and src.artifact_execution_id in cycle_ids:
                                involved_edges.append(ArtifactDependencyEdge(
                                    from_artifact_execution_id=src.artifact_execution_id,
                                    to_artifact_execution_id=unit.artifact_execution_id,
                                    dependency_type=inp.dependency_type,
                                ))

            return CycleDetectionResult(
                cycle_detected=True,
                cycle_path=cycle_path,
                involved_edges=tuple(involved_edges),
                message=f"Dependency cycle detected involving: {', '.join(cycle_path)}",
            )

        return CycleDetectionResult(
            cycle_detected=False,
            cycle_path=(),
            involved_edges=(),
            message="No cycles detected",
        )

    def _execute_waves(self, plan: ArtifactExecutionPlan) -> None:
        """Execute artifacts wave by wave."""
        sorted_waves = sorted(plan.execution_waves, key=lambda w: w.wave_number)

        for wave in sorted_waves:
            self._execute_wave(plan, wave)

    def _execute_wave(
        self,
        plan: ArtifactExecutionPlan,
        wave: ArtifactExecutionWave,
    ) -> None:
        """Execute a single wave of artifacts."""
        wave_start = time.time()
        wave_started = datetime.now(timezone.utc).isoformat()

        wave_status = WaveExecutionStatus(
            wave_number=wave.wave_number,
            wave_name=wave.wave_name,
            total_units=len(wave.artifact_execution_ids),
            ready_units=0,
            running_units=0,
            completed_units=0,
            failed_units=0,
            blocked_units=0,
            skipped_units=0,
            files_written=0,
            duration_ms=0.0,
            started_at=wave_started,
            completed_at=None,
        )

        # Get units for this wave
        wave_units = [
            u for u in plan.execution_units
            if u.artifact_execution_id in wave.artifact_execution_ids
        ]

        # Execute each unit in the wave
        for unit in wave_units:
            result = self._execute_unit(plan, unit)
            if result.success:
                wave_status.completed_units += 1
                if result.file_written:
                    wave_status.files_written += 1
            elif result.state == ExecutionState.FAILED:
                wave_status.failed_units += 1
            elif result.state == ExecutionState.BLOCKED:
                wave_status.blocked_units += 1
            elif result.state == ExecutionState.SKIPPED:
                wave_status.skipped_units += 1

        # Complete wave
        wave_duration = (time.time() - wave_start) * 1000
        wave_status.duration_ms = wave_duration
        wave_status.completed_at = datetime.now(timezone.utc).isoformat()
        self._wave_results.append(wave_status)

    def _execute_unit(
        self,
        plan: ArtifactExecutionPlan,
        unit: ArtifactExecutionUnit,
    ) -> ArtifactExecutionStatus:
        """Execute a single artifact execution unit.

        Args:
            plan: The full artifact execution plan
            unit: The unit to execute

        Returns:
            Updated ArtifactExecutionStatus
        """
        status = self._status_map.get(unit.artifact_execution_id)
        if not status:
            return status

        # Check if dependencies are satisfied
        deps_satisfied = self._check_dependencies(plan, unit)
        if not deps_satisfied:
            self._transition_state(
                status,
                ExecutionState.BLOCKED,
                "Dependencies not satisfied",
            )
            return status

        # Transition to RUNNING
        self._transition_state(
            status,
            ExecutionState.RUNNING,
            "Starting execution",
        )
        status.started_at = datetime.now(timezone.utc).isoformat()

        # Execute using generation engine
        try:
            result = self.generation_engine.generate_single(unit, plan)

            if result.success:
                self._transition_state(
                    status,
                    ExecutionState.COMPLETED,
                    "Execution succeeded",
                )
                status.success = True
                status.content = result.content
                status.file_written = result.file_written
                status.written_path = result.written_path
                status.content_hash = result.content_hash or ""

                # Record errors if any
                if result.errors:
                    status.errors = tuple(result.errors)
            else:
                self._transition_state(
                    status,
                    ExecutionState.FAILED,
                    f"Execution failed: {result.errors[0] if result.errors else 'Unknown error'}",
                )
                status.errors = tuple(result.errors)

                # Propagate failure to dependents
                self._propagate_failure(status, plan)

        except Exception as e:
            self._transition_state(
                status,
                ExecutionState.FAILED,
                f"Exception: {str(e)}",
            )
            status.errors = (str(e),)
            self._propagate_failure(status, plan)

        status.completed_at = datetime.now(timezone.utc).isoformat()
        if status.started_at:
            start_dt = datetime.fromisoformat(status.started_at)
            end_dt = datetime.fromisoformat(status.completed_at)
            status.duration_ms = (end_dt - start_dt).total_seconds() * 1000

        # Update status map
        self._status_map[unit.artifact_execution_id] = status
        return status

    def _check_dependencies(
        self,
        plan: ArtifactExecutionPlan,
        unit: ArtifactExecutionUnit,
    ) -> bool:
        """Check if all dependencies for a unit are satisfied."""
        for inp in unit.required_inputs:
            # Find source unit
            source_unit = None
            for u in plan.execution_units:
                if u.artifact_id == inp.source_artifact_id:
                    source_unit = u
                    break

            if not source_unit:
                continue

            source_status = self._status_map.get(source_unit.artifact_execution_id)
            if not source_status:
                return False

            # Check if source completed successfully
            if source_status.state != ExecutionState.COMPLETED:
                return False

        return True

    def _propagate_failure(
        self,
        failed_status: ArtifactExecutionStatus,
        plan: ArtifactExecutionPlan,
    ) -> None:
        """Propagate failure to dependent artifacts."""
        # Find all units that depend on this failed unit
        failed_unit = None
        for unit in plan.execution_units:
            if unit.artifact_execution_id == failed_status.artifact_execution_id:
                failed_unit = unit
                break

        if not failed_unit:
            return

        # Find dependents
        for unit in plan.execution_units:
            for inp in unit.required_inputs:
                if inp.source_artifact_id == failed_unit.artifact_id:
                    dep_status = self._status_map.get(unit.artifact_execution_id)
                    if dep_status and dep_status.state == ExecutionState.QUEUED:
                        self._transition_state(
                            dep_status,
                            ExecutionState.BLOCKED,
                            f"Blocked by failed dependency: {failed_status.artifact_execution_id}",
                        )

    def _transition_state(
        self,
        status: ArtifactExecutionStatus,
        new_state: ExecutionState,
        reason: str,
    ) -> None:
        """Transition a status to a new state."""
        transition = ExecutionStateTransition(
            artifact_execution_id=status.artifact_execution_id,
            from_state=status.state,
            to_state=new_state,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason=reason,
        )

        # Update status fields
        status.state = new_state
        status.state_history = status.state_history + (transition,)

    def _build_report(
        self,
        plan: ArtifactExecutionPlan,
        execution_started: str,
        start_time: float,
    ) -> ExecutionReport:
        """Build the final execution report."""
        total_duration = (time.time() - start_time) * 1000
        execution_completed = datetime.now(timezone.utc).isoformat()

        # Count results
        successful = sum(1 for s in self._status_map.values() if s.success)
        failed = sum(1 for s in self._status_map.values() if s.state == ExecutionState.FAILED)
        blocked = sum(1 for s in self._status_map.values() if s.state == ExecutionState.BLOCKED)
        skipped = sum(1 for s in self._status_map.values() if s.state == ExecutionState.SKIPPED)
        files_written = sum(1 for s in self._status_map.values() if s.file_written)

        # Build dependency failures
        dep_failures = []
        for status in self._status_map.values():
            if status.state == ExecutionState.FAILED:
                affected = [
                    s.artifact_execution_id
                    for s in self._status_map.values()
                    if s.state == ExecutionState.BLOCKED
                ]
                if affected:
                    dep_failures.append(DependencyFailureInfo(
                        failed_artifact_execution_id=status.artifact_execution_id,
                        affected_artifact_execution_ids=tuple(affected),
                        reason=status.errors[0] if status.errors else "Unknown",
                    ))

        # Collect all errors
        all_errors = []
        for status in self._status_map.values():
            all_errors.extend(status.errors)

        report = ExecutionReport(
            report_id=f"exec-{plan.plan_id[:8]}",
            plan_id=plan.plan_id,
            mission_id=plan.mission_id,
            total_artifacts=len(plan.execution_units),
            successful_artifacts=successful,
            failed_artifacts=failed,
            blocked_artifacts=blocked,
            skipped_artifacts=skipped,
            total_files_written=files_written,
            total_waves=len(plan.execution_waves),
            waves_executed=len(self._wave_results),
            wave_results=tuple(self._wave_results),
            artifact_results=tuple(self._status_map.values()),
            dependency_failures=tuple(dep_failures),
            errors=tuple(all_errors),
            cycle_result=CycleDetectionResult(
                cycle_detected=False,
                cycle_path=(),
                involved_edges=(),
                message="No cycles detected",
            ),
            execution_started=execution_started,
            execution_completed=execution_completed,
            total_duration_ms=total_duration,
            is_complete=True,
            is_success=failed == 0 and blocked == 0,
            is_partial_success=successful > 0 and (failed > 0 or blocked > 0),
            is_cancelled=False,
            deterministic=True,
            deterministic_hash="",
        )

        # Compute hash
        report.deterministic_hash = compute_report_hash(report)

        return report

    def _create_cycle_report(
        self,
        plan: ArtifactExecutionPlan,
        cycle_result: CycleDetectionResult,
        execution_started: str,
        start_time: float,
    ) -> ExecutionReport:
        """Create a report when cycle is detected."""
        total_duration = (time.time() - start_time) * 1000
        execution_completed = datetime.now(timezone.utc).isoformat()

        return ExecutionReport(
            report_id=f"exec-{plan.plan_id[:8]}",
            plan_id=plan.plan_id,
            mission_id=plan.mission_id,
            total_artifacts=len(plan.execution_units),
            successful_artifacts=0,
            failed_artifacts=0,
            blocked_artifacts=len(cycle_result.cycle_path),
            skipped_artifacts=0,
            total_files_written=0,
            total_waves=len(plan.execution_waves),
            waves_executed=0,
            wave_results=(),
            artifact_results=tuple(self._status_map.values()),
            dependency_failures=(),
            errors=(f"Dependency cycle detected: {cycle_result.message}",),
            cycle_result=cycle_result,
            execution_started=execution_started,
            execution_completed=execution_completed,
            total_duration_ms=total_duration,
            is_complete=False,
            is_success=False,
            is_partial_success=False,
            is_cancelled=False,
            deterministic=True,
            deterministic_hash="",
        )

    def get_progress(self) -> ExecutionProgress:
        """Get current execution progress.

        Returns:
            ExecutionProgress with current state
        """
        total = len(self._status_map)
        completed = sum(1 for s in self._status_map.values()
                       if s.state in (ExecutionState.COMPLETED, ExecutionState.FAILED))
        active = sum(1 for s in self._status_map.values()
                     if s.state == ExecutionState.RUNNING)
        successful = sum(1 for s in self._status_map.values() if s.success)
        failed = sum(1 for s in self._status_map.values()
                     if s.state == ExecutionState.FAILED)
        blocked = sum(1 for s in self._status_map.values()
                     if s.state == ExecutionState.BLOCKED)
        files_written = sum(1 for s in self._status_map.values() if s.file_written)

        elapsed = (time.time() - self._execution_start) * 1000 if self._execution_start else 0

        current_wave = 0
        current_artifact = None
        for s in self._status_map.values():
            if s.state == ExecutionState.RUNNING:
                current_artifact = s.artifact_execution_id
                current_wave = s.execution_wave
                break

        return ExecutionProgress(
            current_wave=current_wave,
            total_waves=len(self._wave_results),
            current_artifact=current_artifact,
            completed_artifacts=completed,
            active_artifacts=active,
            total_artifacts=total,
            successful_artifacts=successful,
            failed_artifacts=failed,
            blocked_artifacts=blocked,
            files_written=files_written,
            elapsed_ms=elapsed,
            started_at=datetime.fromtimestamp(self._execution_start, tz=timezone.utc).isoformat()
                       if self._execution_start else None,
            progress_percent=(completed / total * 100) if total > 0 else 0.0,
        )
