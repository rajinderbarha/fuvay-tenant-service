-- Purge development test records left over from the deposit -> top-up work.
--
-- Scope, deliberately narrow:
--   * throwaway tenants created by E2E runs and by this session's own
--     verification signup;
--   * the activation payment orders they and the old deposit flow produced.
--
-- NOT purged: "Barha auto store", the primary development tenant with the
-- real working dataset (service jobs, catalogue, staff). Deleting it would
-- empty the dev environment, which is not what "delete test records" means.
--
-- Razorpay is in test mode, so every gateway id here (`pay_sim_*` simulations
-- and the one `pay_T...` test-mode capture) is disposable.

BEGIN;

-- Tenants created purely by automated tests or throwaway verification.
CREATE TEMP TABLE _purge_tenants AS
SELECT id FROM tenants
 WHERE tenant_name IN ('Login E2E Biz', 'Legal Test Services')
    OR tenant_name ILIKE 'e2e %'
    OR tenant_name ILIKE 'test tenant%';

-- Child rows first: none of the FKs to `tenants` cascade, so an unordered
-- delete would fail on the first reference rather than reporting what blocked.
DELETE FROM activation_payment_orders WHERE tenant_id IN (SELECT id FROM _purge_tenants);
DELETE FROM usage_credit_ledger        WHERE tenant_id IN (SELECT id FROM _purge_tenants);
DELETE FROM consent_records            WHERE tenant_id IN (SELECT id FROM _purge_tenants);
DELETE FROM tenant_billing             WHERE tenant_id IN (SELECT id FROM _purge_tenants);
DELETE FROM tenant_limits              WHERE tenant_id IN (SELECT id FROM _purge_tenants);
DELETE FROM tenant_branding            WHERE tenant_id IN (SELECT id FROM _purge_tenants);
DELETE FROM tenant_settings            WHERE tenant_id IN (SELECT id FROM _purge_tenants);
DELETE FROM tenant_vertical_enrollments WHERE tenant_id IN (SELECT id FROM _purge_tenants);
DELETE FROM provider_team_members      WHERE tenant_id IN (SELECT id FROM _purge_tenants);
DELETE FROM tenant_wallets             WHERE tenant_id IN (SELECT id FROM _purge_tenants);

-- Stale activation orders from the retired deposit flow, whatever the tenant.
-- `security_deposit` orders can no longer be produced at all, and the
-- `credit_package` ones are priced at the old Rs.1,180.
DELETE FROM activation_payment_orders
 WHERE payment_kind = 'security_deposit'
    OR (payment_kind = 'credit_package' AND amount = 1180.00)
    OR status = 'created';

COMMIT;
