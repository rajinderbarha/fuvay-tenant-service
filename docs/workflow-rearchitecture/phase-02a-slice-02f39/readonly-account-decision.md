# readonly@demo-ac-services.local — Decision Packet

| Field | Value |
|---|---|
| Current invalid role | `tenant_readonly` |
| Tenant | demo-ac-services (`5209ef33-a53e-4fc0-b3f6-006335b8d712`) |
| Existing purpose (from evidence) | Unknown beyond the role name itself — no invitation record, no staff/team-member profile, no assigned work |
| Login documentation | None found |
| UI expectations | None documented; would render whatever `TenantLayout` shows for an unrecognized role (untested) |
| Test expectations | None reference this account's role by name in any executable test |
| Current permissions | **Zero** — `tenant_readonly` is absent from `ROLE_PERMISSIONS` |
| Current access scope | N/A — role not recognized, so no scope applies |
| 7 real logins, 7 unrevoked sessions | Yes — real, active usage pattern, but zero non-login actions ever recorded |
| Candidate canonical roles | (a) `staff` — the only real option among the 10, but grants materially more than "read only" implies; (b) none — build a genuine tenant-side read-only role in a future architecture change; (c) deactivate and have the user re-request access |
| Privilege comparison | `staff`: real tenant-scoped operational permissions (job/booking/inventory access per `ROLE_PERMISSIONS['staff']`). No canonical role grants less than `staff` while still being tenant-scoped and non-empty. |
| Risk of (a) | Moderate — a real, active, unidentified user would receive a genuine capability increase based on assumption, not evidence |
| Risk of (b) | None to this account directly; defers the underlying product gap |
| Risk of (c) | Operational — cuts off active use without notice |
| Recommended choice | **None recommended by this investigation** — this is a product/architecture decision (does ServiceOS need a tenant-side read-only role), not a mapping this evidence can respons­ibly pick |
| Exact human decision required | "Does ServiceOS need a genuine tenant-side read-only role? If yes, design it (out of this slice's scope). If no, choose (a) map to `staff` accepting broader access, or (c) deactivate and re-onboard the real user." |

**Outcome: `MANUAL_ROLE_CONFIRMATION_REQUIRED`.**
