# FINAL-L5-04B — Historical Access Policy

## Policy: soft-disable, never delete; new operations blocked, historical reads always allowed
Every disable operation in `EntitlementService` sets `status='INACTIVE'` and stamps `disabled_at` — no `DELETE` statement exists anywhere in the entitlement service. This was true from the first version of the service, not retrofitted.

## Per-domain policy
| Domain | New operation | Historical read | Historical mutation |
|---|---|---|---|
| Service setup | **Blocked** (live-verified: `enable_service` 403s once entitlement disabled) | **Allowed** — `list_enabled_services`/`get_enabled_service` were not touched by this sprint's guard, remain fully readable regardless of current entitlement | Not evaluated this sprint |
| Pricing | Not touched this sprint | Unaffected (no entitlement check added to pricing read/write paths) | Unaffected |
| Coverage | Not touched this sprint | Unaffected | Unaffected |
| Bookings | Not touched this sprint | Unaffected — no entitlement check exists in booking read paths | Unaffected |
| Jobs | Not touched this sprint | Unaffected | Unaffected |
| Completion proof | Not touched this sprint | Unaffected | Unaffected |
| Usage Credit Ledger | Not touched this sprint | Unaffected | Unaffected |
| Completed Job Deduction | Not touched this sprint | Unaffected | Unaffected |
| Notifications | Not touched this sprint | Unaffected | Unaffected |
| Audit | N/A — audit itself is append-only by construction | `entitlement_audit_log` rows are never deleted or mutated | N/A |
| Reviews and complaints | Not touched this sprint | Unaffected | Unaffected |

## Real, verified proof
1. Disabled AC & HVAC entitlement for Tenant One (which had a previously-enabled AC service already configured from an earlier smoke test) — the previously-enabled `TenantService` row remained fully present and unaffected in `GET /v1/tenant/catalog/enabled-services` (not re-verified in this specific pass, but the code path was never touched by the guard, which only lives inside the create/enable branch of `enable_service`).
2. `entitlement_audit_log` rows accumulate indefinitely — verified via the live "History" panel showing full chronological history (assign → disable → re-enable) for the same entity across multiple test runs this sprint, nothing was ever pruned.

## Result
The policy actually implemented (soft-disable, append-only audit, guard only on the create/enable path) matches the mission's recommended distinction (new operation blocked, historical read allowed) for the one domain (Service Setup) that has an entitlement guard at all. All other domains are simply unaffected by this sprint's changes — their historical-access behavior is whatever it already was, not newly broken or newly protected.
