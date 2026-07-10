# E2E-07 Remaining Blockers
**Date:** 2026-07-10

---

## P0 Blockers (Must Fix Before Certification)

**None.** All P0 blockers have been resolved in this sprint.

---

## P1 Issues (Should Fix Before Release)

| # | Issue | File | Priority | Status |
|---|---|---|---|---|
| 1 | `ReadOnlyBanner` not yet integrated into individual pages | Per-page integration needed | P1 | Open — component created, pages not updated |

**Details:** The `ReadOnlyBanner` component exists at `components/shared/ReadOnlyBanner.tsx`. High-mutation pages (Finance, Profile, Staff, Service Setup) should import it and pass `me?.role` from `authApi.me()`. A follow-up sprint should systematically add this to all mutation pages.

---

## P2 Issues (Non-Blocking)

| # | Issue | File | Priority | Status |
|---|---|---|---|---|
| 1 | No per-page `<title>` metadata via Next.js `export const metadata` | All pages | P2 | Open |
| 2 | Mobile layout untested — tenant portal is desktop-first | All pages | P2 | Acknowledged / out of scope |
| 3 | Browser smoke tests pending (requires live server) | All routes | P2 | Open |
| 4 | `"Your Business"` loading fallback visible briefly on first paint | 5 pages | P2 | Acceptable as-is |

---

## Resolved This Sprint

| # | Issue | Fix |
|---|---|---|
| 1 | "Bargain Floor" label in `/provider/pricing` | Renamed to "Min Floor Price" / "Floor Price" |
| 2 | 6 pages using direct `fetch()` bypassing API client | All 6 converted to `apiFetch` |
| 3 | `apiFetch` not exported from `lib/api.ts` | Exported |
| 4 | No `ReadOnlyBanner` component | Created at `components/shared/ReadOnlyBanner.tsx` |
| 5 | E2E-07 docs directory missing | Created `docs/e2e07/` with 20 reports |
| 6 | TypeScript errors | 0 errors confirmed |

---

## Certification Status

**E2E-07: READY FOR CERTIFICATION**

All P0 blockers resolved. P1 item (ReadOnlyBanner page integration) noted for follow-up. P2 items are non-blocking.
