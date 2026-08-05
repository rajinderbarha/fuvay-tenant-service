"""Regression: Review & Submit was stuck on 'incomplete' forever.

get_setup_overview's FINANCE_READINESS section gated on a tenant_billing
row existing, but nothing in the real Finance Readiness onboarding step
(tenant_finance_readiness_router.py) ever creates one -- that row comes
from an independent activation/package flow. So a tenant could fill in
every field on the Finance Readiness page and the Review step would still
show it incomplete, blocking submission forever. The fix reads the
tenant's own tenant_finance_readiness row instead.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
SERVICE = os.path.join(BASE, "app/engines/vertical_catalog/home_services_setup_service.py")


def _read():
    with open(SERVICE, encoding="utf-8") as f:
        return f.read()


class TestFinanceReadinessGate:
    def test_no_longer_gated_on_tenant_billing_row_alone(self):
        c = _read()
        assert 'finance_ready = billing_row is not None' not in c

    def test_gated_on_tenant_finance_readiness_row(self):
        c = _read()
        assert "FROM tenant_finance_readiness WHERE tenant_id=:tid" in c
        assert "finance_methods_selected" in c
        assert "finance_invoice_complete" in c
        assert "finance_ready = finance_methods_selected and finance_invoice_complete" in c

    def test_deposit_still_not_a_submission_blocker(self):
        c = _read()
        block_start = c.index("# ── Finance Readiness")
        block_end = c.index("sections: list[dict] = []")
        block = c[block_start:block_end]
        assert "deposit_amount" not in block.split("finance_ready =")[1]
