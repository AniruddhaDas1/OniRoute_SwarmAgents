from __future__ import annotations

from typing import Any

from .models import ContextObject


class ContextFilter:
    def apply(self, context: ContextObject, *, allow: set[str] | None = None, block: set[str] | None = None, redact: set[str] | None = None, min_priority: int = 0, scopes: set[str] | None = None, compress: bool = False, summarize: bool = False) -> ContextObject:
        if context.priority < min_priority or (scopes and not scopes.intersection(context.scope)):
            return context.model_copy(update={"data": {}})
        data: dict[str, Any] = dict(context.data)
        if allow is not None: data = {key: value for key, value in data.items() if key in allow}
        for key in block or set(): data.pop(key, None)
        sensitive = set(context.sensitive_fields) | set(redact or set())
        for key in sensitive:
            if key in data: data[key] = "[REDACTED]"
        if compress: data = {key: value for key, value in data.items() if value not in (None, "", [], {}, ())}
        if summarize: data["_summary"] = "Summarization requested; no AI summarization performed."
        return context.model_copy(update={"data": data})
