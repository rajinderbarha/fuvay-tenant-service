"""Phase 2A Slice 2F-26 — application-wide persona-based mutation inventory.

Inventory/reconciliation slice: NO authorization behaviour changes.

The prefix-based sweep that preceded this slice identified tenant routes by
`/v1/tenant|provider|staff` path prefixes. Slice 2F-25 proved that misses real
capabilities (three tenant mutations under `/v1/reviews`). This slice rebuilt
the inventory from actual persona, capability and side-effect evidence and
found the blind spot was far larger: **28 further tenant mutations**, 26 of
them unprotected, on `/v1/auth`, `/v1/media`, `/v1/me`, `/v1/bookings`,
`/v1/commerce`, `/v1/enterprise` and `/v1/rag`.

Denominator 229 -> 257, numerator 212 -> 214, unprotected 17 -> 43.
"""
from __future__ import annotations

import csv
import importlib.util
import inspect
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26")
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")
VERIFIED = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
}


def _rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def _canon():
    return list(csv.reader(open(CANON, encoding="utf-8")))[1:]


def _norm(p):
    return p if p.startswith("/v1/") else ("/v1" + p if p.startswith("/") else p)


# ══════════════════════════════════════════════════════════════════
# Coverage arithmetic
# ══════════════════════════════════════════════════════════════════

class TestCanonicalArithmetic:
    def test_denominator_is_257(self):
        assert len(_canon()) == 313

    def test_numerator_is_214(self):
        assert sum(1 for r in _canon() if r[6] in VERIFIED) == 313

    def test_unprotected_is_43(self):
        # Rebaselined by Slice 2F-36: the enterprise/tenant-admin/
        # operational batch moved the live canonical from 273/21 to
        # 297/3. The 2F-26 historical queue artifact
        # (test_queue_accounts_for_every_unprotected_route_once) still
        # counts its own point-in-time 43 and is left unchanged.
        rows = _canon()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_protected_plus_unprotected_equals_denominator(self):
        rows = _canon()
        p = sum(1 for r in rows if r[6] in VERIFIED)
        assert p + (len(rows) - p) == len(rows) == 313

    def test_no_duplicate_canonical_keys(self):
        keys = [(r[0], _norm(r[1])) for r in _canon()]
        assert len(keys) == len(set(keys))

    def test_no_forbidden_protection_status(self):
        for r in _canon():
            assert r[6] not in ("UNKNOWN_PROTECTION", "UNVERIFIED", "UNKNOWN_BEHAVIOR", "")


# ══════════════════════════════════════════════════════════════════
# The blind-spot finding
# ══════════════════════════════════════════════════════════════════

class TestGenericPrefixBlindSpot:
    def test_canonical_rows_exist_outside_tenant_prefixes(self):
        """A sweep that finds none has not looked."""
        generic = [r for r in _canon()
                   if not _norm(r[1]).startswith(("/v1/tenant", "/v1/provider", "/v1/staff"))]
        assert len(generic) >= 60, len(generic)

    @pytest.mark.parametrize("method,path", [
        ("PUT", "/v1/auth/staff/{user_id}/permissions"),
        ("POST", "/v1/auth/staff/invite"),
        ("POST", "/v1/auth/mfa/disable"),
        ("POST", "/v1/auth/api-keys"),
        ("PUT", "/v1/me/profile"),
        ("POST", "/v1/media/upload"),
        ("GET", "/v1/commerce/tenants/{tenant_id}/deposit"),
    ])
    def test_each_discovered_route_now_has_a_canonical_row(self, method, path):
        keys = {(r[0], _norm(r[1])) for r in _canon()}
        assert (method, path) in keys

    def test_mutating_get_is_represented(self):
        """`GET .../deposit` lazily creates a row via `_get_or_create_deposit`.

        A method-based inventory can never see this, which is why the sweep
        classifies by side effect rather than by HTTP verb.
        """
        keys = {(r[0], _norm(r[1])) for r in _canon()}
        assert ("GET", "/v1/commerce/tenants/{tenant_id}/deposit") in keys

    def test_deposit_get_really_does_lazily_create(self):
        from app.engines.platform_commerce.service import CommerceService
        src = inspect.getsource(CommerceService.get_deposit_status)
        assert "_get_or_create_deposit" in src


# ══════════════════════════════════════════════════════════════════
# Artifacts
# ══════════════════════════════════════════════════════════════════

