from dataclasses import dataclass
from enum import StrEnum


class IngestionJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"


ALLOWED_JOB_TRANSITIONS: dict[IngestionJobStatus, frozenset[IngestionJobStatus]] = {
    IngestionJobStatus.PENDING: frozenset({IngestionJobStatus.RUNNING, IngestionJobStatus.FAILED}),
    IngestionJobStatus.RUNNING: frozenset(
        {
            IngestionJobStatus.SUCCEEDED,
            IngestionJobStatus.FAILED,
            IngestionJobStatus.RETRY_SCHEDULED,
        }
    ),
    IngestionJobStatus.RETRY_SCHEDULED: frozenset(
        {IngestionJobStatus.RUNNING, IngestionJobStatus.FAILED}
    ),
    IngestionJobStatus.SUCCEEDED: frozenset(),
    IngestionJobStatus.FAILED: frozenset({IngestionJobStatus.RETRY_SCHEDULED}),
}


class InvalidJobTransitionError(ValueError):
    def __init__(self, current: IngestionJobStatus, target: IngestionJobStatus) -> None:
        super().__init__(f"Cannot transition ingestion job from {current} to {target}")
        self.current = current
        self.target = target


@dataclass(frozen=True, slots=True)
class IngestionJobState:
    status: IngestionJobStatus

    def transition_to(self, target: IngestionJobStatus) -> "IngestionJobState":
        if target not in ALLOWED_JOB_TRANSITIONS[self.status]:
            raise InvalidJobTransitionError(self.status, target)
        return IngestionJobState(status=target)
