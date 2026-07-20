# Demo Account Investigation — Slice 2F-38

No new investigation was performed this slice beyond confirming the prior
evidence still applies unchanged. Full original investigation:
`docs/workflow-rearchitecture/phase-02a-slice-02c/affected-account-investigation.md`
and `remediation-decision-register.md` (present, unmodified, committed on
this branch — confirmed by hash match against the recovery branch).

## Summary of prior evidence (not re-derived, cited)

| Field | manager@demo-ac-services.local | readonly@demo-ac-services.local |
|---|---|---|
| User ID | `72640932-ef3c-4ce5-92a1-6609bff35ee0` | `05deaee8-03f2-40f9-8af6-2f21892c075f` |
| Tenant | demo-ac-services | demo-ac-services (same tenant) |
| Current (invalid) role | `tenant_manager` | `tenant_readonly` |
| Logins | 0 | 7 (real, spanning 2026-07-11 to 2026-07-13) |
| Unrevoked sessions | 0 | 7 |
| Audit records | 0 | 7 (all `login.success`) |
| Effective permissions today | 0 (role absent from `ROLE_PERMISSIONS`) | 0 (same) |
| Evidence basis for any mapping | Only `full_name`="Tenant Manager" + email local-part — explicitly insufficient per the brief's own rule against name-similarity inference | None — no canonical role represents "tenant-side read-only" at all |

No later slice (2D through 2F-37R-A) produced additional evidence or a
different conclusion. This slice re-confirms both remain
`MANUAL_ROLE_CONFIRMATION_REQUIRED`.
