# Runtime Verification Report — Slice 2F-23

## Method
`scripts/workflow_rearchitecture/inventory_mutation_routes.py::walk()` run
against the fully mounted application (`app.main:app`). Total live
POST/PUT/PATCH/DELETE routes: **1186** — consistent with the figure 2F-17A
established, confirming the inventory remains complete.

## All 19 remaining routes: MOUNTED, endpoint confirmed, genuine mutation

| Live guard_status | Count | Routes |
|---|---|---|
| `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` | 6 | `submit_reply`, `flag_review`, `provider_run_report`, `generate_launch_campaign`, `submit_campaign_review`, `update_asset_provider_notes` |
| `PERMISSION_ONLY_NOT_SCOPE_AWARE` | 13 | 6 media profile routes, 3 profile routes, 4 admin_catalog routes |

Zero routes reported a VERIFIED guard_status, so no stale
already-protected row exists.

## The 6 zero-authorization routes

Their entire dependency chain is `get_current_user | get_db`. There is no
role check and no permission check, so **any** authenticated principal —
including `customer` and `technician` — can invoke them. This was previously
recorded in the canonical CSV as the vague `UNVERIFIED`; it is now recorded
precisely.

## The 13 `require_technician` routes

`require_technician` admits `technician`, `staff`, `tenant_owner`,
`super_admin` (read directly from `app/dependencies/auth.py:206`). It is
therefore a broad tenant-side role gate with no access-scope awareness. The
notable consequences, verified in source:

- A **technician** can rewrite the tenant business profile — legal name, GST
  number, address, contact (`update_business_profile`).
- A **technician** can replace or delete the tenant business logo and shop
  photo (`media.new_router`).

These are persona-scope gaps, not IDOR: media ownership is enforced by the
access-policy layer, and the profile schema is a strict allow-list.

## Vocabulary note (documented, not "corrected")

The canonical CSV records 13 of these rows as
`ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE` while the runtime tool computes
`PERMISSION_ONLY_NOT_SCOPE_AWARE`. Both denote "unprotected" and neither is
in the VERIFIED set, so coverage is unaffected. The two labels come from
different eras of the tooling vocabulary; they were **not** rewritten,
because there is no evidence either is wrong — only that they differ. Doing
so would be churn without row-level evidence. Recorded in
`documentation-corrections.md`.

## Exit conditions

| Condition | Result |
|---|---|
| Any remaining row not mounted | NO — all 19 mounted |
| Any row unclassified / UNKNOWN / UNVERIFIED | NO — zero remain (6 corrected) |
| Any row with more than one persona | NO |
| Any row with more than one primary gap | NO |
| Any row in more than one module | NO |
| Duplicate canonical route keys | NO |
| Non-tenant path in the remaining set | NO |
| Recorded guard_status disagreeing with live walk | NO — asserted per row |
| Selected route not mounted | NO — both mounted |
| Application authorization behavior changed | NO — no `app/` file modified |

**Runtime verification exits zero.**

## Test-suite exit code
`tests/test_phase2f23_remaining_queue_reconciliation_and_selection.py` —
**38 passed**, exit 0.
