# Slice 2F-31 Approval Gate

## Final status: SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED

**Scoped to N01_media_assets only. This is not an application-wide security claim.**

## Coverage

| Metric | Before | After |
|---|---|---|
| Protected | 226 | **233** |
| Denominator | 259 | **262** |
| Unprotected | 33 | **29** |
| Canonical hash | fbe7cf863afa0d84 | af8388463ac3dbfa |
| Matrix hash | 753653ed32916f4e | 3066e137e9a23c19 |

c=7, a=3, h=0. 233=226+7+0. 262=259+3.

## Why BLOCKED, not fully closed

Two Set A routes and all three Set B routes could not be remediated because
doing so requires application files outside the frozen 2F-30 allow-list:

- `POST /v1/media/upload`, `POST /v1/media/{media_id}/replace` need a new
  scope-only guard (`app/core/permissions.py` - forbidden).
- All 3 Set B routes live in `app/engines/media/router.py` /
  `MediaService`, neither on the allow-list.

This is the correct, honest outcome of a strict scope discipline: the slice
does not silently widen its file allow-list to force a "closed" status.

## Quality gates

| Gate | Status |
|---|---|
| Set A/B/C counts and hashes verified before any change | MET |
| Every scoped route mounted | MET |
| Every Set A route has a final authority contract | MET |
| Every Set B route has a final adjudication | MET |
| Canonical roles/permissions unchanged; none added | MET |
| Mutation-capable access scope enforced (6/6 role-guarded routes) | MET |
| StaffPermission deny precedence / cross-tenant isolation | MET (unchanged) |
| Principal tenant server-derived on all Set A routes | MET |
| MediaAccessService ownership preserved and re-verified | MET |
| Object ID alone cannot authorize (delete_file scoped by tenant+id) | MET |
| Direct service calls fail closed | MET (no internal callers found; N/A) |
| Storage keys not client-authoritative for Set A | MET; PARTIAL for Set B (documented) |
| Foreign objects create no oracle | MET |
| Metadata/keys/signed tokens remain private | MET (unchanged) |
| Database/storage consistency proven or honestly blocked | HONESTLY BLOCKED (documented, not proven) |
| Set C unchanged | MET |
| M01 does not regress | MET |
| Only Set A + included Set B canonical rows changed | MET |
| Coverage arithmetic exact | MET |
| No unrelated held candidate added | MET |
| No role/permission/migration added | MET |
| Every verifier condition has an executed fixture | MET |
| Full suite green | MET (2290 passed) |

## Honest notes

- **The critical scope finding**: Set B's router is not on the allow-list.
  Rather than either silently expanding scope or blocking the entire slice, I
  completed the 9-route Set A work that WAS in scope, fully adjudicated Set B
  with evidence, added it to the canonical inventory honestly as UNPROTECTED,
  and documented the exact reason remediation could not proceed.
- **A classifier discrepancy was found and corrected**, not hidden: my initial
  canonical write used `TENANT_MUTATION_ROLE_SCOPE_AWARE`; the live classifier
  resolves the new guard to `STAFF_EXECUTION_ROLE_SCOPE_AWARE`. Both are
  "protected", so coverage arithmetic was never wrong, but the recorded status
  now matches what the tooling actually verifies.
- **Database/storage atomicity is explicitly NOT proven** - stated plainly
  rather than assumed, per Workstream 11's permitted "accepted inconsistency"
  outcome.
- 29 canonical unprotected routes remain overall. No next module selected.

Stopping at the Slice 2F-31 approval gate.
