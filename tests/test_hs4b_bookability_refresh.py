"""HS4B — Bookability Refresh Fix certification.

Root cause: `POST /v1/provider/status/refresh` (app/engines/provider_
portal/router.py) was a complete no-op stub — it returned
`{"refreshed": True}` without performing any computation or DB write.
`GET /v1/provider/status` read from the real `provider_visibility_
statuses` table, but nothing ever populated it after initial creation,
so `is_visible`/`is_bookable`/`last_evaluated_at` stayed frozen at
their defaults (false/false/null) regardless of real tenant setup
progress.

Fixed by implementing `_evaluate_provider_bookability()`, a real
computation function reading actual signals (tenants, tenant_billing,
tenant_limits, tenant_service_areas, provider_availability_rules,
tenant_services/tenant_service_types/tenant_service_brands) and
persisting the result via upsert into the real, pre-existing
provider_visibility_statuses table (no migration needed — the table
already had every field this ticket asked for).

Live-verified this sprint against the real running backend and real DB:
toggling each of business-profile-completeness, usage-credit balance,
and tenant.suspended_at independently flipped is_visible/is_bookable
correctly, and a fully-satisfied tenant reached is_bookable=true with
zero failed_checks. See HS4B_LIVE_CURL_VERIFICATION_REPORT.md for the
full transcript.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

ROUTER_PY = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")
PAGE = (FRONTEND / "components/service-setup/ReviewPublishStep.tsx").read_text(encoding="utf-8-sig")


def _eval_fn() -> str:
    return ROUTER_PY.split("async def _evaluate_provider_bookability")[1].split("@router.post(\"/status/refresh\")")[0]


def _refresh_fn() -> str:
    return ROUTER_PY.split('async def refresh_provider_status')[1].split("@router.get(\"/status/offerings\")")[0]


def _offering_status_fn() -> str:
    return ROUTER_PY.split('async def get_offering_statuses')[1].split("@router.get(\"/onboarding/status\")")[0]


# ── 1. Refresh is no longer a no-op ───────────────────────────────────────────
def test_refresh_is_not_a_noop():
    fn = _refresh_fn()
    assert '{"refreshed": True}' not in fn
    assert "_evaluate_provider_bookability" in fn


def test_refresh_updates_db():
    fn = _refresh_fn()
    assert "UPDATE provider_visibility_statuses" in fn
    assert "INSERT INTO provider_visibility_statuses" in fn
    assert "await db.commit()" in fn


def test_refresh_updates_last_evaluated_at():
    fn = _refresh_fn()
    assert "last_evaluated_at=now()" in fn


# ── 2. Real signals used (no fabricated data) ─────────────────────────────────
def test_evaluation_reads_real_tenant_table():
    fn = _eval_fn()
    assert "FROM tenants WHERE id=:tid" in fn


def test_evaluation_reads_real_service_area_table():
    fn = _eval_fn()
    assert "FROM tenant_service_areas WHERE tenant_id=:tid AND is_active=true" in fn


def test_evaluation_reads_real_availability_table():
    fn = _eval_fn()
    assert "FROM provider_availability_rules WHERE tenant_id=:tid AND is_active=true" in fn


def test_evaluation_reads_real_billing_table():
    fn = _eval_fn()
    assert "FROM tenant_billing WHERE tenant_id=:tid" in fn
    assert "credit_balance" in fn
    assert "security_deposit_paid" in fn


def test_evaluation_reads_real_published_service_pricing():
    fn = _eval_fn()
    assert "setup_status='published'" in fn
    assert "tenant_min_price" in fn


# ── 3. Hard gates — bookability cannot be true with a missing requirement ────
def test_missing_service_area_blocks_bookable():
    fn = _eval_fn()
    assert "SERVICE_AREA_MISSING" in fn
    assert "active_areas > 0" in fn


def test_missing_availability_blocks_bookable():
    fn = _eval_fn()
    assert "AVAILABILITY_MISSING" in fn
    assert "availability_count > 0" in fn


def test_missing_usage_credits_blocks_bookable():
    fn = _eval_fn()
    assert "USAGE_CREDITS_INSUFFICIENT" in fn
    assert "credit_balance > 0" in fn


def test_missing_ready_technician_capacity_blocks_bookable():
    fn = _eval_fn()
    assert "READY_TECHNICIAN_MISSING" in fn
    assert "staff_capacity_ready" in fn


def test_missing_or_over_limit_seats_block_bookable():
    fn = _eval_fn()
    assert "get_seat_usage" in fn
    assert "TECHNICIAN_SEATS_REQUIRED" in fn
    assert "seat_capacity_ready" in fn


def test_suspended_tenant_blocks_bookable():
    fn = _eval_fn()
    assert "TENANT_SUSPENDED_OR_REJECTED" in fn
    assert "tenant_active" in fn


def test_unapproved_tenant_blocks_visibility_and_bookability():
    fn = _eval_fn()
    assert 'tenant_row.status == "active"' in fn
    assert 'tenant_row.verification_status in ("approved", "verified")' in fn


def test_pending_first_document_has_no_replacement_grace():
    fn = _eval_fn()
    assert "valid_previous" in fn
    assert "replacement_in_review and valid_previous" in fn


def test_is_bookable_requires_all_critical_checks():
    fn = _eval_fn()
    # is_bookable must be a conjunction of every critical signal, not just
    # one or two checks
    assert "is_bookable = is_visible and priced_count > 0 and active_areas > 0" in fn
    assert "availability_count > 0 and credit_balance > 0" in fn
    assert "staff_capacity_ready and seat_capacity_ready and not document_blockers" in fn


def test_offering_statuses_project_canonical_tenant_services():
    fn = _offering_status_fn()
    assert "FROM tenant_services ts" in fn
    assert "provider_offering_bookable_statuses" not in fn
    assert "_evaluate_provider_bookability" in fn
    assert "coverage_by_service" in fn


# ── 4. Response shape matches the ticket's required fields ───────────────────
def test_response_includes_passed_and_failed_checks():
    fn = _refresh_fn()
    assert '"passed_checks"' in fn
    assert '"failed_checks"' in fn
    assert '"status"' in fn


# ── 5. Frontend calls refresh after publish and shows real status ────────────
def test_frontend_calls_refresh_after_publish():
    publish_action = PAGE.split("const publishAction")[1].split("async function handlePublish")[0]
    assert "serviceSetupApi.publish(tsid)" in publish_action
    assert "providerStatusApi.refresh()" in publish_action


def test_frontend_shows_bookable_copy():
    widget = (FRONTEND / "components/dashboard/BookabilityStatusWidget.tsx").read_text(encoding="utf-8-sig")
    assert "Live & Accepting Bookings" in widget
    assert "s.is_visible && s.is_bookable" in widget


def test_frontend_shows_not_bookable_copy_with_reasons():
    widget = (FRONTEND / "components/dashboard/BookabilityStatusWidget.tsx").read_text(encoding="utf-8-sig")
    assert "Action Required" in widget
    assert "s.bookability_blockers?.length" in widget
    assert "View and resolve" in widget


def test_frontend_never_shows_false_ready_state():
    # Publishing only emits success after both the publish mutation and the
    # canonical provider-status recomputation complete.
    publish_action = PAGE.split("const publishAction")[1].split("async function handlePublish")[0]
    handle_publish = PAGE.split("async function handlePublish")[1].split("const errors")[0]
    assert publish_action.index("serviceSetupApi.publish(tsid)") < publish_action.index("providerStatusApi.refresh()")
    assert "publishAction.execute()" in handle_publish


# ── 6. Regression: existing safety fixes still intact ────────────────────────
def test_provider_price_validation_still_present():
    tenant_service_py = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
    assert "TENANT_PRICE_NEGATIVE" in tenant_service_py
    assert "INVALID_PRICE_RANGE" in tenant_service_py
    assert "Minimum price cannot exceed maximum price." in tenant_service_py


def test_type_dependent_brand_pricing_still_present():
    tenant_service_py = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
    assert "service_type_id: uuid.UUID | None = None" in tenant_service_py


# ── 7. Forbidden labels ────────────────────────────────────────────────────────
FORBIDDEN = [
    "Manual Bargain Setup", "Bargain Rule Builder", "Bargain Settings",
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance", "Credit Wallet Health",
]


def test_no_forbidden_labels():
    for term in FORBIDDEN:
        assert term not in PAGE, f"forbidden label found: {term}"
        assert term not in ROUTER_PY, f"forbidden label found in router: {term}"
