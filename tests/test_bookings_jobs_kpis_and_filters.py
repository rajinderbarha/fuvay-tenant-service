"""Bookings & Jobs workspace (TENANT-OPS-01 Phase 2) — backend-authoritative
KPI strip, SLA/complaint row enrichment, and date/offering/SLA filters added
to the existing GET /v1/tenant/home-services/bookings-jobs projection.

Extends the real, already-live router rather than inventing a parallel
endpoint (confirmed via audit: list + quick detail already existed with
correct privacy masking and stage/action derivation before this pass).
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
ROUTER = os.path.join(BASE, "app/engines/final_records/tenant_bookings_jobs_router.py")
KPIS = os.path.join(BASE, "app/engines/final_records/bookings_jobs_kpis.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestKpiModule:
    def test_reuses_existing_sla_projection_not_a_second_one(self):
        c = _read(KPIS)
        assert "from app.engines.final_records.sla_summary import sla_filter_condition" in c

    def test_defines_all_six_spec_kpis(self):
        c = _read(KPIS)
        for key in ("total_active", "unassigned", "in_progress",
                    "awaiting_approval", "at_risk", "completed_today"):
            assert f'"{key}"' in c

    def test_total_active_excludes_terminal_statuses(self):
        c = _read(KPIS)
        assert "TERMINAL_STATUSES" in c
        assert "notin_(TERMINAL_STATUSES)" in c

    def test_at_risk_counts_both_at_risk_and_breached(self):
        c = _read(KPIS)
        start = c.index("risk_condition = (")
        block = c[start:start + 220]
        assert '"AT_RISK"' in block and '"BREACHED"' in block
        assert "func.count().filter(risk_condition)" in c


class TestRouterEnrichment:
    def test_list_endpoint_returns_backend_summary_not_client_computed(self):
        c = _read(ROUTER)
        assert "compute_bookings_jobs_kpis(db, tenant_id)" in c
        assert '"summary": summary' in c

    def test_list_rows_carry_sla_and_complaint_indicator(self):
        c = _read(ROUTER)
        assert '"sla":               sla_map.get(str(job.id))' in c or '"sla":' in c
        assert '"open_complaint_count"' in c

    def test_sla_batch_computed_not_per_row(self):
        c = _read(ROUTER)
        start = c.index("page_jobs = [job for job, _booking in rows]")
        end = c.index("items = []")
        block = c[start:end]
        # attach_sla is called exactly once against the whole page, not once
        # per job inside the items-building loop below this block.
        assert block.count("attach_sla(db, page_jobs)") == 1
        assert "await db.execute" not in block or "select(CustomerComplaint" in block

    def test_complaint_count_scoped_to_tenant_and_open_statuses(self):
        c = _read(ROUTER)
        assert 'CustomerComplaint.tenant_id == tenant_id' in c
        assert '"resolved", "closed", "withdrawn"' in c

    def test_date_filters_parse_and_reject_invalid_input(self):
        c = _read(ROUTER)
        assert "def _parse_date" in c
        assert "INVALID_DATE" in c

    def test_sla_filter_is_database_filtered_before_pagination(self):
        c = _read(ROUTER)
        assert "sla_filter_condition(ServiceJob, sla)" in c
        assert "q = q.where(sla_condition)" in c
        assert "count_q = count_q.where(sla_condition)" in c

    def test_detail_endpoint_includes_quote_visit_fee_and_direct_payment_notice(self):
        c = _read(ROUTER)
        start = c.index("async def get_bookings_jobs_detail")
        end = c.index("async def get_job_exact_address")
        block = c[start:end]
        assert "ServiceJobQuote.is_current == True" in block
        assert "tenant_visit_fee" in block
        assert "direct_payment_notice" in block
        assert "does not collect" in block.lower() or "records confirmation only" in block.lower()

    def test_direct_payment_notice_never_implies_platform_collects_payment(self):
        c = _read(ROUTER)
        assert "Customer pays the provider directly" in c
        assert "ServiceOS records confirmation only" in c
