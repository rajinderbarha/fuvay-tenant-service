"""Finance Readiness step (onboarding step 7 of 8) — router + model structure tests.

Home Services canonical model: the customer pays the tenant's business
directly; ServiceOS never collects/holds/settles that payment. These tests
assert the router only ever reads the LIVE commission/credit/deposit
authorities and never invents a payout/settlement mechanism or reads from
the frozen package_commerce commission path.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
ROUTER = os.path.join(BASE, "app/engines/vertical_catalog/tenant_finance_readiness_router.py")
MODELS = os.path.join(BASE, "app/engines/tenant_engine/models.py")
MIGRATION = os.path.join(BASE, "alembic/versions/191_tenant_finance_readiness.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestRouterStructure:
    def test_router_has_expected_endpoints(self):
        c = _read(ROUTER)
        assert 'router = APIRouter(prefix="/v1/tenant/home-services/setup/finance"' in c
        assert '@router.get("")' in c
        assert '@router.put("")' in c

    def test_uses_shared_live_commission_resolver_not_frozen_package_commerce_path(self):
        c = _read(ROUTER)
        assert "resolve_provider_commission_rate" in c
        assert "from app.engines.invoice_payment.commission_service import resolve_provider_commission_rate" in c
        assert "from app.engines.package_commerce" not in c
        assert "_resolve_commission_rate" not in c

    def test_uses_live_tenant_billing_for_credits(self):
        """The deposit fields went with the deposit (migration 317/318).

        `tenant_billing.credit_balance` is the one live number this surface
        reads now; capacity and the booking floor are what replaced collateral.
        """
        c = _read(ROUTER)
        assert "tenant_billing" in c
        assert "credit_balance" in c
        assert "security_deposit" not in c

    def test_projection_uses_current_topup_quote_contract(self):
        c = _read(ROUTER)
        assert 'funding_quote["credit_tax"]' not in c
        assert 'funding_quote["credit_gross"]' not in c
        assert '.get("gst_amount", 0.0)' in c
        assert 'funding_quote.get("can_pay")' in c

    def test_no_payout_or_settlement_fields_exposed(self):
        c = _read(ROUTER)
        for forbidden in (
            "payout", "settlement_bank", "beneficiary",
            "merchant_account",
        ):
            assert forbidden not in c.lower(), f"unexpected payout/settlement concept: {forbidden}"

    def test_deposit_is_never_collected_during_onboarding(self):
        c = _read(ROUTER)
        # The save endpoint request body must not accept a deposit amount or
        # a "paid" flag — deposit collection happens only after admin approval,
        # in a separate activation flow, never from this step's PUT.
        assert "class SaveFinanceReadinessRequest(BaseModel):" in c
        body_start = c.index("class SaveFinanceReadinessRequest")
        body_end = c.index("@router.put", body_start)
        body = c[body_start:body_end]
        assert "deposit" not in body.lower()

    def test_direct_payment_methods_are_the_only_editable_finance_fields(self):
        c = _read(ROUTER)
        for field in (
            "accepts_cash", "accepts_upi", "accepts_card_at_service_location",
            "accepts_bank_transfer", "payment_confirmation_required",
            "invoice_business_name", "invoice_prefix", "issue_customer_receipt",
        ):
            assert field in c

    def test_notice_states_servicos_does_not_hold_funds(self):
        c = _read(ROUTER)
        assert "does not hold or settle job funds" in c

    def test_mutation_requires_tenant_owner(self):
        c = _read(ROUTER)
        assert "require_tenant_owner_mutation" in c

    def test_guarded_by_vertical_not_active(self):
        c = _read(ROUTER)
        assert c.count("require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)") >= 2


class TestModel:
    def test_model_fields_present(self):
        c = _read(MODELS)
        assert "class TenantFinanceReadiness(ServiceOSBase):" in c
        assert '__tablename__ = "tenant_finance_readiness"' in c
        for field in (
            "accepts_cash", "accepts_upi", "accepts_card_at_service_location",
            "accepts_bank_transfer", "payment_confirmation_required",
            "invoice_business_name", "invoice_prefix", "issue_customer_receipt",
        ):
            assert field in c

    def test_model_has_no_payout_or_settlement_fields(self):
        c = _read(MODELS)
        block_start = c.index("class TenantFinanceReadiness")
        block_end = c.index("class TenantLimits")
        block = c[block_start:block_end]
        # The deposit was removed in migration 317/318, so its readiness
        # snapshot is gone too. Job-payment payout/settlement concepts remain
        # forbidden because customers pay providers directly.
        assert "security_deposit" not in block
        for forbidden in ("payout", "settlement", "bank_account"):
            assert forbidden not in block.lower()


class TestMigration:
    def test_migration_chains_from_latest_head(self):
        c = _read(MIGRATION)
        assert 'revision = "191"' in c
        assert 'down_revision = "190"' in c

    def test_migration_creates_expected_table_and_index(self):
        c = _read(MIGRATION)
        assert '"tenant_finance_readiness"' in c
        assert "ix_tfr_tenant_id" in c
        assert "unique=True" in c
