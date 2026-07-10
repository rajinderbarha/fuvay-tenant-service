# Notification Entry Point Baseline Report (Part 10)

- Bell icon exists in the topbar (`TopNav` in `AdminLayout.tsx`, line ~543) with a static red
  unread-indicator dot.
- **Real gap found**: the bell `<button>` has **no `onClick` handler at all** — it doesn't open a
  dropdown, doesn't navigate to `/admin/notifications`, and does nothing when clicked. Confirmed
  by reading the full `TopNav` function body — only `theme toggle`, `logout`, and the
  name/avatar link (to `/admin/profile`) have real behavior; the bell button is purely decorative.
- The badge count is also static (a fixed dot, not a real unread count) — consistent with the
  spec's instruction not to fabricate a count; it was never wired to a real API to begin with.
- `/admin/notifications` IS a real, working page (confirmed in route map, Part 1/6) — it's simply
  not linked from the bell.
- Not fixed in this sprint: wiring the bell to open a dropdown or navigate is a genuine, safe,
  small shell fix that arguably fits "small fixes if shell/navigation blocks route testing" — but
  it did NOT block any route testing (the `/admin/notifications` route is reachable directly via
  sidebar and via the smoke test), so per the strict scope ("do NOT fully certify... notifications
  delivery") this was left as a documented gap rather than silently wired up without a design
  decision on dropdown-vs-navigate. Recommended minimal fix for a future pass: `onClick={() =>
  window.location.href = "/admin/notifications"}`.
