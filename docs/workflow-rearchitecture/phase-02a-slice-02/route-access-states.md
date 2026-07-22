# Route Access States

## Status: largely pre-existing, verified rather than built this slice

The brief asks for standardized Loading/Unauthorized/Forbidden/Not Found/Retired/Temporarily Unavailable/Blocked-by-backend-gap/Partial-data-unavailable states. This slice did not build a new shared component system for these — doing so would risk touching shared layout/styling broadly, which conflicts with "no new visual design" and "no broad page consolidation." Instead, existing per-surface behavior was verified:

| State | Existing handling | Verified this slice |
|---|---|---|
| Loading | `usePermissions()` / `useApi()` hooks return `loading: true`; nav items fail closed (hidden) while loading | Yes — read `usePermissions.ts` and `AdminLayout.tsx`'s `isNavItemPermitted` |
| Unauthorized (401) | Existing auth flow (token refresh/redirect to login) — unchanged | Not re-verified this slice (no auth flow file was touched) |
| Forbidden (403) | `StaffLayout` shows an explicit "This app is for staff/technician accounts only" message with the actual role name, without exposing raw permission internals | Yes — read the exact JSX |
| Not Found | Standard Next.js 404 — unchanged | Not touched |
| Retired | New this slice: `POST /v1/reviews` returns 410 with an explicit message naming the canonical replacement (`customer_reviews`) | Yes — this is the one new "retired" state added this slice |
| Temporarily unavailable | My Work page (`/staff/my-work`, Slice 1) shows a `sources_unavailable` banner rather than silently showing incomplete data | Unchanged from Slice 1, re-verified still present |
| Blocked by backend gap | Not newly built this slice | N/A |
| Partial data unavailable | Same as "temporarily unavailable" above (My Work's `sources_unavailable`) | Unchanged from Slice 1 |

## What was NOT built this slice
A shared, reusable "route access state" component/pattern used consistently across all 3 frontend apps — the brief's Workstream 8 implies a standardized set of states, but building that generically would be new shared-component work across surfaces this slice didn't otherwise touch, risking scope creep into visual/component-library territory explicitly excluded ("no new component library"). The existing per-page patterns (StaffLayout's access-denied message, My Work's partial-data banner, the new 410 response) are consistent in spirit (clear, honest, role-appropriate messaging) without introducing a new shared abstraction.
