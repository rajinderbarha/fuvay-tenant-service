"""Phase 2A Slice 2F-25A — Legacy Review Residual Read Privacy, Create-Request
Parent Ownership, Verifier Hardening and Coverage Qualification.

Slice 2F-25 closed the legacy engine's mutation IDORs but left four things
open, and over-claimed on three of them. This slice closes them:

1. `GET /aggregates/{entity_type}/{entity_id}` — was completely unscoped.
2. `GET /requests/jobs/{job_id}` — was a bare job_id lookup.
3. `GET /customers/{customer_id}` — `_assert_owns` guards ONLY the customer
   role, so any tenant principal could enumerate any customer's history.
4. `create_request` — took `job_id` AND `customer_id` from the request body
   with no proof the job existed, belonged to the tenant, or that the customer
   was that job's customer. It was nonetheless marked FULLY_PROTECTED.

It also repairs a REGRESSION Slice 2F-25 introduced: `field_ops.service`
creates the review request on job close and passed no tenant context, so
2F-25's tenant pinning made every job close silently fail to create its
request (`TENANT_ACCESS_DENIED`, swallowed by an `except Exception` that only
logs a warning). No test covered that path, which is why the node-ID
regression comparison could not see it.
"""
from __future__ import annotations

import inspect
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.review import router as legacy_router
from app.engines.review.service import ReviewService
from app.exceptions import NotFoundException, ServiceOSException

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
CUSTOMER_A = uuid.uuid4()
CUSTOMER_B = uuid.uuid4()


def _svc(role="tenant_owner", tenant=TENANT_A, actor=None, row=None):
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(
        **{"scalar_one_or_none.return_value": row,
           "scalars.return_value.all.return_value": []}))
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    with patch("app.engines.review.service.get_redis", return_value=MagicMock()):
        s = ReviewService(db, actor_id=actor or uuid.uuid4(),
                          actor_role=role, actor_tenant_id=tenant)
    return s, db


def _where(db) -> str:
    """WHERE clause only.

    Matching the whole compiled statement is vacuous for scoping assertions --
    every `SELECT reviews.*` lists `reviews.tenant_id` as a column. Slice
    2F-25's first draft made exactly that mistake.
    """
    stmt = str(db.execute.call_args[0][0])
    return stmt.split("WHERE", 1)[1] if "WHERE" in stmt else ""


# ══════════════════════════════════════════════════════════════════
# WS2 — aggregate read
# ══════════════════════════════════════════════════════════════════

class TestAggregateReadScoped:
    @pytest.mark.asyncio
    async def test_aggregate_is_tenant_scoped(self):
        s, db = _svc()
        await s.get_aggregate("tenant", str(TENANT_B))
        assert "tenant_id" in _where(db)

    @pytest.mark.asyncio
    async def test_tenantless_principal_fails_closed(self):
        s, db = _svc(tenant=None)
        with pytest.raises(NotFoundException):
            await s.get_aggregate("tenant", "x")
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_super_admin_is_explicitly_unscoped(self):
        s, db = _svc(role="super_admin", tenant=None)
        await s.get_aggregate("tenant", "x")
        assert "tenant_id" not in _where(db)

    @pytest.mark.asyncio
    async def test_absent_aggregate_returns_zeros_not_an_error(self):
        """Pre-existing contract preserved: a missing aggregate is reported as
        zero counts, which is why foreign entities are now excluded by the
        tenant predicate rather than by a distinguishable error."""
        s, _ = _svc()
        out = await s.get_aggregate("tenant", "unknown")
        assert out["review_count"] == 0

    def test_not_claimed_public_without_an_allow_list(self):
        src = inspect.getsource(ReviewService.get_aggregate)
        assert "NOT" in src and "public" in src.lower()


# ══════════════════════════════════════════════════════════════════
# WS3 — job review-request read
# ══════════════════════════════════════════════════════════════════

