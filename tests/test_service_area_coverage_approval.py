"""Service-area coverage-approval workflow.

Replaces the platform pricing-tier / city-zipcode-tier-mapping system as
the mechanism that gates tenant service coverage. Covers the core request
lifecycle (draft -> submit -> admin decide -> materialized coverage),
authorization boundaries, and confirms the retired legacy tier endpoints
fail closed rather than silently continuing to work.
"""
from __future__ import annotations
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import ServiceOSException, NotFoundException
from app.engines.serviceability.service import ServiceabilityService
from app.engines.serviceability.models import (
    TenantServiceAreaRequest, TenantServiceAreaRequestItem, TenantServiceArea,
)
from app.engines.serviceability.constants import (
    ERR_REQUEST_NOT_EDITABLE, ERR_DECISION_REASON_REQUIRED, ERR_REQUEST_EMPTY,
)

pytestmark = pytest.mark.asyncio


def make_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


def result(scalar_one_or_none=None, scalars_all=None, scalar_one=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar_one_or_none
    r.scalar_one.return_value = scalar_one
    r.scalars.return_value.all.return_value = scalars_all or []
    return r


def make_tenant_service(tenant_id, category_id, master_service_id, job_type="repair"):
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.tenant_id = tenant_id
    ts.category_id = category_id
    ts.master_service_id = master_service_id
    ts.job_type = job_type
    ts.deleted_at = None
    return ts


def _dict_from_attrs(obj, attrs):
    return {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in
            ((a, getattr(obj, a)) for a in attrs)}


def make_request(tenant_id, category_id, status="DRAFT"):
    req = MagicMock(spec=TenantServiceAreaRequest)
    req.id = uuid.uuid4()
    req.tenant_id = tenant_id
    req.category_id = category_id
    req.status = status
    req.version = 1
    req.submitted_at = None
    req.submitted_by = None
    req.reviewed_at = None
    req.reviewed_by = None
    req.tenant_notes = None
    req.admin_notes = None
    req.superseded_by_request_id = None
    req.to_dict = lambda: _dict_from_attrs(
        req, ("id", "tenant_id", "category_id", "status", "version"))
    return req


def make_item(request_id, tenant_service_id, master_service_id, city="Ludhiana",
              zipcode="141001", decision_status="PENDING", applies_to_all=False):
    item = MagicMock(spec=TenantServiceAreaRequestItem)
    item.id = uuid.uuid4()
    item.request_id = request_id
    item.tenant_service_id = tenant_service_id
    item.master_service_id = master_service_id
    item.job_type_id = None
    item.applies_to_all_job_types = applies_to_all
    item.country = "India"
    item.state = "Punjab"
    item.district = "Ludhiana"
    item.city = city
    item.zipcode = zipcode
    item.requested_effective_date = None
    item.decision_status = decision_status
    item.decision_reason = None
    item.reviewed_at = None
    item.reviewed_by = None
    item.to_dict = lambda: _dict_from_attrs(
        item, ("id", "request_id", "decision_status", "city", "zipcode"))
    return item


# ══════════════════════════════════════════════════════════════════════════
# 1/2. Tenant can submit a request; can select multiple zipcodes
# ══════════════════════════════════════════════════════════════════════════

class TestTenantSubmitRequest:
    async def test_create_draft_and_add_item(self):
        tenant_id, category_id = uuid.uuid4(), uuid.uuid4()
        db = make_db()
        db.get.return_value = MagicMock(id=category_id)  # ServiceCategory exists
        svc = ServiceabilityService(db=db, actor_role="tenant_owner",
                                     actor_id=uuid.uuid4(), actor_tenant_id=tenant_id)
        out = await svc.create_service_area_request(tenant_id, category_id)
        assert out["tenant_id"] == str(tenant_id)
        assert out["status"] == "DRAFT"

    async def test_add_multiple_zipcode_items_to_same_request(self):
        tenant_id, category_id = uuid.uuid4(), uuid.uuid4()
        master_service_id = uuid.uuid4()
        db = make_db()
        req = make_request(tenant_id, category_id, status="DRAFT")
        ts = make_tenant_service(tenant_id, category_id, master_service_id)
        db.get.side_effect = [req, ts, req, ts]  # _get_request, _get_tenant_service (x2 calls)
        svc = ServiceabilityService(db=db, actor_role="tenant_owner",
                                     actor_id=uuid.uuid4(), actor_tenant_id=tenant_id)
        for zipcode in ("141001", "141002"):
            out = await svc.add_service_area_request_item(req.id, {
                "tenant_service_id": str(ts.id), "job_type_id": str(uuid.uuid4()),
                "state": "Punjab", "city": "Ludhiana", "zipcode": zipcode,
            })
            assert out["zipcode"] == zipcode
        assert db.add.call_count == 2


# ══════════════════════════════════════════════════════════════════════════
# 3/12. Request is scoped to tenant; cross-tenant access denied
# ══════════════════════════════════════════════════════════════════════════

class TestTenantScoping:
    async def test_cross_tenant_request_access_denied(self):
        owner_tenant, other_tenant = uuid.uuid4(), uuid.uuid4()
        db = make_db()
        req = make_request(owner_tenant, uuid.uuid4())
        db.get.return_value = req
        svc = ServiceabilityService(db=db, actor_role="tenant_owner",
                                     actor_id=uuid.uuid4(), actor_tenant_id=other_tenant)
        with pytest.raises(NotFoundException):
            await svc.get_service_area_request_detail(req.id)

    async def test_super_admin_can_view_any_tenants_request(self):
        db = make_db()
        req = make_request(uuid.uuid4(), uuid.uuid4())
        db.get.return_value = req
        db.execute.return_value = result(scalars_all=[])
        svc = ServiceabilityService(db=db, actor_role="super_admin", actor_id=uuid.uuid4())
        out = await svc.get_service_area_request_detail(req.id)
        assert out["id"] == str(req.id)


# ══════════════════════════════════════════════════════════════════════════
# 4. Submitted request cannot be edited
# ══════════════════════════════════════════════════════════════════════════

class TestSubmittedImmutable:
    async def test_cannot_add_item_to_submitted_request(self):
        tenant_id = uuid.uuid4()
        db = make_db()
        req = make_request(tenant_id, uuid.uuid4(), status="SUBMITTED")
        db.get.return_value = req
        svc = ServiceabilityService(db=db, actor_role="tenant_owner",
                                     actor_id=uuid.uuid4(), actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as exc:
            await svc.add_service_area_request_item(req.id, {
                "tenant_service_id": str(uuid.uuid4()), "applies_to_all_job_types": True,
                "state": "Punjab", "city": "Ludhiana",
            })
        assert exc.value.error_code == ERR_REQUEST_NOT_EDITABLE

    async def test_submit_requires_at_least_one_item(self):
        tenant_id = uuid.uuid4()
        db = make_db()
        req = make_request(tenant_id, uuid.uuid4(), status="DRAFT")
        db.get.return_value = req
        db.execute.return_value = result(scalar_one=0)
        svc = ServiceabilityService(db=db, actor_role="tenant_owner",
                                     actor_id=uuid.uuid4(), actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as exc:
            await svc.submit_service_area_request(req.id)
        assert exc.value.error_code == ERR_REQUEST_EMPTY


# ══════════════════════════════════════════════════════════════════════════
# 5/9. Admin can approve all items -> creates active coverage
# ══════════════════════════════════════════════════════════════════════════

class TestAdminApproveAll:
    async def test_approve_all_items_materializes_coverage(self):
        tenant_id, category_id, master_service_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        db = make_db()
        req = make_request(tenant_id, category_id, status="SUBMITTED")
        ts = make_tenant_service(tenant_id, category_id, master_service_id)
        item = make_item(req.id, ts.id, master_service_id)

        db.get.side_effect = [req, ts]  # _get_request, then TenantService lookup in materialize
        db.execute.side_effect = [
            result(scalars_all=[item]),      # load items_by_id
            result(scalar_one_or_none=None), # no existing TenantServiceArea -> create
            result(scalar_one_or_none=None), # no existing TenantServiceAreaService -> create
        ]
        svc = ServiceabilityService(db=db, actor_role="super_admin", actor_id=uuid.uuid4())
        out = await svc.admin_decide_request_items(req.id, [
            {"item_id": str(item.id), "decision": "APPROVED"},
        ])
        assert out["status"] == "APPROVED"
        assert item.decision_status == "APPROVED"
        # A new TenantServiceArea was added (materialization), status ACTIVE, no price field set.
        added_areas = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], TenantServiceArea)]
        assert len(added_areas) == 1
        assert added_areas[0].status == "ACTIVE"
        assert added_areas[0].approved_request_item_id == item.id
        assert not hasattr(added_areas[0], "price")


