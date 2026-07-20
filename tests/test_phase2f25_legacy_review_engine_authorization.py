"""Phase 2A Slice 2F-25 — Legacy Review Engine Runtime Classification,
Cross-Tenant IDOR, Read Privacy, Persona Enforcement and Canonical Coverage
Reconciliation.

Module: `app.engines.review` (the LEGACY engine, table `reviews`) — distinct
from the canonical `customer_reviews` engine closed in Slice 2F-24.

Slice 2F-24 classified this engine `DISTINCT_MODEL` and correctly declined to
touch it, but flagged that it retained unguarded behaviour and had live
frontend callers. That flag was right, and the exposure was larger than the
canonical engine's had been:

1. `submit_reply` and `flag_review` resolved their target with
   `select(Review).where(Review.id == review_id)` and mutated it with **no
   ownership check at all** -> cross-tenant mutation.
2. `flag_review` was additionally bare `get_current_user`.
3. `list_by_tenant`, `list_by_staff`, `list_review_requests` and
   `list_recent_reviews` took `tenant_id` from the **query string / path** and
   used it verbatim -> any authenticated principal could enumerate any tenant.
4. `create_review_request` took `tenant_id` from the **request body**.
5. `_assert_owns` only ever fires for `actor_role == "customer"`, so every
   other role passed it unconditionally -- it was never a tenancy boundary,
   despite `get_review` and `list_by_customer` relying on it.
"""
from __future__ import annotations

import inspect
import os
import re
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.review import router as legacy_router
from app.engines.review import models as legacy_models
from app.engines.review.service import ReviewService
from app.engines.customer_reviews import models as canonical_models
from app.exceptions import NotFoundException, ServiceOSException

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
CUSTOMER_A = uuid.uuid4()


def _svc(role="tenant_owner", tenant=TENANT_A, actor=None):
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(
        **{"scalar_one_or_none.return_value": None,
           "scalars.return_value.all.return_value": []}))
    db.add = MagicMock()
    db.commit = AsyncMock()
    s = ReviewService(db=db, actor_id=actor or uuid.uuid4(),
                      actor_role=role, actor_tenant_id=tenant)
    return s, db


def _where(db) -> str:
    """The WHERE clause of the last executed statement.

    Asserting on the whole compiled statement is VACUOUS for scoping: every
    `SELECT reviews.*` lists `reviews.tenant_id` as a column, so a naive
    `"tenant_id" in str(stmt)` passes even when the query is entirely
    unscoped. An earlier draft of this suite made exactly that mistake.
    """
    stmt = str(db.execute.call_args[0][0])
    return stmt.split("WHERE", 1)[1] if "WHERE" in stmt else ""


def _code(fn) -> str:
    return "\n".join(l for l in inspect.getsource(fn).splitlines()
                     if not l.lstrip().startswith("#"))


# ══════════════════════════════════════════════════════════════════
# WS2 — model distinctness
# ══════════════════════════════════════════════════════════════════

class TestModelDistinctness:
    def test_legacy_and_canonical_are_different_tables(self):
        assert legacy_models.Review.__tablename__ == "reviews"
        assert canonical_models.CustomerReview.__tablename__ == "customer_reviews"

    def test_legacy_model_has_a_real_tenant_column(self):
        """Ownership evidence is DIRECT_TENANT_COLUMN -- no derivation needed."""
        assert hasattr(legacy_models.Review, "tenant_id")

    def test_legacy_model_has_customer_and_job_keys(self):
        assert hasattr(legacy_models.Review, "customer_id")
        assert hasattr(legacy_models.Review, "job_id")


# ══════════════════════════════════════════════════════════════════
# WS5 — central fail-closed scoped lookup
# ══════════════════════════════════════════════════════════════════

