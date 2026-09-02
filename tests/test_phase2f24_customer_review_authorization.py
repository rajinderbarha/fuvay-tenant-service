"""Phase 2A Slice 2F-24 — Customer Review Provider Reply, Flagging, Tenant
Ownership, Actor Attribution, Moderation State and Same-Record Alternate-Route
Closure.

Selected module: `app.engines.customer_reviews.provider_router`
Selected mutations:
  POST /v1/provider/reviews/{review_id}/reply   (submit_reply)
  POST /v1/provider/reviews/{review_id}/flag    (flag_review)

The defects closed here:

1. `flag_review` resolved the review with a PRIMARY-KEY-ONLY lookup and
   performed NO ownership check, then wrote `status = flagged`. Behind a
   bare-authenticated route, any authenticated principal could flag any
   review in ANY tenant.
2. `submit_reply` was bare-authenticated, so a `customer` could post the
   official provider reply -- recorded in the event log as ACTOR_PROVIDER.
3. `customer_router.flag_review` took `tenant_id` from the request BODY, so a
   client chose the tenant its moderation record was attributed to.
4. Both `GET /{review_id}` routes (provider and customer) were unscoped
   primary-key reads -- read IDOR across every tenant, exposing pending,
   hidden, rejected and deleted reviews plus moderation/rejection reasons.
"""
from __future__ import annotations

import inspect
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.customer_reviews import (
    admin_router, customer_router, provider_router, review_service,
)
from app.engines.customer_reviews.constants import (
    ACTOR_CUSTOMER, ACTOR_PROVIDER, ERR_PERMISSION_DENIED, ERR_REVIEW_NOT_FOUND,
    FLAG_REASONS,
)
from app.engines.customer_reviews.provider_router import (
    ProviderReplyRequest, ReviewFlagRequest,
)
from app.engines.customer_reviews.customer_router import CustomerFlagRequest

SVC = review_service.ReviewService


def _code(fn) -> str:
    """Source with comment lines stripped.

    Assertions about what a route *does* must not be satisfied (or defeated)
    by prose in an explanatory comment -- an early draft of this suite
    matched the word `Depends(get_current_user)` inside a comment describing
    the very defect that had been removed.
    """
    return "\n".join(
        line for line in inspect.getsource(fn).splitlines()
        if not line.lstrip().startswith("#")
    )


def _fake_db(row=None):
    """Async session double whose SELECT resolves to `row`."""
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.first.return_value": row}
    ))
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


# ══════════════════════════════════════════════════════════════════
# WS4 — the central fail-closed scoped lookup
# ══════════════════════════════════════════════════════════════════

class TestCentralScopedLookup:
    def test_scoped_lookup_exists(self):
        assert hasattr(SVC, "_get_review_scoped")

    @pytest.mark.asyncio
    async def test_no_scope_fails_closed_before_any_query(self):
        """There is no `tenant_id=None means all tenants` global mode."""
        svc = SVC()
        db = _fake_db()
        with pytest.raises(ValueError) as exc:
            await svc._get_review_scoped(db, uuid.uuid4())
        assert str(exc.value) == ERR_PERMISSION_DENIED
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_tenant_scope_applied_as_sql_predicate(self):
        """Ownership must filter in SQL, not after loading the foreign row."""
        svc = SVC()
        db = _fake_db(row=None)
        with pytest.raises(ValueError) as exc:
            await svc._get_review_scoped(db, uuid.uuid4(), tenant_id=uuid.uuid4())
        assert str(exc.value) == ERR_REVIEW_NOT_FOUND
        stmt = str(db.execute.call_args[0][0])
        assert "tenant_id" in stmt

    @pytest.mark.asyncio
    async def test_customer_scope_applied_as_sql_predicate(self):
        svc = SVC()
        db = _fake_db(row=None)
        with pytest.raises(ValueError):
            await svc._get_review_scoped(db, uuid.uuid4(), customer_id=uuid.uuid4())
        assert "customer_id" in str(db.execute.call_args[0][0])

    @pytest.mark.asyncio
    async def test_foreign_and_missing_are_privacy_equivalent(self):
        """Both raise REVIEW_NOT_FOUND, so the route is not an existence
        oracle for other tenants' reviews."""
        svc = SVC()
        for scope in ({"tenant_id": uuid.uuid4()}, {"customer_id": uuid.uuid4()}):
            with pytest.raises(ValueError) as exc:
                await svc._get_review_scoped(_fake_db(row=None), uuid.uuid4(), **scope)
            assert str(exc.value) == ERR_REVIEW_NOT_FOUND

    def test_unscoped_helper_documents_admin_only_use(self):
        src = inspect.getsource(SVC._get_review)
        assert "UNSCOPED" in src
        assert "never be" in src or "must never" in src


