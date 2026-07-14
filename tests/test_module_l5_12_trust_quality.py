"""MODULE-L5-12 — Trust & Quality recalculation + health scoring.

Locks in three defects found during the Level-5 sweep of the trust_quality engine:

  1. run_recalculation_job was a no-op. It inserted a job row, stamped it
     "completed" and returned — never enumerating a target, never calling any of
     the per-target engines. Every one of the 190 historical jobs read 0/0, so an
     admin clicking "Recalculate" got a green tick while nothing was recalculated.

  2. _calc_score scored the weighted sum straight out of 100 even though optional
     components whose metric is unavailable are skipped. Their weight stayed in
     the denominator, so a provider scoring perfectly on every metric the platform
     can actually measure was still capped at the total weight of those metrics.

  3. Renormalising naively then broke the other way: a provider whose only known
     metric was "documents verified" (one 10-point component) renormalised to
     100/100 and landed in the TOP band. Health bands gate commission, so a band
     awarded off a sliver of evidence is worse than no band at all.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.engines.trust_quality.service import TrustQualityService, _MIN_HEALTH_COVERAGE_PERCENT

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
ADMIN_PASS = "Password123!"

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
    # A full recalculation sweep can take a while when the box is also compiling
    # the two Next.js frontends, so give the client generous headroom.
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {token}"}, timeout=120) as c:
        yield c


class _Component:
    def __init__(self, metric_key, weight_percent, direction="positive",
                 is_required=False, min_value=0, max_value=100):
        self.metric_key = metric_key
        self.weight_percent = weight_percent
        self.direction = direction
        self.is_required = is_required
        self.min_value = min_value
        self.max_value = max_value


class _Formula:
    def __init__(self, base_score=100, min_score=0, max_score=100):
        self.base_score = base_score
        self.min_score = min_score
        self.max_score = max_score


class _Band:
    def __init__(self, band_key, min_score, max_score):
        self.band_key = band_key
        self.min_score = min_score
        self.max_score = max_score
        self.recommended_action = None


class _Penalty:
    def __init__(self, metric_key, operator, value_json, penalty_points=0,
                 hard_override_score=None):
        self.metric_key = metric_key
        self.operator = operator
        self.value_json = value_json
        self.penalty_points = penalty_points
        self.hard_override_score = hard_override_score


BANDS = [
    _Band("blocked", 0, 19.99),
    _Band("at_risk", 20, 39.99),
    _Band("watchlist", 40, 59.99),
    _Band("silver", 60, 74.99),
    _Band("gold", 75, 89.99),
    _Band("platinum", 90, 100),
]


def _calc(components, metrics, penalties=None):
    svc = TrustQualityService.__new__(TrustQualityService)
    return svc._calc_score(_Formula(), components, penalties or [], [], BANDS, metrics)


class TestHealthScoreRenormalisation:
    """Bug 2 + 3 — the score must reflect what is measurable, and must not band a
    target on a sliver of evidence."""

    def test_unmeasured_weight_does_not_drag_the_score_down(self):
        # Measurable: 60 of the formula's 100 weight, all perfect. The remaining
        # 40 points of weight have no metric behind them. The provider is flawless
        # on everything we can see, so it must not be dragged to 60/100.
        components = [
            _Component("job_completion_rate", 30),
            _Component("rating_score", 30),
            _Component("security_deposit_score", 20),   # unmeasurable
            _Component("package_credit_score", 20),      # unmeasurable
        ]
        d = _calc(components, {"job_completion_rate": 100, "rating_score": 100})

        assert d["score"] == 100.0
        assert d["band_key"] == "platinum"
        assert d["coverage_percent"] == 60.0
        assert d["insufficient_data"] is False

    def test_score_is_proportional_within_the_measured_weight(self):
        components = [
            _Component("job_completion_rate", 30),
            _Component("rating_score", 30),
            _Component("security_deposit_score", 40),  # unmeasurable
        ]
        # 100 and 40 across two equally-weighted components -> 70.
        d = _calc(components, {"job_completion_rate": 100, "rating_score": 40})

        assert d["score"] == 70.0
        assert d["band_key"] == "silver"

    def test_sliver_of_evidence_is_left_unbanded(self):
        # The exact live case: the only known fact about this provider is that its
        # documents are verified (one 10-point component). Renormalising that alone
        # yields 100 -- it must NOT be crowned platinum off 10% coverage.
        components = [
            _Component("document_verification_score", 10),
            _Component("job_completion_rate", 30),
            _Component("rating_score", 30),
            _Component("security_deposit_score", 30),
        ]
        d = _calc(components, {"document_verification_score": 100})

        assert d["coverage_percent"] == 10.0
        assert d["coverage_percent"] < _MIN_HEALTH_COVERAGE_PERCENT
        assert d["insufficient_data"] is True
        assert d["band_key"] is None, "a 10%-coverage target must not be banded"

    def test_hard_override_bands_regardless_of_coverage(self):
        # A suspended tenant is a declared verdict, not an inferred score, so it
        # bands even with zero measurable metrics.
        components = [_Component("job_completion_rate", 100)]
        penalties = [_Penalty("tenant_status", "equals", "suspended",
                              penalty_points=0, hard_override_score=0)]
        d = _calc(components, {"tenant_status": "suspended"}, penalties)

        assert d["score"] == 0.0
        assert d["band_key"] == "blocked"
        assert d["insufficient_data"] is False


class TestRecalculationJobIsReal:
    """Bug 1 — the job must actually enumerate and process targets."""

    async def test_job_processes_targets_and_reports_true_counts(self, client):
        r = await client.post("/v1/admin/trust-quality/recalculate/all",
                              json={"job_type": "health", "scope_type": "all"})
        assert r.status_code == 200, r.text
        job = r.json()["data"]

        assert job["job_type"] == "health"
        assert job["status"] in ("completed", "completed_with_errors")
        # The no-op version always reported 0/0. A real run touches real targets.
        assert job["total_count"] > 0, "recalculation job enumerated no targets"
        assert job["processed_count"] == job["total_count"] - job["failed_count"]
        assert job["failed_count"] == 0, job.get("error_summary")

    async def test_job_shows_up_in_the_jobs_list(self, client):
        await client.post("/v1/admin/trust-quality/recalculate/all",
                          json={"job_type": "badges", "scope_type": "all"})
        r = await client.get("/v1/admin/trust-quality/recalculation-jobs")
        assert r.status_code == 200
        d = r.json()["data"]
        jobs = d.get("items", d)
        assert any(j["job_type"] == "badges" and j["total_count"] > 0 for j in jobs)

    async def test_admin_can_configure_the_engine_end_to_end(self, client):
        """The admin must be able to CREATE config, not just toggle it — a badge,
        an award rule with criteria, and a health formula with components/bands,
        then activate the formula. (User feedback: the console could only
        enable/disable, not configure.)"""
        import random
        sfx = random.randint(10000, 99999)

        # 1. Create a badge definition.
        r = await client.post("/v1/admin/trust-quality/badges/definitions", json={
            "badge_key": f"l5cfg_badge_{sfx}", "name": "L5 Cfg Badge",
            "target_type": "tenant", "customer_visible": True, "status": "active"})
        assert r.status_code == 200, r.text
        badge_id = r.json()["data"]["id"]

        # 2. Create an auto-award rule that awards it, with a metric criterion.
        r = await client.post("/v1/admin/trust-quality/badge-rules", json={
            "rule_key": f"l5cfg_rule_{sfx}", "badge_id": badge_id, "target_type": "tenant",
            "rule_type": "auto_award", "auto_award": True, "status": "draft",
            "criteria": [{"metric_key": "average_rating", "operator": "greater_than_or_equal",
                          "value": 4.5, "is_required": True}]})
        assert r.status_code == 200, r.text
        rule = r.json()["data"]
        assert len(rule["criteria"]) == 1
        assert rule["status"] == "draft"

        # 3. Create a health formula with weighted components (=100) and 0-100 bands.
        r = await client.post("/v1/admin/trust-quality/health-rules", json={
            "formula_key": f"l5cfg_formula_{sfx}", "name": "L5 Cfg Formula",
            "target_type": "tenant_provider", "base_score": 100, "min_score": 0, "max_score": 100,
            "status": "draft",
            "components": [
                {"metric_key": "job_completion_rate", "weight_percent": 60, "direction": "positive",
                 "min_value": 0, "max_value": 100},
                {"metric_key": "average_rating", "weight_percent": 40, "direction": "positive",
                 "min_value": 0, "max_value": 5}],
            "bands": [
                {"band_key": "blocked", "band_name": "Blocked", "min_score": 0, "max_score": 49},
                {"band_key": "healthy", "band_name": "Healthy", "min_score": 50, "max_score": 100}]})
        assert r.status_code == 200, r.text
        formula = r.json()["data"]
        formula_id = formula["id"]
        assert len(formula["components"]) == 2

        # 4. The configured draft can be activated (weights total 100, bands cover 0-100).
        r = await client.post(f"/v1/admin/trust-quality/health-rules/{formula_id}/activate",
                              json={"reason": "L5 config lifecycle test"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "active"

        # Leave nothing active behind: a live test formula would join real scoring.
        await client.post(f"/v1/admin/trust-quality/health-rules/{formula_id}/deactivate",
                          json={"reason": "cleanup"})

    async def test_admin_can_edit_existing_config(self, client):
        """The admin must be able to EDIT config in place — badge presentation,
        a rule's criteria, and a formula's components — not just create/toggle.
        (User feedback: no edit button existed.)"""
        import random
        sfx = random.randint(10000, 99999)

        # Badge: edit name + icon + color.
        r = await client.post("/v1/admin/trust-quality/badges/definitions", json={
            "badge_key": f"l5ed_badge_{sfx}", "name": "Before", "target_type": "tenant",
            "icon": "star", "color": "#3b82f6", "status": "active"})
        badge_id = r.json()["data"]["id"]
        r = await client.put(f"/v1/admin/trust-quality/badges/definitions/{badge_id}",
                            json={"name": "After", "icon": "crown", "color": "#8b5cf6"})
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert (d["name"], d["icon"], d["color"]) == ("After", "crown", "#8b5cf6")

        # Rule: replace criteria (1 -> 2) and flip auto_award.
        r = await client.post("/v1/admin/trust-quality/badge-rules", json={
            "rule_key": f"l5ed_rule_{sfx}", "badge_id": badge_id, "target_type": "tenant",
            "rule_type": "auto_award", "status": "draft",
            "criteria": [{"metric_key": "average_rating", "operator": "greater_than_or_equal",
                          "value": 4.0, "is_required": True}]})
        rule_id = r.json()["data"]["id"]
        r = await client.put(f"/v1/admin/trust-quality/badge-rules/{rule_id}", json={
            "auto_award": False,
            "criteria": [
                {"metric_key": "completed_jobs_count", "operator": "greater_than_or_equal",
                 "value": 50, "is_required": True},
                {"metric_key": "average_rating", "operator": "greater_than_or_equal",
                 "value": 4.7, "is_required": True}]})
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["auto_award"] is False
        assert len(d["criteria"]) == 2

        # Formula: replace components (1 -> 2).
        r = await client.post("/v1/admin/trust-quality/health-rules", json={
            "formula_key": f"l5ed_formula_{sfx}", "name": "F", "target_type": "tenant_provider",
            "status": "draft",
            "components": [{"metric_key": "job_completion_rate", "weight_percent": 100,
                            "direction": "positive", "min_value": 0, "max_value": 100}],
            "bands": [{"band_key": "h", "band_name": "H", "min_score": 0, "max_score": 100}]})
        formula_id = r.json()["data"]["id"]
        r = await client.put(f"/v1/admin/trust-quality/health-rules/{formula_id}", json={
            "name": "F2",
            "components": [
                {"metric_key": "job_completion_rate", "weight_percent": 50, "direction": "positive",
                 "min_value": 0, "max_value": 100},
                {"metric_key": "average_rating", "weight_percent": 50, "direction": "positive",
                 "min_value": 0, "max_value": 5}]})
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["name"] == "F2"
        assert len(d["components"]) == 2

    async def test_editing_active_formula_to_bad_weights_is_rejected_and_rolled_back(self, client):
        """An edit cannot leave a LIVE formula invalid: setting an active formula's
        weights to 60% must 422, and the formula must stay active at 100%."""
        import random
        sfx = random.randint(10000, 99999)
        r = await client.post("/v1/admin/trust-quality/health-rules", json={
            "formula_key": f"l5edg_{sfx}", "name": "G", "target_type": "tenant_provider",
            "status": "draft",
            "components": [{"metric_key": "job_completion_rate", "weight_percent": 100,
                            "direction": "positive", "min_value": 0, "max_value": 100}],
            "bands": [{"band_key": "h", "band_name": "H", "min_score": 0, "max_score": 100}]})
        fid = r.json()["data"]["id"]
        await client.post(f"/v1/admin/trust-quality/health-rules/{fid}/activate",
                          json={"reason": "guard test"})

        bad = await client.put(f"/v1/admin/trust-quality/health-rules/{fid}", json={
            "components": [{"metric_key": "job_completion_rate", "weight_percent": 60,
                            "direction": "positive", "min_value": 0, "max_value": 100}]})
        assert bad.status_code == 422

        # Rolled back: still active, still one 100% component.
        r = await client.get(f"/v1/admin/trust-quality/health-rules/{fid}")
        d = r.json()["data"]
        assert d["status"] == "active"
        assert sum(float(c["weight_percent"]) for c in d["components"]) == 100.0
        await client.post(f"/v1/admin/trust-quality/health-rules/{fid}/deactivate",
                          json={"reason": "cleanup"})

    async def test_health_formula_rejects_bad_weights_on_activation(self, client):
        """Weights that don't total 100 must be refused at activation — the config
        UI shows the running total for exactly this reason."""
        import random
        sfx = random.randint(10000, 99999)
        r = await client.post("/v1/admin/trust-quality/health-rules", json={
            "formula_key": f"l5bad_{sfx}", "name": "L5 Bad Weights",
            "target_type": "tenant_provider", "status": "draft",
            "components": [{"metric_key": "job_completion_rate", "weight_percent": 60,
                            "direction": "positive", "min_value": 0, "max_value": 100}],
            "bands": [{"band_key": "healthy", "band_name": "Healthy",
                       "min_score": 0, "max_score": 100}]})
        assert r.status_code == 200, r.text
        fid = r.json()["data"]["id"]
        bad = await client.post(f"/v1/admin/trust-quality/health-rules/{fid}/activate",
                               json={"reason": "should fail"})
        assert bad.status_code == 422, "60% weight total must be rejected"

    async def test_earned_badges_surface_to_all_audiences(self, client):
        """A configured badge, once awarded, must be readable by admin, provider
        and public surfaces — with its icon/colour — not just live in the admin
        config. (User: 'do these icons show on tenant/staff/customer/admin side?')
        Also proves the read layer dedupes and applies visibility."""
        import random, httpx
        sfx = random.randint(10000, 99999)

        # A customer-visible badge with an icon + colour.
        r = await client.post("/v1/admin/trust-quality/badges/definitions", json={
            "badge_key": f"l5surf_{sfx}", "name": "Surfacing Badge", "target_type": "tenant",
            "icon": "crown", "color": "#8b5cf6", "customer_visible": True, "status": "active"})
        badge_id = r.json()["data"]["id"]

        # Pick a real tenant to award it to.
        r = await client.get("/v1/admin/tenants?page=1&page_size=1")
        items = r.json()["data"]["items"]
        assert items, "need a tenant to award to"
        tenant_id = items[0]["tenant_id"]

        await client.post("/v1/admin/trust-quality/badges/manual-award", json={
            "badge_id": badge_id, "target_type": "tenant", "target_id": tenant_id,
            "reason": "L5 surfacing test"})
        # Award the same badge twice — the read layer must still report it once.
        await client.post("/v1/admin/trust-quality/badges/manual-award", json={
            "badge_id": badge_id, "target_type": "tenant", "target_id": tenant_id,
            "reason": "L5 dup"})

        def _find(items):
            return [b for b in items if b["badge_key"] == f"l5surf_{sfx}"]

        # 1. Admin per-target view.
        r = await client.get(
            f"/v1/admin/trust-quality/badges/earned?target_type=tenant&target_id={tenant_id}")
        mine = _find(r.json()["data"]["items"])
        assert len(mine) == 1, "read layer must dedupe repeated assignments"
        assert mine[0]["icon"] == "crown" and mine[0]["color"] == "#8b5cf6"

        # 2. Public (customer) view — same badge, customer-visible.
        async with httpx.AsyncClient(base_url=BASE, timeout=30) as anon:
            r = await anon.get(f"/v1/public/trust-quality/providers/{tenant_id}/badges")
        pub = _find(r.json()["data"]["items"])
        assert len(pub) == 1 and pub[0]["icon"] == "crown"

    async def test_internal_badge_hidden_from_customers(self, client):
        """A non-customer-visible badge must appear to the admin but never to the
        public/customer audience — visibility gating is enforced in the read
        layer, not just the UI."""
        import random, httpx
        sfx = random.randint(10000, 99999)
        r = await client.post("/v1/admin/trust-quality/badges/definitions", json={
            "badge_key": f"l5int_{sfx}", "name": "Internal Only", "target_type": "tenant",
            "icon": "shield", "color": "#64748b", "customer_visible": False, "status": "active"})
        badge_id = r.json()["data"]["id"]
        r = await client.get("/v1/admin/tenants?page=1&page_size=1")
        tenant_id = r.json()["data"]["items"][0]["tenant_id"]
        await client.post("/v1/admin/trust-quality/badges/manual-award", json={
            "badge_id": badge_id, "target_type": "tenant", "target_id": tenant_id,
            "reason": "internal test"})

        r = await client.get(
            f"/v1/admin/trust-quality/badges/earned?target_type=tenant&target_id={tenant_id}")
        assert any(b["badge_key"] == f"l5int_{sfx}" for b in r.json()["data"]["items"])

        async with httpx.AsyncClient(base_url=BASE, timeout=30) as anon:
            r = await anon.get(f"/v1/public/trust-quality/providers/{tenant_id}/badges")
        assert not any(b["badge_key"] == f"l5int_{sfx}" for b in r.json()["data"]["items"]), \
            "internal badge must never surface to customers"

    async def test_rule_toggle_requires_a_reason(self, client):
        r = await client.get("/v1/admin/trust-quality/badge-rules")
        d = r.json()["data"]
        rule = (d.get("items", d))[0]

        # The admin UI must collect a reason -- an empty body is refused, and that
        # is why the console prompts for one before it calls.
        bad = await client.post(
            f"/v1/admin/trust-quality/badge-rules/{rule['id']}/deactivate", json={})
        assert bad.status_code == 422

        good = await client.post(
            f"/v1/admin/trust-quality/badge-rules/{rule['id']}/deactivate",
            json={"reason": "L5 test"})
        assert good.status_code == 200

        await client.post(
            f"/v1/admin/trust-quality/badge-rules/{rule['id']}/activate",
            json={"reason": "L5 test restore"})
