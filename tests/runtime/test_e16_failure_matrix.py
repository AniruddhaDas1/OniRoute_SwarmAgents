"""E1.6.12 Failure Matrix verification.

Covers the failure matrix with structured outcomes. Each case must:
- produce a structured failure or correct state transition
- not produce a false success
- not corrupt a final artifact
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.contracts import EngineeringContract
from runtime.engineering import EngineeringWorkerEngine, InvocationPlanner, ResponseAggregator
from runtime.invocation import InvocationEngine, InvocationRequest, StreamChunk
from runtime.invocation.adapters import InterfaceOnlyAdapter, OpenAICompatibleAdapter
from runtime.invocation.dispatcher import InvocationDispatcher
from runtime.invocation.exceptions import InvocationError, StreamConnectionError, StreamUnsupportedError
from runtime.invocation.models import Usage
from runtime.invocation.response import InvocationResponse
from runtime.models import Capability, ModelManager, SelectionRequest
from runtime.models.exceptions import NoCompatibleModelError

ROOT = Path(__file__).parents[2]


def _contract():
    return EngineeringContract(
        contract_id="ctr-fm-001",
        target_path="src/app.py",
        target_type="file",
        assigned_profile_id="prof-fm",
        assigned_profile_role="Backend Engineer",
        engineering_discipline="Backend",
        contract_hash="0" * 64,
    )


def _manager():
    return ModelManager(ROOT / "config" / "models.yaml")


# 1. provider unavailable
def test_failure_provider_unavailable():
    class _Adapter:
        protocol = "mock"
        def invoke(self, model, request):
            raise InvocationError("provider unavailable")
        def stream(self, model, request):
            raise StreamConnectionError("provider unavailable")
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", _Adapter())
    engine = InvocationEngine(_manager(), dispatcher)
    with pytest.raises(InvocationError):
        engine.invoke(InvocationRequest(prompt="Hi"), SelectionRequest())


# 2. model unavailable
def test_failure_model_unavailable():
    manager = _manager()
    # "nonexistent-model" not in catalog.
    with pytest.raises(Exception):
        manager.resolver.find_model("nonexistent-model").id


# 3. capability unavailable
def test_failure_capability_unavailable():
    manager = _manager()
    with pytest.raises(NoCompatibleModelError):
        manager.select_best_model(SelectionRequest(capabilities=frozenset({Capability.VISION})))


# 4. authentication failure
def test_failure_authentication():
    class _Adapter:
        protocol = "mock"
        def invoke(self, model, request):
            raise InvocationError("401 unauthorized")
        def stream(self, model, request):
            raise StreamConnectionError("401 unauthorized")
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", _Adapter())
    engine = InvocationEngine(_manager(), dispatcher)
    with pytest.raises(InvocationError):
        engine.invoke(InvocationRequest(prompt="Hi"), SelectionRequest())


# 5. malformed provider response
def test_failure_malformed_response():
    transport = type("T", (), {
        "post": lambda self, *a, **k: {"unexpected": "shape"},
        "stream": lambda self, *a, **k: (_ for _ in ()).throw(AssertionError("not used")),
    })()
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    with pytest.raises(Exception):
        adapter.invoke(_manager().resolver.find_model("default-local"), InvocationRequest(prompt="Hi"))


# 6. timeout
def test_failure_timeout():
    class _Adapter:
        protocol = "mock"
        def invoke(self, model, request):
            raise InvocationError("timed out")
        def stream(self, model, request):
            raise StreamConnectionError("timed out")
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", _Adapter())
    engine = InvocationEngine(_manager(), dispatcher)
    with pytest.raises(InvocationError):
        engine.invoke(InvocationRequest(prompt="Hi"), SelectionRequest())


# 7. stream interruption
def test_failure_stream_interruption():
    class _Adapter:
        protocol = "mock"
        def invoke(self, model, request):
            raise AssertionError("not used")
        def stream(self, model, request):
            yield StreamChunk(sequence=0, delta="partial", provider=model.provider, model=model.id)
            raise StreamConnectionError("connection reset")
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", _Adapter())
    engine = InvocationEngine(_manager(), dispatcher)
    collected = []
    with pytest.raises(StreamConnectionError):
        for chunk in engine.stream(InvocationRequest(prompt="Hi"), SelectionRequest()):
            collected.append(chunk)
    assert collected[0].delta == "partial"


# 8. empty model response
def test_failure_empty_model_response():
    class _Adapter:
        protocol = "mock"
        def invoke(self, model, request):
            return InvocationResponse(text="", usage=Usage(), finish_reason="stop")
        def stream(self, model, request):
            yield StreamChunk(sequence=0, delta="", finish_reason="stop", provider=model.provider, model=model.id)
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", _Adapter())
    engine = InvocationEngine(_manager(), dispatcher)
    resp = engine.invoke(InvocationRequest(prompt="Hi"), SelectionRequest())
    assert resp.text == ""


# 9. dependent task failure — existing fallback behavior
def test_failure_dependent_task():
    """Impl failure is recorded; fallback template satisfies the dependency.

    This verifies the EXISTING E1.3 fallback design, not a new architecture.
    The failed task is recorded in evidence.failures while fallback content
    lets the dependent doc task proceed.
    """
    class _FailAdapter:
        protocol = "mock"
        def invoke(self, model, request):
            raise InvocationError("impl failed")
        def stream(self, model, request):
            raise AssertionError("not used")
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", _FailAdapter())
    engine = InvocationEngine(_manager(), dispatcher)
    worker = EngineeringWorkerEngine(invocation_engine=engine)
    import tempfile
    with tempfile.TemporaryDirectory() as ws:
        result = worker.execute_contract(_contract(), ws)
        failures = result.evidence.get("failures", [])
        assert any(f["task_id"] == "task-impl-ctr-fm-001" for f in failures)
        # The fallback path marks the impl task complete for dependency purposes,
        # so the doc task is not blocked in the current design.
        assert "blocked_tasks" not in result.evidence or not result.evidence.get("blocked_tasks")
        # The impl failure is NOT silently converted to success — it remains in failures.
        assert any(f["error_message"] == "impl failed" for f in failures)


# 10. unsupported streaming
def test_failure_unsupported_streaming():
    adapter = InterfaceOnlyAdapter("http://x")
    with pytest.raises(StreamUnsupportedError):
        list(adapter.stream(_manager().resolver.find_model("default-local"), InvocationRequest(prompt="Hi", streaming=True)))


# 11. invalid execution context
def test_failure_invalid_execution_context():
    from runtime.engineering.models import TaskContext
    with pytest.raises(Exception):
        TaskContext()  # missing required engineering_contract_id


# 12. workspace boundary violation
def test_failure_workspace_boundary():
    worker = EngineeringWorkerEngine(invocation_engine=InvocationEngine(_manager(), InvocationDispatcher()))
    from runtime.engineering.exceptions import EngineeringBoundaryViolation
    import tempfile
    with tempfile.TemporaryDirectory() as ws:
        with pytest.raises(EngineeringBoundaryViolation):
            worker._enforce_boundary_safety(
                "../../etc/passwd",
                (Path(ws) / "../../etc/passwd").resolve(),
                Path(ws).resolve(),
            )
