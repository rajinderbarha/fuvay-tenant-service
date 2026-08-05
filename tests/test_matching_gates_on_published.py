"""Regression: provider matching never checked whether a tenant's offering
was actually published.

Found live: the real eligibility gate (_passes_full_eligibility_gate) reads
tenant_service_area_services for coverage, but never joined tenant_services
.setup_status -- a draft/unpublished TenantService could still be matched
to a customer, and (separately) a published one had its price ignored by
_resolve_selected_tenant_price for the same reason. Verified zero blast
radius against live data (every real tenant_service_area_services row in
this environment already belonged to a published TenantService) before
adding the gate.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
MATCHING_ENGINE = os.path.join(BASE, "app/engines/home_service_booking/matching_engine.py")
BOOKING_SERVICE = os.path.join(BASE, "app/engines/home_service_booking/service.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestMatchingGatesOnPublished:
    def test_eligibility_gate_checks_setup_status(self):
        c = _read(MATCHING_ENGINE)
        start = c.index("async def _passes_full_eligibility_gate")
        end = c.index("\n\n\n", start)
        block = c[start:end]
        assert "FROM tenant_services WHERE tenant_id=:tid AND master_service_id=:oid" in block
        assert 'published_row.setup_status != "published"' in block
        assert '"OFFERING_NOT_PUBLISHED"' in block

    def test_absence_of_tenant_service_row_is_not_itself_a_block(self):
        """Legacy/simple offerings covered without an explicit TenantService
        row must not be newly excluded -- only an explicit non-published
        status blocks."""
        c = _read(MATCHING_ENGINE)
        start = c.index("published_row = (await db.execute")
        block = c[start:start + 400]
        assert "published_row is not None and" in block

    def test_reason_code_registered_in_eligibility_gate_codes(self):
        c = _read(MATCHING_ENGINE)
        start = c.index("ELIGIBILITY_GATE_CODES = (")
        end = c.index(")", start)
        block = c[start:end]
        assert '"OFFERING_NOT_PUBLISHED"' in block

    def test_selected_tenant_price_resolution_also_gates_on_published(self):
        c = _read(BOOKING_SERVICE)
        start = c.index("async def _resolve_selected_tenant_price")
        end = c.index("async def _compute_price_snapshot")
        block = c[start:end]
        assert 'TenantService.setup_status == "published"' in block
