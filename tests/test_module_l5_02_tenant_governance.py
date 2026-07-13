"""MODULE-L5-02 — tenant-governance guard + state-registry consistency tests."""
import e2e.tenant_governance_guard as g
from app.engines.tenant_engine.constants import TENANT_STATES, VALID_TRANSITIONS


def test_state_registry_covers_all_transitions():
    referenced = set(VALID_TRANSITIONS) | {t for ts in VALID_TRANSITIONS.values() for t in ts}
    assert referenced <= set(TENANT_STATES), referenced - set(TENANT_STATES)


def test_terminated_is_terminal():
    assert VALID_TRANSITIONS.get("terminated", []) == []


def test_guard_passes_on_real_repo():
    res = g.check()
    assert res["state_machine"] == []
    assert res["tenant_scope"] == []
    assert res["single_onboarding"] == []


def test_guard_detects_undeclared_state():
    bad_states = ["active", "suspended"]
    bad_transitions = {"active": ["suspended", "ghost_state"], "suspended": ["active"]}
    findings = g.check_state_machine(bad_states, bad_transitions)
    assert any("ghost_state" in f for f in findings)


def test_guard_detects_self_transition():
    findings = g.check_state_machine(["active"], {"active": ["active"]})
    assert any("self-transition" in f for f in findings)


def test_guard_detects_terminal_with_outgoing():
    findings = g.check_state_machine(
        ["active", "terminated"], {"active": ["terminated"], "terminated": ["active"]}
    )
    assert any("terminal state 'terminated' has outgoing" in f for f in findings)
