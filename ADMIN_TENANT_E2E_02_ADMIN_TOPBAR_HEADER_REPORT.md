# Topbar/Header Baseline Report (Part 4)

## Topbar (verified in `AdminLayout.tsx` `TopNav`, browser-verified via Playwright)
- Notification bell: present (`<Bell>` icon + static red dot badge). PASS but see Part 10 for
  badge-count caveat.
- User avatar/name: present — `authApi.me()` populates real name + avatar via `DefaultAvatar`.
- Role label: present but generic — always renders literal text "Platform", not the user's actual
  role (e.g. super_admin vs admin.operator). Minor gap — not a blocker, but not literally a "role
  label" per the spec's intent. Documented, not fixed (touches auth data model, outside "safe
  shell fix" scope).
- Profile/logout menu: not a dropdown menu — instead two separate direct elements: an `<a
  href="/admin/profile">` around the name+avatar, and a standalone logout icon button. Functionally
  equivalent (both reachable, both work — verified in Part 9), just not a single combined menu.
- Search/command-shortcut: a search input exists but is decorative — `useState` only, not wired to
  any search API or keyboard shortcut. Pre-existing, not fabricated as "already existing"; flagged,
  not implemented (out of scope — would require picking/building a real search endpoint).
- Environment indicator: none exists; not invented per spec's instruction to only verify existing
  features.

## Per-page breadcrumb/title/subtitle/CTA (spot-check, 6 pages across sidebar groups)
| Page | Breadcrumb | Title | Subtitle | Primary CTA |
|---|---|---|---|---|
| /admin/dashboard | none | yes (`Dashboard`-style header) | yes | n/a (overview page) |
| /admin/tenants | none | yes | yes | "Add Tenant"-style action present |
| /admin/home-services/pricing-rules | none | yes | yes | "New Rule" action present |
| /admin/categories | none | yes | yes | "New Category" |
| /admin/security | none | yes | yes | n/a |
| /admin/users/roles | none | yes | yes | "New Role" |

**Finding**: `components/layout/Breadcrumbs.tsx` exists as a standalone component but
`grep -rl "Breadcrumbs" app/admin --include=*.tsx` returns **zero** matches — no admin page
actually imports/renders it. Every page instead uses its own inline title via `SectionHeader`
(from `components/shared/ui.tsx`), which provides title+subtitle+actions consistently, but no
page shows a breadcrumb trail. This is a real, pre-existing gap (not introduced this sprint) —
out of "small safe shell fix" scope to retrofit into 157 page files; flagged for a dedicated
follow-up sprint since it touches every page, not just the shell.