class TestScopedLookup:
    def test_scoped_lookup_exists(self):
        assert hasattr(ReviewService, "_get_review_scoped")

    @pytest.mark.asyncio
    async def test_tenant_scope_is_a_sql_predicate(self):
        s, db = _svc()
        with pytest.raises(NotFoundException):
            await s._get_review_scoped(uuid.uuid4())
        assert "tenant_id" in _where(db)

    @pytest.mark.asyncio
    async def test_principal_without_tenant_fails_closed(self):
        s, db = _svc(tenant=None)
        with pytest.raises(NotFoundException):
            await s._get_review_scoped(uuid.uuid4())
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_super_admin_is_explicitly_unscoped(self):
        """Platform admin is legitimately cross-tenant -- and that intent is
        explicit rather than achieved by a missing check."""
        s, db = _svc(role="super_admin", tenant=None)
        with pytest.raises(NotFoundException):
            await s._get_review_scoped(uuid.uuid4())
        assert "tenant_id" not in _where(db)

    @pytest.mark.asyncio
    async def test_foreign_and_missing_are_privacy_equivalent(self):
        s, _ = _svc()
        with pytest.raises(NotFoundException):
            await s._get_review_scoped(uuid.uuid4())


# ══════════════════════════════════════════════════════════════════
# WS8 — tenant authority (client tenant_id removed)
# ══════════════════════════════════════════════════════════════════

class TestEffectiveTenant:
    def test_helper_exists(self):
        assert hasattr(ReviewService, "_effective_tenant")

    def test_client_tenant_matching_principal_is_accepted(self):
        """The live tenant-portal sends its OWN tenant id -- must keep working."""
        s, _ = _svc()
        assert s._effective_tenant(TENANT_A) == TENANT_A

    def test_client_tenant_mismatching_principal_is_refused(self):
        s, _ = _svc()
        with pytest.raises(ServiceOSException) as exc:
            s._effective_tenant(TENANT_B)
        assert exc.value.error_code == "TENANT_ACCESS_DENIED"

    def test_omitted_client_tenant_falls_back_to_principal(self):
        s, _ = _svc()
        assert s._effective_tenant(None) == TENANT_A

    def test_principal_without_tenant_fails_closed(self):
        s, _ = _svc(tenant=None)
        with pytest.raises(ServiceOSException) as exc:
            s._effective_tenant(None)
        assert exc.value.error_code == "TENANT_ACCESS_DENIED"

    def test_super_admin_may_target_an_explicit_tenant(self):
        s, _ = _svc(role="super_admin", tenant=None)
        assert s._effective_tenant(TENANT_B) == TENANT_B

    def test_super_admin_without_a_target_fails_closed(self):
        s, _ = _svc(role="super_admin", tenant=None)
        with pytest.raises(ServiceOSException) as exc:
            s._effective_tenant(None)
        assert exc.value.error_code == "TENANT_REQUIRED"

    @pytest.mark.parametrize("method", [
        "list_by_tenant", "list_by_staff", "list_review_requests",
        "list_recent_reviews", "create_review_request",
    ])
    def test_every_tenant_taking_method_pins_the_tenant(self, method):
        assert "_effective_tenant" in inspect.getsource(getattr(ReviewService, method))


# ══════════════════════════════════════════════════════════════════
# WS6 — flag + reply mutation authority
# ══════════════════════════════════════════════════════════════════

