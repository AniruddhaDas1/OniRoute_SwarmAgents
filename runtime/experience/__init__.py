"""Execution Experience Subsystem Package (Phase P6.D2).

Presentation-agnostic event distribution, CLI rendering, and session watching interface.
"""

from runtime.experience.adapter import PresentationAdapter
from runtime.experience.models import SessionStatusReport, StreamEvent, StreamEventType
from runtime.experience.recovery import SessionRecoveryWatcher
from runtime.experience.renderer import ExecutionRenderer
from runtime.experience.stream import ExecutionEventStream

__all__ = [
    "ExecutionEventStream",
    "PresentationAdapter",
    "ExecutionRenderer",
    "SessionRecoveryWatcher",
    "StreamEvent",
    "StreamEventType",
    "SessionStatusReport",
]
