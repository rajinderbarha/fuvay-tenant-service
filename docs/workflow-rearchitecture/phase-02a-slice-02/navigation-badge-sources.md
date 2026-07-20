# Navigation Badge Sources

Per the approved rule: every badge must define source endpoint, role, permission, refresh behavior, loading behavior, error behavior, click destination.

## Technician "My Work" badge (implemented this slice)

| Field | Value |
|---|---|
| Source endpoint | `GET /v1/staff/my-work` (Slice 1 endpoint, no new backend call) |
| Role | technician, staff |
| Permission | Same as the page itself — `get_current_user` + tenant/staff scoping (no separate permission check for the badge) |
| Refresh behavior | Refetches on component mount (same lifecycle as the layout itself — no polling, no separate cache) |
| Loading behavior | No badge rendered |
| Error behavior | No badge rendered — never a fake "0" |
| Count logic | `items.filter(it => it.priority === "urgent" || it.category === "REQUIRES_MY_ACTION").length` |
| Zero-count behavior | No badge rendered (a "0" badge is visually noise, and this is a deliberate UX choice distinct from the error case — see code comment in `StaffLayout.tsx`) |
| Click destination | Clicking the nav item navigates to `/staff/my-work` (the badge itself is not independently clickable — it's part of the nav link) |

## Network call cost
One additional `GET /v1/staff/my-work` call per page load of any page using `StaffLayout` (since the badge hook lives in the layout, not the page). This duplicates the call already made by the `/staff/my-work` page itself when that specific page is open. Per the "avoid one network call per menu item" rule: this is **one** call for **one** badge (not one call per menu item), so it complies with that rule, but it does mean visiting the My Work page itself results in 2 near-simultaneous identical requests (layout badge + page content). Not deduplicated this slice — see `known-limitations.md`.

## Badges NOT implemented this slice
- Admin or tenant-owner My Work counts — explicitly excluded per the brief ("Do not add admin or tenant-owner My Work counts before their aggregation endpoints exist") since neither endpoint exists yet.
- Any other nav item badge (notifications count, chat unread count, etc.) — out of scope, not touched.