# ══════════════════════════════════════════════════════════════════
# WS7 — provider flag authority (the cross-tenant IDOR)
# ══════════════════════════════════════════════════════════════════

class TestProviderFlagAuthority:
    def test_flag_route_uses_mutation_capable_dependency(self):
        src = inspect.getsource(provider_router.flag_review)
        assert "require_tenant_owner_mutation" in src

    def test_flag_route_no_longer_bare_authenticated(self):
        assert "Depends(get_current_user)" not in _code(provider_router.flag_review)

    def test_service_uses_scoped_lookup_not_primary_key(self):
        src = _code(SVC.flag_review)
        assert "_get_review_scoped" in src
        assert "self._get_review(" not in src

    def test_flag_tenant_is_taken_from_the_review_not_the_caller(self):
        src = inspect.getsource(SVC.flag_review)
        assert "tenant_id          = review.tenant_id" in src

    @pytest.mark.asyncio
    async def test_cross_tenant_flag_is_rejected(self):
        """Tenant A flagging Tenant B's review: the scoped SELECT matches no
        row, so it is rejected as NOT_FOUND with no status mutation."""
        svc = SVC()
        db = _fake_db(row=None)
        with pytest.raises(ValueError) as exc:
            await svc.flag_review(
                db, uuid.uuid4(), uuid.uuid4(), ACTOR_PROVIDER, "spam",
                tenant_id=uuid.uuid4(),
            )
        assert str(exc.value) == ERR_REVIEW_NOT_FOUND
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_unscoped_flag_call_fails_closed(self):
        svc = SVC()
        db = _fake_db()
        with pytest.raises(ValueError) as exc:
            await svc.flag_review(db, uuid.uuid4(), uuid.uuid4(), ACTOR_PROVIDER, "spam")
        assert str(exc.value) == ERR_PERMISSION_DENIED
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_actor_type_fails_closed(self):
        """A caller cannot attribute a flag to a persona it is not."""
        svc = SVC()
        db = _fake_db()
        for bogus in ("admin", "system", "", "PROVIDER", "staff"):
            with pytest.raises(ValueError) as exc:
                await svc.flag_review(
                    db, uuid.uuid4(), uuid.uuid4(), bogus, "spam",
                    tenant_id=uuid.uuid4(),
                )
            assert str(exc.value) == ERR_PERMISSION_DENIED
        db.add.assert_not_called()

    def test_reason_code_is_validated_at_the_schema(self):
        for reason in FLAG_REASONS:
            assert ReviewFlagRequest(reason_code=reason).reason_code == reason
        with pytest.raises(Exception):
            ReviewFlagRequest(reason_code="arbitrary_reason")


# ══════════════════════════════════════════════════════════════════
# WS6 — provider reply authority (customer impersonation)
# ══════════════════════════════════════════════════════════════════