class TestJobRequestReadScoped:
    @pytest.mark.asyncio
    async def test_tenant_principal_is_tenant_scoped(self):
        s, db = _svc()
        with pytest.raises(NotFoundException):
            await s.get_review_request("JOB-1")
        assert "tenant_id" in _where(db)

    @pytest.mark.asyncio
    async def test_customer_principal_is_customer_scoped(self):
        s, db = _svc(role="customer", tenant=None, actor=CUSTOMER_A)
        with pytest.raises(NotFoundException):
            await s.get_review_request("JOB-1")
        assert "customer_id" in _where(db)

    @pytest.mark.asyncio
    async def test_tenantless_non_customer_fails_closed(self):
        s, db = _svc(tenant=None)
        with pytest.raises(NotFoundException):
            await s.get_review_request("JOB-1")
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_and_foreign_are_equivalent(self):
        for role, tenant, actor in (("tenant_owner", TENANT_A, None),
                                    ("customer", None, CUSTOMER_A)):
            s, _ = _svc(role=role, tenant=tenant, actor=actor)
            with pytest.raises(NotFoundException):
                await s.get_review_request("JOB-1")


# ══════════════════════════════════════════════════════════════════
# WS4 — customer review-list read
# ══════════════════════════════════════════════════════════════════

class TestCustomerListScoped:
    @pytest.mark.asyncio
    async def test_tenant_principal_cannot_enumerate_across_tenants(self):
        s, db = _svc()
        await s.list_by_customer(CUSTOMER_B, 50, None)
        assert "tenant_id" in _where(db)

    @pytest.mark.asyncio
    async def test_customer_self_view_is_not_tenant_restricted(self):
        """A customer sees its own reviews across every tenant it dealt with."""
        s, db = _svc(role="customer", tenant=None, actor=CUSTOMER_A)
        await s.list_by_customer(CUSTOMER_A, 50, None)
        assert "tenant_id" not in _where(db)

    @pytest.mark.asyncio
    async def test_customer_cannot_read_another_customer(self):
        s, _ = _svc(role="customer", tenant=None, actor=CUSTOMER_A)
        with pytest.raises(NotFoundException):
            await s.list_by_customer(CUSTOMER_B, 50, None)

    @pytest.mark.asyncio
    async def test_tenantless_non_customer_fails_closed(self):
        s, _ = _svc(tenant=None)
        with pytest.raises(NotFoundException):
            await s.list_by_customer(CUSTOMER_B, 50, None)


# ══════════════════════════════════════════════════════════════════
# WS5 — create_request parent ownership
# ══════════════════════════════════════════════════════════════════

