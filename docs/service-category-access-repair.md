# “Offer this service” category-access correction

The Services & Pricing checkbox calls `TenantCatalogService.enable_service`. It checks the service group's effective category entitlement independently of technician-seat capacity.

Public registration already grants the selected vertical and its active service groups. Two legitimate gaps can occur: registrations completed before that provisioning existed, and service groups added after registration. They must not be fixed by removing the entitlement check, buying extra technician seats, or publishing/approving a provider automatically.

On an explicit enable request, the backend now attempts a narrowly scoped repair before returning `CATEGORY_NOT_ENTITLED`:

- Only an active Home Services catalog group is eligible.
- The tenant must have a permitted account state and a non-suspended/non-rejected Home Services enrollment.
- An effective module with the existing `active_vertical_service_groups` registration policy can acquire a missing group grant.
- Older self-signups require a completed Home Services registration tied to that exact tenant. A missing module grant can then be provisioned alongside the group.
- Any existing category entitlement, including inactive, suspended, expired, pending, archived or future-dated, prevents automatic repair when it fails the effective-access check. An ineffective module also prevents repair.
- Admin-restricted modules without the registration policy are not broadened automatically.
- Grants use the existing audited entitlement service, within the service-enable transaction. A tenant row lock serializes concurrent repair attempts; the repair does not commit independently.

Canonical access resolution additionally verifies that the parent module belongs to the same tenant and actual vertical, and that the service group is active and not deleted. Matching/customer visibility/booking confirmation continue using that same resolver.

Technician-seat limits, provider submission and admin approval, service pricing, and publication checks are unchanged. The remaining denial message now directs the provider to an admin access review instead of implying that a seat purchase resolves it.

Verification is local and isolated. The configured local database contains no tenant entitlement or enrollment records, so it cannot prove the state of the tenant on `129.121.137.155`. No remote data, access grants, approvals or deployment were changed during this fix. After deploying, retry the checkbox with the affected account. Genuine explicit restrictions still require an admin decision.
