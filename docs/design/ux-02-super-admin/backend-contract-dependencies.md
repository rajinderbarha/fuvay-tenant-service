# Backend Contract Dependencies

Every non-`READ_ONLY_READY`/`PRODUCTION_READY` UX-02 page depends on a backend contract that is
either unconfirmed or known partial. Frontend-only phase — no backend code was written or changed.

| Area | Depends on | Status |
|---|---|---|
| Tenant List/360 core fields | `admin_catalog/tenant_service` | Confirmed real engine (existing routes read from it today). |
| Verification Review | onboarding engine's applicant/document/checklist model | Existing `app/admin/onboarding/providers/page.tsx` proves the route exists; document secure-preview token mechanism not independently re-verified this phase. |
| Compliance cases | a dedicated compliance-case table/engine | Existing `app/admin/compliance/page.tsx` route exists; whether it matches the `ComplianceCaseFixture` shape 1:1 was not verified (frontend-only phase, no backend read performed beyond route existence). |
| Security observations | unified security-telemetry/detection pipeline | No confirmed single endpoint; `SECURITY_CONTRACT_PENDING` reflects this directly. |
| Audit Explorer | structured, cross-engine audit-entry emission | `app/admin/audit-logs/page.tsx` exists but coverage across every engine is not confirmed uniform. |
| Global Search | any unified cross-domain search endpoint | None found. `API_CONTRACT_REQUIRED`. |
| Platform Configuration | a settings read/write API with change-history | Not confirmed to exist in the shape needed (current value + last-changed-by/when + history). `PRODUCT_DECISION_REQUIRED`. |
| Finance presentation | `finance_hub`, `package_commerce`, tenant `commissionRateBps`/deposit fields | Existing finance routes exist; exact field names for commission/deposit were not independently re-derived from backend models this phase (fixture field names are a best-effort mirror, not guaranteed 1:1). |

No backend endpoint was modified, added, or called by this phase — all of the above is presentation
design against typed fixtures, pending real contract confirmation before wiring.
