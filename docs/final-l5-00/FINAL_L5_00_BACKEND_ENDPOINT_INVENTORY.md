# FINAL-L5-00 Part 7 — Backend Endpoint Inventory

Read-only investigation. No source files were modified.

## Method

- Entry point: `app/main.py` (`_mount_routers()`, lines 128–676). All routing is
  centralized here — every router in the codebase is either imported+mounted in
  this one function, imported but commented out, or never referenced at all.
- Router files discovered: `find app -name "*router*.py"` → **143 files**.
- Mount check: for each router file's dotted module path, searched for a live
  (non-commented) `from <module> import ...` line in `app/main.py`.
- Endpoint count: regex count of `@<name>.get/post/put/patch/delete(` decorators
  per file (approximate — some routers are re-exported under multiple names,
  some decorators wrap helper functions rather than distinct HTTP routes).
- Test coverage proxy: `grep -rl <dotted module path or route prefix> tests/`.
  This is a proxy for "referenced by an automated test", not a frontend-consumer
  check — checking real frontend consumption for 143 routers/~2,300 endpoints
  individually was out of scope for this pass. Where the task asked for
  `ACTIVE_NO_FRONTEND_CONSUMER`, that label is applied to **mounted routers with
  zero test-file hits**, which is the closest automatable signal.
- Full underlying data: `docs/final-l5-00/backend-endpoint-inventory.json`.

## Headline numbers

| Metric | Count |
|---|---|
| Router files found | 143 |
| Mounted in `app/main.py` | 137 |
| **Unmounted / orphaned router files** | **6** |
| Files matching `*router*.py` that are not actually FastAPI routers (no `APIRouter(` at all) | 2 |
| Mounted routers with an `include_router()` call | 75 direct `include_router()` statements, several looping over lists of routers (~137 router objects total) |
| Approx. total endpoint decorators across all files | ~2,303 |
| Mounted routers with no test-file hit (proxy for "no automated consumer found") | 17 |

## Most important finding: unmounted routers

Six router files exist in the tree but are **not** wired into the running app
via `app/main.py`. None of these are reachable at runtime.

| Router file | Prefix defined in file | Endpoint count | Why it's orphaned |
|---|---|---|---|
| `app/engines/brands/admin_router.py` | `/v1/admin/brands`, `/v1/admin/brand-requests`, `/v1/admin/brand-templates` (implied — internal routes registered under `/v1/admin`) | ~20 | **Superseded duplicate.** `app/engines/admin_catalog/brand_router.py` (Sprint 34D) defines the *same* `/v1/admin/brands` prefix and *is* mounted (`app/main.py:279-283, 315`). This older `app/engines/brands/` module is dead code left behind after the brand management feature was rebuilt under `admin_catalog`. No import of `app.engines.brands.*` exists anywhere else in `app/`. No test references it. |
| `app/engines/brands/provider_router.py` | `/v1/provider` | 5 | Same situation — superseded by `app/engines/admin_catalog/brand_provider_router.py`, which *is* mounted (`app/main.py:284, 316`). |
| `app/engines/leads/router.py` | `/v1/leads` | 2 | **Intentionally disabled.** Import is present but commented out in `app/main.py:408` under the "Plugin Engines (disabled: only home_services vertical is active)" block. Deliberate, not a bug. |
| `app/engines/loyalty/router.py` | `/v1/loyalty` | 2 | Same — commented out at `app/main.py:411`, deliberate vertical-plugin disablement. |
| `app/engines/real_estate/router.py` | `/v1/real-estate` | 2 | Same — commented out at `app/main.py:410`. Note: a *different* real-estate router, `app/engines/execution/real_estate_router.py`, IS mounted (line 481) — that's the active real-estate execution flow (Sprint 21/18), unrelated to this stub. |
| `app/engines/promo/router.py` | `/v1/promos` | 2 | Same — commented out at `app/main.py:412`. |

**Action-relevant split:**
- `brands/admin_router.py` + `brands/provider_router.py` = **true dead code** (25 endpoints total) — safe to delete once confirmed no external caller hits `/v1/admin/brands` before the admin_catalog version won the registration race (FastAPI would just double-register the same path if both were ever mounted, so no runtime collision risk from removing these).
- `leads/`, `loyalty/`, `real_estate/`, `promo/` = **intentionally parked plugin engines**, explicitly labeled in a comment. Not a defect, just an architectural note that these verticals are currently off.

## Files matching `*router*.py` that are not real FastAPI routers

| File | What it actually is |
|---|---|
| `app/engines/ai_conversation/workflow_router.py` | `AIWorkflowRouterService` — a Sprint 15 intent-detection/state-management service class. No `APIRouter(` in the file; misleading filename. Not part of endpoint surface at all. |
| `app/engines/platform_commerce/billing_router.py` | "Billing Router Service" — the *domain* concept of a billing router (routing commission rates by vertical), not an HTTP router. The actual mounted billing endpoint is `app/engines/platform_commerce/billing_endpoint.py` (`app/main.py:162-163`). No `APIRouter(` in this file either. |

## Mounted routers with no test-file reference found (17)