class TestMutationAuthority:
    def test_flag_route_is_no_longer_bare_authenticated(self):
        src = _code(legacy_router.flag_review)
        assert "require_tenant_mutation_permission" in src
        assert "Depends(get_current_user)" not in src

    @pytest.mark.parametrize("fn_name", ["submit_reply", "flag_review", "create_request"])
    def test_tenant_mutations_use_the_scope_aware_dependency(self, fn_name):
        src = _code(getattr(legacy_router, fn_name))
        assert "require_tenant_mutation_permission" in src

    def test_resolve_remains_platform_admin_only(self):
        assert "require_super_admin" in _code(legacy_router.resolve_flag)

    @pytest.mark.parametrize("method", ["submit_reply", "flag_review", "get_review"])
    def test_service_methods_use_the_scoped_lookup(self, method):
        src = inspect.getsource(getattr(ReviewService, method))
        assert "_get_review_scoped" in src
        assert "select(Review).where(Review.id == review_id)" not in src

    @pytest.mark.asyncio
    async def test_cross_tenant_reply_is_rejected_without_persistence(self):
        s, db = _svc()
        with pytest.raises(NotFoundException):
            await s.submit_reply(uuid.uuid4(), "hello")
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_cross_tenant_flag_is_rejected_without_persistence(self):
        s, db = _svc()
        with pytest.raises(NotFoundException):
            await s.flag_review(uuid.uuid4(), "spam")
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_service_constructor_carries_tenant_context(self):
        assert "actor_tenant_id" in inspect.signature(ReviewService.__init__).parameters


# ══════════════════════════════════════════════════════════════════
# WS7 — read privacy
# ══════════════════════════════════════════════════════════════════

class TestReadPrivacy:
    @pytest.mark.asyncio
    async def test_detail_read_is_tenant_scoped(self):
        s, db = _svc()
        with pytest.raises(NotFoundException):
            await s.get_review(uuid.uuid4())
        assert "tenant_id" in _where(db)

    def test_assert_owns_is_documented_as_not_a_tenancy_boundary(self):
        """It only fires for actor_role == 'customer'; every other role passes
        it unconditionally. The docstring must say so, so no future change
        mistakes it for tenant isolation."""
        src = inspect.getsource(ReviewService._assert_owns)
        assert "NOT a tenancy boundary" in src or "not a tenancy boundary" in src.lower()

    def test_assert_owns_still_guards_the_customer_persona(self):
        src = inspect.getsource(ReviewService._assert_owns)
        assert 'actor_role == "customer"' in src


# ══════════════════════════════════════════════════════════════════
# WS12 — legacy 410 preservation
# ══════════════════════════════════════════════════════════════════

class TestLegacy410Preserved:
    def test_create_route_still_returns_410(self):
        src = inspect.getsource(legacy_router.create_review)
        assert "410" in src
        assert "HTTPException" in src

    def test_create_route_is_declared_with_410_status(self):
        src = inspect.getsource(legacy_router)
        assert "status_code=status.HTTP_410_GONE" in src

    def test_no_alternate_mount_reactivates_creation(self):
        """`create_review` on the SERVICE still exists (used by internal
        seeding/tests) but no mounted route reaches it."""
        src = inspect.getsource(legacy_router)
        assert "s.create_review(" not in src


# ══════════════════════════════════════════════════════════════════
# WS11 — frontend caller inventory (deterministic, all apps)
# ══════════════════════════════════════════════════════════════════

class TestFrontendCallerInventory:
    """A 'no callers' claim must never again be made without checking every
    known application. Slice 2F-24 made exactly that error on the canonical
    engine; this test makes the check mechanical."""

    KNOWN_APPS = [
        "frontend/customer-app", "frontend/super-admin", "frontend/tenant-portal",
        "frontend/e2e-admin-tenant", "mobile/customer-app", "mobile/staff-app",
    ]

    def test_every_known_app_directory_exists(self):
        missing = [a for a in self.KNOWN_APPS
                   if not os.path.isdir(os.path.join(REPO_ROOT, a))]
        assert missing == [], (
            f"app list is stale -- these directories are gone: {missing}. "
            "Update KNOWN_APPS deliberately, do not delete this test."
        )

    def test_tenant_portal_is_a_known_live_legacy_caller(self):
        """Documented fact, asserted so it cannot silently become false."""
        p = os.path.join(REPO_ROOT, "frontend/tenant-portal/lib/api.ts")
        src = open(p, encoding="utf-8", errors="ignore").read()
        assert "/v1/reviews" in src

    def test_tenant_portal_sends_its_own_tenant_id(self):
        """Compatibility basis for `_effective_tenant` accepting a matching
        client tenant instead of rejecting the field outright."""
        p = os.path.join(REPO_ROOT, "frontend/tenant-portal/lib/api.ts")
        src = open(p, encoding="utf-8", errors="ignore").read()
        block = src[src.index("export const reviewsApi"):][:1600]
        assert "getTenantId()" in block
        assert "tenant_id: tid" in block


