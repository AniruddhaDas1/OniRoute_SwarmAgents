from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OptimizationRequest(BaseModel):
    source: Any
    target: str = "model-context"
    budget: int | None = None
    protected: frozenset[str] = Field(default_factory=frozenset)
    modules: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizationPlugin(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str; version: str; capabilities: tuple[str, ...] = (); permissions: tuple[str, ...] = (); trust: str = "Unknown"; health: str = "Unknown"; compatibility: tuple[str, ...] = (); optional: bool = True


class OptimizationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)
    request_id: str; modules: tuple[str, ...]; plugins: tuple[str, ...] = (); budget: int | None = None


class OptimizationMeasurements(BaseModel):
    before_bytes: int = 0; after_bytes: int = 0; estimated_tokens_before: int = 0; estimated_tokens_after: int = 0; latency_ms: float = 0; memory_bytes: int = 0

    @property
    def reduction_ratio(self) -> float:
        return 0 if not self.before_bytes else round(1 - self.after_bytes / self.before_bytes, 4)


class OptimizationReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    request_id: str; actions: tuple[str, ...] = (); removed: tuple[str, ...] = (); preserved: tuple[str, ...] = (); measurements: OptimizationMeasurements; fallback: str | None = None; validated: bool = True


class OptimizedContextEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)
    request_id: str; payload: Any; provenance: tuple[str, ...] = (); report: OptimizationReport


class OptimizationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    envelope: OptimizedContextEnvelope; report: OptimizationReport


class OptimizationBenchmark(BaseModel):
    name: str; results: tuple[OptimizationMeasurements, ...] = (); created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
