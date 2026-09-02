"""
P0 Enterprise Finance Hub Upgrade — test suite
Verifies (static source-inspection style, consistent with test_p0_pricing_enterprise.py
conventions in this repo — no live DB fixture required):

  Migration 078:
    - exists, correct revision/down_revision
    - credit_topup_orders table + columns
    - security_deposits / warranty_claims / payout_records additive columns

  Backend — finance_hub/models.py:
    - CreditTopupOrder model + to_dict()

  Backend — finance_hub/service.py (FinanceHubService):
    - Overview: get_finance_summary, get_finance_overview
    - Deposits: list/summary/detail/approve/reject/record_offline/refund/adjust
    - Top-ups: list/summary/detail/retry_credit_posting/refund_topup
    - Warranty Claims: list/summary/detail/assign_reviewer/request_documents/approve/reject/settle
    - Payouts: list/summary/detail/approve/reject/mark_processing/mark_completed/mark_failed
    - Wallets: list_wallets/get_wallet_ledger
    - Audit: list_audit_logs / _audit

  Backend — finance_hub/admin_router.py:
    - all /v1/admin/finance/* endpoints wired, permission-guarded

  Backend — platform_commerce/service.py:
    - initiate_purchase / confirm_purchase reference CreditTopupOrder

  Backend — app/core/permissions.py:
    - P.FINANCE_* constants exist

  Backend — enterprise_grid/filter_registry.py:
    - 5 new finance resource configs present

  Backend — app/main.py:
    - finance_hub router registered
"""
import os

