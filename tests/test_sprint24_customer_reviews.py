"""
Sprint 24 — Customer Reviews + Rating Engine
37 tests: constants (4), models (5), eligibility (4), review_service (12),
aggregation (4), routers (6), swagger (2)
"""
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# ── Helpers ───────────────────────────────────────────────────────────────────
def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _make_review(**kwargs) -> MagicMock:
    rv = MagicMock()
    rv.id               = kwargs.get("id", _uuid())
    rv.review_number    = kwargs.get("review_number", "REV-12345678")
    rv.customer_id      = kwargs.get("customer_id", _uuid())
    rv.tenant_id        = kwargs.get("tenant_id", _uuid())
    rv.record_type      = kwargs.get("record_type", "service_job")
    rv.record_id        = kwargs.get("record_id", _uuid())
    rv.overall_rating   = kwargs.get("overall_rating", 5)
    rv.provider_rating  = kwargs.get("provider_rating", 4)
    rv.staff_rating     = kwargs.get("staff_rating", 5)
    rv.communication_rating = kwargs.get("communication_rating", 4)
    rv.punctuality_rating   = kwargs.get("punctuality_rating", 4)
    rv.quality_rating   = kwargs.get("quality_rating", 5)
    rv.value_rating     = kwargs.get("value_rating", 4)
    rv.review_title     = kwargs.get("review_title", "Great service")
    rv.review_text      = kwargs.get("review_text", "Very happy")
    rv.review_tags      = kwargs.get("review_tags", ["clean", "professional"])
    rv.media_urls       = kwargs.get("media_urls", [])
    rv.status           = kwargs.get("status", "pending")
    rv.visibility       = kwargs.get("visibility", "private_until_approved")
    rv.moderation_reason = kwargs.get("moderation_reason", None)
    rv.rejection_reason  = kwargs.get("rejection_reason", None)
    rv.submitted_at     = kwargs.get("submitted_at", datetime.now(timezone.utc))
    rv.approved_at      = kwargs.get("approved_at", None)
    rv.rejected_at      = kwargs.get("rejected_at", None)
    rv.hidden_at        = kwargs.get("hidden_at", None)
    rv.edited_at        = kwargs.get("edited_at", None)
    rv.created_at       = kwargs.get("created_at", datetime.now(timezone.utc))
    rv.updated_at       = kwargs.get("updated_at", datetime.now(timezone.utc))
    rv.staff_member_id  = kwargs.get("staff_member_id", None)
    rv.to_dict = lambda: {
        "id": str(rv.id), "review_number": rv.review_number,
        "customer_id": str(rv.customer_id), "tenant_id": str(rv.tenant_id),
        "record_type": rv.record_type, "record_id": str(rv.record_id),
        "overall_rating": rv.overall_rating, "status": rv.status,
        "visibility": rv.visibility, "submitted_at": None,
        "created_at": None, "updated_at": None,
    }
    return rv


def _make_db(result_value=None, scalar_value=None):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = scalar_value
    mock_result.scalars.return_value.all.return_value   = result_value or []
    db.execute = AsyncMock(return_value=mock_result)
    db.add    = MagicMock()
    db.flush  = AsyncMock()
    db.commit = AsyncMock()
    # MODULE-L5-22: submit_review now notifies the provider, resolving the tenant
    # owner via db.get. Return None so the notify step finds no recipient and
    # no-ops (default AsyncMock would return a truthy mock -> bad UUID).
    db.get    = AsyncMock(return_value=None)
    return db


