"""Regression: publish_service's per-type pricing check contradicted the
documented inheritance model and disagreed with validate_for_publish.

Found live: a tenant set only the service's DEFAULT price (min/max on
TenantService itself) for a type/brand-required service (AC Installation,
2 enabled types, no per-type override). The Services & Pricing workspace's
readiness check (validate_for_publish, via resolve_tenant_price's
inheritance) correctly reported "ready" -- but calling the real publish
endpoint 422'd with "Set a price range for every selected type", because
publish_service had its OWN, stricter, undocumented rule that ignored
inheritance entirely. The spec is explicit: "Do not require every Brand to
have a separate price." Fixed by having publish_service reuse
resolve_tenant_price (the same resolver validate_for_publish already
uses) instead of a duplicated, contradictory check -- there is now exactly
one publish-readiness authority.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
SERVICE = os.path.join(BASE, "app/engines/admin_catalog/tenant_service.py")


def _read():
    with open(SERVICE, encoding="utf-8") as f:
        return f.read()


class TestPublishServiceUsesSharedResolver:
    def test_publish_service_reuses_preflight_validation(self):
        c = _read()
        start = c.index("async def publish_service")
        end = c.index("async def save_draft")
        block = c[start:end]
        assert "validation = await self.validate_for_publish(tenant_service_id)" in block

    def test_no_longer_requires_every_type_to_carry_its_own_price(self):
        c = _read()
        start = c.index("async def publish_service")
        end = c.index("async def save_draft")
        block = c[start:end]
        assert "Set a price range for every selected type." not in block

    def test_brand_partial_override_still_rejected(self):
        """A half-filled brand override (only min or only max set) is a real
        data-integrity problem regardless of inheritance -- must stay caught."""
        c = _read()
        start = c.index("async def validate_for_publish")
        end = c.index("async def get_blueprint_update_status")
        block = c[start:end]
        assert "has_partial" in block
        assert "Brand override price range is incomplete." in block

    def test_simple_service_default_price_check_still_present(self):
        c = _read()
        start = c.index("async def validate_for_publish")
        end = c.index("async def get_blueprint_update_status")
        block = c[start:end]
        assert "not requires_type and not requires_brand" in block
        assert "Set the provider price for this service." in block
