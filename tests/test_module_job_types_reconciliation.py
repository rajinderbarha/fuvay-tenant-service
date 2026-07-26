"""Reconciles a real 3-vs-9 job_type value divergence found live between
app.engines.admin_catalog.service.VALID_JOB_TYPES (9 values) and
app.engines.field_ops.constants.JobType/TYPE_TRANSITION_OVERRIDES (only 3).
Migration 151 added an admin-configurable `job_types` table (workflow flags
only, no monetary columns) and backfilled job_type_id onto master_services,
service_pricing_rules, tenant_services, jobs, bookings. This file proves the
6 previously-undifferentiated job types (installation/uninstallation/
inspection/maintenance/cleaning/custom) no longer silently fall back to the
full repair/mandatory-assessment graph, and that repair/service/consultation
(the original 3) are completely unchanged. No live DB required for the
constants-level assertions; a live DB check confirms the migration backfill.
"""
from __future__ import annotations

from app.engines.field_ops.constants import (
    JobType, JS, JOB_TYPES, get_allowed_transitions, ALLOWED_TRANSITIONS,
)


class TestOriginalThreeUnchanged:
    """The 3 job types with existing hand-written overrides must behave
    exactly as before -- this migration must not alter their behavior."""

    def test_repair_still_requires_assessment(self):
        assert get_allowed_transitions(JobType.REPAIR, JS.ARRIVED) == [JS.ASSESSMENT_STARTED]

    def test_service_still_skips_assessment(self):
        assert JS.WORK_STARTED in get_allowed_transitions(JobType.SERVICE, JS.ARRIVED)
        assert JS.ASSESSMENT_STARTED not in get_allowed_transitions(JobType.SERVICE, JS.ARRIVED)

    def test_consultation_still_never_touches_work_started(self):
        allowed = get_allowed_transitions(JobType.CONSULTATION, JS.ASSESSMENT_COMPLETE)
        assert JS.WORK_STARTED not in allowed
        assert JS.QUOTE_PENDING in allowed


class TestPreviouslyUndifferentiatedJobTypes:
    """Real bug: these 6 job_type values are allowed by admin_catalog's
    VALID_JOB_TYPES but had zero entry in field_ops's TYPE_TRANSITION_
    OVERRIDES, so they silently inherited repair's mandatory-assessment
    requirement with no way to configure otherwise."""

    def test_installation_skips_assessment_like_service(self):
        allowed = get_allowed_transitions(JobType.INSTALLATION, JS.ARRIVED)
        assert JS.WORK_STARTED in allowed
        assert JS.ASSESSMENT_STARTED not in allowed

    def test_maintenance_skips_assessment(self):
        allowed = get_allowed_transitions(JobType.MAINTENANCE, JS.ARRIVED)
        assert JS.WORK_STARTED in allowed
        assert JS.ASSESSMENT_STARTED not in allowed

    def test_cleaning_skips_assessment(self):
        allowed = get_allowed_transitions(JobType.CLEANING, JS.ARRIVED)
        assert JS.WORK_STARTED in allowed
        assert JS.ASSESSMENT_STARTED not in allowed

    def test_uninstallation_skips_assessment_and_has_no_checklist_gate(self):
        allowed = get_allowed_transitions(JobType.UNINSTALLATION, JS.ARRIVED)
        assert JS.WORK_STARTED in allowed
        assert JS.ASSESSMENT_STARTED not in allowed
        # No checklist requirement -- WORK_STARTED falls through to the base
        # graph's [WORK_COMPLETE, PARTS_REQUIRED], no override needed there.
        assert get_allowed_transitions(JobType.UNINSTALLATION, JS.WORK_STARTED) \
            == ALLOWED_TRANSITIONS[JS.WORK_STARTED]

    def test_inspection_falls_back_to_base_repair_graph_correctly(self):
        """Inspection's flags (requires_assessment=True, allows_quote=True,
        requires_checklist=False) are exactly the base graph's shape -- no
        override needed, but must be a deliberate match, not an accident."""
        assert get_allowed_transitions(JobType.INSPECTION, JS.ARRIVED) == [JS.ASSESSMENT_STARTED]
        assert get_allowed_transitions(JobType.INSPECTION, JS.ASSESSMENT_COMPLETE) == \
            ALLOWED_TRANSITIONS[JS.ASSESSMENT_COMPLETE]

    def test_custom_requires_assessment_and_checklist(self):
        assert get_allowed_transitions(JobType.CUSTOM, JS.ARRIVED) == [JS.ASSESSMENT_STARTED]
        allowed_after_work_started = get_allowed_transitions(JobType.CUSTOM, JS.WORK_STARTED)
        assert JS.CHECKLIST_STARTED in allowed_after_work_started
        assert JS.WORK_COMPLETE not in allowed_after_work_started  # must go through checklist

    def test_all_nine_job_types_are_registered(self):
        assert set(JOB_TYPES) == {
            "repair", "service", "consultation",
            "installation", "uninstallation", "inspection",
            "maintenance", "cleaning", "custom",
        }


class TestJobTypesTableLive:
    """Confirms the migration 151 table + backfill against the real DB."""

    async def test_job_types_seeded_and_backfilled(self):
        import asyncio
        from app.database import get_session_factory, init_db
        from sqlalchemy import text

        await init_db()
        factory = get_session_factory()
        async with factory() as db:
            rows = (await db.execute(text(
                "SELECT key, requires_assessment, allows_quote, requires_checklist FROM job_types ORDER BY display_order"
            ))).fetchall()
            by_key = {r[0]: (r[1], r[2], r[3]) for r in rows}
            assert by_key["repair"] == (True, True, False)
            assert by_key["service"] == (False, False, True)
            assert by_key["consultation"] == (True, True, False)
            assert by_key["installation"] == (False, False, True)
            assert by_key["uninstallation"] == (False, False, False)

            for table in ("master_services", "service_pricing_rules", "tenant_services"):
                total = (await db.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
                mapped = (await db.execute(text(
                    f"SELECT count(*) FROM {table} WHERE job_type_id IS NOT NULL"))).scalar()
                if total:
                    assert mapped == total, f"{table} has unmapped job_type rows"

    def test_job_types_table_has_no_monetary_columns(self):
        """Structural guard for the platform's admin-never-sets-price rule:
        this new admin-owned table must never grow a price/fee/amount column."""
        from app.engines.admin_catalog.models import JobTypeDefinition
        forbidden_substrings = ("price", "fee", "amount", "cost")
        for col in JobTypeDefinition.__table__.columns:
            name = col.name.lower()
            assert not any(s in name for s in forbidden_substrings), \
                f"job_types.{col.name} looks monetary -- violates admin-price-prohibition"
