"""Agent Execution Engine for OniRoute Agent Runtime (ACR-006 Phase R3).

Consumes READY AgentSessions, validates via Governance, resolves model via UMAL,
delegates AI invocation through the existing InvocationEngine, registers artifacts,
records events, drives state through SessionManager, and returns ExecutionResults.

Does NOT modify Mission, Organization, Workspace, or ExecutionBlueprint.
Does NOT implement parallel execution, retries, recovery, or scheduling.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from runtime.governance import AuditEngine, BudgetLimits, BudgetTracker, Decision, GovernanceRequest, PolicyEngine
from runtime.invocation import InvocationEngine, InvocationRequest, InvocationResponse
from runtime.invocation.adapters import OllamaAdapter, OpenAICompatibleAdapter
from runtime.invocation.dispatcher import InvocationDispatcher
from runtime.models import Capability, ModelManager, SelectionRequest
from runtime.organization.blueprint import ExecutionBlueprint

from .artifact_collector import ArtifactCollector
from .event_recorder import EventRecorder
from .execution_reporter import ExecutionReporter
from .models import (
    AgentSession,
    ArtifactRecord,
    ArtifactType,
    ExecutionEvent,
    ExecutionResult,
    ExecutionStatus,
    RuntimeEventType,
    RuntimeReport,
    RuntimeState,
)
from .session_manager import SessionManager
from .session_registry import SessionRegistry


class AgentExecutionEngine:
    """Core execution engine: reads READY sessions, executes via the Invocation Layer,
    collects artifacts, records events, and drives lifecycle to COMPLETED or FAILED."""

    def __init__(
        self,
        repository_root: Path,
        governance_config: dict | None = None,
        endpoint: str | None = None,
    ) -> None:
        self._repo_root = repository_root
        self._endpoint = endpoint or "http://127.0.0.1:11434"

        # Wire ModelManager (UMAL)
        config_path = repository_root / "config" / "models.yaml"
        self._manager = ModelManager(config_path)

        # Wire Invocation Layer (provider-independent)
        dispatcher = InvocationDispatcher()
        dispatcher.register("openai-compatible", OpenAICompatibleAdapter(self._endpoint))
        dispatcher.register("ollama", OllamaAdapter(self._endpoint))
        dispatcher.register("local-process", OllamaAdapter(self._endpoint))

        # Wire Governance
        cfg = governance_config or {
            "permission_defaults": [],
            "approval_defaults": "Automatic",
            "risk_threshold": 100,
        }
        self._governance = PolicyEngine(cfg, BudgetTracker(BudgetLimits()), AuditEngine())
        self._invocation_engine = InvocationEngine(self._manager, dispatcher, self._governance)

        # Session management components
        self._session_manager = SessionManager()
        self._artifact_collector = ArtifactCollector()
        self._event_recorder = EventRecorder()
        self._reporter = ExecutionReporter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_session(self, session: AgentSession, blueprint: ExecutionBlueprint) -> ExecutionResult:
        """Execute a single READY AgentSession through the full pipeline.

        Pipeline:
          READY → Governance validation → UMAL model selection →
          InvocationEngine → Artifact registration → COMPLETED (or FAILED)
        """
        if session.state != RuntimeState.READY:
            raise ValueError(
                f"Session {session.session_id} is not READY (current: {session.state.value})"
            )

        # 1. Transition READY → RUNNING
        session = self._session_manager.transition_state(session, RuntimeState.RUNNING)

        # Record EXECUTION_STARTED
        self._emit_event(session, RuntimeEventType.EXECUTION_STARTED,
                         "Execution started via Invocation Layer.")

        try:
            # 2. Governance validation
            self._validate_governance(session)

            # 3. Build invocation prompt from session context
            prompt = self._build_prompt(session, blueprint)

            # 4. Resolve capability set for UMAL model selection
            selection = self._build_selection_request(session, blueprint)

            # 5. Invoke via existing InvocationEngine (provider-independent)
            response = self._invocation_engine.invoke(
                InvocationRequest(
                    prompt=prompt,
                    system_prompt=self._build_system_prompt(session),
                    context={
                        "session_id": session.session_id,
                        "member_id": session.member_id,
                        "role": session.role_title,
                        "blueprint_id": session.blueprint_id,
                        "capabilities": session.capability_ids,
                    },
                    max_tokens=4096,
                ),
                selection,
            )

            # 6. Collect execution output as an ArtifactRecord
            artifact = self._register_response_artifact(session, response)

            # Record ARTIFACT_PRODUCED
            self._emit_event(
                session, RuntimeEventType.ARTIFACT_PRODUCED,
                f"Artifact produced: {artifact.artifact_id}",
                payload={"artifact_id": artifact.artifact_id, "artifact_type": artifact.artifact_type},
            )

            # 7. Transition RUNNING → COMPLETED
            session = self._session_manager.transition_state(session, RuntimeState.COMPLETED)
            self._emit_event(session, RuntimeEventType.EXECUTION_COMPLETED,
                             "Execution completed successfully.")

            # 8. Update metrics
            if session.metrics:
                session.metrics.end_time = datetime.now(timezone.utc).isoformat()
                session.metrics.artifact_count = len(session.artifacts)
                session.metrics.event_count = len(session.events)

            return ExecutionResult(
                result_id=f"res-{session.session_id}",
                session_id=session.session_id,
                member_id=session.member_id,
                status=ExecutionStatus.DONE,
                artifacts_produced=[artifact.artifact_id],
                events_recorded=len(session.events),
                summary=(
                    f"{session.role_title} completed: "
                    f"{len(response.text)} chars produced. "
                    f"Tokens: {response.usage.total_tokens}. "
                    f"Latency: {response.latency_ms:.0f}ms."
                ),
                metadata={
                    "model": response.metadata.get("model", "unknown"),
                    "provider": response.metadata.get("provider", "unknown"),
                    "latency_ms": response.latency_ms,
                    "tokens": response.usage.total_tokens,
                },
            )

        except PermissionError as exc:
            # Governance denied
            session = self._session_manager.transition_state(session, RuntimeState.FAILED)
            self._emit_event(session, RuntimeEventType.EXECUTION_FAILED,
                             f"Governance denied execution: {exc}")
            if session.metrics:
                session.metrics.end_time = datetime.now(timezone.utc).isoformat()
                session.metrics.event_count = len(session.events)
            return ExecutionResult(
                result_id=f"res-{session.session_id}",
                session_id=session.session_id,
                member_id=session.member_id,
                status=ExecutionStatus.ERROR,
                events_recorded=len(session.events),
                summary=f"Governance denied: {exc}",
            )

        except Exception as exc:  # noqa: BLE001
            # General execution failure
            try:
                session = self._session_manager.transition_state(session, RuntimeState.FAILED)
            except ValueError:
                pass  # Already in terminal state
            self._emit_event(session, RuntimeEventType.EXECUTION_FAILED,
                             f"Execution failed: {exc}")
            if session.metrics:
                session.metrics.end_time = datetime.now(timezone.utc).isoformat()
                session.metrics.event_count = len(session.events)
            return ExecutionResult(
                result_id=f"res-{session.session_id}",
                session_id=session.session_id,
                member_id=session.member_id,
                status=ExecutionStatus.ERROR,
                events_recorded=len(session.events),
                summary=f"Execution failed: {exc}",
            )

    def execute_all(
        self, blueprint: ExecutionBlueprint, registry: SessionRegistry
    ) -> tuple[list[ExecutionResult], RuntimeReport]:
        """Execute all READY sessions from a registry sequentially."""
        ready_sessions = registry.find_by_state(RuntimeState.READY)
        results: list[ExecutionResult] = []
        all_sessions = registry.list_sessions()

        for session in ready_sessions:
            result = self.execute_session(session, blueprint)
            results.append(result)

        report = self._reporter.compile_report(blueprint, all_sessions)
        return results, report

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _validate_governance(self, session: AgentSession) -> None:
        """Evaluate governance policy before executing an agent session."""
        request = GovernanceRequest(
            kind="agent",
            agent=session.session_id,
            capabilities=frozenset(session.capability_ids),
            permissions=frozenset(["invoke:model"]),
            estimated_tokens=4096,
        )
        result = self._governance.evaluate(request)
        if result.decision == Decision.DENY:
            raise PermissionError(
                f"Governance denied session '{session.session_id}': {', '.join(result.reasons)}"
            )

    def _build_selection_request(
        self, session: AgentSession, blueprint: ExecutionBlueprint
    ) -> SelectionRequest:
        """Map session capabilities to a UMAL SelectionRequest."""
        local_only = blueprint.mission.constraints.local_only if blueprint.mission.constraints else False
        return SelectionRequest(
            capabilities=frozenset(),  # let UMAL pick best available
            local_only=local_only,
            local_preference=self._manager.config.get("local_first", False),
        )

    def _build_system_prompt(self, session: AgentSession) -> str:
        """Construct the system prompt for the agent session."""
        return (
            f"You are {session.role_title} in a professional engineering organization. "
            f"Your responsibilities: {session.metadata.get('primary_responsibility', 'deliver quality work')}. "
            f"You are executing session {session.session_id}. "
            f"Deliver production-quality, concise output."
        )

    def _build_prompt(self, session: AgentSession, blueprint: ExecutionBlueprint) -> str:
        """Build the execution prompt for an agent session from blueprint context."""
        mission_goal = blueprint.mission.requirements.primary_goal
        capabilities_str = ", ".join(session.capability_ids) if session.capability_ids else "general engineering"
        responsibilities = session.metadata.get("responsibilities", [])
        resp_str = "\n".join(f"- {r}" for r in responsibilities) if responsibilities else "- Deliver assigned work"
        return (
            f"Mission Goal: {mission_goal}\n\n"
            f"Your Role: {session.role_title}\n"
            f"Your Capabilities: {capabilities_str}\n\n"
            f"Your Responsibilities:\n{resp_str}\n\n"
            f"Provide a concise, structured execution plan and deliverables for your assigned scope."
        )

    def _register_response_artifact(
        self, session: AgentSession, response: InvocationResponse
    ) -> ArtifactRecord:
        """Convert an InvocationResponse into a registered ArtifactRecord."""
        artifact_id = f"art-{session.session_id}-{uuid.uuid4().hex[:8]}"
        artifact = ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.REPORT,
            owner_session_id=session.session_id,
            owner_member_id=session.member_id,
            capability_id=session.capability_ids[0] if session.capability_ids else "cap-general",
            name=f"{session.role_title} Execution Output",
            description=f"Execution output for {session.role_title} ({session.member_id})",
            lineage=[],
            references=[],
            metadata={
                "model": response.metadata.get("model", "unknown"),
                "provider": response.metadata.get("provider", "unknown"),
                "tokens": response.usage.total_tokens,
                "latency_ms": response.latency_ms,
                "finish_reason": response.finish_reason,
                "text_length": len(response.text),
            },
        )
        self._artifact_collector.register_artifact(session, artifact)
        return artifact

    def _emit_event(
        self,
        session: AgentSession,
        event_type: RuntimeEventType,
        description: str,
        payload: dict | None = None,
    ) -> None:
        """Append an ExecutionEvent to the session via EventRecorder."""
        event = ExecutionEvent(
            event_id=f"ev-{event_type.value}-{session.session_id}-{uuid.uuid4().hex[:6]}",
            event_type=event_type,
            session_id=session.session_id,
            member_id=session.member_id,
            description=description,
            event_payload=payload or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._event_recorder.record_event(session, event)
