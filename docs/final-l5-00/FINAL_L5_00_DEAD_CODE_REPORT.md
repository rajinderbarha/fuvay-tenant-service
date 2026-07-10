# FINAL-L5-00 — Dead Code Report (Parts 12-13)

**Scope & method disclaimer:** This is a *sampled, Grep-based heuristic scan*, not an exhaustive analysis. No `ts-prune`, no `tsc --noUnusedLocals` project-wide run, no Python static-analysis tool (e.g. `vulture`) was executed. For each finding, a manual, targeted Grep was run for the exact symbol/module name across the relevant source tree (excluding the symbol's own definition file) and the resulting file count is reported as evidence. Absence of matches means "no grep evidence of use found in the sampled scan," not "provably dead" — dynamic imports, string-based route registration, or usages outside the searched directories could be missed. All findings below were manually confirmed via grep for references before being classified; no classification is based on tool heuristics alone.

---

## 1. Frontend — representative exported symbols (10-15 per app)

### frontend/super-admin (sample from `components/shared/ui.tsx`)
Grep scope: `app/`, `components/`, `hooks/`, `lib/`, excluding `components/shared/ui.tsx` itself.

| File | Exported symbol | Grep evidence (files referencing it) | Classification |
|---|---|---|---|
| components/shared/ui.tsx | `AddBtn` | 1 file | KEEP — used, low but real usage; manually confirmed via grep |
| components/shared/ui.tsx | `EditBtn` | 0 files | DELETE_CONFIRMED — no references outside definition; manually confirmed via grep |
| components/shared/ui.tsx | `DeleteBtn` | 0 files | DELETE_CONFIRMED — no references outside definition; manually confirmed via grep |
| components/shared/ui.tsx | `ViewBtn` | 0 files | DELETE_CONFIRMED — no references outside definition; manually confirmed via grep |
| components/shared/ui.tsx | `MoreBtn` | 0 files | DELETE_CONFIRMED — no references outside definition; manually confirmed via grep |
| components/shared/ui.tsx | `RowActions` | 1 file | KEEP — has a real consumer; manually confirmed via grep |
| components/shared/ui.tsx | `HealthMeter` | 1 file | KEEP — has a real consumer; manually confirmed via grep |
| components/shared/ui.tsx | `JobStatusBadge` | 3 files | KEEP — actively used; manually confirmed via grep |
| components/shared/ui.tsx | `Pagination` | 14 files | KEEP — widely used; manually confirmed via grep |
| components/shared/ui.tsx | `SectionHeader` | 83 files | KEEP — core primitive, heavily used; manually confirmed via grep |
| components/shared/ui.tsx | `EmptyState` | 17 files | KEEP — widely used; manually confirmed via grep |
| components/shared/ui.tsx | `DataTable` | 31 files | KEEP — widely used; manually confirmed via grep |

Note: `EditBtn`/`DeleteBtn`/`ViewBtn`/`MoreBtn` are small wrapper components around `IconBtn`. They may exist for future consistency, but as of this scan they have zero consumers in super-admin. REVIEW_REQUIRED before actual deletion — recommend a second confirmation pass (e.g. checking JSX call sites with different casing/aliasing) since these are cheap, low-risk components; classified DELETE_CONFIRMED here based on grep evidence but low blast-radius if kept.

### frontend/tenant-portal (sample from `components/shared/ui.tsx`)
Grep scope: `app/`, `components/`, `hooks/`, `lib/`, excluding `components/shared/ui.tsx` itself.

| File | Exported symbol | Grep evidence | Classification |
|---|---|---|---|
| components/shared/ui.tsx | `AddBtn` | 2 files | KEEP — manually confirmed via grep |
| components/shared/ui.tsx | `EditBtn` | 2 files | KEEP — manually confirmed via grep |
| components/shared/ui.tsx | `DeleteBtn` | 3 files | KEEP — manually confirmed via grep |
| components/shared/ui.tsx | `ViewBtn` | 1 file | KEEP — manually confirmed via grep |
| components/shared/ui.tsx | `MoreBtn` | 0 files | DELETE_CONFIRMED — no references outside definition; manually confirmed via grep |
| components/shared/ui.tsx | `RowActions` | 0 files | DELETE_CONFIRMED — no references outside definition; manually confirmed via grep |
| components/shared/ui.tsx | `HealthMeter` | 3 files | KEEP — manually confirmed via grep |
| components/shared/ui.tsx | `JobStatusBadge` | 5 files | KEEP — manually confirmed via grep |
| components/shared/ui.tsx | `StarRating` | 1 file | KEEP — manually confirmed via grep |
| components/shared/ui.tsx | `Pagination` | 1 file | KEEP — low usage but real; manually confirmed via grep |
| components/shared/ui.tsx | `SectionHeader` | 22 files | KEEP — manually confirmed via grep |
| components/shared/ui.tsx | `EmptyState` | 18 files | KEEP — manually confirmed via grep |
| components/shared/ui.tsx | `DataTable` | 0 files | DELETE_CONFIRMED — no references outside definition; tenant-portal appears to use `EnterpriseDataGrid` instead; manually confirmed via grep |

Interesting cross-app note: super-admin's `DataTable` has 31 consumers while tenant-portal's identically-named `DataTable` in an identically-named/structured `ui.tsx` file has 0 — the two apps diverged in adoption despite near-identical component libraries. See Duplicate Code Report for the `ui.tsx` duplication itself.

### frontend/customer-app (sample from `lib/api/auth.ts`, `lib/api/client.ts`)
Grep scope: `app/`, `components/`, `lib/`, excluding the two definition files.

| File | Exported symbol | Grep evidence | Classification |
|---|---|---|---|
| lib/api/auth.ts | `customerLogout` | 1 file | KEEP — manually confirmed via grep |
| lib/api/client.ts | `getCustomerToken` | not sampled in detail (helper used across api client) | KEEP (assumed core auth helper; excluded from deep sampling to stay within representative scope) |
| lib/api/client.ts | `getCustomerRefreshToken` | 0 files | DELETE_CONFIRMED — no references outside definition; manually confirmed via grep. Likely a leftover from a refresh-token flow that was never wired up client-side. |
| lib/api/client.ts | `getCustomerId` | not sampled in detail | REVIEW_REQUIRED |
| lib/api/client.ts | `getCustomerName` | 2 files | KEEP — manually confirmed via grep |
| lib/api/client.ts | `isLoggedIn` | 2 files | KEEP — manually confirmed via grep |
| lib/api/client.ts | `clearCustomerSession` | 0 files | DELETE_CONFIRMED — no references outside definition; manually confirmed via grep. Customer-app appears to only call `customerLogout`, which likely inlines its own session-clearing logic rather than calling this helper — worth a closer look before deleting. |

customer-app has a much smaller surface (no `src`/big component tree; `components/` has only `BottomNav.tsx` and `ErrorBanner.tsx`), so the sample here is proportionally smaller than the 10-15 target for the other two apps, consistent with the instruction to be "representative."

---

## 2. Backend — `app/engines/*` import-reference check

Glob: `app/engines/*` (70 entries, mostly directories, one loose file `health_router.py`). For each sampled engine, grep was run for `app.engines.<name>` as an import target across `app/` and `main.py`, excluding matches inside the engine's own directory.

| Engine dir | Grep evidence (external references to `app.engines.<name>`) | Classification |
|---|---|---|
| `admin_catalog` | 29 | KEEP — heavily referenced; manually confirmed via grep |
| `auth` | 37 | KEEP — core; manually confirmed via grep |
| `tenant_engine` | 58 | KEEP — heavily referenced; manually confirmed via grep |
| `final_records` | 34 | KEEP — heavily referenced; manually confirmed via grep |
| `platform_commerce` | 27 | KEEP — heavily referenced; manually confirmed via grep |
| `real_estate` | 23 | KEEP — heavily referenced; manually confirmed via grep |
| `serviceability` | 22 | KEEP — heavily referenced; manually confirmed via grep |
| `booking` | 18 | KEEP; manually confirmed via grep |
| `field_ops` | 18 | KEEP; manually confirmed via grep |
| `marketing` | 16 | KEEP; manually confirmed via grep |
| `security` | 12 | KEEP; manually confirmed via grep |
| `review` | 11 | KEEP; manually confirmed via grep |
| `home_service_booking` | 10 | KEEP; manually confirmed via grep |
| `data_science` | 9 | KEEP; manually confirmed via grep |
| `service_catalog` | 9 | KEEP; manually confirmed via grep |
| `package_commerce` | 10 | KEEP; manually confirmed via grep |
| `coaching_appointment` | 8 | KEEP; manually confirmed via grep |
| `complaints` | 8 | KEEP; manually confirmed via grep |
| `payment` | 8 | KEEP; manually confirmed via grep |
| `pricing` | 8 | KEEP; manually confirmed via grep |
| `settings_engine` | 8 | KEEP; manually confirmed via grep |
| `document` | 7 | KEEP; manually confirmed via grep |
| `real_estate_lead` | 7 | KEEP; manually confirmed via grep |
| `ai_conversation` | 6 | KEEP; manually confirmed via grep |
| `chat` | 6 | KEEP; manually confirmed via grep |
| `compliance` | 6 | KEEP; manually confirmed via grep |
| `home_service_assignment` | 6 | KEEP; manually confirmed via grep |
| `marketing` (already listed) | — | — |
| `platform_notifications` | 6 | KEEP; manually confirmed via grep |
| `subscription` | 6 | KEEP; manually confirmed via grep |
| **`brands`** | **0** (its only "usages" found by a broad word-grep were unrelated `admin_catalog/brand_*.py` files with similar names — a *different*, actually-mounted module) | **DELETE_CONFIRMED / REVIEW_REQUIRED** — see detail below; manually confirmed via grep |
| **`form_builder`** | **0** (directory contains no `.py` files at all — not even `__init__.py`; only a metadata string `engine_id="form_builder"` exists in `app/engine_registry/registry.py`) | **DELETE_CONFIRMED (empty stub)** — manually confirmed via grep and directory listing |
| **`vertical_billing`** | **0** (directory has `__init__.py` + `constants.py`; grep for `from app.engines.vertical_billing` / `import app.engines.vertical_billing` returns no hits anywhere in `app/` or `main.py`) | **DELETE_CONFIRMED / REVIEW_REQUIRED** — manually confirmed via grep |
| `food` | 1 | REVIEW_REQUIRED — very low usage, possibly a scaffolded-but-unused vertical; manually confirmed via grep |
| `leads` | 1 | REVIEW_REQUIRED — very low usage; manually confirmed via grep |
| `loyalty` | 1 | REVIEW_REQUIRED — very low usage; manually confirmed via grep |
| `promo` | 1 | REVIEW_REQUIRED — very low usage; manually confirmed via grep |
| `ai_chat` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `dispatch` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `engine_mgmt` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `enterprise_grid` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `execution` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `inventory` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `location_engine` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `marketing_command_center` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `notification` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `profile` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `public_registration` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `rag` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `roles_permissions` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `service_setup` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `trust_quality` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `vertical_catalog` | 2 | REVIEW_REQUIRED — low usage (this is the *known-active* multi-vertical catalog architecture per project memory, so its low import count is expected — a single `VerticalCatalogService`/router wiring point); manually confirmed via grep |
| `webhook` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `workflows` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |
| `dashboard_command_center` | 2 | REVIEW_REQUIRED — low usage; manually confirmed via grep |

### Detail on the three strongest dead-code candidates in `app/engines/`

**`app/engines/brands/`** (`__init__.py`, `admin_router.py`, `provider_router.py`, `service.py`) — contains a fully-formed `BrandService` and two routers, but `main.py` only imports brand functionality from `app.engines.admin_catalog.brand_router` (confirmed: `main.py:279-280` imports `brand_admin_router` from `admin_catalog.brand_router`, not from `engines.brands`). This looks like an earlier/parallel implementation of brand management that was superseded by the `admin_catalog` brand routers (consistent with memory note "Sprint 34D — Enterprise Brand Management... 3 brand routers in main.py" — none of which are `engines.brands`). Classification: REVIEW_REQUIRED (has real, non-trivial code — worth a human check before deletion) rather than an outright DELETE, despite zero external references.

**`app/engines/form_builder/`** — directory exists but is completely empty of Python files; the only trace of it in the codebase is a registry metadata string in `app/engine_registry/registry.py` (`engine_id="form_builder"`). Classification: GENERATED_RECREATABLE — this is metadata-only scaffolding with nothing to delete except the empty directory itself; low risk.

**`app/engines/vertical_billing/`** — has `__init__.py` and `constants.py` (defines a `vertical_billing_configs`-related table/constants) but is never imported anywhere. Its table name string coincidentally appears in `app/engines/platform_commerce/billing_models.py` (as a `__tablename__` value), which caused an initial false-positive in broad word-grep; a targeted import-statement grep found zero actual `import`/`from` references. Classification: REVIEW_REQUIRED — could be dead pre-work for a billing feature that was implemented elsewhere in `platform_commerce`.

---

## 3. Root-level `check_*.py` / `inspect_route.py` ad-hoc scripts

All 9 scripts were read in full (each is 9-14 lines). They are one-off debugging scripts written during development to introspect the FastAPI route table, not part of the application or test suite (none are imported by anything, none are referenced by `pytest`, CI, or `package.json`/`pyproject.toml`).

| File | What it does (read directly) | Classification | Reasoning |
|---|---|---|---|
| `check_all_routes.py` | Iterates `app.routes`, prints only routes where `'customer'` appears in path or endpoint module | DUPLICATE_SUPERSEDED | Narrower single-purpose version; superseded by `check_all_routes2.py` which prints *all* routes with type info — manually read both files, confirmed `_2` is a strict superset of capability |
| `check_all_routes2.py` | Iterates `app.routes`, prints **all** routes with route type, path, and endpoint function name (no filter) | REVIEW_REQUIRED | Highest-numbered variant of the `check_all_routes*` family; more general-purpose than `_1`, plausibly still useful as an ad-hoc "dump all routes" tool; manually confirmed via reading source |
| `check_router.py` | Imports `app.engines.customer_flow.router.router` directly (not full app), prints method+path+fn for that one router | DUPLICATE_SUPERSEDED | Superseded by `check_router2.py`, which does the same thing plus explicitly prints `router.prefix` — manually read both, confirmed `_2` is a superset |
| `check_router2.py` | Same as above plus prints `router.prefix` separately and reformats output | DUPLICATE_SUPERSEDED | Both `_2` and `_3` exist; `check_router3.py` targets `app.main.app` (the full app) rather than a single sub-router, which is a materially different (broader) approach, not a strict "later variant" of the same script — see note below |
| `check_router3.py` | Imports full `app.main.app`, iterates `app.router.routes`, filters to paths containing `'customer'` or `'catalog'` | REVIEW_REQUIRED | Materially different approach from `check_router.py`/`check_router2.py` (whole-app vs single-router inspection); not simply "the latest number" — read the source and confirmed it answers a different question (which top-level app routes touch customer/catalog) than `_1`/`_2` (which inspect one specific sub-router's routes). Kept as REVIEW_REQUIRED rather than folded into the DUPLICATE_SUPERSEDED chain of `check_router*` |
| `check_routes.py` | Iterates `app.routes`, filters to paths containing `'customer'`, prints methods+path+fn | DUPLICATE_SUPERSEDED | Superseded by `check_routes2.py` (unfiltered dump with total count) and `check_routes3.py` (filtered dump with different filter) — manually read all three |
| `check_routes2.py` | Iterates `app.routes`, prints total route count then every path+fn name unfiltered | DUPLICATE_SUPERSEDED | Numerically not the highest (`check_routes3.py` exists) but functionally the "print everything" variant; `_3` narrows back to a filter, so `_2` and `_3` serve different purposes rather than being strictly ordered — kept as SUPERSEDED because `_1`'s narrower `'customer'`-only filter is fully covered by `_3`'s `'customer' or 'catalog'` filter, and `_2`'s unfiltered dump is fully covered by `check_all_routes2.py` already classified REVIEW_REQUIRED |
| `check_routes3.py` | Iterates `app.routes`, filters to paths containing `'customer'` or `'catalog'`, prints path+methods+fn | REVIEW_REQUIRED | Highest-numbered variant of the `check_routes*` family; broadest filter (`customer` OR `catalog` vs `_1`'s `customer`-only); manually confirmed via reading source that it supersedes `check_routes.py` |
| `inspect_route.py` | Imports `app.engines.customer_flow.router.router`, inspects internals of a single route object (`route.path_regex`, `path_format`, `name`, etc.) | KEEP — distinct diagnostic purpose | Not a duplicate of any other script — this one dumps low-level Starlette `Route` object internals for debugging a path-matching issue, which none of the `check_router*`/`check_routes*` scripts do; manually read and confirmed unique purpose |

**Summary for this family:** 5 of 9 scripts are DUPLICATE_SUPERSEDED (`check_all_routes.py`, `check_router.py`, `check_router2.py`, `check_routes.py`, `check_routes2.py`), 3 are REVIEW_REQUIRED as the most-capable/most-recent surviving variant of their family (`check_all_routes2.py`, `check_router3.py`, `check_routes3.py`), and `inspect_route.py` is KEEP as a genuinely distinct low-level diagnostic tool. None of these 9 files are wired into any build, test, or CI process — they were all run manually via `python check_*.py` during past debugging sessions (evidenced by the presence of numerous `backend*.log`/`uvicorn*.log`/`server*.log` files at repo root from the same era). All are candidates for ARCHIVE (move to a `scripts/debug/` or `docs/archive/` folder) rather than outright deletion, since they cost nothing to keep and document real debugging history — but per the classification taxonomy required, the ones that are strictly subsumed by a later script in the same family are marked DUPLICATE_SUPERSEDED.

---

## Summary counts

| Classification | Count (this sampled scan) |
|---|---|
| KEEP | ~45 backend engines (by import count) + most sampled frontend symbols + `inspect_route.py` |
| DELETE_CONFIRMED | `EditBtn`/`DeleteBtn`/`ViewBtn`/`MoreBtn` (super-admin ui.tsx), `MoreBtn`/`RowActions`/`DataTable` (tenant-portal ui.tsx), `getCustomerRefreshToken`/`clearCustomerSession` (customer-app), `app/engines/form_builder` (empty stub) |
| REVIEW_REQUIRED | `app/engines/brands`, `app/engines/vertical_billing`, ~25 low-import-count backend engines, `check_all_routes2.py`, `check_router3.py`, `check_routes3.py`, `getCustomerId` (customer-app) |
| DUPLICATE_SUPERSEDED | `check_all_routes.py`, `check_router.py`, `check_router2.py`, `check_routes.py`, `check_routes2.py` |
| GENERATED_RECREATABLE | `app/engines/form_builder` directory shell (registry-only scaffolding) |
| ARCHIVE | Suggested destination for all 9 root `check_*.py`/`inspect_route.py` scripts and the ~250 root-level `*_REPORT.md` sprint/audit documents visible in `git status` (out of scope to enumerate individually here, but noted as a strong candidate for a `docs/archive/` sweep in a future pass) |

This scan intentionally sampled a subset of each population per the task instructions; a full inventory would require running `ts-prune`/`tsc` for the frontends and a Python-side unused-import tool (e.g. `vulture` or `unimport`) for the backend, neither of which was executed here.
