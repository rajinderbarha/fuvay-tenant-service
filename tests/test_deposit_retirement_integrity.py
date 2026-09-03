"""Cross-surface guards for the security-deposit retirement."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_runtime_services_do_not_query_removed_deposit_models_or_columns():
    sources = {
        "commerce": _read("app/engines/platform_commerce/service.py"),
        "preflight": _read("app/engines/platform_commerce/preflight.py"),
        "tenant_admin": _read("app/engines/tenant_engine/admin_service.py"),
        "tenant": _read("app/engines/tenant_engine/service.py"),
        "trust": _read("app/engines/trust_quality/service.py"),
        "trust_bulk": _read("app/engines/trust_quality/recalculation.py"),
    }
    for name, source in sources.items():
        assert "select(SecurityDeposit)" not in source, name
        assert "security_deposit_paid" not in source, name
        assert "security_deposit_amount" not in source, name


def test_tenant_wallet_reads_use_the_canonical_usage_credit_account():
    source = _read("app/engines/tenant_engine/admin_service.py")
    wallet_body = source.split("async def get_credit_wallet", 1)[1].split("\n    async def ", 1)[0]
    ledger_body = source.split("async def get_credit_ledger", 1)[1].split("\n    async def ", 1)[0]
    assert "TenantBilling" in wallet_body
    assert "UsageCreditLedger" in wallet_body
    assert "UsageCreditLedger" in ledger_body
    assert "TenantWallet" not in source
    assert "WalletTransaction" not in source


def test_field_ops_no_longer_shadows_canonical_tenant_wallet_routes():
    main_source = _read("app/main.py")
    admin_source = _read("app/engines/field_ops/admin_finance_router.py")
    tenant_source = _read("app/engines/field_ops/tenant_finance_router.py")
    billing_source = _read("app/engines/field_ops/billing_service.py")

    assert "fieldops_admin_wallet_router" not in main_source
    assert "fieldops_tenant_wallet_router" not in main_source
    assert "wallet_router" not in admin_source
    assert "wallet_router" not in tenant_source
    assert "UsageCreditService" in billing_source
    assert "admin_credit_wallet" not in billing_source
    assert "credit_wallet(" not in billing_source
    assert "debit_wallet(" not in billing_source


def test_finance_and_analytics_reads_use_canonical_usage_credit_data():
    analytics_sources = [
        _read("app/engines/analytics/admin_analytics.py"),
        _read("app/engines/analytics/provider_analytics.py"),
        _read("app/engines/analytics/report_service.py"),
    ]
    for source in analytics_sources:
        assert "tenant_wallets" not in source
        assert "wallet_transactions" not in source

    finance = _read("app/engines/finance_hub/service.py")
    wallet_directory = finance.split("async def list_wallets", 1)[1]
    assert "TenantBilling" in wallet_directory
    assert "UsageCreditLedger" in wallet_directory
    assert "select(TenantWallet" not in wallet_directory


def test_admin_configuration_and_notifications_do_not_offer_deposits():
    settings = _read("app/engines/settings_engine/seed_data.py")
    notifications = _read("app/engines/notification/seed_data.py")
    notification_constants = _read("app/engines/notification/constants.py")
    provider_workspace = _read(
        "frontend/super-admin/components/directory/ProviderDetailWorkspace.tsx"
    )
    assert "security_deposit" not in settings
    assert "security_deposit_required" not in notifications
    assert "security_deposit_required" not in notification_constants
    assert "Security Deposit" not in provider_workspace


def test_database_cleanup_chain_is_present():
    assert (ROOT / "alembic/versions/317_topup_seats_remove_security_deposit.py").exists()
    assert (ROOT / "alembic/versions/318_dispute_settlement_credit_only.py").exists()
    assert (ROOT / "alembic/versions/330_remove_deposit_from_trust_health.py").exists()
    assert (ROOT / "alembic/versions/331_retire_deposit_admin_artifacts.py").exists()
    assert (ROOT / "alembic/versions/334_remove_refund_deposit_artifact.py").exists()
    assert (ROOT / "alembic/versions/335_retire_deposit_finance_model_key.py").exists()


def test_public_category_configuration_has_no_legacy_deposit_finance_model():
    sources = [
        _read("app/engines/admin_catalog/service.py"),
        _read("app/engines/settings_engine/admin_router.py"),
        _read("frontend/super-admin/app/admin/categories/page.tsx"),
    ]
    for source in sources:
        assert "security_deposit_plus_credit_wallet" not in source
    assert '"credit_wallet_only"' in sources[0]


def test_public_finance_and_refund_contracts_have_no_deposit_fields():
    sources = [
        _read("app/engines/analytics/platform_service.py"),
        _read("app/engines/finance_hub/home_services_finance_service.py"),
        _read("app/engines/complaints/models.py"),
        _read("app/engines/complaints/refund_service.py"),
    ]
    for source in sources:
        assert '"security_deposit' not in source