class TestProviderReplyAuthority:
    def test_reply_route_uses_mutation_capable_dependency(self):
        src = inspect.getsource(provider_router.submit_reply)
        assert "require_tenant_owner_mutation" in src

    def test_reply_route_no_longer_bare_authenticated(self):
        assert "Depends(get_current_user)" not in _code(provider_router.submit_reply)

    def test_reply_uses_central_scoped_lookup(self):
        src = inspect.getsource(SVC.submit_reply)
        assert "_get_review_scoped" in src

    @pytest.mark.asyncio
    async def test_cross_tenant_reply_is_rejected_without_persistence(self):
        svc = SVC()
        db = _fake_db(row=None)
        with pytest.raises(ValueError) as exc:
            await svc.submit_reply(
                db, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "hello",
            )
        assert str(exc.value) == ERR_REVIEW_NOT_FOUND
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_actor_id_is_server_derived(self):
        src = inspect.getsource(provider_router.submit_reply)
        assert "replied_by_user_id = user.user_id" in src

    def test_reply_body_rejects_actor_tenant_and_status_fields(self):
        assert ProviderReplyRequest(reply_text="ok").reply_text == "ok"
        for bad in ("tenant_id", "replied_by_user_id", "actor_type", "status",
                    "provider_id", "review_id"):
            with pytest.raises(Exception):
                ProviderReplyRequest(**{"reply_text": "ok", bad: "x"})

    def test_reply_text_is_validated(self):
        with pytest.raises(Exception):
            ProviderReplyRequest(reply_text="")

    def test_one_reply_per_review_preserved(self):
        src = inspect.getsource(SVC.submit_reply)
        assert "ERR_REPLY_ALREADY_EXISTS" in src


# ══════════════════════════════════════════════════════════════════
# WS8 — customer flag route (same-record alternate)
# ══════════════════════════════════════════════════════════════════

class TestCustomerFlagAuthority:
    def test_client_tenant_id_is_no_longer_read(self):
        src = _code(customer_router.flag_review)
        assert 'body["tenant_id"]' not in src
        assert 'body.get("tenant_id")' not in src

    def test_route_passes_no_client_tenant_authority(self):
        src = inspect.getsource(customer_router.flag_review)
        assert "tenant_id          = None" in src
        assert "customer_id        = user.user_id" in src

    def test_schema_rejects_tenant_id_explicitly(self):
        assert CustomerFlagRequest().reason_code == "other"
        with pytest.raises(Exception):
            CustomerFlagRequest(tenant_id=str(uuid.uuid4()))

    def test_schema_rejects_actor_and_status_fields(self):
        for bad in ("flagged_by_type", "status", "customer_id", "flagged_by_user_id"):
            with pytest.raises(Exception):
                CustomerFlagRequest(**{bad: "x"})

    def test_actor_type_is_server_set_to_customer(self):
        src = inspect.getsource(customer_router.flag_review)
        assert 'flagged_by_type    = "customer"' in src

    @pytest.mark.asyncio
    async def test_customer_cannot_flag_another_customers_review(self):
        svc = SVC()
        db = _fake_db(row=None)
        with pytest.raises(ValueError) as exc:
            await svc.flag_review(
                db, uuid.uuid4(), uuid.uuid4(), ACTOR_CUSTOMER, "spam",
                customer_id=uuid.uuid4(),
            )
        assert str(exc.value) == ERR_REVIEW_NOT_FOUND
        db.add.assert_not_called()


# ══════════════════════════════════════════════════════════════════
# WS14 — read privacy (the unscoped GET routes)
# ══════════════════════════════════════════════════════════════════

class TestReadPrivacy:
    def test_provider_detail_read_is_tenant_scoped(self):
        src = inspect.getsource(provider_router.get_review)
        assert "tenant_id=user.tenant_id" in src

    def test_customer_detail_read_is_customer_scoped(self):
        src = inspect.getsource(customer_router.get_my_review)
        assert "customer_id=user.user_id" in src

    def test_public_get_review_requires_a_scope(self):
        sig = inspect.signature(SVC.get_review)
        assert "tenant_id" in sig.parameters
        assert "customer_id" in sig.parameters

    @pytest.mark.asyncio
    async def test_unscoped_public_read_fails_closed(self):
        svc = SVC()
        with pytest.raises(ValueError) as exc:
            await svc.get_review(_fake_db(), uuid.uuid4())
        assert str(exc.value) == ERR_PERMISSION_DENIED

    def test_provider_list_and_summaries_remain_tenant_scoped(self):
        for fn in (provider_router.list_my_reviews,
                   provider_router.get_tenant_rating_summary,
                   provider_router.get_staff_rating_summary):
            assert "user.tenant_id" in inspect.getsource(fn)


