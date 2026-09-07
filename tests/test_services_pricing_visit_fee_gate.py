"""Regression: Services & Pricing showed 'incomplete' on Review & Submit for
published visit-fee-only (inspection workflow) services.

admin_catalog/tenant_service.py::validate_for_publish treats a simple
(no type/brand) service as priced when EITHER tenant_min_price+
tenant_max_price OR tenant_visit_fee is set -- the visit-fee path is the
real, common case for inspection-based Repair jobs. But the Setup Overview
and Activation-Gate priced_count queries only ever checked tenant_min_price,
so a tenant who published a visit-fee service (which the platform itself
allowed) got stuck on a permanently "incomplete" Services & Pricing section.
"""
import os
import pathlib
from app.engines.vertical_catalog.pricing_readiness import PUBLISHED_PRICED_SERVICES_SQL

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
OVERVIEW = os.path.join(BASE, "app/engines/vertical_catalog/home_services_setup_service.py")
ACTIVATION = os.path.join(BASE, "app/engines/vertical_catalog/activation.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestPricedCountRecognizesVisitFee:
    def test_setup_overview_priced_count_includes_visit_fee(self):
        c = _read(OVERVIEW)
        start = c.index("priced_count = (await db.execute(")
        end = c.index("services_ready")
        block = c[start:end]
        assert "text(PUBLISHED_PRICED_SERVICES_SQL)" in block
        assert "ts.tenant_visit_fee > 0" in PUBLISHED_PRICED_SERVICES_SQL

    def test_activation_gate_priced_count_includes_visit_fee(self):
        c = _read(ACTIVATION)
        start = c.index("priced_count = (await db.execute(")
        end = c.index("offerings_ready")
        block = c[start:end]
        assert "text(PUBLISHED_PRICED_SERVICES_SQL)" in block
        assert "ts.tenant_visit_fee > 0" in PUBLISHED_PRICED_SERVICES_SQL

    def test_both_queries_stay_in_sync(self):
        """Same price-recognition SQL fragment in both places -- prevents the
        two gates from silently drifting apart again."""
        overview_block = _read(OVERVIEW)
        activation_block = _read(ACTIVATION)
        assert "text(PUBLISHED_PRICED_SERVICES_SQL)" in overview_block
        assert "text(PUBLISHED_PRICED_SERVICES_SQL)" in activation_block
        # Both gates now use one query, including the provider-wide fee.
        for clause in (
            "ts.tenant_min_price > 0",
            "ts.tenant_visit_fee > 0",
            "tenant_service_types tst",
            "tenant_service_brands tsb",
            "consultation_fee",
        ):
            assert clause in PUBLISHED_PRICED_SERVICES_SQL
