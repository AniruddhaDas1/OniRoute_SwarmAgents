from .models import ContextObject


class InMemoryContextStorage:
    def __init__(self): self._contexts: dict[str, ContextObject] = {}

    def put(self, context: ContextObject) -> None: self._contexts[context.context_id] = context

    def get(self, context_id: str) -> ContextObject | None: return self._contexts.get(context_id)

    def remove(self, context_id: str) -> None: self._contexts.pop(context_id, None)

    def clear(self) -> None: self._contexts.clear()
