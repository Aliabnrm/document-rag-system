import pytest

from app.modules.ingestion.domain import (
    IngestionJobState,
    IngestionJobStatus,
    InvalidJobTransitionError,
)


def test_transient_failure_can_schedule_retry() -> None:
    state = IngestionJobState(IngestionJobStatus.RUNNING)

    state = state.transition_to(IngestionJobStatus.RETRY_SCHEDULED)
    state = state.transition_to(IngestionJobStatus.RUNNING)

    assert state.status is IngestionJobStatus.RUNNING


def test_successful_job_cannot_run_again() -> None:
    state = IngestionJobState(IngestionJobStatus.SUCCEEDED)

    with pytest.raises(InvalidJobTransitionError):
        state.transition_to(IngestionJobStatus.RUNNING)
