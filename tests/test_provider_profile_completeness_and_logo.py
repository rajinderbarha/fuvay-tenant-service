from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

import pytest

from app.dependencies.auth import UserContext
from app.engines.profile.service import ProfileService


class _Result:
    def __init__(self, *, scalar=None, row=None, rows=None):
        self._scalar = scalar
        self._row = row
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._scalar

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _DB:
    def __init__(self, tenant):
        self.results = iter([
            _Result(scalar=tenant),
            _Result(scalar=None),  # dangling business_logo_media_id
            _Result(row=SimpleNamespace(
                active_services=4, service_areas=1, active_technicians=1,
            )),
            _Result(row=SimpleNamespace(avg=5, total=2)),
            _Result(rows=[]),
        ])

    async def execute(self, _statement, _params=None):
        return next(self.results)


def _tenant():
    tenant_id = uuid.uuid4()
    return SimpleNamespace(
        id=tenant_id,
        tenant_name="Test Ac Service",
        business_name="Test Ac Service",
        legal_name="Test Ac Service",
        owner_name="India uio",
        phone="+919876765465",
        email="test@gmail.com",
        gst_number=None,
        business_type="sole_proprietorship",
        address_line1="NEWSARIAN",
        address_line2="#5,wno-3",
        city="Bassi Pathana",
        district="sarafa bazar",
        state="Punjab",
        country="India",
        zipcode="140412",
        logo_url="http://api.example/uploads/provider_business_logo/missing.png",
        business_logo_media_id=uuid.uuid4(),
        shop_photo_media_id=None,
        verification_status="approved",
        status="active",
        plan_type="starter",
        slug=None,
        meta={"year_established": 2000},
        created_at=datetime(2026, 9, 7, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_approved_profile_is_complete_without_optional_public_fields_and_hides_dangling_logo():
    tenant = _tenant()
    actor = UserContext(
        user_id=str(uuid.uuid4()),
        email="owner@example.com",
        role="tenant_owner",
        tenant_id=str(tenant.id),
        full_name="Owner",
        is_verified=True,
    )

    profile = await ProfileService(_DB(tenant), actor).get_business_profile()

    assert profile["completeness"] == {
        "percentage": 100,
        "completed_count": 10,
        "total_count": 10,
        "completed_requirements": [
            "owner_name", "phone", "business_name", "legal_name", "business_type",
            "email", "address_line1", "city", "state", "zipcode",
        ],
        "missing_requirements": [],
    }
    assert profile["logo_url"] is None
    assert profile["business_logo_media_id"] is None
    assert profile["logo_needs_reupload"] is True


def test_review_gate_uses_the_same_required_fields_as_profile_completeness():
    assert ProfileService.REQUIRED_FOR_REVIEW == ProfileService._COMPLETENESS_FIELDS
    optional = {"gst_number", "logo_url", "description", "shop_photo_media_id"}
    assert optional.isdisjoint({key for key, _label in ProfileService.REQUIRED_FOR_REVIEW})
