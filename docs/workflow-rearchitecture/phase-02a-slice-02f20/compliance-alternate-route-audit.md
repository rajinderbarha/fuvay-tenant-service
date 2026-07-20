# Compliance Alternate Route Audit

| Alternate surface | Same records? | Persona/dependency | Disposition |
|---|---|---|---|
| `customer_router.py` (`/v1/me/compliance/*`) | SAME (`ComplianceRequest`, `ComplianceExport`, `ConsentRecord`) | `require_customer`, scoped by the REAL `subject_id` column (stronger than provider_router's JSONB approach) | `ALTERNATE_PROTECTED` — stronger, not weaker; unchanged, out of scope. Its `revoke_consent` call site shares the SAME `tenant_id=None` mechanism this slice fixed, but for a customer caller `tenant_id=None` is CORRECT (customers have no tenant_id) — not a bug for that persona. |
| `admin_router.py` (`/v1/admin/compliance/*`) | SAME | `require_super_admin`, platform-wide (no tenant filter — by design) | `TRUSTED_INTERNAL` / `ALTERNATE_PROTECTED` — stronger persona, not a weaker same-record route. Its `create_request` call passes raw client body with no server-side subject derivation (weaker INPUT validation than provider/customer routers) — but this is intentional for a super_admin-only surface (an admin operator managing compliance on behalf of any tenant), not a bypass of tenant scoping (there is no tenant scoping to bypass at this level, by design). |
| `app/jobs/compliance_sla.py` | SAME (`ComplianceRequest`, `ComplianceExport`) | Internal scheduled job, no HTTP surface | `TRUSTED_INTERNAL` — not reachable by any external caller; only mutates `status`/`sla_status`/`expires_at`-driven expiry, never `metadata_json`. |
| Privacy portal / DPDP routes elsewhere in the app | Searched — none found reaching `ComplianceRequest`/`ComplianceExport` outside the 3 routers above | n/a | `DISTINCT_MODEL` / not found |
| Generic media/storage routes | Not applicable — `ComplianceExport` has no storage/media reference to a shared media engine | n/a | `DISTINCT_MODEL` |
| Audit-log routes | `ComplianceAuditLog` is read via `admin_router.audit_trail` (`require_super_admin`, implicitly via `_svc`) | stronger persona | `ALTERNATE_PROTECTED` |

## Conclusion
No weaker same-record route was found. `customer_router.py` is
independently stronger (real column scoping); `admin_router.py` is
intentionally platform-wide and gated by the strongest available role.
This slice's fix to `provider_router.py` (the genuinely weakest surface
before this slice) closes the gap without requiring any change to either
alternate router.