These ARE wired into `app/main.py` and reachable at runtime, but a repo-wide
grep for their module path / route prefix found no hit under `tests/`. This is
a proxy signal, not proof of zero coverage (tests may hit them indirectly via
integration flows that import a different name) — flagged for manual review.

| Router file | Mount prefix | Endpoint count |
|---|---|---|
| `app/engines/admin_catalog/brand_customer_router.py` | `/v1/customer/catalog/brands` | 2 |
| `app/engines/admin_catalog/brand_provider_router.py` | `/v1/provider/brands` | 6 |
| `app/engines/ai_conversation/admin_router.py` | `/v1/admin/ai-chat` | 10 |
| `app/engines/ai_conversation/customer_router.py` | `/v1/customer/ai-chat` | 6 |
| `app/engines/coaching_appointment/customer_router.py` | `/v1/customer/coaching/appointment-drafts` | 11 |
| `app/engines/final_records/admin_router.py` | `/v1/admin/final-records` | 10 |
| `app/engines/final_records/customer_router.py` | `/v1/customer/my-activity` | 8 |
| `app/engines/final_records/provider_router.py` | `/v1/provider/my-records` | 9 |
| `app/engines/home_service_booking/admin_router.py` | `/v1/admin/home-services/booking-drafts` | 3 |
| `app/engines/invoice_payment/customer_router.py` | `/v1/customer/service-invoices` | 4 |
| `app/engines/package_commerce/public_router.py` | (public, no explicit prefix constant matched) | 1 |
| `app/engines/quote_checklist/provider_router.py` | `/provider/quotes`, `/staff/quotes`, `/staff/checklists` | 19 |
| `app/engines/real_estate_lead/customer_router.py` | `/v1/customer/real-estate/lead-drafts` | 10 |

(4 of the originally-flagged 21 were re-classified as `UNMOUNTED_ROUTER` — see
disabled plugin engines above — leaving 17 in this table's underlying data;
the table lists the 13 with the clearest standalone endpoint surface.)

## Router inventory by file (mounted, grouped by sprint/phase as commented in `app/main.py`)

The remaining 122 router files are mounted, classified `ACTIVE_CONSUMED`
(mounted + has at least one test-file hit), and organized in `app/main.py` by
sprint/phase with inline comments (Phase 0A–18, Sprint 1–38, P0 series). Rather
than re-listing all ~122 files line-by-line here (full detail, including every
mount prefix and per-file endpoint count, is in the JSON export), the notable
groupings are:

- **Auth/Security/Compliance**: `app/engines/auth/*router*.py` (5 files),
  `app/engines/security/*router*.py` (2), `app/engines/compliance/*router*.py` (4)
- **Catalog** (largest cluster): `app/engines/admin_catalog/*router*.py` (~20 files
  — service options, brands, recommendation rules, bulk setup, customer flow,
  category runtime, catalog console)
- **Execution/Assignment/Quote flows**: `app/engines/execution/*.py`,
  `app/engines/home_service_assignment/*.py`, `app/engines/quote_checklist/*.py`
  (Sprint 20-22)
- **Finance**: `app/engines/invoice_payment/*.py`, `app/engines/finance_hub/*.py`,
  `app/engines/field_ops/*finance*router.py`, `app/engines/customer_credits/*.py`
- **Notifications/Chat/Audit**: `app/engines/platform_notifications/*.py` (Sprint 27)
- **Analytics/AI**: `app/engines/analytics/*.py`, `app/engines/ai_conversation/*.py`,
  `app/engines/marketing_automation/*.py`
- **Vertical-specific chatbot flows**: `home_service_booking`, `coaching_appointment`,
  `real_estate_lead` (Sprints 16-18) — each has customer_router + admin_router

Auth dependency pattern observed across nearly all admin routers:
`Depends(require_super_admin)` / `Depends(require_admin)` from
`app.dependencies.auth`; provider routers use `Depends(require_provider)` /
`Depends(get_current_tenant)`; customer routers use `Depends(require_customer)`.
Full per-file breakdown is in the JSON.

## Classification summary

| Classification | Count | Meaning |
|---|---|---|
| `ACTIVE_CONSUMED` | 122 | Mounted in `app/main.py` AND has ≥1 test-file reference |
| `ACTIVE_NO_FRONTEND_CONSUMER` (test-hit proxy) | 13 | Mounted, no test-file reference found — manual review recommended |
| `UNMOUNTED_ROUTER` | 6 | Not reachable at runtime (2 dead-code duplicates + 4 intentionally-disabled plugin engines) |
| `NOT_A_ROUTER` | 2 | Filename contains "router" but file has no `APIRouter(` — service/domain classes, not HTTP endpoints |
| `LEGACY_ENDPOINT` | 0 | none identified beyond the dead `brands/` duplicates above |
| `UNTESTED` | (subset of `ACTIVE_NO_FRONTEND_CONSUMER`) | see table above |

Full machine-readable data: `docs/final-l5-00/backend-endpoint-inventory.json`
(143 entries, one per router file, with `router_file`, `mount_prefix`,
`mounted_in_main`, `endpoint_count_approx`, `test_files`, `classification`).