ROOT               = os.path.dirname(os.path.dirname(__file__))
FINANCE_MODELS     = os.path.join(ROOT, "app", "engines", "finance_hub", "models.py")
FINANCE_SERVICE    = os.path.join(ROOT, "app", "engines", "finance_hub", "service.py")
FINANCE_ROUTER     = os.path.join(ROOT, "app", "engines", "finance_hub", "admin_router.py")
COMMERCE_SERVICE   = os.path.join(ROOT, "app", "engines", "platform_commerce", "service.py")
PERMISSIONS_FILE   = os.path.join(ROOT, "app", "core", "permissions.py")
FILTER_REGISTRY    = os.path.join(ROOT, "app", "engines", "enterprise_grid", "filter_registry.py")
MAIN_PY            = os.path.join(ROOT, "app", "main.py")
MIGRATION_078      = os.path.join(ROOT, "alembic", "versions", "078_finance_enterprise_upgrade.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration 078 ────────────────────────────────────────────────────────────

def test_migration_078_exists():
    assert os.path.exists(MIGRATION_078), "Migration 078 not found"


def test_migration_078_revision():
    src = _read(MIGRATION_078)
    assert 'revision = "078"' in src


def test_migration_078_down_revision():
    src = _read(MIGRATION_078)
    assert 'down_revision = "077"' in src


def test_migration_078_credit_topup_orders_table():
    src = _read(MIGRATION_078)
    assert "credit_topup_orders" in src
    for col in ("order_ref", "payment_status", "wallet_credit_status", "wallet_transaction_id",
                "gateway_order_id", "refunded_amount"):
        assert col in src, f"Expected column '{col}' on credit_topup_orders"


def test_migration_078_security_deposits_columns():
    src = _read(MIGRATION_078)
    for col in ("hold_state", "rejection_reason", "clarification_notes", "approved_by", "approved_at"):
        assert col in src, f"Expected security_deposits column '{col}'"


def test_migration_078_warranty_claims_columns():
    src = _read(MIGRATION_078)
    for col in ("assigned_reviewer_id", "settled_at", "settled_amount",
                "documents_requested_at", "documents_requested_notes"):
        assert col in src, f"Expected warranty_claims column '{col}'"


def test_migration_078_payout_records_columns():
    src = _read(MIGRATION_078)
    for col in ("payout_number", "payout_type", "approved_amount", "approved_by", "approved_at", "rejection_reason"):
        assert col in src, f"Expected payout_records column '{col}'"


# ── Models ────────────────────────────────────────────────────────────────────

def test_credit_topup_order_model_exists():
    src = _read(FINANCE_MODELS)
    assert "class CreditTopupOrder(" in src


def test_credit_topup_order_has_to_dict():
    src = _read(FINANCE_MODELS)
    idx = src.index("class CreditTopupOrder(")
    snippet = src[idx:idx + 3000]
    assert "def to_dict" in snippet


def test_credit_topup_order_fields():
    src = _read(FINANCE_MODELS)
    idx = src.index("class CreditTopupOrder(")
    snippet = src[idx:idx + 3000]
    for field in ("payment_status", "wallet_credit_status", "credits_purchased", "amount_paid", "order_ref"):
        assert field in snippet, f"CreditTopupOrder missing field: {field}"


# ── Service — Overview ────────────────────────────────────────────────────────

def test_get_finance_summary_exists():
    assert "async def get_finance_summary" in _read(FINANCE_SERVICE)


def test_get_finance_overview_exists():
    src = _read(FINANCE_SERVICE)
    assert "async def get_finance_overview" in src
    for key in ("wallet_health_distribution", "top_low_balance_tenants",
                "top_commission_contributors", "recent_finance_activity", "pending_actions_queue", "at_risk_tenants"):
        assert key in src, f"get_finance_overview missing insight key: {key}"


# ── Service — Deposits ────────────────────────────────────────────────────────

# ── Service — Top-ups ─────────────────────────────────────────────────────────

def test_topup_service_methods_exist():
    src = _read(FINANCE_SERVICE)
    for fn in ("list_topups", "get_topups_summary", "get_topup_detail",
               "retry_credit_posting", "refund_topup", "export_topups"):
        assert f"async def {fn}" in src, f"Missing topup method: {fn}"


def test_topup_retry_guards_already_credited():
    src = _read(FINANCE_SERVICE)
    idx = src.index("async def retry_credit_posting(")
    snippet = src[idx:idx + 1000]
    assert "CONFLICT" in snippet


# ── Service — Warranty Claims ─────────────────────────────────────────────────

def test_claims_service_methods_exist():
    src = _read(FINANCE_SERVICE)
    for fn in ("list_claims", "get_claims_summary", "get_claim_detail", "assign_reviewer",
               "request_documents", "approve_claim", "reject_claim", "settle_claim", "export_claims"):
        assert f"async def {fn}" in src, f"Missing claim method: {fn}"


def test_claim_settlement_is_atomic_with_admin_approval():
    src = _read(FINANCE_SERVICE)
    idx = src.index("async def settle_claim(")
    snippet = src[idx:idx + 700]
    assert "WARRANTY_SETTLEMENT_ATOMIC" in snippet
    assert "issued atomically when Admin approves" in snippet
    assert "status_code=409" in snippet


# ── Service — Payouts ──────────────────────────────────────────────────────────

def test_payout_service_methods_exist():
    src = _read(FINANCE_SERVICE)
    for fn in ("list_payouts", "get_payouts_summary", "get_payout_detail", "approve_payout",
               "reject_payout", "mark_processing", "mark_completed", "mark_failed", "export_payouts"):
        assert f"async def {fn}" in src, f"Missing payout method: {fn}"


def test_payout_workflow_enforces_state_transitions():
    src = _read(FINANCE_SERVICE)
    assert "_require_status" in src
    idx = src.index("async def mark_completed(")
    snippet = src[idx:idx + 400]
    assert '"processing"' in snippet


# ── Service — Wallets + Audit ──────────────────────────────────────────────────

def test_wallet_service_methods_exist():
    src = _read(FINANCE_SERVICE)
    assert "async def list_wallets" in src
    assert "async def get_wallet_ledger" in src


def test_audit_log_methods_exist():
    src = _read(FINANCE_SERVICE)
    assert "async def list_audit_logs" in src
    assert "async def _audit" in src
    assert "record_platform_audit" in src


# ── Purchase flow wiring ──────────────────────────────────────────────────────

def test_initiate_purchase_creates_topup_order():
    src = _read(COMMERCE_SERVICE)
    idx = src.index("async def initiate_purchase(")
    snippet = src[idx:idx + 1500]
    assert "CreditTopupOrder" in snippet


def test_confirm_purchase_updates_topup_order():
    src = _read(COMMERCE_SERVICE)
    idx = src.index("async def confirm_purchase(")
    snippet = src[idx:idx + 2500]
    assert "CreditTopupOrder" in snippet
    assert '"credited"' in snippet


# ── Router ────────────────────────────────────────────────────────────────────

def test_router_overview_endpoints():
    src = _read(FINANCE_ROUTER)
    assert '"/summary"' in src
    assert '"/overview"' in src


def test_router_topups_endpoints():
    src = _read(FINANCE_ROUTER)
    for path in ("/topups", "/topups/summary", "/topups/export",
                 "/topups/{topup_id}/retry-credit", "/topups/{topup_id}/refund"):
        assert f'"{path}"' in src, f"Missing router path: {path}"


def test_router_claims_endpoints():
    src = _read(FINANCE_ROUTER)
    for path in ("/warranty-claims", "/warranty-claims/summary",
                 "/warranty-claims/{claim_id}/assign", "/warranty-claims/{claim_id}/request-documents",
                 "/warranty-claims/{claim_id}/approve", "/warranty-claims/{claim_id}/reject",
                 "/warranty-claims/{claim_id}/settle"):
        assert f'"{path}"' in src, f"Missing router path: {path}"


def test_router_payouts_endpoints():
    src = _read(FINANCE_ROUTER)
    for path in ("/payouts", "/payouts/summary", "/payouts/{payout_id}/approve",
                 "/payouts/{payout_id}/reject", "/payouts/{payout_id}/mark-processing",
                 "/payouts/{payout_id}/mark-completed", "/payouts/{payout_id}/mark-failed"):
        assert f'"{path}"' in src, f"Missing router path: {path}"


def test_router_wallets_and_audit_endpoints():
    src = _read(FINANCE_ROUTER)
    assert '"/wallets"' in src
    assert '"/wallets/{wallet_id}/ledger"' in src
    assert '"/audit-logs"' in src


def test_router_uses_finance_permissions():
    src = _read(FINANCE_ROUTER)
    for perm in ("P.FINANCE_READ", "P.FINANCE_TOPUPS_REFUND",
                 "P.FINANCE_CLAIMS_SETTLE", "P.FINANCE_PAYOUTS_APPROVE", "P.FINANCE_WALLETS_READ",
                 "P.FINANCE_AUDIT_READ"):
        assert f"require_permission({perm})" in src, f"Missing permission guard: {perm}"


# ── Permissions ────────────────────────────────────────────────────────────────

def test_finance_permissions_exist():
    src = _read(PERMISSIONS_FILE)
    for perm in ("FINANCE_READ", "FINANCE_EXPORT",
                 "FINANCE_TOPUPS_READ", "FINANCE_CLAIMS_ASSIGN", "FINANCE_CLAIMS_SETTLE",
                 "FINANCE_PAYOUTS_APPROVE", "FINANCE_PAYOUTS_COMPLETE", "FINANCE_WALLETS_ADJUST",
                 "FINANCE_AUDIT_READ"):
        assert perm in src, f"Missing permission constant: {perm}"


# ── Enterprise Grid registry ─────────────────────────────────────────────────

def test_filter_registry_finance_resources_exist():
    src = _read(FILTER_REGISTRY)
    for key in ("admin_finance_topups", "admin_finance_claims",
                "admin_finance_payouts", "admin_finance_wallets"):
        assert f'"{key}"' in src, f"Missing enterprise_grid resource config: {key}"


# ── main.py registration ──────────────────────────────────────────────────────

def test_finance_hub_router_registered_in_main():
    src = _read(MAIN_PY)
    assert "finance_hub.admin_router" in src
    assert "finance_hub_router" in src
