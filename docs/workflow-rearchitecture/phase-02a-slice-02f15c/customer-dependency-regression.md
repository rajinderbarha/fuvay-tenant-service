# Customer Dependency Regression

No defect was found in `require_tenant_mutation_permission`'s customer-branch behavior this slice — the dependency is unchanged from 2F-15B. All previously-proven properties were re-verified via full regression (`TestCustomerDependencyIndependentOfTenantScope`, 4 tests, unmodified, passing):

| Property | Status |
|---|---|
| Customer requires no tenant mutation access scope | Re-verified — `test_customer_user_without_access_scope_passes_tenant_mutation_permission` passes unchanged |
| Customer identity is principal-derived | Re-verified — `create_booking`'s router still derives `customer_id = uuid.UUID(u.user_id)` when `u.role == "customer"`, never client-suppliable |
| Tenant roles cannot enter customer ownership logic | Re-verified — `_assert_can_access_booking`'s `if/elif` role switch is unchanged; no shared code path exists between the `customer` and tenant-scoped branches |
| Read-only tenant users cannot use the customer branch | Re-verified — `test_tenant_owner_with_readonly_scope_still_denied` passes unchanged |
| Unknown role and malformed scope fail closed | Re-verified — `require_permission`'s underlying role-grant lookup fails closed for undefined roles (unchanged); `test_customer_user_with_forged_readonly_scope_is_denied` (adversarial forged-scope case) still correctly denies |
| Foreign Booking ownership fails | Re-verified via full regression of `_assert_can_access_booking`-dependent tests (cancel_booking, request_reschedule, add_note ownership tests, unchanged) |
| Customer account state is respected | Re-verified — `create_job`'s/`create_booking`'s own customer-account validation blocks (active/non-deleted) are unchanged and still exercised by the full regression sweep |

Per the mission's explicit instruction ("Do not alter the dependency unless a direct defect is found"), `require_tenant_mutation_permission` itself was NOT modified this slice — only the Booking-provenance queries (a separate, unrelated code path) were changed.
