import pytest
from app.engines.admin_catalog.workflow_steps import (
    validate_workflow_steps, check_definition, check_capability_alignment,
    annotate_progress, validate_steps,
)


def step(key, status=None):
    return {"step_key": key, "step_name": key, "maps_to_status": status}


def test_empty_journey_is_optional_with_standard_approval():
    assert validate_workflow_steps([], []) == ([], [])
    assert check_definition([], [])["valid"]
    assert check_capability_alignment({"quote_approval_required": True, "steps_json": []}) == []


def test_custom_journey_still_requires_visible_approval_stage():
    assert check_capability_alignment({"quote_approval_required": True, "steps_json": [step("assigned", "assigned")]})


def test_duplicate_statuses_are_rejected_before_publishing():
    with pytest.raises(ValueError, match="ambiguous"):
        validate_workflow_steps([step("one", "assigned"), step("two", "assigned")], [])


def test_impossible_status_transition_is_rejected_before_publishing():
    with pytest.raises(ValueError, match="can never fire"):
        validate_workflow_steps([step("one", "assigned"), step("two", "completed")], [
            {"from_step_key": "one", "to_step_key": "two", "allowed_role": "technician"}])


@pytest.mark.parametrize("sla", [-1, 0, 1.5, True, "bad"])
def test_invalid_sla_is_rejected(sla):
    with pytest.raises(ValueError, match="positive whole"):
        validate_steps([{**step("one"), "sla_minutes": sla}])


def test_partial_journey_does_not_mark_future_completion_skipped():
    result = annotate_progress([step("one", "assigned"), step("two", "completed")], "on_the_way", {"assigned", "on_the_way"})
    assert [s["state"] for s in result] == ["done", "pending"]


def test_skipped_stage_before_a_mapped_current_stage_stays_skipped():
    result = annotate_progress([step("one", "assigned"), step("two", "on_the_way"), step("three", "completed")], "on_the_way", {"on_the_way"})
    assert [s["state"] for s in result] == ["skipped", "current", "pending"]


def test_descriptive_metadata_is_not_advertised_as_enforced():
    review = check_definition([{**step("one", "assigned"), "owner_app": "staff_app", "requires_photo": True}], [])
    assert any("descriptive only" in warning for warning in review["warnings"])
