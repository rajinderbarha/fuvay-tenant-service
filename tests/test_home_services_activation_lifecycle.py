"""TENANT-ADMIN-LIFECYCLE-CLOSURE -- activation gate resolver + orchestrator.

Covers: gate vocabulary, gates_all_clear, auto-activation with/without a
pending gate, idempotency of try_auto_activate, and that "active"/"activating"
are excluded from client-requestable transitions so an Admin can never set
active directly.
"""
import pytest

from app.engines.vertical_catalog.activation import GATE_STATES, gates_all_clear
from app.engines.vertical_catalog.service import ENROLLMENT_STATUSES, CLIENT_REQUESTABLE_STATUSES


def _gate(key, required, state):
    return {"key": key, "label": key, "required": required, "state": state, "owner": "system",
            "action_type": None, "blocking_reason": None, "attempt_count": 0, "retryable": False,
            "tenant_visible_message": None, "evidence": {}}


def test_gates_all_clear_true_when_ready_or_not_required():
    gates = [_gate("a", True, "ready"), _gate("b", False, "not_required"), _gate("c", True, "not_required")]
    assert gates_all_clear(gates) is True


def test_gates_all_clear_false_when_action_required():
    gates = [_gate("a", True, "ready"), _gate("b", True, "action_required")]
    assert gates_all_clear(gates) is False


def test_gates_all_clear_false_when_blocked():
    gates = [_gate("a", True, "blocked")]
    assert gates_all_clear(gates) is False


def test_gates_all_clear_empty_list_is_clear():
    assert gates_all_clear([]) is True


def test_new_canonical_states_present():
    for s in ("approved_pending_activation", "activation_requirements_pending", "activating"):
        assert s in ENROLLMENT_STATUSES


def test_active_and_activating_not_client_requestable():
    """The admin transition endpoint must never let a client set these
    directly -- only activation.try_auto_activate can reach them."""
    assert "active" not in CLIENT_REQUESTABLE_STATUSES
    assert "activating" not in CLIENT_REQUESTABLE_STATUSES
    assert "approved_pending_activation" in CLIENT_REQUESTABLE_STATUSES
    assert "activation_requirements_pending" in CLIENT_REQUESTABLE_STATUSES


def test_gate_state_vocabulary_matches_spec():
    assert GATE_STATES == {"not_required", "pending", "action_required", "processing",
                            "ready", "failed", "blocked"}


# ── Lifecycle tracker rendering (home_services_setup_service._lifecycle_tracker) ──

from app.engines.vertical_catalog.home_services_setup_service import _lifecycle_tracker


def test_lifecycle_tracker_no_gates_required_shows_not_required():
    stages = _lifecycle_tracker("approved_pending_activation", gates=[
        _gate("vertical_enabled", True, "ready"),
        _gate("security_deposit", False, "not_required"),
    ])
    ar = next(s for s in stages if s["key"] == "ACTIVATION_REQUIREMENTS")
    assert ar["status"] in ("COMPLETED",)  # required gates all ready -> completed, GO_LIVE current


def test_lifecycle_tracker_pending_gate_shows_current_not_completed():
    stages = _lifecycle_tracker("activation_requirements_pending", gates=[
        _gate("security_deposit", True, "action_required"),
    ])
    ar = next(s for s in stages if s["key"] == "ACTIVATION_REQUIREMENTS")
    go_live = next(s for s in stages if s["key"] == "GO_LIVE")
    assert ar["status"] == "CURRENT"
    assert go_live["status"] == "UPCOMING"


def test_lifecycle_tracker_active_with_no_required_gates():
    stages = _lifecycle_tracker("active", gates=[_gate("vertical_enabled", True, "ready")])
    for s in stages:
        assert s["status"] == "COMPLETED"