# ══════════════════════════════════════════════════════════════════════════
# 6. Admin can partially approve items
# ══════════════════════════════════════════════════════════════════════════

class TestPartialApproval:
    async def test_mixed_decisions_produce_partially_approved(self):
        tenant_id, category_id, master_service_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        db = make_db()
        req = make_request(tenant_id, category_id, status="UNDER_REVIEW")
        ts = make_tenant_service(tenant_id, category_id, master_service_id)
        item_approve = make_item(req.id, ts.id, master_service_id, zipcode="141001")
        item_reject = make_item(req.id, ts.id, master_service_id, zipcode="141002")

        db.get.side_effect = [req, ts]
        db.execute.side_effect = [
            result(scalars_all=[item_approve, item_reject]),
            result(scalar_one_or_none=None),  # new area for approved item
            result(scalar_one_or_none=None),  # new mapping for approved item
        ]
        svc = ServiceabilityService(db=db, actor_role="super_admin", actor_id=uuid.uuid4())
        out = await svc.admin_decide_request_items(req.id, [
            {"item_id": str(item_approve.id), "decision": "APPROVED"},
            {"item_id": str(item_reject.id), "decision": "REJECTED", "reason": "Outside coverage capacity"},
        ])
        assert out["status"] == "PARTIALLY_APPROVED"
        assert item_approve.decision_status == "APPROVED"
        assert item_reject.decision_status == "REJECTED"
        # Only ONE TenantServiceArea was created (for the approved item).
        added_areas = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], TenantServiceArea)]
        assert len(added_areas) == 1