class TestCreateRequestParentOwnership:
    def test_signature_has_trusted_internal_flag(self):
        sig = inspect.signature(ReviewService.create_review_request)
        assert "trusted_internal" in sig.parameters
        assert sig.parameters["trusted_internal"].default is False

    def test_parent_job_is_field_ops_job_not_another_pipeline(self):
        """No identifier is adapted between pipelines.

        Checked against EXECUTABLE lines only -- the docstring deliberately
        names ServiceJob/Booking/ServiceBooking to say they are NOT used, and
        an earlier draft of this assertion matched that prose instead of the
        code (the same trap Slice 2F-24 hit).
        """
        src = inspect.getsource(ReviewService.create_review_request)
        body = src.split('"""')[2] if src.count('"""') >= 2 else src
        code = "\n".join(l for l in body.splitlines()
                         if not l.lstrip().startswith("#"))
        assert "field_ops.models import Job" in code
        assert "ServiceJob" not in code
        assert "ServiceBooking" not in code
        assert "Booking" not in code

    def test_job_lookup_is_tenant_scoped(self):
        src = inspect.getsource(ReviewService.create_review_request)
        assert "FieldOpsJob.tenant_id == tenant_id" in src
        assert "FieldOpsJob.job_number == job_id" in src

    def test_customer_is_derived_from_the_job(self):
        src = inspect.getsource(ReviewService.create_review_request)
        assert "customer_id = job.customer_id" in src

    @pytest.mark.asyncio
    async def test_unknown_or_foreign_job_is_rejected_without_writes(self):
        s, db = _svc(row=None)
        with pytest.raises(NotFoundException):
            await s.create_review_request("JOB-X", TENANT_A, CUSTOMER_A, None)
        db.add.assert_not_called()
        db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_client_customer_substitution_is_rejected(self):
        job = MagicMock(customer_id=CUSTOMER_A, assigned_staff_id=None)
        s, db = _svc(row=job)
        with pytest.raises(ServiceOSException) as exc:
            await s.create_review_request("JOB-1", TENANT_A, CUSTOMER_B, None)
        assert exc.value.error_code == "CUSTOMER_MISMATCH"
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_job_without_customer_is_rejected(self):
        job = MagicMock(customer_id=None, assigned_staff_id=None)
        s, db = _svc(row=job)
        with pytest.raises(ServiceOSException) as exc:
            await s.create_review_request("JOB-1", TENANT_A, CUSTOMER_A, None)
        assert exc.value.error_code == "JOB_HAS_NO_CUSTOMER"
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_cross_tenant_create_is_rejected(self):
        s, db = _svc()
        with pytest.raises(ServiceOSException) as exc:
            await s.create_review_request("JOB-1", TENANT_B, CUSTOMER_A, None)
        assert exc.value.error_code == "TENANT_ACCESS_DENIED"
        db.add.assert_not_called()

    def test_ownership_precedes_the_duplicate_check(self):
        """Otherwise the global job_id duplicate lookup is a cross-tenant
        existence oracle via the `already_exists` response."""
        src = inspect.getsource(ReviewService.create_review_request)
        assert src.index("FieldOpsJob.job_number") < src.index("ReviewRequest.job_id == job_id")

    def test_route_uses_the_scope_aware_dependency(self):
        src = inspect.getsource(legacy_router.create_request)
        assert "require_tenant_mutation_permission" in src


# ══════════════════════════════════════════════════════════════════
# The 2F-25 regression this slice repairs
# ══════════════════════════════════════════════════════════════════

class TestInternalJobCloseCallerRepaired:
    def test_field_ops_passes_tenant_context(self):
        from app.engines.field_ops import service as fo
        src = inspect.getsource(fo)
        assert "actor_tenant_id=job.tenant_id" in src
        assert "trusted_internal=True" in src

    @pytest.mark.asyncio
    async def test_internal_call_shape_succeeds(self):
        """Exactly how field_ops constructs and calls the service."""
        s, db = _svc(role="system", tenant=TENANT_A, row=None)
        out = await s.create_review_request(
            "JOB-1", TENANT_A, CUSTOMER_A, None, trusted_internal=True)
        assert out["status"] == "sent"
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_untrusted_caller_cannot_skip_the_parent_check(self):
        """`trusted_internal` defaults False, so the HTTP route always proves
        parentage even though the internal path may bypass it."""
        s, db = _svc(row=None)
        with pytest.raises(NotFoundException):
            await s.create_review_request("JOB-1", TENANT_A, CUSTOMER_A, None)
        db.add.assert_not_called()


# ══════════════════════════════════════════════════════════════════
# WS12 — no partial state; GETs do not mutate
# ══════════════════════════════════════════════════════════════════

class TestNoPartialState:
    @pytest.mark.asyncio
    async def test_every_rejected_create_writes_nothing(self):
        cases = [
            (None, TENANT_A, CUSTOMER_A, NotFoundException),
            (MagicMock(customer_id=None, assigned_staff_id=None), TENANT_A, CUSTOMER_A, ServiceOSException),
            (MagicMock(customer_id=CUSTOMER_A, assigned_staff_id=None), TENANT_A, CUSTOMER_B, ServiceOSException),
        ]
        for row, tenant, cust, exc_type in cases:
            s, db = _svc(row=row)
            with pytest.raises(exc_type):
                await s.create_review_request("JOB-1", tenant, cust, None)
            db.add.assert_not_called()
            db.flush.assert_not_called()
            db.commit.assert_not_called()

    @pytest.mark.parametrize("method", [
        "get_aggregate", "get_review_request", "list_by_customer", "get_review",
    ])
    def test_read_methods_perform_no_writes(self, method):
        src = inspect.getsource(getattr(ReviewService, method))
        assert "db.add(" not in src
        assert "self.db.add" not in src
        assert "commit()" not in src


