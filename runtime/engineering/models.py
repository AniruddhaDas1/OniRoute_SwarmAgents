"""Autonomous Engineering Worker Data Contracts (Phase P5.E1)."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class EngineeringResult(BaseModel):
    """Immutable Engineering Result contract produced by EngineeringWorkerEngine."""

    model_config = ConfigDict(frozen=True)

    result_id: str = Field(..., description="Unique engineering execution result ID (engres-xxxxxx)")
    contract_id: str = Field(..., description="Associated EngineeringContract ID (ctr-xxxxxx)")
    profile_id: str = Field(..., description="Assigned Agent Profile ID")
    modified_files: List[str] = Field(default_factory=list, description="List of relative paths of modified files")
    created_files: List[str] = Field(default_factory=list, description="List of relative paths of created files")
    artifacts: List[str] = Field(default_factory=list, description="List of generated implementation artifact paths")
    execution_time_ms: float = Field(..., description="Execution duration in milliseconds")
    provider: str = Field(default="oniroute-local-engine", description="AI/LLM provider used for generation")
    model: str = Field(default="gemini-2.5-pro", description="AI/LLM model used for generation")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics (prompt, completion, total)")
    cost_usd: float = Field(default=0.0, description="Estimated execution cost in USD")
    trace_references: List[str] = Field(default_factory=list, description="Trace IDs recorded during execution")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Validation evidence, performance metrics, and safety checks")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
    result_hash: str = Field(..., description="SHA-256 hash of engineering result payload")
