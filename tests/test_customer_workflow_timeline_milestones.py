"""Customer workflow milestone regression tests.

Status-less workflow milestones must not contradict the persisted job state.
"""
from app.engines.admin_catalog.workflow_steps import annotate_progress, to_client_stages


def _step(key: str, label: str, status: str | None = None) -> dict:
    return {
        "step_key": key,
        "step_name": label,
        "maps_to_status": status,
        "customer_visible": True,
    }


STEPS = [
    _step("booking_created", "Booking Created"),
    _step("provider_accepted", "Provider Accepted"),
    _step("technician_assigned", "Technician Assigned", "assigned"),
    _step("on_the_way", "On The Way", "on_the_way"),
]


def test_provider_acceptance_marks_creation_done_and_technician_upcoming():
    annotated = annotate_progress(STEPS, "accepted", {"accepted"})
    assert [step["state"] for step in annotated] == [
        "done", "current", "pending", "pending",
    ]
    client = to_client_stages(annotated)
    assert [step["state"] for step in client] == [
        "completed", "current", "upcoming", "upcoming",
    ]


def test_technician_assignment_advances_without_skipping_provider():
    annotated = annotate_progress(STEPS, "assigned", {"accepted", "assigned"})
    assert [step["state"] for step in annotated] == [
        "done", "done", "current", "pending",
    ]
