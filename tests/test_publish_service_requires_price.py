"""Regression: publish_service let a simple (no type/brand) service reach
setup_status='published' with NO price configured at all -- no min/max
range, no visit fee. Found live: a real tenant had a published "AC Gas
Refilling" service with every price field NULL, permanently unsellable and
never flagged again anywhere in the product, because publish_service only
validated pricing when types or brands existed.

validate_for_publish (used for the pre-publish check UI) already enforced
this correctly; publish_service (the endpoint that actually flips the
status) did not. This fixes publish_service to match.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
SERVICE = os.path.join(BASE, "app/engines/admin_catalog/tenant_service.py")


def _read():
    with open(SERVICE, encoding="utf-8") as f:
        return f.read()


class TestPublishServiceRequiresPrice:
    def test_publish_service_validates_simple_service_pricing(self):
        c = _read()
        start = c.index("async def publish_service")
        end = c.index("async def save_draft")
        block = c[start:end]
        assert "validation = await self.validate_for_publish(tenant_service_id)" in block
        assert 'if not validation["valid"]' in block

    def test_check_happens_before_publish_commit(self):
        c = _read()
        start = c.index("async def publish_service")
        end = c.index("async def save_draft")
        block = c[start:end]
        price_check_pos = block.index("validation = await self.validate_for_publish")
        commit_pos = block.index('ts.setup_status = "published"')
        assert price_check_pos < commit_pos

    def test_matches_validate_for_publish_same_rule(self):
        c = _read()
        validate_start = c.index("async def validate_for_publish")
        validate_end = c.index("async def get_blueprint_update_status")
        validate_block = c[validate_start:validate_end]
        assert "not requires_type and not requires_brand" in validate_block
        assert "Set the provider price for this service." in validate_block
        assert "is_inspection_pricing" in validate_block
        assert "Set the visit or inspection fee for this service." in validate_block