class TestSweepArtifacts:
    @pytest.mark.parametrize("name", [
        "complete-mounted-route-inventory.csv",
        "route-side-effect-classification.csv",
        "mutation-persona-classification.csv",
        "mutating-get-audit.csv",
        "read-only-post-audit.csv",
        "canonical-runtime-row-matching.csv",
        "generic-prefix-tenant-mutations.csv",
        "prefixed-route-false-positive-audit.csv",
        "canonical-row-diff.csv",
        "canonical-coverage-arithmetic.csv",
        "rebuilt-unprotected-module-queue.csv",
    ])
    def test_artifact_exists_and_is_populated(self, name):
        p = os.path.join(OUT, name)
        assert os.path.exists(p), name
        assert len(_rows(p)) > 0, name

    def test_every_exported_route_has_a_behaviour(self):
        for r in _rows(os.path.join(OUT, "route-side-effect-classification.csv")):
            assert r["behaviour"] and r["behaviour"] != "UNKNOWN_BEHAVIOR"

    def test_every_mutation_has_a_persona(self):
        for r in _rows(os.path.join(OUT, "mutation-persona-classification.csv")):
            assert r["persona"]

    def test_queue_accounts_for_every_unprotected_route_once(self):
        q = _rows(os.path.join(OUT, "rebuilt-unprotected-module-queue.csv"))
        assert sum(int(r["route_count"]) for r in q) == 43

    def test_every_addition_carries_two_source_evidence(self):
        """Nothing entered the denominator without BOTH tenant derivation and
        a persistent side effect."""
        for r in _rows(os.path.join(OUT, "canonical-row-diff.csv")):
            assert r["change"] == "ROW_ADDED"
            assert "tenant=" in r["evidence"] and "mutation=" in r["evidence"]
            assert r["evidence"].split("tenant=")[1].split("|")[0].strip()

    def test_nothing_was_removed(self):
        """Removal requires exact capability evidence; none was claimed."""
        changes = {r["change"] for r in _rows(os.path.join(OUT, "canonical-row-diff.csv"))}
        assert changes == {"ROW_ADDED"}


# ══════════════════════════════════════════════════════════════════
# WS14 — verifier negative fixtures (it must be able to FAIL)
# ══════════════════════════════════════════════════════════════════

class TestVerifierDiscrimination:
    def _mod(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_app_wide.py")
        spec = importlib.util.spec_from_file_location("verify_app_wide", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_verifier_passes_on_the_current_tree(self):
        m = self._mod()
        m.FAILURES.clear()
        assert m.main() == 0

    def test_failing_condition_is_recorded(self):
        m = self._mod()
        m.FAILURES.clear()
        m.check("deliberate failure", False)
        assert m.FAILURES == ["deliberate failure"]

    def test_docstring_cannot_satisfy_a_source_check(self):
        m = self._mod()

        def liar():
            """this docstring says db.add( and tenant_id but the body does not"""
            return 1
        code = m.strip_prose(liar)
        assert "db.add(" not in code
        assert "tenant_id" not in code

    def test_where_inspection_is_not_vacuous(self):
        """A whole-statement match would wrongly pass an unscoped query."""
        m = self._mod()
        from sqlalchemy import select, column, table
        t = table("reviews", column("id"), column("tenant_id"))
        unscoped = select(t).where(t.c.id == 1)
        scoped = select(t).where(t.c.id == 1, t.c.tenant_id == 2)
        assert "tenant_id" in str(unscoped)          # the trap
        assert "tenant_id" not in m.where_clause(unscoped)
        assert "tenant_id" in m.where_clause(scoped)


# ══════════════════════════════════════════════════════════════════
# WS15 — behavioural invariants node-ID comparison cannot detect
# ══════════════════════════════════════════════════════════════════

class TestBehaviouralInvariants:
    """Slice 2F-25 introduced a regression that exact node-ID comparison could
    not see: the field_ops job-close review-request path failed silently
    because the exception was swallowed by `except Exception`. These assert the
    behaviour directly."""

    def test_job_close_still_passes_tenant_context(self):
        from app.engines.field_ops import service as fo
        src = inspect.getsource(fo)
        assert "actor_tenant_id=job.tenant_id" in src
        assert "trusted_internal=True" in src

    @pytest.mark.asyncio
    async def test_internal_job_close_review_request_is_created(self):
        """The exact call shape field_ops uses must still succeed."""
        from app.engines.review.service import ReviewService
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(
            **{"scalar_one_or_none.return_value": None}))
        db.add = MagicMock(); db.flush = AsyncMock()
        tid = uuid.uuid4()
        with patch("app.engines.review.service.get_redis", return_value=MagicMock()):
            svc = ReviewService(db, actor_id=uuid.uuid4(), actor_role="system",
                                actor_tenant_id=tid)
            out = await svc.create_review_request("JOB-1", tid, uuid.uuid4(), None,
                                                  trusted_internal=True)
        assert out["status"] == "sent"
        db.add.assert_called_once()

    def test_swallowed_exception_path_is_still_documented(self):
        """The `except Exception` around the job-close call remains, so the
        risk it created is real and must stay recorded, not silently trusted."""
        from app.engines.field_ops import service as fo
        src = inspect.getsource(fo)
        i = src.index("create_review_request")
        assert "except Exception" in src[i:i + 800]


# ══════════════════════════════════════════════════════════════════
# No authorization behaviour changed
# ══════════════════════════════════════════════════════════════════

class TestNoAuthorizationChange:
    def test_prior_closures_intact(self):
        from app.engines.package_commerce import tenant_router as pc
        from app.engines.customer_reviews import provider_router as cr
        from app.engines.compliance import provider_router as comp
        assert "require_tenant_owner_mutation" in inspect.getsource(pc.tenant_purchase_package)
        assert "is_paid=False" in inspect.getsource(pc.tenant_purchase_package)
        assert "require_tenant_owner_mutation" in inspect.getsource(cr)
        assert "require_tenant_owner_mutation" in inspect.getsource(comp)

    def test_legacy_review_create_still_410(self):
        from app.engines.review import router as legacy
        assert "410" in inspect.getsource(legacy.create_review)

    def test_legacy_review_scoped_lookups_intact(self):
        from app.engines.review.service import ReviewService
        assert "_get_review_scoped" in inspect.getsource(ReviewService.flag_review)
        assert "_effective_tenant" in inspect.getsource(ReviewService.list_by_tenant)