# ════════════════════════════════════════════════════════════════════════════════
# 1. Constants (4 tests)
# ════════════════════════════════════════════════════════════════════════════════
class TestSprint24Constants:
    def test_review_statuses(self):
        from app.engines.customer_reviews.constants import (
            STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED,
            STATUS_HIDDEN, STATUS_FLAGGED, STATUS_DELETED, REVIEW_STATUSES,
        )
        assert STATUS_PENDING in REVIEW_STATUSES
        assert STATUS_APPROVED in REVIEW_STATUSES
        assert STATUS_REJECTED in REVIEW_STATUSES
        assert STATUS_HIDDEN in REVIEW_STATUSES
        assert STATUS_FLAGGED in REVIEW_STATUSES
        assert STATUS_DELETED in REVIEW_STATUSES

    def test_eligible_statuses_per_record_type(self):
        from app.engines.customer_reviews.constants import ELIGIBLE_STATUSES
        assert "completed" in ELIGIBLE_STATUSES["service_job"]
        assert "work_done" in ELIGIBLE_STATUSES["service_job"]
        assert "completed" in ELIGIBLE_STATUSES["service_booking"]
        assert "paid" in ELIGIBLE_STATUSES["service_booking"]
        assert "completed" in ELIGIBLE_STATUSES["coaching_appointment"]
        assert "converted" in ELIGIBLE_STATUSES["real_estate_lead"]
        assert "closed_lost" in ELIGIBLE_STATUSES["real_estate_lead"]

    def test_valid_record_types(self):
        from app.engines.customer_reviews.constants import VALID_RECORD_TYPES
        assert "service_booking"      in VALID_RECORD_TYPES
        assert "service_job"          in VALID_RECORD_TYPES
        assert "coaching_appointment" in VALID_RECORD_TYPES
        assert "real_estate_lead"     in VALID_RECORD_TYPES

    def test_flag_reasons(self):
        from app.engines.customer_reviews.constants import FLAG_REASONS
        assert "spam"      in FLAG_REASONS
        assert "fake"      in FLAG_REASONS
        assert "offensive" in FLAG_REASONS
        assert "other"     in FLAG_REASONS


# ════════════════════════════════════════════════════════════════════════════════
# 2. Models (5 tests)
# ════════════════════════════════════════════════════════════════════════════════
class TestSprint24Models:
    def test_customer_review_to_dict(self):
        from app.engines.customer_reviews.models import CustomerReview
        rv = CustomerReview(
            id=_uuid(), review_number="REV-00000001",
            customer_id=_uuid(), tenant_id=_uuid(),
            record_type="service_job", record_id=_uuid(),
            overall_rating=4, status="pending",
            visibility="private_until_approved",
        )
        d = rv.to_dict()
        assert d["review_number"] == "REV-00000001"
        assert d["overall_rating"] == 4
        assert d["status"] == "pending"

    def test_customer_review_to_public_dict_hides_customer_id(self):
        from app.engines.customer_reviews.models import CustomerReview
        rv = CustomerReview(
            id=_uuid(), review_number="REV-00000002",
            customer_id=_uuid(), tenant_id=_uuid(),
            record_type="service_job", record_id=_uuid(),
            overall_rating=5, status="approved",
            visibility="public",
        )
        d = rv.to_public_dict()
        assert "customer_id" not in d

    def test_review_reply_to_dict(self):
        from app.engines.customer_reviews.models import ReviewReply
        rp = ReviewReply(
            id=_uuid(), review_id=_uuid(), tenant_id=_uuid(),
            reply_text="Thank you!", status="pending",
        )
        d = rp.to_dict()
        assert d["reply_text"] == "Thank you!"
        assert d["status"] == "pending"

    def test_review_flag_to_dict(self):
        from app.engines.customer_reviews.models import ReviewFlag
        rf = ReviewFlag(
            id=_uuid(), review_id=_uuid(),
            flagged_by_type="customer", reason_code="spam", status="open",
        )
        d = rf.to_dict()
        assert d["reason_code"] == "spam"
        assert d["status"] == "open"

    def test_review_policy_to_dict(self):
        from app.engines.customer_reviews.models import ReviewPolicy
        p = ReviewPolicy(
            id=_uuid(), policy_key="default", policy_name="Default Policy",
            auto_approve_enabled=False, require_admin_moderation=True,
            allow_provider_reply=True, require_reply_moderation=True,
            allow_review_edit=True, edit_window_hours=48,
            min_rating=1, max_rating=5, allow_media=True, max_media_count=5,
        )
        d = p.to_dict()
        assert d["policy_key"] == "default"
        assert d["edit_window_hours"] == 48
        assert d["auto_approve_enabled"] is False