# ══════════════════════════════════════════════════════════════════════════
# 7/8/10. Reject requires a reason; rejected items create no coverage
# ══════════════════════════════════════════════════════════════════════════

class TestRejection:
    async def test_reject_without_reason_is_rejected(self):
        tenant_id, category_id, master_service_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        db = make_db()
        req = make_request(tenant_id, category_id, status="SUBMITTED")
        item = make_item(req.id, uuid.uuid4(), master_service_id)
        db.get.return_value = req
        db.execute.return_value = result(scalars_all=[item])
        svc = ServiceabilityService(db=db, actor_role="super_admin", actor_id=uuid.uuid4())
        with pytest.raises(ServiceOSException) as exc:
            await svc.admin_decide_request_items(req.id, [
                {"item_id": str(item.id), "decision": "REJECTED"},
            ])
        assert exc.value.error_code == ERR_DECISION_REASON_REQUIRED

    async def test_rejected_item_creates_no_coverage_row(self):
        tenant_id, category_id, master_service_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        db = make_db()
        req = make_request(tenant_id, category_id, status="SUBMITTED")
        item = make_item(req.id, uuid.uuid4(), master_service_id)
        db.get.return_value = req
        db.execute.return_value = result(scalars_all=[item])
        svc = ServiceabilityService(db=db, actor_role="super_admin", actor_id=uuid.uuid4())
        out = await svc.admin_decide_request_items(req.id, [
            {"item_id": str(item.id), "decision": "REJECTED", "reason": "Not commercially viable"},
        ])
        assert out["status"] == "REJECTED"
        added_areas = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], TenantServiceArea)]
        assert len(added_areas) == 0


# ══════════════════════════════════════════════════════════════════════════
# 11. Tenant cannot approve its own request
# ══════════════════════════════════════════════════════════════════════════

class TestTenantCannotSelfApprove:
    async def test_tenant_owner_role_cannot_call_admin_decide(self):
        db = make_db()
        svc = ServiceabilityService(db=db, actor_role="tenant_owner",
                                     actor_id=uuid.uuid4(), actor_tenant_id=uuid.uuid4())
        with pytest.raises(ServiceOSException) as exc:
            await svc.admin_decide_request_items(uuid.uuid4(), [])
        assert exc.value.status_code == 403

    async def test_tenant_owner_cannot_start_review(self):
        db = make_db()
        svc = ServiceabilityService(db=db, actor_role="tenant_owner",
                                     actor_id=uuid.uuid4(), actor_tenant_id=uuid.uuid4())
        with pytest.raises(ServiceOSException) as exc:
            await svc.admin_start_review(uuid.uuid4())
        assert exc.value.status_code == 403


# ══════════════════════════════════════════════════════════════════════════
# 16. Suspended coverage excluded from matching (status + is_active mirrored)
# ══════════════════════════════════════════════════════════════════════════

