# CUSTOMER-L5-03 — Failure Matrix

Supplements `home-failure-matrix.md` (first pass — still accurate for
Services-section-specific failures) with the module-registry-level
failures introduced this pass.

| Failure | Detection point | Page/module impact | Customer message | Retry | Cache behavior | Analytics | Log level | Severity |
|---|---|---|---|---|---|---|---|---|
| `GET /v1/customer/categories` network/timeout/500 | `apiClient` → `ApiError` | Services section only (non-critical failure path — the module itself is critical, but a query error is handled by `ErrorState`, not by hiding the whole page) | "Couldn't load services" | Retry button | None (no cache — see cache policy) | none | warn | P2 |
| Malformed category item(s) | `category-schema.ts` Zod validation | Partial — valid items still render | none if ≥1 valid item remains | N/A | N/A | none | warn (`home_module_validation_failed`) | P3 |
| Unknown module type | `module-registry.ts#resolveModuleRenderer` | That module skipped, page continues | No message (silent skip, by design) | N/A | N/A | none | warn (`home_module_skipped`) | P3 (not currently reachable — only one module type exists client-side, so this path is only exercised by the unit test, not real traffic) |
| Critical module resolves non-VISIBLE | `module-visibility.ts` evaluation in `HomeScreen.tsx` | **Whole page** — page-level `ErrorState` replaces the Services section entirely | "Home is temporarily unavailable. Please sign in again or try later." | None offered (no retry button on this specific state — the underlying cause, e.g. session no longer authenticated, needs a real sign-in, not a query retry) | N/A | none | none (no log call at this site currently — see known-gaps) | P1 if it ever actually fires in production (should be unreachable given Home is already auth-gated by `route-guards.ts` before it can mount) |
| Wrong tenant / wrong marketplace | Not exercised (single-tenant environment) | UNVERIFIED | — | — | — | — | — | UNVERIFIED |
| Offline, no cache | `useConnectivity` + empty query cache | `OfflineBanner` shown; Services section shows its own error/empty state independently (no coordinated "offline mode" for Home specifically) | Generic offline banner text (CUSTOMER-L5-00) | Retry via pull-to-refresh | N/A | none | none | P2 |
| Locale change mid-session | `i18n.on("languageChanged")` → `setRequestLocale` → next query uses new key | Categories refetch under the new locale's query key automatically | N/A (transparent) | N/A | Old-locale cache entry remains in TanStack Query's cache but is never served for the new locale (different key) — not proactively evicted, just orphaned until GC | none | none | P3 |

## New This Pass

The "critical module resolves non-VISIBLE" and "unknown module type" rows
are new — they did not exist before this pass because the module-registry/
visibility-evaluator layer itself is new. Both are currently theoretical
(not reachable by real traffic today) since there is exactly one module,
always recognized, and Home is already auth-gated before it can render —
they exist to make the *next* module type's addition safe by construction,
per CUSTOMER-L5-03 §8's requirement that unknown/critical-failure handling
exist architecturally, not just accidentally work today.