# ════════════════════════════════════════════════════════════════════════════════
# 3. Eligibility Service (4 tests)
# ════════════════════════════════════════════════════════════════════════════════
class TestSprint24Eligibility:
    async def _run_check(self, record_type, status, expected_eligible):
        from app.engines.customer_reviews.eligibility_service import ReviewEligibilityService
        svc = ReviewEligibilityService()

        customer_id = _uuid()
        record_id   = _uuid()

        # Mock the record fetch
        mock_record = MagicMock()
        mock_record.id          = record_id
        mock_record.status      = status
        mock_record.customer_id = customer_id
        mock_record.tenant_id   = _uuid()

        db = AsyncMock()
        existing_result = MagicMock()
        existing_result.scalars.return_value.first.return_value = None  # no existing review

        with patch.object(svc, "_fetch_record", AsyncMock(return_value=mock_record)), \
             patch.object(svc, "_customer_owns_record", AsyncMock(return_value=True)):
            db.execute = AsyncMock(return_value=existing_result)
            result = await svc.check_eligible(db, customer_id, record_type, record_id)
            assert result["eligible"] == expected_eligible

    async def test_service_job_completed_eligible(self):
        await self._run_check("service_job", "completed", True)

    async def test_service_job_pending_not_eligible(self):
        await self._run_check("service_job", "pending", False)

    async def test_coaching_appointment_completed_eligible(self):
        await self._run_check("coaching_appointment", "completed", True)

    async def test_invalid_record_type_raises(self):
        from app.engines.customer_reviews.eligibility_service import ReviewEligibilityService
        from app.engines.customer_reviews.constants import ERR_REVIEW_NOT_ELIGIBLE
        svc = ReviewEligibilityService()
        db  = AsyncMock()
        with pytest.raises(ValueError, match=ERR_REVIEW_NOT_ELIGIBLE):
            await svc.check_eligible(db, _uuid(), "invalid_type", _uuid())


