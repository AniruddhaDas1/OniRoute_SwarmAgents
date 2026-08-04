from .models import ExecutionResult


class ExecutionHistory:
    def __init__(self): self.records: list[ExecutionResult] = []
    def add(self, result: ExecutionResult) -> None: self.records.append(result)
    def all(self) -> tuple[ExecutionResult, ...]: return tuple(self.records)
