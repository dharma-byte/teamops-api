import pytest

from app.models.task import TaskStatus
from app.services.task_service import DirectDoneTransitionError, ensure_not_direct_done_transition


def test_direct_done_transition_is_rejected() -> None:
    """The checkpoint: a task cannot reach Done via a plain PATCH, regardless
    of who's calling — only approve_task() (Manager+, via the approval
    workflow) is allowed to set status=done. This is the exact guard
    update_task_endpoint calls before touching the database.
    """
    with pytest.raises(DirectDoneTransitionError):
        ensure_not_direct_done_transition({"status": TaskStatus.DONE})


@pytest.mark.parametrize(
    "updates",
    [
        {"status": TaskStatus.IN_PROGRESS},
        {"status": TaskStatus.IN_REVIEW},
        {"title": "Renamed, no status change"},
        {},
    ],
)
def test_other_transitions_are_allowed(updates: dict[str, object]) -> None:
    ensure_not_direct_done_transition(updates)  # should not raise
