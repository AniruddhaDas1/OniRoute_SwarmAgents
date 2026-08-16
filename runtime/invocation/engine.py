from runtime.models import ModelManager, SelectionRequest

from .dispatcher import InvocationDispatcher
from .exceptions import StreamUnsupportedError
from .models import StreamChunk
from .request import InvocationRequest
from .retry import RetryPolicy, with_retry
from .router import InvocationRouter
from runtime.governance import AuditEngine, BudgetLimits, BudgetTracker, Decision, GovernanceRequest, PolicyEngine


class InvocationEngine:
    def __init__(self, manager: ModelManager, dispatcher: InvocationDispatcher, governance: PolicyEngine | None = None):
        self.manager = manager; self.dispatcher = dispatcher; self.router = InvocationRouter(manager)
        self.governance = governance or PolicyEngine({"permission_defaults": [], "approval_defaults": "Automatic", "risk_threshold": 100}, BudgetTracker(BudgetLimits()), AuditEngine())

    def invoke(self, request: InvocationRequest, selection: SelectionRequest, model_id: str | None = None, retry: RetryPolicy | None = None):
        model = self.router.route(selection, model_id)
        decision = self.governance.authorize(GovernanceRequest(kind="model", model=model.id, provider=model.provider, protocol=model.protocol, capabilities=frozenset(x.value for x in request.capabilities), estimated_tokens=request.max_tokens or 0))
        if decision.decision != Decision.ALLOW:
            raise PermissionError(f"Invocation denied: {decision.decision}: {decision.reasons}")
        adapter = self.dispatcher.dispatch(model.protocol)
        response = with_retry(lambda: adapter.invoke(model, request), retry or RetryPolicy())
        return response.model_copy(update={"metadata": {**response.metadata, "model": model.id, "provider": model.provider, "protocol": model.protocol}})

    def stream(self, request: InvocationRequest, selection: SelectionRequest, model_id: str | None = None):
        """Propagate real incremental provider chunks through to callers.

        ``invoke()`` is NOT used as a streaming implementation. Each provider
        chunk is yielded verbatim from ``ProtocolAdapter.stream()`` and enriched
        with provider/model/protocol metadata when the adapter did not carry it.

        If the selected provider does not implement real streaming, a single
        structured ``StreamChunk`` is emitted with
        ``finish_reason="streaming_unsupported"`` instead of simulating data.
        """
        model = self.router.route(selection, model_id)
        decision = self.governance.authorize(GovernanceRequest(kind="model", model=model.id, provider=model.provider, protocol=model.protocol, capabilities=frozenset(x.value for x in request.capabilities), estimated_tokens=request.max_tokens or 0))
        if decision.decision != Decision.ALLOW:
            raise PermissionError(f"Invocation denied: {decision.decision}: {decision.reasons}")
        adapter = self.dispatcher.dispatch(model.protocol)
        try:
            raw_chunks = adapter.stream(model, request)
        except StreamUnsupportedError as exc:
            yield StreamChunk(
                sequence=0,
                delta="",
                provider=model.provider,
                model=model.id,
                protocol=model.protocol,
                finish_reason="streaming_unsupported",
                metadata={"unsupported": True, "error": str(exc)},
            )
            return
        for chunk in raw_chunks:
            updates = {}
            if not chunk.provider:
                updates["provider"] = model.provider
            if not chunk.model:
                updates["model"] = model.id
            if not chunk.protocol:
                updates["protocol"] = model.protocol
            if updates:
                chunk = chunk.model_copy(update=updates)
            yield chunk
