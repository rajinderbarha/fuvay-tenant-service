"""Tenant-side enforcement: seats limit the roster, credit suspends it.

Four rules, and the traps each one hides:

  * a technician seat is BOUGHT -- the roster is gated on the plan;
  * the Team surface is LOCKED without a plan, never hidden, so the purchase
    stays reachable;
  * a workspace with no credit has its technicians suspended, and restored on
    top-up -- without disturbing anyone the provider switched off deliberately;
  * new bookings stop at the credit floor, while work already booked finishes.
"""
from __future__ import annotations

import inspect

import pytest


class TestSeatGateCannotBeWalkedPast:
    def test_the_gate_uses_the_shared_predicate(self):
        from app.engines.provider_portal import router
        src = inspect.getsource(router)
        # Lowercasing a designation and comparing it to snake_case keys let
        # every MULTI-WORD title through: "Senior Technician" folded to
        # "senior technician", matched nothing, and consumed no seat.
        assert "is_technician_role(payload.get(\"designation\")" in src
        assert '_desig in ELIGIBLE_DESIGNATIONS' not in src

    def test_multi_word_titles_are_recognised_as_technicians(self):
        from app.engines.home_service_assignment.eligibility import is_technician_role
        for title in ("Technician", "Senior Technician", "Field Engineer", "field-engineer"):
            assert is_technician_role(title, None), title

    def test_a_technician_with_no_designation_still_consumes_a_seat(self):
        from app.engines.home_service_assignment.eligibility import is_technician_role
        assert is_technician_role("", "technician")
        assert is_technician_role(None, "owner_technician")

    def test_a_non_technician_consumes_no_seat(self):
        from app.engines.home_service_assignment.eligibility import is_technician_role
        assert not is_technician_role("Manager", "owner")
        assert not is_technician_role("Dispatcher", "staff")


class TestSeatsAreBought:
    def test_there_is_no_free_seat(self):
        from app.engines.vertical_catalog.seat_enforcement import FREE_STARTER_SEATS
        assert FREE_STARTER_SEATS == 0

    def test_the_team_page_locks_rather_than_hides(self):
        from pathlib import Path
        src = Path("frontend/tenant-portal/app/(tenant)/home-services/team/"
                   "[[...staffId]]/page.tsx").read_text(encoding="utf-8")
        # Hiding the menu would leave no route to the purchase.
        assert "Buy a top-up plan to add technicians" in src
        assert "disabled={noPlan || seatsFull}" in src

    def test_the_team_page_no_longer_names_the_deposit(self):
        from pathlib import Path
        src = Path("frontend/tenant-portal/app/(tenant)/home-services/team/"
                   "[[...staffId]]/page.tsx").read_text(encoding="utf-8")
        assert "deposit_required" not in src


class TestCreditSuspension:
    def test_only_currently_active_members_are_suspended(self):
        from app.engines.vertical_catalog import seat_enforcement
        src = inspect.getsource(seat_enforcement.sync_team_credit_suspension)
        # Suspending someone already inactive would make the restore switch on
        # a person who was deliberately off.
        assert "status = 'active'" in src
        assert "credit_suspended_at IS NULL" in src

    def test_only_auto_suspended_members_are_restored(self):
        from app.engines.vertical_catalog import seat_enforcement
        src = inspect.getsource(seat_enforcement.sync_team_credit_suspension)
        assert "credit_suspended_at IS NOT NULL" in src

    def test_the_marker_is_cleared_on_restore(self):
        from app.engines.vertical_catalog import seat_enforcement
        src = inspect.getsource(seat_enforcement.sync_team_credit_suspension)
        assert "credit_suspended_at = NULL" in src

    def test_suspension_is_driven_by_balance_not_by_the_event(self):
        """Makes it idempotent and safe to run late."""
        from app.engines.vertical_catalog import seat_enforcement
        src = inspect.getsource(seat_enforcement.sync_team_credit_suspension)
        assert "credit_balance" in src

    @pytest.mark.parametrize("hook", [
        "app.engines.execution.usage_credit_deduction",
        "app.engines.vertical_catalog.activation_payment_service",
        "app.jobs.expire_topup_entitlements",
    ])
    def test_every_balance_movement_reconciles_the_team(self, hook):
        import importlib
        src = inspect.getsource(importlib.import_module(hook))
        assert "sync_team_credit_suspension" in src, hook

    def test_a_failed_sync_never_undoes_the_money_movement(self):
        from app.engines.execution import usage_credit_deduction
        src = inspect.getsource(usage_credit_deduction.deduct_for_completed_job)
        sync = src.index("sync_team_credit_suspension")
        assert "except Exception" in src[sync:sync + 400]