# ══════════════════════════════════════════════════════════════════
# WS12 — alternate routes and legacy 410
# ══════════════════════════════════════════════════════════════════

class TestAlternateRoutes:
    def test_admin_moderation_remains_super_admin_only(self):
        src = inspect.getsource(admin_router)
        assert "require_super_admin" in src
        # Every admin mutation route is guarded; none is bare-authenticated.
        assert "Depends(get_current_user)" not in src

    def test_admin_read_uses_explicitly_unscoped_helper(self):
        """Platform admin is legitimately cross-tenant; the intent must be
        visible at the call site rather than achieved with a fake scope."""
        src = inspect.getsource(admin_router)
        assert "_svc._get_review(" in src

    def test_legacy_review_create_remains_410(self):
        from app.engines.review import router as legacy
        src = inspect.getsource(legacy.create_review)
        assert "410" in src

    def test_legacy_engine_is_a_distinct_model(self):
        """`app.engines.review` operates on the `reviews` table, NOT
        `customer_reviews`, so it is not a same-record alternate."""
        from app.engines.review import models as legacy_models
        assert legacy_models.Review.__tablename__ == "reviews"
        from app.engines.customer_reviews import models as canonical
        assert canonical.CustomerReview.__tablename__ == "customer_reviews"


# ══════════════════════════════════════════════════════════════════
# WS13 / WS18 — service-layer safety and no partial persistence
# ══════════════════════════════════════════════════════════════════

class TestServiceLayerSafety:
    def test_no_tenant_none_global_mode(self):
        src = inspect.getsource(SVC._get_review_scoped)
        assert "if tenant_id is None and customer_id is None" in src

    @pytest.mark.asyncio
    async def test_denied_flag_writes_nothing(self):
        svc = SVC()
        db = _fake_db(row=None)
        with pytest.raises(ValueError):
            await svc.flag_review(
                db, uuid.uuid4(), uuid.uuid4(), ACTOR_PROVIDER, "spam",
                tenant_id=uuid.uuid4(),
            )
        db.add.assert_not_called()
        db.flush.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_denied_reply_writes_nothing(self):
        svc = SVC()
        db = _fake_db(row=None)
        with pytest.raises(ValueError):
            await svc.submit_reply(db, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "x")
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_ownership_check_precedes_any_write_in_flag(self):
        src = inspect.getsource(SVC.flag_review)
        assert src.index("_get_review_scoped") < src.index("db.add")

    def test_ownership_check_precedes_any_write_in_reply(self):
        src = inspect.getsource(SVC.submit_reply)
        assert src.index("_get_review_scoped") < src.index("db.add")


# ══════════════════════════════════════════════════════════════════
# WS11 — rating aggregate integrity
# ══════════════════════════════════════════════════════════════════

class TestRatingAggregateIntegrity:
    def test_flagging_does_not_touch_rating_aggregates(self):
        src = inspect.getsource(SVC.flag_review)
        assert "_trigger_aggregation" not in src

    def test_reply_does_not_touch_rating_aggregates(self):
        src = inspect.getsource(SVC.submit_reply)
        assert "_trigger_aggregation" not in src


# ══════════════════════════════════════════════════════════════════
# Previously closed modules remain intact
# ══════════════════════════════════════════════════════════════════

class TestPreviousClosuresIntact:
    def test_retired_package_commerce_stays_absent(self):
        from pathlib import Path
        assert not Path("app/engines/package_commerce/tenant_router.py").exists()

    def test_compliance_closure_intact(self):
        from app.engines.compliance import provider_router as comp
        assert "require_tenant_owner_mutation" in inspect.getsource(comp)
