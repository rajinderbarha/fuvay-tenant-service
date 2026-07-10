"""
P0 Enterprise Customer Users Management Upgrade — test suite
Static source-inspection style, consistent with test_p0_security_enterprise.py /
test_p0_finance_enterprise.py conventions in this repo — no live DB fixture required.
"""
import os

ROOT             = os.path.dirname(os.path.dirname(__file__))
ROUTER           = os.path.join(ROOT, "app", "engines", "auth", "admin_customers_router.py")
SERVICE          = os.path.join(ROOT, "app", "engines", "auth", "admin_customers_service.py")
PERMISSIONS_FILE = os.path.join(ROOT, "app", "core", "permissions.py")
FILTER_REGISTRY  = os.path.join(ROOT, "app", "engines", "enterprise_grid", "filter_registry.py")
COMPLIANCE_SVC   = os.path.join(ROOT, "app", "engines", "compliance", "enterprise_service.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Regression guard: the actual P0 outage bugs ─────────────────────────────

def test_router_has_no_bookings_deleted_at_references():
    """bookings has no deleted_at column — this exact bug caused the live 500 outage."""
    src = _read(ROUTER)
    assert "b2.deleted_at" not in src
    assert "b.deleted_at" not in src
    assert "bfilt.deleted_at" not in src


def test_router_has_no_tenants_deleted_at_references():
    """tenants has no deleted_at column either — second bug found during the live fix."""
    src = _read(ROUTER)
    assert "t.deleted_at" not in src


def test_router_count_sql_has_no_double_select():
    """count_sql wrapped _SELECT_COLS (which already starts with SELECT) in another SELECT."""
    src = _read(ROUTER)
    assert "SELECT u.id FROM (SELECT" not in src
    assert "SELECT sq.id FROM" in src


def test_router_uuid_casts_have_space_before_cast():
    """SQLAlchemy's text() bind-param parser mis-tokenizes `:param::type` (no space) with
    asyncpg — third bug found live. Every `:name::type` must have a space before `::`."""
    src = _read(ROUTER)
    import re
    assert not re.search(r":\w+::", src), "found a `:param::type` cast with no space — will 500"


def test_router_reviews_uses_overall_rating_not_rating():
    """customer_reviews has no `rating` column — it's `overall_rating`. Fourth bug found live."""
    src = _read(ROUTER)
    assert "cr2.rating" not in src
    assert "cr2.overall_rating" in src


def test_router_health_band_filter_uses_outer_alias_not_inner_columns():
    """hb_cond used to re-evaluate _HEALTH_BAND_EXPR (referencing bk./cc./u. from the inner
    subquery) in the OUTER query where only `sq.*` columns are visible — fifth bug found
    live, broke both /?health_band= and /export?health_band=. Must filter on sq.health_band."""
    src = _read(ROUTER)
    assert 'hb_cond = "AND sq.health_band = :health_band"' in src


# ── admin_customers_service.py ───────────────────────────────────────────────

def test_service_importable():
    import importlib
    mod = importlib.import_module("app.engines.auth.admin_customers_service")
    assert hasattr(mod, "CustomerAdminService")


def test_service_composes_existing_engines_not_new_tables():
    src = _read(SERVICE)
    assert "from app.engines.complaints.complaint_service import ComplaintService" in src
    assert "from app.engines.customer_credits.service import CustomerCreditService" in src
    assert "from app.engines.compliance.enterprise_service import ComplianceEnterpriseService" in src
    assert "from app.engines.security.admin_service import SecurityAdminService" in src
    assert "from app.engines.auth.service import AuthService" in src
    assert "from app.engines.serviceability.models import CustomerAddress" in src


def test_service_has_complaints_methods():
    src = _read(SERVICE)
    assert "async def list_complaints" in src


def test_service_has_service_credit_methods():
    src = _read(SERVICE)
    assert "async def list_service_credits" in src
    assert "async def issue_service_credit" in src


def test_service_has_address_methods():
    src = _read(SERVICE)
    assert "async def list_addresses" in src


def test_service_has_session_methods():
    src = _read(SERVICE)
    assert "async def list_sessions" in src
    assert "async def list_login_history" in src
    assert "async def revoke_all_sessions" in src


def test_service_has_privacy_methods():
    src = _read(SERVICE)
    assert "async def list_privacy_requests" in src


def test_service_has_audit_methods():
    src = _read(SERVICE)
    assert "async def list_audit_logs" in src


def test_service_has_account_action_methods():
    src = _read(SERVICE)
    for m in ("block_customer", "unblock_customer", "suspend_customer", "reactivate_customer"):
        assert f"async def {m}" in src


def test_service_account_actions_reuse_authservice_not_reimplemented():
    """Block/suspend must call AuthService.lock_user/unlock_user/suspend_user/unsuspend_user
    (Phase 0E infra) rather than duplicating account_status logic."""
    src = _read(SERVICE)
    assert "auth.lock_user(" in src
    assert "auth.unlock_user(" in src
    assert "auth.suspend_user(" in src
    assert "auth.unsuspend_user(" in src


def test_service_writes_platform_audit_for_every_mutation():
    src = _read(SERVICE)
    assert "record_platform_audit" in src
    assert src.count("await self._audit(") >= 6


# ── admin_customers_router.py — new routes ──────────────────────────────────

def test_router_has_new_detail_tab_routes():
    src = _read(ROUTER)
    for path in ('"/{customer_id}/complaints"', '"/{customer_id}/service-credits"',
                 '"/{customer_id}/addresses"', '"/{customer_id}/sessions"',
                 '"/{customer_id}/login-history"', '"/{customer_id}/privacy-requests"',
                 '"/{customer_id}/audit-logs"'):
        assert path in src, f"missing route {path}"


def test_router_has_new_action_routes():
    src = _read(ROUTER)
    for path in ('"/{customer_id}/block"', '"/{customer_id}/unblock"',
                 '"/{customer_id}/suspend"', '"/{customer_id}/reactivate"',
                 '"/{customer_id}/sessions/revoke-all"'):
        assert path in src, f"missing route {path}"


def test_router_new_routes_permission_guarded():
    src = _read(ROUTER)
    for perm in ("P.CUSTOMERS_VIEW_DETAIL", "P.CUSTOMERS_SERVICE_CREDITS_READ",
                 "P.CUSTOMERS_SERVICE_CREDITS_CREATE", "P.CUSTOMERS_ADDRESSES_READ",
                 "P.CUSTOMERS_SESSIONS_READ", "P.CUSTOMERS_SESSIONS_REVOKE",
                 "P.CUSTOMERS_LOGIN_HISTORY_READ", "P.CUSTOMERS_PRIVACY_READ",
                 "P.CUSTOMERS_AUDIT_READ", "P.CUSTOMERS_BLOCK", "P.CUSTOMERS_SUSPEND",
                 "P.CUSTOMERS_REACTIVATE"):
        assert perm in src


# ── permissions.py ───────────────────────────────────────────────────────────

def test_permissions_customers_constants_exist():
    src = _read(PERMISSIONS_FILE)
    for const in ("CUSTOMERS_VIEW_DETAIL", "CUSTOMERS_EXPORT", "CUSTOMERS_BLOCK",
                  "CUSTOMERS_SUSPEND", "CUSTOMERS_REACTIVATE", "CUSTOMERS_SESSIONS_READ",
                  "CUSTOMERS_SESSIONS_REVOKE", "CUSTOMERS_LOGIN_HISTORY_READ",
                  "CUSTOMERS_ADDRESSES_READ", "CUSTOMERS_ADDRESSES_VIEW_FULL",
                  "CUSTOMERS_SERVICE_CREDITS_READ", "CUSTOMERS_SERVICE_CREDITS_CREATE",
                  "CUSTOMERS_PRIVACY_READ", "CUSTOMERS_AUDIT_READ"):
        assert const in src


# ── compliance/enterprise_service.py — subject_id filter ────────────────────

def test_compliance_list_requests_has_subject_id_filter():
    src = _read(COMPLIANCE_SVC)
    assert "subject_id: uuid.UUID | None = None" in src
    assert "ComplianceRequest.subject_id == subject_id" in src


# ── enterprise_grid/filter_registry.py ──────────────────────────────────────

def test_filter_registry_admin_customers_present():
    src = _read(FILTER_REGISTRY)
    assert '"admin_customers": {' in src


def test_filter_registry_resource_count_36():
    # Note: total grew to 39 after the Platform Settings Enterprise Upgrade added
    # admin_settings/admin_feature_flags/admin_setting_audit_logs; this test only
    # asserts Customers' resource is present, not the exact global total
    # (see test_sprint26_enterprise_grid.py for that).
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    assert len(EnterpriseFilterRegistry.all_resource_keys()) >= 36