class TestBookedWorkStillFinishes:
    def test_the_credit_floor_gates_new_bookings(self):
        from app.engines.home_service_booking import service
        assert "assert_booking_allowed" in inspect.getsource(service)

    def test_assignment_is_not_gated_on_credit(self):
        """Deliberate: stranding a customer who already booked would put the
        cost of the provider's balance on the wrong person."""
        from app.engines.home_service_assignment import service
        src = inspect.getsource(service)
        assert "assert_wip_capacity" in src
        assert "assert_booking_allowed" not in src


class TestBookabilityNoLongerReadsTheDeposit:
    def test_the_dropped_columns_are_gone_from_the_query(self):
        from app.engines.provider_portal import router
        src = inspect.getsource(router._evaluate_provider_bookability)
        # Comments still explain why the columns went; what must not survive is
        # a reference in the CODE. Selecting them raised UndefinedColumnError,
        # so recomputing bookability 500'd and a provider's visible/bookable
        # state was frozen wherever it happened to stand.
        code = chr(10).join(
            line for line in src.splitlines() if not line.strip().startswith("#")
        )
        assert "security_deposit_paid" not in code
        assert "security_deposit_amount" not in code

    def test_credit_still_gates_bookability(self):
        from app.engines.provider_portal import router
        src = inspect.getsource(router._evaluate_provider_bookability)
        assert "USAGE_CREDITS_INSUFFICIENT" in src


class TestDocumentsAreNotTenantManaged:
    """Approval verifies the business; the provider sees a Verified badge.

    The documents themselves are KEPT -- nothing is purged -- they simply stop
    being a surface the provider manages day to day.
    """

    def test_the_documents_menu_is_gone(self):
        from pathlib import Path
        src = Path("frontend/tenant-portal/lib/nav-config.ts").read_text(encoding="utf-8")
        assert 'label: "Documents"' not in src

    def test_the_verified_badge_survives(self):
        from pathlib import Path
        src = Path("frontend/tenant-portal/app/(tenant)/profile/page.tsx").read_text(
            encoding="utf-8")
        assert 'variant="success">Verified' in src

    def test_a_document_needing_action_still_has_a_route(self):
        """Bookability blocks on a rejected or expired required document. With
        the menu gone and no conditional link, fixing one would be impossible
        and the provider would be stuck unbookable with nowhere to go."""
        from pathlib import Path
        src = Path("frontend/tenant-portal/app/(tenant)/profile/page.tsx").read_text(
            encoding="utf-8")
        assert "documentsNeedingAction" in src
        assert 'href="/documents"' in src
        assert "Replace document" in src

    def test_only_rejected_or_expired_documents_surface(self):
        from pathlib import Path
        src = Path("frontend/tenant-portal/app/(tenant)/profile/page.tsx").read_text(
            encoding="utf-8")
        # pending_review is the ADMIN's turn, not the provider's -- surfacing it
        # would be the "pending document approval" noise we are removing.
        assert 'doc.status === "rejected"' in src
        assert "expiry_date" in src

    def test_the_bookability_gate_still_requires_documents(self):
        """Removing the menu must not weaken the check itself."""
        import inspect
        from app.engines.provider_portal import router
        src = inspect.getsource(router._evaluate_provider_bookability)
        assert "REQUIRED_DOCUMENT_ACTION_NEEDED" in src
