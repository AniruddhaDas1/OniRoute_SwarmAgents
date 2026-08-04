from enum import StrEnum


class ExecutionStatus(StrEnum):
    PENDING = "Pending"
    READY = "Ready"
    RUNNING = "Running"
    WAITING = "Waiting"
    COMPLETED = "Completed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    CANCELLED = "Cancelled"
    ROLLBACK = "Rollback"
