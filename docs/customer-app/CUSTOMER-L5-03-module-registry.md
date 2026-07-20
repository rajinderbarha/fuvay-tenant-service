# CUSTOMER-L5-03 — Module Registry

## Supported Module Types

Only one, because only one has a real backend data source
(`CUSTOMER-L5-03-backend-contract-audit.md`):

| Module type | category-grid |
|---|---|
| Backend schema | `GET /v1/customer/categories` → `CategorySummaryDto[]` |
| Client schema | `category-schema.ts#categorySummarySchema` (Zod) |
| Renderer | `components/CategoryGrid.tsx` → `CategoryCard.tsx` |
| Layout | Bounded flex-wrap grid, capped at 12 items (`discovery-composer.ts`) |
| Navigation | None yet — category press shows a toast (`toastService.info`), since no category-detail route exists (CUSTOMER-L5-04) |
| Analytics | Not wired (no vendor authorized — see known-gaps) |
| Accessibility | `home-accessibility.md` (unchanged from the first L5-03 pass) |
| Loading | `Skeleton` × 2 |
| Empty | `EmptyState` ("No services available") |
| Error | `ErrorState` with retry |
| Test coverage | `category-schema.test.ts`, `discovery-composer.test.ts`, `module-visibility.test.ts`, `module-registry.test.ts` |

## The Registry Itself

`domain/module-registry.ts#resolveModuleRenderer(moduleType: string)`
returns either `{recognized: true, moduleType}` (a `SupportedModuleType`)
or `{recognized: false, moduleType}` for anything else — the latter never
throws, never attempts to dynamically resolve a component from the string,
and logs a safe `home_module_skipped` warning (module type only, never any
payload). `HomeScreen.tsx` calls this before deciding what to render;
because there is only one real module type, `HomeScreen` does not yet need
a `Record<SupportedModuleType, Component>` map — that map's *shape* exists
implicitly (a single `if (recognized) render CategoryGrid`), and adding a
second real module type means adding a second `case`, not restructuring
this architecture.

## Visibility Evaluator

`domain/module-visibility.ts#evaluateModuleVisibility` — the single
deterministic evaluator (CUSTOMER-L5-03 §9). Outcomes actually reachable
given this backend's real capabilities: `VISIBLE`, `CONFIGURATION_INVALID`
(unknown type), `DISABLED`, `AUTH_REQUIRED`, `UNSUPPORTED_VERSION`,
`OUTSIDE_REGION`. Not reachable this sprint (no data source to drive them):
`HIDDEN` (would require a backend/remote-config "visible" flag distinct
from "enabled" — the categories endpoint only has `is_customer_visible`
which is already filtered out server-side before the client ever sees a
hidden category, so there's no client-observable HIDDEN case for this
module), `PROFILE_REQUIRED`, `DEPENDENCY_DISABLED`,
`EXPERIMENT_EXCLUDED`, `OUTSIDE_AVAILABILITY_WINDOW` — none of these have
a real data source in this backend contract. Listed as reserved, not
faked.

## Critical Module Handling

`HomeScreen.tsx`'s `CATEGORY_GRID_MODULE.critical = true`. If
`evaluateModuleVisibility` ever returns anything other than `VISIBLE` for
an authenticated customer (which given the current inputs — always
authenticated by the time Home renders, always a valid app version —
should never actually happen in practice), the screen renders a page-level
`ErrorState` instead of silently omitting the Services section, per
CUSTOMER-L5-03 §31 ("For a critical module failure: use a safe page-level
error state").

## Duplicate/Invalid Module Handling

Not applicable at the *module* level (there's exactly one module,
compiled client-side, not received as a list from any backend "modules"
endpoint). At the *item* level (individual categories within the one
module), `discovery-composer.ts#composeCategorySections` already
deduplicates by ID and drops invalid items — see
`CUSTOMER-L5-03/home-content-composition.md` (first-pass doc, still
accurate).

## Extending This Registry

Adding a second real module type (once a backend data source exists)
requires: (1) add the type string to `SUPPORTED_MODULE_TYPES` in
`home-module-types.ts`, (2) add its Zod schema, (3) add its query in
`home-queries.ts` with a properly-scoped key, (4) add its renderer
component, (5) add its case to `HomeScreen`'s render logic. Do not add a
type to `SUPPORTED_MODULE_TYPES` without a real query/renderer to back it
— an entry with no data source would make `resolveModuleRenderer` claim
"recognized" for something that then has nothing to actually render.