class TestCoverageSuspension:
    async def test_suspend_sets_status_and_is_active_false(self):
        db = make_db()
        area = MagicMock(tenant_id=uuid.uuid4(), is_active=True, status="ACTIVE")
        db.get.return_value = area
        svc = ServiceabilityService(db=db, actor_role="super_admin", actor_id=uuid.uuid4())
        await svc.suspend_coverage(uuid.uuid4(), "Compliance hold")
        assert area.status == "SUSPENDED"
        assert area.is_active is False
        assert area.suspension_reason == "Compliance hold"

    async def test_suspend_without_reason_is_rejected(self):
        db = make_db()
        svc = ServiceabilityService(db=db, actor_role="super_admin", actor_id=uuid.uuid4())
        with pytest.raises(ServiceOSException) as exc:
            await svc.suspend_coverage(uuid.uuid4(), "")
        assert exc.value.error_code == ERR_DECISION_REASON_REQUIRED

    async def test_reactivate_restores_active_status(self):
        db = make_db()
        area = MagicMock(tenant_id=uuid.uuid4(), is_active=False, status="SUSPENDED")
        db.get.return_value = area
        svc = ServiceabilityService(db=db, actor_role="super_admin", actor_id=uuid.uuid4())
        await svc.reactivate_coverage(uuid.uuid4())
        assert area.status == "ACTIVE"
        assert area.is_active is True


# ══════════════════════════════════════════════════════════════════════════
# 19/20. No price field anywhere in the request/coverage models
# ══════════════════════════════════════════════════════════════════════════

class TestNoPriceCoupling:
    def test_request_item_model_has_no_price_column(self):
        cols = {c.name for c in TenantServiceAreaRequestItem.__table__.columns}
        assert not any("price" in c for c in cols)

    def test_request_model_has_no_price_column(self):
        cols = {c.name for c in TenantServiceAreaRequest.__table__.columns}
        assert not any("price" in c for c in cols)


# ══════════════════════════════════════════════════════════════════════════
# 24. Old tier write endpoints fail closed (410, not silently working)
# ══════════════════════════════════════════════════════════════════════════

class TestLegacyTierRetirement:
    async def test_create_tier_is_retired(self):
        from app.engines.admin_catalog.service import AdminCatalogService
        db = make_db()
        svc = AdminCatalogService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_tier({"name": "Metro", "code": "metro", "tier_type": "metro"})
        assert exc.value.error_code == "PRICING_TIER_WRITES_RETIRED"
        assert exc.value.status_code == 410

    async def test_create_tier_location_is_retired(self):
        from app.engines.admin_catalog.service import AdminCatalogService
        db = make_db()
        svc = AdminCatalogService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_tier_location({"tier_id": str(uuid.uuid4()), "city": "Mumbai"})
        assert exc.value.error_code == "PRICING_TIER_WRITES_RETIRED"

    async def test_bulk_change_tier_locations_is_retired(self):
        from app.engines.admin_catalog.service import AdminCatalogService
        db = make_db()
        svc = AdminCatalogService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
        with pytest.raises(ServiceOSException) as exc:
            await svc.bulk_change_tier_locations([str(uuid.uuid4())], str(uuid.uuid4()))
        assert exc.value.error_code == "PRICING_TIER_WRITES_RETIRED"


# ══════════════════════════════════════════════════════════════════════════
# Withdraw
# ══════════════════════════════════════════════════════════════════════════

class TestWithdraw:
    async def test_withdraw_draft_request(self):
        tenant_id = uuid.uuid4()
        db = make_db()
        req = make_request(tenant_id, uuid.uuid4(), status="DRAFT")
        db.get.return_value = req
        svc = ServiceabilityService(db=db, actor_role="tenant_owner",
                                     actor_id=uuid.uuid4(), actor_tenant_id=tenant_id)
        out = await svc.withdraw_service_area_request(req.id)
        assert out["status"] == "WITHDRAWN"
        assert req.status == "WITHDRAWN"

    async def test_cannot_withdraw_already_approved_request(self):
        tenant_id = uuid.uuid4()
        db = make_db()
        req = make_request(tenant_id, uuid.uuid4(), status="APPROVED")
        db.get.return_value = req
        svc = ServiceabilityService(db=db, actor_role="tenant_owner",
                                     actor_id=uuid.uuid4(), actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as exc:
            await svc.withdraw_service_area_request(req.id)
        assert exc.value.error_code == ERR_REQUEST_NOT_EDITABLE
