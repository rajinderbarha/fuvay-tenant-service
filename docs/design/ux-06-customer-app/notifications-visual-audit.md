# Notifications Visual Audit — UX-06 Round 5 (Workstream 8)

Real screen, real production nav (Profile → Notifications). Already used the
new design (confirmed in Round 4's route audit as one of the 15 verified) —
this round fixed its 2 remaining typecheck errors (`notificationsApi.list()`
returns `{items,total}` not `{notifications,unread_count}`; unread count now
comes from the real separate `GET /v1/customer/notifications/unread-count`
endpoint rather than a nonexistent field on the list response).

Shows: icon per type, read/unread visual state (dot + bold + tinted
background), relative time ("Just now"/"2h ago"/date fallback), a real
"mark all read" action, real empty state ("All caught up!" with contextual
copy), real loading skeletons. No mock notification is fabricated — the
screen renders whatever the real endpoint returns, including zero rows.

Not exercised this round: an actual populated notification list (no real
notification-triggering event — e.g., a completed booking — was produced
this round, since booking submission itself remains blocked) — only the
empty/loading states were re-verified. Dark theme: not applicable, no dark
theme exists in this app (see light-dark-runtime-report.md, unchanged from
Round 4).
