from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    model_config = ConfigDict(frozen=True); role: str; content: str
class ToolRequest(BaseModel):
    model_config = ConfigDict(frozen=True); name: str; arguments: dict[str, Any] = Field(default_factory=dict)
class ToolCall(BaseModel):
    model_config = ConfigDict(frozen=True); id: str | None = None; name: str; arguments: dict[str, Any] = Field(default_factory=dict)
class Usage(BaseModel):
    model_config = ConfigDict(frozen=True); input_tokens: int = 0; output_tokens: int = 0; total_tokens: int = 0


class StreamFinishReason(StrEnum):
    """Finish reasons that a streaming provider may report."""
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    STREAMING_UNSUPPORTED = "streaming_unsupported"


class StreamUsage(BaseModel):
    """Token usage as reported by a streaming provider.

    Fields are optional because many streaming providers do not emit usage
    per-chunk. Do NOT invent values; leave a field ``None`` when the provider
    does not supply it.
    """
    model_config = ConfigDict(frozen=True)
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    input_tokens_details: dict[str, Any] | None = None
    output_tokens_details: dict[str, Any] | None = None

    def to_usage(self) -> "Usage":
        """Convert to the canonical non-streaming Usage contract.

        ``None`` provider values are normalized to ``0`` so callers using the
        canonical contract never receive ``None``, while the streaming contract
        faithfully records provider absence.
        """
        return Usage(
            input_tokens=self.input_tokens or 0,
            output_tokens=self.output_tokens or 0,
            total_tokens=self.total_tokens if self.total_tokens is not None
            else (self.input_tokens or 0) + (self.output_tokens or 0),
        )


class StreamChunk(BaseModel):
    """Immutable incremental streaming chunk received from a provider.

    One ``StreamChunk`` corresponds to exactly one actual provider SSE / ndjson
    event. The runtime never synthesizes content-bearing chunks; an empty delta
    with a real ``finish_reason`` is only emitted when the provider itself
    emits that terminal event (carrying real usage/finish metadata).
    """
    model_config = ConfigDict(frozen=True)

    sequence: int = Field(default=0, ge=0, description="Zero-based monotonic sequence index")
    delta: str = Field(default="", description="Incremental content delta from the provider")
    provider: str = Field(default="", description="Provider identifier (model.provider)")
    model: str = Field(default="", description="Model identifier (model.id)")
    protocol: str = Field(default="", description="Protocol identifier (model.protocol)")
    finish_reason: str | None = Field(default=None, description="Provider-reported finish reason, when supplied")
    usage: StreamUsage | None = Field(default=None, description="Usage supplied with a terminal provider event, when supplied")
    latency_ms: float = Field(default=0.0, description="Milliseconds elapsed for this single chunk at the adapter")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO-8601 UTC timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Provider-specific metadata carried through from the event")
