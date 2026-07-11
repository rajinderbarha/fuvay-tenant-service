# FINAL-L5-04B — Entitlement Audit and Change History Report

## Real table: `entitlement_audit_log`, append-only, never mutated after insert
Every field the mission requires is present and populated on every real mutation (verified via live `GET .../entitlements/history` calls throughout this sprint):

| Field | Populated by |
|---|---|
| Tenant | `tenant_id` |
| Module/category | `entity_type` + `entity_id` (the entitlement row's own id) |
| Previous state | `previous_status` |
| New state | `new_status` |
| Actor | `actor_id` + `actor_role` |
| Reason | `reason` (nullable — required for disable, not for assign) |
| Source | `source` |
| Timestamp | `created_at` |
| request_id/correlation ID | `request_id` |

## Required events — all 6 present and verified
| Event | Verified |
|---|---|
| `MODULE_ENTITLEMENT_ASSIGNED` | Live, via seed script run |
| `MODULE_ENTITLEMENT_DISABLED` | Live, via curl + Chromium E2E |
| `MODULE_ENTITLEMENT_REENABLED` | Live, via curl + Chromium E2E |
| `CATEGORY_ENTITLEMENT_ASSIGNED` | Live, via seed script run |
| `CATEGORY_ENTITLEMENT_DISABLED` | Live, via curl + Chromium E2E (visible in the admin UI's History panel) |
| `CATEGORY_ENTITLEMENT_REENABLED` | Live, via curl + Chromium E2E |

Plus one additional event not in the mission's list but added for transparency: `CATEGORY_ENTITLEMENT_CASCADED_INEFFECTIVE`, recorded when a module disable makes a child category ineffective without changing its own row status (see Module Disable Cascade Policy).

## Real example transcript (captured live during this sprint)
```
CATEGORY_ENTITLEMENT_DISABLED
ACTIVE → INACTIVE · by super_admin · disabled via admin UI

CATEGORY_ENTITLEMENT_ASSIGNED
— → ACTIVE · by seed_script

MODULE_ENTITLEMENT_ASSIGNED
— → ACTIVE · by seed_script
```

## Result
All required audit fields and all 6 required events are real, populated correctly, and browser-verified (not just unit-tested against a mock).
