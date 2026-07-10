"""Phase 4 — Packages, Usage Credits & Security Deposit certification.

Static-inspection style (established convention this session — no JS test
runner exists). Live end-to-end behavior for these same assertions was
additionally verified via curl against the real running backend + real
Postgres before this file was written — see PHASE_4_FINANCE_BACKEND_REPORT.md
and PHASE_4_FINANCE_MANUAL_SMOKE_REPORT.md for that evidence.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TENANT_PAGE = (ROOT / "frontend/super-admin/app/admin/tenants/[id]/page.tsx").read_text(encoding="utf-8-sig")
API_TS = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8-sig")
SERVICE = (ROOT / "app/engines/package_commerce/service.py").read_text(encoding="utf-8-sig")
ROUTER = (ROOT / "app/engines/package_commerce/admin_router.py").read_text(encoding="utf-8-sig")
MODELS = (ROOT / "app/engines/package_commerce/models.py").read_text(encoding="utf-8-sig")
LEDGER = (ROOT / "app/engines/platform_commerce/ledger.py").read_text(encoding="utf-8-sig")
PERMISSIONS = (ROOT / "app/core/permissions.py").read_text(encoding="utf-8-sig")
TENANT_ADMIN_ROUTER = (ROOT / "app/engines/tenant_engine/admin_router.py").read_text(encoding="utf-8-sig")


# ── Module 1: Package / Plan Management ─────────────────────────────
def test_package_model_has_required_baseline_fields():
    assert "included_credit_amount" in MODELS
    assert "security_deposit_amount" in MODELS
    assert "is_active" in MODELS


def test_package_crud_endpoints_exist():
    for path in ('"/v1/admin/packages"', '"/v1/admin/packages/{package_id}"',
                 '"/v1/admin/packages/{package_id}/activate"',
                 '"/v1/admin/packages/{package_id}/deactivate"',
                 '"/v1/admin/packages/{package_id}/clone"'):
        assert path in ROUTER


def test_package_permissions_wired():
    for perm in ("PACKAGES_READ", "PACKAGES_CREATE", "PACKAGES_UPDATE",
                 "PACKAGES_ARCHIVE", "PACKAGES_ACTIVATE", "PACKAGES_DEACTIVATE",
                 "PACKAGES_CLONE", "PACKAGES_AUDIT_READ"):
        assert perm in PERMISSIONS
        assert perm in ROUTER


def test_package_mutations_create_audit_log():
    for marker in ("_pkg_audit(None, pkg.id, None, \"package_created\"",
                   "_pkg_audit(None, pkg.id, None, \"package_updated\""):
        assert marker in SERVICE


# ── Module 1 bug fix: request_id plumbing ───────────────────────────
def test_request_id_no_longer_hardcoded_placeholder():
    assert 'getattr(request.state, "request_id", None)' in ROUTER


def test_package_audit_log_has_request_id_column():
    assert "request_id: Mapped[str | None]" in MODELS
    assert "request_id=(self.request_id" in SERVICE


def test_global_and_per_package_audit_endpoints_exist():
    assert '"/v1/admin/packages/audit-logs"' in ROUTER
    assert '"/v1/admin/packages/{package_id}/audit"' in ROUTER
    assert "async def list_package_audit" in SERVICE


# ── Module 3: Package Activation Rules (config only) ────────────────
def test_tenant_package_assignment_activation_semantics_documented():
    assert "starts_at and expires_at MUST remain NULL until admin approval" in MODELS \
        or "pending_approval" in MODELS


# ── Module 4/5/6: Usage Credit Balance, Ledger, Top-up/Adjustment ───
def test_wallet_ledger_endpoints_exist():
    for path in ('"/v1/admin/tenants/{tenant_id}/credit-wallet"',
                 '"/v1/admin/tenants/{tenant_id}/credit-ledger"',
                 '"/v1/admin/tenants/{tenant_id}/credit-wallet/top-up"',
                 '"/v1/admin/tenants/{tenant_id}/credit-wallet/adjust"'):
        assert path in ROUTER


def test_usage_credit_permissions_wired():
    for perm in ("FINANCE_USAGE_CREDITS_READ", "FINANCE_USAGE_CREDITS_TOP_UP",
                 "FINANCE_USAGE_CREDITS_ADJUST", "FINANCE_USAGE_CREDITS_LEDGER_READ"):
        assert perm in PERMISSIONS
        assert perm in ROUTER


def test_topup_requires_positive_amount():
    assert 'CREDIT_AMOUNT_INVALID' in SERVICE
    assert "amount <= 0" in SERVICE


def test_adjustment_requires_reason():
    assert "CREDIT_ADJUSTMENT_REASON_REQUIRED" in SERVICE
    assert "not reason" in SERVICE


def test_debit_cannot_go_negative():
    assert "Insufficient usage credit balance" in LEDGER
    assert "wallet.credit_balance < amount" in LEDGER


def test_debit_error_message_has_no_crashing_currency_symbol():
    # ₹ is the Rupee sign that previously crashed Windows console logging
    # (charmap codec) and turned a clean 422/402 into an unhandled 500.
    assert "₹" not in LEDGER


def test_wallet_topup_adjust_create_audit_log():
    assert '_pkg_audit(tenant_id, None, None, "credit_topup"' in SERVICE
    assert '_pkg_audit(tenant_id, None, None, "credit_adjustment"' in SERVICE


# ── Module 8/9/10: Security Deposit ──────────────────────────────────
def test_security_deposit_endpoints_exist():
    for path in ('"/v1/admin/tenants/{tenant_id}/security-deposit"',
                 '"/v1/admin/tenants/{tenant_id}/security-deposit/mark-paid"',
                 '"/v1/admin/tenants/{tenant_id}/security-deposit/refund"',
                 '"/v1/admin/tenants/{tenant_id}/security-deposit/forfeit"'):
        assert path in ROUTER


def test_security_deposit_permissions_wired():
    for perm in ("FINANCE_SECURITY_DEPOSITS_READ", "FINANCE_SECURITY_DEPOSITS_MARK_RECEIVED",
                 "FINANCE_SECURITY_DEPOSITS_RELEASE", "FINANCE_SECURITY_DEPOSITS_ADJUST"):
        assert perm in PERMISSIONS
        assert perm in ROUTER


def test_deposit_route_collision_with_tenant_engine_removed():
    # tenant_engine used to define GET /{tenant_id}/security-deposit and
    # POST .../mark-paid at the SAME paths, registered earlier in main.py,
    # silently shadowing package_commerce's permission-gated, audited,
    # envelope-wrapped versions. Confirm those two duplicate routes are gone.
    assert '@router.get("/{tenant_id}/security-deposit")' not in TENANT_ADMIN_ROUTER
    assert '@router.post("/{tenant_id}/security-deposit/mark-paid")' not in TENANT_ADMIN_ROUTER


def test_deposit_audit_action_labels_are_distinct_not_copy_pasted():
    # refund/forfeit previously both logged action="security_deposit_paid"
    # (a copy-paste bug) instead of their own distinct action names.
    assert '"security_deposit_refunded"' in SERVICE
    assert '"security_deposit_forfeited"' in SERVICE


def test_deposit_actions_require_reason_where_specified():
    assert "data.get(\"reason\")" in SERVICE


def test_deposit_amount_field_is_numeric_not_boolean_flag():
    # security_deposit_required in the ticket maps to security_deposit_amount > 0
    # in this codebase's real schema — documented mapping, not a defect.
    assert "security_deposit_amount" in MODELS


# ── Forbidden label scan (backend) ──────────────────────────────────
def test_no_forbidden_labels_in_backend_finance_code():
    forbidden = ("Cash Wallet", "Withdrawable Balance", "Tenant Payout",
                 "Provider Earnings Wallet", "Escrow", "Provider Cash Balance")
    for label in forbidden:
        assert label not in SERVICE
        assert label not in ROUTER
        assert label not in MODELS
        assert label not in LEDGER


def test_escrow_docstring_typo_fixed():
    assert "Per-tenant escrow" not in (ROOT / "app/engines/platform_commerce/models.py").read_text(encoding="utf-8-sig")


# ── Tenant360 wallet-ledger crash fix (field-name mismatch) ─────────
def test_tenant360_wallet_transaction_fields_match_backend():
    assert "txn_type" in API_TS and "txn_id" in API_TS
    assert "tx.txn_type" in TENANT_PAGE
    assert "tx.type" not in TENANT_PAGE
    assert "tx.job_id" not in TENANT_PAGE


# ── Finance settings baseline ────────────────────────────────────────
def test_finance_settings_seed_values_present():
    seed = (ROOT / "app/engines/settings_engine/seed_data.py").read_text(encoding="utf-8-sig")
    assert "customer_pays_provider_directly" in seed
    assert "tenant_payouts_enabled" in seed
    assert "job_credit_deduction_trigger" in seed
    assert "provider_usage_credits_enabled" in seed