# ════════════════════════════════════════════════════════════════════════════════
# 4. Review Service — core (12 tests)
# ════════════════════════════════════════════════════════════════════════════════
class TestSprint24ReviewService:
    def _svc(self):
        from app.engines.customer_reviews.review_service import ReviewService
        return ReviewService()

    # ── Submit review ─────────────────────────────────────────────────────────
    async def test_submit_review_invalid_record_type(self):
        from app.engines.customer_reviews.constants import ERR_REVIEW_NOT_ELIGIBLE
        svc = self._svc()
        db  = _make_db()
        with pytest.raises(ValueError, match=ERR_REVIEW_NOT_ELIGIBLE):
            await svc.submit_review(db, _uuid(), _uuid(), "bad_type", _uuid(), 5)

    async def test_submit_review_invalid_rating(self):
        from app.engines.customer_reviews.constants import ERR_REVIEW_INVALID_RATING
        svc = self._svc()
        db  = _make_db()
        with patch.object(svc._eligibility, "check_eligible", AsyncMock(return_value={"eligible": True, "reason": None, "record": {}})):
            with pytest.raises(ValueError, match=ERR_REVIEW_INVALID_RATING):
                await svc.submit_review(db, _uuid(), _uuid(), "service_job", _uuid(), 0)

    async def test_submit_review_not_eligible(self):
        from app.engines.customer_reviews.constants import ERR_REVIEW_NOT_ELIGIBLE
        svc = self._svc()
        db  = _make_db()
        with patch.object(svc._eligibility, "check_eligible",
                          AsyncMock(return_value={"eligible": False, "reason": "status ineligible", "record": {}})):
            with pytest.raises(ValueError, match=ERR_REVIEW_NOT_ELIGIBLE):
                await svc.submit_review(db, _uuid(), _uuid(), "service_job", _uuid(), 4)

    async def test_submit_review_creates_record(self):
        from app.engines.customer_reviews.review_service import ReviewService
        svc = ReviewService()
        db  = _make_db()

        with patch.object(svc._eligibility, "check_eligible",
                          AsyncMock(return_value={"eligible": True, "reason": None, "record": {}})), \
             patch.object(svc, "_get_policy", AsyncMock(return_value=None)), \
             patch.object(svc, "_log_event", AsyncMock()), \
             patch.object(svc, "_trigger_aggregation", AsyncMock()), \
             patch("app.engines.customer_reviews.review_service.CustomerReview") as MockCR:
            instance = MagicMock()
            instance.status = "pending"
            instance.id     = _uuid()
            instance.tenant_id = _uuid()
            instance.staff_member_id = None
            MockCR.return_value = instance

            result = await svc.submit_review(db, _uuid(), _uuid(), "service_job", _uuid(), 5,
                                             review_text="Great!")
            assert result.status == "pending"
            db.add.assert_called_once()

    # ── Approve review ────────────────────────────────────────────────────────
    async def test_approve_review_sets_approved_status(self):
        svc = self._svc()
        db  = _make_db()
        review = _make_review(status="pending")

        with patch.object(svc, "_get_review", AsyncMock(return_value=review)), \
             patch.object(svc, "_log_event", AsyncMock()), \
             patch.object(svc, "_trigger_aggregation", AsyncMock()):
            result = await svc.approve_review(db, review.id, _uuid())
            assert result.status == "approved"
            assert result.visibility == "public"

    async def test_approve_already_approved_raises(self):
        from app.engines.customer_reviews.constants import ERR_REVIEW_ALREADY_APPROVED
        svc = self._svc()
        db  = _make_db()
        review = _make_review(status="approved")
        with patch.object(svc, "_get_review", AsyncMock(return_value=review)):
            with pytest.raises(ValueError, match=ERR_REVIEW_ALREADY_APPROVED):
                await svc.approve_review(db, review.id, _uuid())

    # ── Reject review ─────────────────────────────────────────────────────────
    async def test_reject_review_sets_rejection_reason(self):
        svc = self._svc()
        db  = _make_db()
        review = _make_review(status="pending")

        with patch.object(svc, "_get_review", AsyncMock(return_value=review)), \
             patch.object(svc, "_log_event", AsyncMock()):
            result = await svc.reject_review(db, review.id, _uuid(), reason="Fake content")
            assert result.status == "rejected"
            assert result.rejection_reason == "Fake content"

    # ── Hide / delete ─────────────────────────────────────────────────────────
    async def test_hide_review(self):
        svc = self._svc()
        db  = _make_db()
        review = _make_review(status="approved")
        with patch.object(svc, "_get_review", AsyncMock(return_value=review)), \
             patch.object(svc, "_log_event", AsyncMock()), \
             patch.object(svc, "_trigger_aggregation", AsyncMock()):
            result = await svc.hide_review(db, review.id, _uuid())
            assert result.status == "hidden"
            assert result.visibility == "hidden"

    async def test_delete_review(self):
        svc = self._svc()
        db  = _make_db()
        review = _make_review(status="approved")
        with patch.object(svc, "_get_review", AsyncMock(return_value=review)), \
             patch.object(svc, "_log_event", AsyncMock()), \
             patch.object(svc, "_trigger_aggregation", AsyncMock()):
            result = await svc.delete_review(db, review.id, _uuid())
            assert result.status == "deleted"

    # ── Reply ─────────────────────────────────────────────────────────────────
    async def test_submit_reply_duplicate_raises(self):
        from app.engines.customer_reviews.constants import ERR_REPLY_ALREADY_EXISTS
        svc = self._svc()
        db  = _make_db()
        review = _make_review(status="approved")
        existing_reply = MagicMock()

        with patch.object(svc, "_get_review", AsyncMock(return_value=review)):
            db.execute = AsyncMock(return_value=MagicMock(
                **{"scalars.return_value.first.return_value": existing_reply}
            ))
            with pytest.raises(ValueError, match=ERR_REPLY_ALREADY_EXISTS):
                await svc.submit_reply(db, review.id, review.tenant_id, _uuid(), "Thank you!")

    async def test_submit_reply_success(self):
        from app.engines.customer_reviews.review_service import ReviewService
        svc = ReviewService()
        # db: first execute call (existing reply check) returns None; second for flush is covered
        db  = _make_db(scalar_value=None)
        review = _make_review(status="approved")

        with patch.object(svc, "_get_review", AsyncMock(return_value=review)), \
             patch.object(svc, "_get_policy", AsyncMock(return_value=None)), \
             patch.object(svc, "_log_event", AsyncMock()):
            # Don't patch ReviewReply class — let a real instance be created
            result = await svc.submit_reply(db, review.id, review.tenant_id, _uuid(), "Great service!")
            # A real ReviewReply is created and added to db
            db.add.assert_called_once()
            assert result.status == "pending"

    # ── Flag ──────────────────────────────────────────────────────────────────
    async def test_flag_review_not_found(self):
        from app.engines.customer_reviews.constants import ERR_REVIEW_NOT_FOUND
        svc = self._svc()
        db  = _make_db()
        with patch.object(svc, "_get_review", AsyncMock(side_effect=ValueError(ERR_REVIEW_NOT_FOUND))):
            with pytest.raises(ValueError, match=ERR_REVIEW_NOT_FOUND):
                await svc.flag_review(db, _uuid(), _uuid(), "customer", "spam")