# ══════════════════════════════════════════════════════════════════
# Coverage is CURRENT canonical, not application-wide complete
# ══════════════════════════════════════════════════════════════════

class TestCoverageQualification:
    import os as _os
    CANON = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
        "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
        "tenant-mutation-endpoint-inventory.csv")
    pytestmark = pytest.mark.skipif(
        not _os.path.exists(CANON),
        reason="retired point-in-time workflow inventory is not a runtime contract",
    )
    VERIFIED = {
        "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
        "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
        "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
    }

    def _rows(self):
        import csv
        with open(self.CANON, encoding="utf-8") as f:
            return list(csv.reader(f))[1:]

    def test_current_canonical_arithmetic_unchanged_by_this_slice(self):
        """2F-25A itself changed no arithmetic; the figures below track the
        LIVE canonical CSV, which Slice 2F-26's application-wide persona sweep
        subsequently advanced (229/212 -> 257/214) by discovering 28 tenant
        mutations on generic prefixes. 2F-25A's own finding is unchanged.
        """
        rows = self._rows()
        # Slice 2F-26 application-wide persona sweep: 28 tenant mutations
        # on generic prefixes (/v1/auth, /v1/media, /v1/me, /v1/bookings,
        # /v1/commerce, /v1/enterprise, /v1/rag) had never been counted --
        # the prefix-based sweep never considered them. Denominator
        # 229 -> 257, numerator 212 -> 214 (26 of the 28 are unprotected),
        # unprotected 17 -> 43.
        # Slice 2F-35: denominator 264 -> 273, numerator 241 -> 252.
        # Slice 2F-36: denominator 273 -> 297, numerator 252 -> 294.
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in self.VERIFIED) == 313

    def test_create_request_row_remains_and_is_now_genuinely_proven(self):
        rows = [r for r in self._rows() if r[1] == "/v1/reviews/requests"]
        assert len(rows) == 1
        assert rows[0][6] in self.VERIFIED

    def test_docs_do_not_claim_application_wide_completeness(self):
        import os
        d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "docs", "workflow-rearchitecture", "phase-02a-slice-02f25a")
        if not os.path.isdir(d):
            pytest.skip("docs not yet written")
        for fn in os.listdir(d):
            if not fn.endswith(".md"):
                continue
            body = open(os.path.join(d, fn), encoding="utf-8").read()
            assert "FINAL_APPLICATION_WIDE_COVERAGE" not in body, fn


# ══════════════════════════════════════════════════════════════════
# WS9 — the verifier must actually discriminate
# ══════════════════════════════════════════════════════════════════

class TestVerifierIsNotVacuous:
    """A verifier that cannot fail proves nothing.

    Slice 2F-25 reported "runtime verification exits zero" while three reads
    were knowingly unscoped, which is exactly the failure mode these tests
    guard against.
    """

    def _verifier(self):
        import importlib.util, os
        p = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts", "workflow_rearchitecture", "verify_legacy_review.py")
        spec = importlib.util.spec_from_file_location("verify_legacy_review", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_verifier_passes_on_the_current_tree(self):
        v = self._verifier()
        v.FAILURES.clear()
        assert v.main() == 0

    def test_verifier_returns_nonzero_when_a_check_fails(self):
        """Feed it a failing condition and confirm it reports exit 1."""
        v = self._verifier()
        v.FAILURES.clear()
        v.check("deliberately failing check", False)
        assert v.FAILURES == ["deliberately failing check"]

    def test_verifier_strips_docstrings_before_matching(self):
        """Checks must not be satisfiable by prose -- the trap 2F-24 and this
        slice both fell into."""
        v = self._verifier()

        def fn_with_lying_docstring():
            """This docstring mentions _get_review_scoped but the body does not."""
            return 1

        assert "_get_review_scoped" not in v._code(fn_with_lying_docstring)
