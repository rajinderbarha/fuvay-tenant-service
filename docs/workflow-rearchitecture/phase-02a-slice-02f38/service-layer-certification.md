# Service-Layer Certification

Evidence: `_require_trusted_tenant(requested_tenant_id=None)` pattern,
established and reused across every touched service in Slices 2F-35/36/37
(WebhookService, RAGService, SecurityService, DocumentService,
ChatService, InventoryService, AppointmentService, ServiceCatalogService,
DispatchService, DSService, SettingsService, NotificationService,
PricingService, PaymentService, SubscriptionService), re-confirmed present
via `verify_2f37.py` R06 ("every touched service has a
`_require_trusted_tenant` helper") in this worktree.

| Claim | Status |
|---|---|
| Trusted context is mandatory | PASS — helper raises `PERMISSION_DENIED` if `actor_tenant_id is None` |
| Missing/incomplete context fails | PASS — same helper |
| Client-derived context fails | PASS — mismatch between `requested_tenant_id` and `actor_tenant_id` raises |
| Tenant mismatch fails | PASS |
| Object/parent ownership enforced | PASS for the 313 canonical routes (R07-R10); not independently re-verified for the ~1,873 non-canonical mutation routes this slice |
| Internal callers pass trusted context | PASS (reviewed in 2F-35/36 service-layer-enforcement-audit.csv) |
| Workers do not bypass authorization | NOT INDEPENDENTLY RE-VERIFIED THIS SLICE — no worker process is running in this environment to observe live |
| Broad exception handling preserves authorization failures | PASS (reviewed pattern: `PermissionError`/`PermissionDenied` is never caught by a generic `except Exception` that converts to success) |
| No legacy unprotected service signature remains | PASS for canonical routes; not verified for the broader mutation set |

This certification is scoped to the 313 canonical routes plus the specific
services already audited in 2F-35/36/37. It is not a from-scratch
re-audit of every service in the codebase.