# ════════════════════════════════════════════════════════════════════════════════
# 5. Aggregation Service (4 tests)
# ════════════════════════════════════════════════════════════════════════════════
class TestSprint24Aggregation:
    def _agg(self):
        from app.engines.customer_reviews.aggregation_service import RatingAggregationService
        return RatingAggregationService()

    async def test_avg_empty_list_returns_zero(self):
        from app.engines.customer_reviews.aggregation_service import RatingAggregationService
        result = RatingAggregationService._avg([])
        assert result == Decimal("0.00")

    async def test_avg_computes_correctly(self):
        from app.engines.customer_reviews.aggregation_service import RatingAggregationService
        result = RatingAggregationService._avg([4, 5, 3, 4])
        assert float(result) == pytest.approx(4.0, abs=0.01)

    async def test_recompute_tenant_summary_no_reviews(self):
        agg = self._agg()
        tenant_id = _uuid()

        summary_mock = MagicMock()
        summary_mock.tenant_id = tenant_id
        summary_mock.total_reviews = 0

        db = _make_db(result_value=[])
        with patch.object(agg, "_get_or_create_tenant_summary", AsyncMock(return_value=summary_mock)):
            result = await agg.recompute_tenant_summary(db, tenant_id)
            assert result.total_reviews == 0

    async def test_recompute_tenant_summary_with_reviews(self):
        agg = self._agg()
        tenant_id = _uuid()

        r1 = _make_review(overall_rating=5, status="approved",
                          approved_at=datetime.now(timezone.utc),
                          provider_rating=5, communication_rating=4,
                          punctuality_rating=4, quality_rating=5, value_rating=4)
        r2 = _make_review(overall_rating=3, status="approved",
                          approved_at=datetime.now(timezone.utc),
                          provider_rating=3, communication_rating=3,
                          punctuality_rating=3, quality_rating=3, value_rating=3)

        summary_mock = MagicMock()
        summary_mock.tenant_id = tenant_id

        db = _make_db(result_value=[r1, r2])
        with patch.object(agg, "_get_or_create_tenant_summary", AsyncMock(return_value=summary_mock)):
            result = await agg.recompute_tenant_summary(db, tenant_id)
            assert result.total_reviews == 2
            assert float(result.average_rating) == pytest.approx(4.0, abs=0.1)
            assert result.five_star_count == 1
            assert result.three_star_count == 1


# ════════════════════════════════════════════════════════════════════════════════
# 6. Router / endpoint smoke tests (6 tests)
# ════════════════════════════════════════════════════════════════════════════════
class TestSprint24RouterImports:
    def test_customer_router_importable(self):
        from app.engines.customer_reviews.customer_router import customer_review_router
        assert customer_review_router is not None
        routes = [r.path for r in customer_review_router.routes]
        assert "/customer/reviews" in routes or any("/customer/reviews" in p for p in routes)

    def test_provider_router_importable(self):
        from app.engines.customer_reviews.provider_router import provider_review_router
        assert provider_review_router is not None
        routes = [r.path for r in provider_review_router.routes]
        assert any("/provider/reviews" in p for p in routes)

    def test_public_router_importable(self):
        from app.engines.customer_reviews.public_router import public_review_router
        assert public_review_router is not None
        routes = [r.path for r in public_review_router.routes]
        assert any("/public/reviews" in p for p in routes)

    def test_admin_review_router_importable(self):
        from app.engines.customer_reviews.admin_router import admin_review_router
        assert admin_review_router is not None
        routes = [r.path for r in admin_review_router.routes]
        assert any("/admin/reviews" in p for p in routes)

    def test_admin_flag_router_importable(self):
        from app.engines.customer_reviews.admin_router import admin_flag_router
        assert admin_flag_router is not None
        routes = [r.path for r in admin_flag_router.routes]
        assert any("/admin/review-flags" in p for p in routes)

    def test_admin_policy_router_importable(self):
        from app.engines.customer_reviews.admin_router import admin_policy_router
        assert admin_policy_router is not None
        routes = [r.path for r in admin_policy_router.routes]
        assert any("/admin/review-policies" in p for p in routes)


# ════════════════════════════════════════════════════════════════════════════════
# 7. Swagger / OpenAPI (2 tests)
# ════════════════════════════════════════════════════════════════════════════════
class TestSprint24Swagger:
    def test_openapi_schema_loadable(self):
        from app.main import app
        schema = app.openapi()
        paths = schema.get("paths", {})
        review_paths = [p for p in paths if "reviews" in p]
        assert len(review_paths) >= 5, f"Expected ≥5 review paths, got {review_paths}"

    def test_admin_review_endpoints_in_schema(self):
        from app.main import app
        schema = app.openapi()
        paths  = schema.get("paths", {})
        assert any("/admin/reviews" in p for p in paths)
        assert any("/admin/review-flags" in p for p in paths)
        assert any("/admin/review-policies" in p for p in paths)
