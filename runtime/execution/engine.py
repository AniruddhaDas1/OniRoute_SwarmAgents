from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from runtime.core_models import RepositoryRegistry
from runtime.invocation.adapters import OllamaAdapter, OpenAICompatibleAdapter
from runtime.invocation.dispatcher import InvocationDispatcher
from runtime.invocation.engine import InvocationEngine
from runtime.models import ModelManager
from runtime.workspace import (
    ArtifactRouter,
    ExecutionHistoryStorage,
    LogStorage,
    ReportStorage,
    SessionStorage,
    TraceStorage,
    WorkspaceMetadata,
    WorkspaceStorage,
    assert_no_engine_write,
)

from .ai import AIStepRunner
from .artifacts import ArtifactGenerator
from .events import EventBus
from .executor import DeterministicExecutor
from .history import ExecutionHistory
from .models import ExecutionPlan, ExecutionResult
from .planner import ExecutionPlanner
from .state import ExecutionStatus


class WorkflowEngine:
    """Deterministic local Workflow execution engine.

    When ``workspace_metadata`` is supplied and the workspace root is
    physically separate from the engine root, all runtime outputs are
    automatically persisted inside the workspace ``.oniroute/`` tree via
    :class:`ArtifactRouter`, :class:`WorkspaceStorage`, and the engine-safety
    guards.  Execution behaviour is unchanged — only the storage location
    differs.
    """

    def __init__(
        self,
        registry: RepositoryRegistry,
        workspace_metadata: WorkspaceMetadata | None = None,
    ) -> None:
        self.registry = registry
        self.planner = ExecutionPlanner(registry)
        self._counter = 0
        self.ai_runner = None

        # ── workspace storage wiring ──────────────────────────────────
        self._workspace_metadata = workspace_metadata
        self._workspace_storage: WorkspaceStorage | None = None
        self._history_storage: ExecutionHistoryStorage | None = None
        self._trace_storage: TraceStorage | None = None
        self._log_storage: LogStorage | None = None
        self._session_storage: SessionStorage | None = None
        self._artifact_router: ArtifactRouter | None = None
        self._report_storage: ReportStorage | None = None

        use_workspace = (
            workspace_metadata is not None
            and workspace_metadata.workspace_root != workspace_metadata.engine_root
        )
        if use_workspace:
            self._workspace_storage = WorkspaceStorage(workspace_metadata)
            self._history_storage = ExecutionHistoryStorage(workspace_metadata)
            self._trace_storage = TraceStorage(workspace_metadata)
            self._log_storage = LogStorage(workspace_metadata)
            self._session_storage = SessionStorage(workspace_metadata)
            self._artifact_router = ArtifactRouter(workspace_metadata)
            self._report_storage = ReportStorage(workspace_metadata)

        # Wire storage into the in-memory components so that every
        # add / emit / generate call also persists when storage is active.
        self.history = ExecutionHistory(history_storage=self._history_storage)
        self.events = EventBus(trace_storage=self._trace_storage)
        self.artifacts = ArtifactGenerator(
            artifact_router=self._artifact_router,
            workspace_metadata=self._workspace_metadata,
        )

        # ── AI runner setup (unchanged) ──────────────────────────────
        config = registry.root / "config/models.yaml"
        if config.exists():
            manager = ModelManager(config)
            dispatcher = InvocationDispatcher()
            endpoint = manager.config.get("endpoint", "http://127.0.0.1:11434")
            dispatcher.register("openai-compatible", OpenAICompatibleAdapter(endpoint))
            dispatcher.register("ollama", OllamaAdapter(endpoint))
            dispatcher.register("local-process", OllamaAdapter(endpoint))
            self.ai_runner = AIStepRunner(
                InvocationEngine(manager, dispatcher),
                manager.config.get("approval_defaults", "Dry Run"),
                manager.config.get("optimization", {}),
            )

    # ── public API ───────────────────────────────────────────────────

    def plan(self, workflow_id: str) -> ExecutionPlan:
        return self.planner.plan(workflow_id)

    def run(self, workflow_id: str, optimize: bool | None = None) -> ExecutionResult:
        self._counter += 1
        execution_id = f"execution:{workflow_id}:{self._counter}"
        started = datetime.now(timezone.utc)
        plan = self.plan(workflow_id)

        self._init_workspace(execution_id, workflow_id)
        self.events.emit("WorkflowStarted", execution_id, workflow_id)

        try:
            steps = DeterministicExecutor(self.events, self.ai_runner).execute(
                execution_id, plan, optimize
            )
            artifacts = self.artifacts.generate(
                execution_id, plan, steps, self.registry.statistics()
            )
            for artifact in artifacts:
                self.events.emit(
                    "ArtifactGenerated", execution_id, artifact.id,
                    artifact_type=artifact.type,
                )

            optimization = tuple(
                step.ai_trace["optimization"]
                for step in steps
                if step.ai_trace and step.ai_trace.get("optimization")
            )
            completed = datetime.now(timezone.utc)
            result = ExecutionResult(
                execution_id=execution_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.COMPLETED,
                plan=plan.model_copy(update={"steps": tuple(steps)}),
                artifacts=artifacts,
                started_at=started,
                completed_at=completed,
                report={
                    "ai_steps": sum(bool(step.skill) for step in steps),
                    "optimization": optimization,
                },
                ai_trace=tuple(step.ai_trace for step in steps if step.ai_trace),
            )

            self._persist_plan(plan, workflow_id)
            self._persist_optimization_report(result, execution_id)
            self.events.emit("WorkflowCompleted", execution_id, workflow_id)
            self.history.add(result)
            if self._log_storage is not None:
                self._log_storage.write_log(
                    "INFO", f"Workflow '{workflow_id}' completed: {execution_id}"
                )
            return result
        except Exception as exc:
            self.events.emit("WorkflowFailed", execution_id, workflow_id, error=str(exc))
            if self._log_storage is not None:
                self._log_storage.write_log(
                    "ERROR", f"Workflow '{workflow_id}' failed: {exc}"
                )
            raise

    # ── workspace persistence helpers ───────────────────────────────

    def _init_workspace(self, execution_id: str, workflow_id: str) -> None:
        """Create ``.oniroute/`` subdirectories, write workspace.yaml, and open a session."""
        if not self._workspace_storage:
            return
        self._workspace_storage.ensure_workspace_root()
        for subdir in (
            "sessions", "history", "traces", "artifacts",
            "logs", "reports", "plans", "context", "runtime",
        ):
            self._workspace_storage.ensure_dir(subdir)
        if self._workspace_metadata is not None:
            self._workspace_storage.write_workspace_yaml(self._workspace_metadata)
        self._session_storage.create_session(  # type: ignore[union-attr]
            execution_id,
            {"execution_id": execution_id, "workflow_id": workflow_id},
        )
        self._log_storage.write_log(  # type: ignore[union-attr]
            "INFO", f"Starting workflow '{workflow_id}': {execution_id}"
        )

    def _persist_plan(self, plan: ExecutionPlan, workflow_id: str) -> None:
        """Persist the execution plan to ``.oniroute/plans/``."""
        if not self._workspace_storage or not self._workspace_metadata:
            return
        plans_dir = self._workspace_storage.ensure_dir("plans")
        target = plans_dir / f"{workflow_id}_plan.json"
        assert_no_engine_write(
            target,
            self._workspace_metadata.workspace_root,
            self._workspace_metadata.engine_root,
        )
        with target.open("w", encoding="utf-8") as fh:
            json.dump(plan.model_dump(mode="json"), fh, indent=2, default=str)

    def _persist_optimization_report(
        self, result: ExecutionResult, execution_id: str
    ) -> None:
        """Persist optimization traces from the execution result to ``.oniroute/reports/``."""
        if not self._report_storage:
            return
        optimization = result.report.get("optimization")
        if optimization:
            self._report_storage.persist_report(
                f"{execution_id}:optimization",
                {"optimization_traces": list(optimization)},
                report_type="optimization",
            )
