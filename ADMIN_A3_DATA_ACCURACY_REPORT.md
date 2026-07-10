# Admin A3 — Data Accuracy Report

## Method
Live curl calls against the real running backend (port 8000), cross-
checked against direct Postgres queries (`psql -U postgres -d serviceos`),
using the single real seeded tenant "Demo AC Services"
(`34b427a7-b2be-496c-b826-6d51bb181248`).

## Checks performed
| Field | Frontend/API value | DB value | Match |
|---|---|---|---|
| status | pending_setup | `tenants.status='pending_setup'` | ✅ |
| verification_status | pending | `tenants.verification_status='pending'` | ✅ |
| vertical | home_services | `tenants.vertical='home_services'` | ✅ |
| Usage Credit Balance | matches ledger sum | `platform_commerce` usage-credit ledger for tenant | ✅ |
| Security Deposit Held | matches deposit table | `package_commerce` security_deposit row | ✅ |
| Audit log entries | matches `TenantAuditLog` count | direct row count query | ✅ |
| Activity feed (post-fix) | new admin_note_added event present | `platform_audit_logs` row confirmed | ✅ (fixed this sprint) |

## Bug found via this cross-check
Before the fix, admin tenant mutations produced `TenantAuditLog` rows but
zero corresponding `platform_audit_logs` rows — a real, confirmed data-
accuracy defect (audit trail incomplete platform-wide). Fixed and
re-verified as above.

## Note on scale
Only one real tenant exists in the dev database, so pagination/sort/
filter correctness at scale could not be live-verified beyond code
inspection (server-side SQL confirmed correct via reading
`admin_service.py`'s query-building logic, but not exercised against a
multi-row dataset).

## Verdict
All spot-checked fields match the real database exactly. One real defect
found and fixed. Scale-testing limited by single-tenant dev data
(documented, not a regression).
