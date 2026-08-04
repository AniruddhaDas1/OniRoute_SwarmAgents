from typing import Protocol

from .models import ContextObject, RoutingPlan


class ContextSource(Protocol):
    def build(self, kind: str, identifier: str) -> ContextObject: ...


class ContextDestination(Protocol):
    def put(self, context: ContextObject) -> None: ...


class ContextRoutingContract(Protocol):
    def plan(self, workflow_id: str) -> RoutingPlan: ...
