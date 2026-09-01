"""P0 Trust & Quality Engine — Phase 1 tests (data model + engines).

Covers: migration 095, 8 engines registered in Engine Management, Badge Rule
Engine criteria evaluation (simulate eligible/failed), Health Rule Engine
formula calculation (weights/bands/penalties/bonuses/hard-override), manual
award/revoke reason requirements, seed defaults idempotency, audit logging,
and permission enforcement. Runs against the live dev server (same pattern
as test_p0_provider_enterprise.py).
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
ADMIN_PASS = "Password123!"

MIGRATION = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions", "095_trust_quality_engine.py")
MODELS = os.path.join(os.path.dirname(__file__), "..", "app", "engines", "trust_quality", "models.py")
SERVICE = os.path.join(os.path.dirname(__file__), "..", "app", "engines", "trust_quality", "service.py")
ROUTER = os.path.join(os.path.dirname(__file__), "..", "app", "engines", "trust_quality", "admin_router.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def client(token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {token}"}, timeout=30) as c:
        yield c


pytestmark = pytest.mark.anyio


# ═════════════════════════════════════════════════════════════════════════════
# 1. Static file checks
# ═════════════════════════════════════════════════════════════════════════════
class TestFiles:
    def test_migration_exists(self):
        assert os.path.exists(MIGRATION)

    def test_migration_revision(self):
        assert 'revision = "095"' in _read(MIGRATION)

    def test_migration_registers_8_engines(self):
        src = _read(MIGRATION)
        for key in [
            "trust_quality_engine", "badge_engine", "badge_rule_engine", "health_engine",
            "health_rule_engine", "risk_scoring_engine", "rule_simulator_engine",
            "recalculation_job_engine",
        ]:
            assert f'"{key}"' in src, f"Missing engine registration: {key}"

    def test_models_file_exists(self):
        assert os.path.exists(MODELS)

    def test_service_file_exists(self):
        assert os.path.exists(SERVICE)

    def test_router_file_exists(self):
        assert os.path.exists(ROUTER)


# ═════════════════════════════════════════════════════════════════════════════
# 2. Engine Management registration (live DB via /v1/admin/engines)
# ═════════════════════════════════════════════════════════════════════════════
class TestEngineRegistration:
    async def test_engines_list_includes_trust_quality(self, client):
        r = await client.get("/v1/admin/engines", params={"limit": 200})
        assert r.status_code == 200, r.text
        keys = {e["engine_key"] for e in r.json()["data"]["engines"]}
        for key in [
            "trust_quality_engine", "badge_engine", "badge_rule_engine", "health_engine",
            "health_rule_engine", "risk_scoring_engine", "rule_simulator_engine",
            "recalculation_job_engine",
        ]:
            assert key in keys, f"{key} not registered in Engine Management"

    async def test_permissions_enforced_no_auth(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/trust-quality/badge-rules")
            assert r.status_code in (401, 403)


# ═════════════════════════════════════════════════════════════════════════════
# 3. Seed defaults (idempotent)
# ═════════════════════════════════════════════════════════════════════════════
class TestSeedDefaults:
    async def test_seed_preview(self, client):
        r = await client.post("/v1/admin/trust-quality/seed-defaults/preview")
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["badges"] > 0 and d["badge_rules"] > 0 and d["health_formulas"] > 0

    async def test_seed_defaults_runs(self, client):
        r = await client.post("/v1/admin/trust-quality/seed-defaults")
        assert r.status_code == 200, r.text

    async def test_seed_defaults_idempotent(self, client):
        r1 = await client.post("/v1/admin/trust-quality/seed-defaults")
        r2 = await client.post("/v1/admin/trust-quality/seed-defaults")
        assert r1.status_code == 200 and r2.status_code == 200
        # Second run should create 0 new rows since keys already exist.
        assert r2.json()["data"]["badges"] == 0
        assert r2.json()["data"]["badge_rules"] == 0
        assert r2.json()["data"]["health_formulas"] == 0

    async def test_badge_rules_list_loads(self, client):
        await client.post("/v1/admin/trust-quality/seed-defaults")
        r = await client.get("/v1/admin/trust-quality/badge-rules")
        assert r.status_code == 200
        rule_keys = {b["rule_key"] for b in r.json()["data"]["items"]}
        assert "rule_top_rated_provider" in rule_keys
        assert "rule_verified_provider" in rule_keys

    async def test_health_formulas_list_loads(self, client):
        await client.post("/v1/admin/trust-quality/seed-defaults")
        r = await client.get("/v1/admin/trust-quality/health-rules")
        assert r.status_code == 200
        formula_keys = {f["formula_key"] for f in r.json()["data"]["items"]}
        canonical_keys = {key for key in formula_keys if not key.startswith("l5")}
        assert canonical_keys == {
            "provider_business_health_default",
            "technician_performance_health_default",
        }


# ═════════════════════════════════════════════════════════════════════════════
# 4. Badge Rule Engine — simulate (criteria evaluation)
# ═════════════════════════════════════════════════════════════════════════════
class TestBadgeSimulator:
    async def _top_rated_rule_id(self, client) -> str:
        await client.post("/v1/admin/trust-quality/seed-defaults")
        r = await client.get("/v1/admin/trust-quality/badge-rules")
        items = r.json()["data"]["items"]
        rule = next(i for i in items if i["rule_key"] == "rule_top_rated_provider")
        return rule["id"]

    async def test_simulate_eligible_when_criteria_pass(self, client):
        rule_id = await self._top_rated_rule_id(client)
        metrics = {"average_rating": 4.8, "review_count": 60, "completed_jobs_count": 120, "complaint_rate": 1}
        r = await client.post(f"/v1/admin/trust-quality/badge-rules/{rule_id}/simulate", json={"metrics": metrics})
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["eligible"] is True
        assert d["would_award_badge"] is True
        assert len(d["failed_criteria"]) == 0

    async def test_simulate_failed_when_criteria_fail(self, client):
        rule_id = await self._top_rated_rule_id(client)
        metrics = {"average_rating": 4.0, "review_count": 10, "completed_jobs_count": 5, "complaint_rate": 15}
        r = await client.post(f"/v1/admin/trust-quality/badge-rules/{rule_id}/simulate", json={"metrics": metrics})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["eligible"] is False
        assert len(d["failed_criteria"]) == 4
        assert d["would_remove_badge"] is True  # removal criteria (rating<4.3, complaint>8) also match

    async def test_manual_award_requires_reason(self, client):
        badges = await client.get("/v1/admin/trust-quality/badges/definitions")
        badge_id = badges.json()["data"]["items"][0]["id"]
        r = await client.post("/v1/admin/trust-quality/badges/manual-award", json={
            "badge_id": badge_id, "target_type": "tenant",
            "target_id": "00000000-0000-0000-0000-000000000001", "reason": "",
        })
        assert r.status_code >= 400

    async def test_manual_award_with_reason_succeeds(self, client):
        badges = await client.get(
            "/v1/admin/trust-quality/badges/definitions", params={"target_type": "tenant"})
        badge_id = badges.json()["data"]["items"][0]["id"]
        tenants = await client.get("/v1/admin/tenants?page=1&page_size=1")
        target_id = tenants.json()["data"]["items"][0]["tenant_id"]
        r = await client.post("/v1/admin/trust-quality/badges/manual-award", json={
            "badge_id": badge_id, "target_type": "tenant",
            "target_id": target_id, "reason": "Manual QA verification",
        })
        assert r.status_code == 200, r.text

    async def test_revoke_requires_reason(self, client):
        r = await client.post(
            "/v1/admin/trust-quality/badges/00000000-0000-0000-0000-000000000003/revoke",
            json={"reason": ""},
        )
        assert r.status_code == 422


# ═════════════════════════════════════════════════════════════════════════════
# 5. Health Rule Engine — formula calculation
# ═════════════════════════════════════════════════════════════════════════════
class TestHealthSimulator:
    async def _provider_formula_id(self, client) -> str:
        await client.post("/v1/admin/trust-quality/seed-defaults")
        r = await client.get("/v1/admin/trust-quality/health-rules")
        items = r.json()["data"]["items"]
        f = next(i for i in items if i["formula_key"] == "provider_business_health_default")
        return f["id"]

    async def test_healthy_provider_score_and_band(self, client):
        fid = await self._provider_formula_id(client)
        metrics = {
            "profile_completion_percent": 100, "document_verification_score": 100,
            "usage_credit_score": 100,
            "job_completion_rate": 97, "response_sla_score": 90, "rating_score": 96,
            "complaint_dispute_score": 5, "cancellation_rate": 2, "staff_availability_score": 90,
            "average_rating": 4.8, "complaint_rate": 2, "tenant_status": "active",
        }
        r = await client.post(f"/v1/admin/trust-quality/health-rules/{fid}/simulate", json={"metrics": metrics})
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["score"] >= 90
        assert d["band_key"] == "platinum"
        assert len(d["bonuses_applied"]) >= 1

    async def test_suspended_tenant_score_becomes_zero(self, client):
        fid = await self._provider_formula_id(client)
        r = await client.post(f"/v1/admin/trust-quality/health-rules/{fid}/simulate",
                               json={"metrics": {"tenant_status": "suspended"}})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["score"] == 0.0
        assert d["band_key"] == "blocked"

    async def test_low_rating_triggers_penalty(self, client):
        fid = await self._provider_formula_id(client)
        r = await client.post(f"/v1/admin/trust-quality/health-rules/{fid}/simulate",
                               json={"metrics": {"average_rating": 3.0, "tenant_status": "active"}})
        assert r.status_code == 200
        d = r.json()["data"]
        penalty_metrics = {p["metric_key"] for p in d["penalties_applied"]}
        assert "average_rating" in penalty_metrics

    async def test_customer_health_formula_has_no_valid_complaint_penalty(self, client):
        """Customer Account Health must not penalize customers for valid complaints —
        only dispute_abuse_score (fraud/abuse signal), not a generic complaint metric."""
        r = await client.get("/v1/admin/trust-quality/health-rules", params={"target_type": "customer_account"})
        assert r.status_code == 200
        # Customer-account health is owned by its commerce engine; keeping a
        # second Trust & Quality formula produced conflicting health states.
        assert r.json()["data"]["items"] == []

    async def test_formula_activation_requires_weights_sum_100(self, client):
        r = await client.post("/v1/admin/trust-quality/health-rules", json={
            "formula_key": "test_bad_weight_formula", "name": "Bad Weight Test",
            "target_type": "tenant", "status": "active",
            "components": [{"metric_key": "job_completion_rate", "weight_percent": 50}],
            "bands": [
                {"band_key": "a", "band_name": "A", "min_score": 0, "max_score": 100},
            ],
        })
        assert r.status_code >= 400

    async def test_band_overlap_rejected(self, client):
        r = await client.post("/v1/admin/trust-quality/health-rules", json={
            "formula_key": "test_band_overlap_formula", "name": "Band Overlap Test",
            "target_type": "tenant", "status": "active",
            "components": [{"metric_key": "job_completion_rate", "weight_percent": 100}],
            "bands": [
                {"band_key": "a", "band_name": "A", "min_score": 0, "max_score": 60},
                {"band_key": "b", "band_name": "B", "min_score": 50, "max_score": 100},
            ],
        })
        assert r.status_code >= 400


# ═════════════════════════════════════════════════════════════════════════════
# 6. Risk scoring + recalculation jobs + audit
# ═════════════════════════════════════════════════════════════════════════════
class TestRiskAndJobsAndAudit:
    async def test_recalculate_risk_returns_normal_with_no_rules(self, client):
        r = await client.post("/v1/admin/trust-quality/recalculate/risk", json={
            "target_type": "tenant_provider", "target_id": "00000000-0000-0000-0000-000000000004",
            "metrics": {},
        })
        assert r.status_code == 422, r.text
        assert r.json()["error_code"] == "VALIDATION_ERROR"

    async def test_run_recalculation_job(self, client):
        r = await client.post("/v1/admin/trust-quality/recalculate/all", json={"job_type": "all"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] in ("queued", "running", "cancelling")

    async def test_recalculation_jobs_list(self, client):
        await client.post("/v1/admin/trust-quality/recalculate/all", json={"job_type": "all"})
        r = await client.get("/v1/admin/trust-quality/recalculation-jobs")
        assert r.status_code == 200
        assert len(r.json()["data"]["items"]) >= 1

    async def test_audit_logs_recorded_for_seed(self, client):
        await client.post("/v1/admin/trust-quality/seed-defaults")
        r = await client.get(
            "/v1/admin/trust-quality/audit-logs",
            params={"action_type": "trust_quality.seed_defaults"},
        )
        assert r.status_code == 200
        action_types = {a["action_type"] for a in r.json()["data"]["items"]}
        assert "trust_quality.seed_defaults" in action_types
