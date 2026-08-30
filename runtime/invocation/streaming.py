"""Runtime Streaming facade (Phase E1.5).

Provides an ordered chunk iterator facade and an assembler that reconstructs
final content + accounting from a sequence of *real* ``StreamChunk`` objects.

This module never synthesizes content. An empty delta with a ``finish_reason``
is only surfaced when the provider emits that terminal event.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from collections.abc import Iterator
from typing import Iterable, Optional

from .models import StreamChunk, StreamFinishReason, StreamUsage


@dataclass
class StreamAssembly:
    """Immutable-ish summary assembled from a real provider chunk sequence."""
    content: str
    sequences: list[int]
    finish_reason: Optional[str]
    usage: Optional[StreamUsage]
    chunk_count: int
    chunk_deltas: list[str] = field(default_factory=list)


class StreamResponse:
    """Iterable facade over an ordered provider chunk stream.

    Wraps the iterator returned by ``InvocationEngine.stream()`` (or an
    adapter) so callers can consume chunks in order while optionally draining
    them into a final assembly.
    """

    def __init__(self, chunks: Iterable[StreamChunk]) -> None:
        self._chunks = chunks
        self._buffer: deque[StreamChunk] = deque()

    def __iter__(self) -> Iterator[StreamChunk]:
        return iter(self._chunks)

    def iter_chunks(self) -> Iterator[StreamChunk]:
        return iter(self._chunks)


def assemble_stream(chunks: Iterable[StreamChunk]) -> StreamAssembly:
    """Assemble an iterable of real ``StreamChunk`` objects.

    Accumulates ``delta`` values in arrival order, captures the provider's
    last non-null ``finish_reason`` and the last emitted ``usage``. No content
    is synthesized; chunks with an empty delta simply contribute no text.
    """
    content_parts: list[str] = []
    sequences: list[int] = []
    chunk_deltas: list[str] = []
    finish_reason: Optional[str] = None
    usage: Optional[StreamUsage] = None
    count = 0

    for chunk in chunks:
        count += 1
        sequences.append(chunk.sequence)
        chunk_deltas.append(chunk.delta)
        if chunk.delta:
            content_parts.append(chunk.delta)
        if chunk.finish_reason:
            finish_reason = chunk.finish_reason
        if chunk.usage is not None:
            usage = chunk.usage

    return StreamAssembly(
        content="".join(content_parts),
        sequences=sequences,
        finish_reason=finish_reason or StreamFinishReason.STOP.value,
        usage=usage,
        chunk_count=count,
        chunk_deltas=chunk_deltas,
    )