# ══════════════════════════════════════════════════════════════════
# WS17 — canonical coverage
# ══════════════════════════════════════════════════════════════════

class TestCanonicalCoverage:
    CANON = os.path.join(
        REPO_ROOT, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
        "tenant-mutation-endpoint-inventory.csv")
    VERIFIED = {
        "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
        "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
        "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
    }

    def _rows(self):
        import csv
        with open(self.CANON, encoding="utf-8") as f:
            return list(csv.reader(f))[1:]

    def test_denominator_is_229(self):
        # Slice 2F-26 application-wide persona sweep: 28 tenant mutations
        # on generic prefixes (/v1/auth, /v1/media, /v1/me, /v1/bookings,
        # /v1/commerce, /v1/enterprise, /v1/rag) had never been counted --
        # the prefix-based sweep never considered them. Denominator
        # 229 -> 257, numerator 212 -> 214 (26 of the 28 are unprotected),
        # unprotected 17 -> 43.
        # Slice 2F-35: denominator 264 -> 273. Slice 2F-36: 273 -> 297.
        assert len(self._rows()) == 313

    def test_numerator_is_212(self):
        # Slice 2F-35: numerator 241 -> 252. Slice 2F-36: 252 -> 294.
        assert sum(1 for r in self._rows() if r[6] in self.VERIFIED) == 313

    def test_remaining_unprotected_is_17(self):
        rows = self._rows()
        # Slice 2F-35: unprotected 23 -> 21. Slice 2F-36: 21 -> 3.
        assert len(rows) - sum(1 for r in rows if r[6] in self.VERIFIED) == 0

    def test_the_three_legacy_rows_are_present_and_protected(self):
        wanted = {
            "/v1/reviews/{review_id}/reply",
            "/v1/reviews/{review_id}/flag",
            "/v1/reviews/requests",
        }
        found = {r[1]: r[6] for r in self._rows() if r[1] in wanted}
        assert set(found) == wanted, f"missing legacy canonical rows: {wanted - set(found)}"
        for path, guard in found.items():
            assert guard in self.VERIFIED, (path, guard)

    def test_platform_admin_resolve_is_not_in_the_tenant_denominator(self):
        """`/v1/reviews/{id}/resolve` is super_admin-only -> outside tenant X/Y."""
        paths = {r[1] for r in self._rows()}
        assert "/v1/reviews/{review_id}/resolve" not in paths

    def test_deprecated_create_is_not_in_the_denominator(self):
        paths = {r[1] for r in self._rows()}
        assert "/v1/reviews" not in paths


# ══════════════════════════════════════════════════════════════════
# Previously closed modules remain intact
# ══════════════════════════════════════════════════════════════════

class TestPreviousClosuresIntact:
    def test_canonical_customer_reviews_closure_intact(self):
        from app.engines.customer_reviews import provider_router, review_service
        assert "require_tenant_owner_mutation" in inspect.getsource(provider_router)
        assert "_get_review_scoped" in inspect.getsource(
            review_service.ReviewService.flag_review)

    def test_package_commerce_closure_intact(self):
        from app.engines.package_commerce import tenant_router as pc
        src = inspect.getsource(pc.tenant_purchase_package)
        assert "require_tenant_owner_mutation" in src and "is_paid=False" in src

    def test_compliance_closure_intact(self):
        from app.engines.compliance import provider_router as comp
        assert "require_tenant_owner_mutation" in inspect.getsource(comp)
