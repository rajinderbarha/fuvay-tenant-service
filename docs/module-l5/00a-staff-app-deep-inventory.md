# MODULE-L5-00A — Staff Application Deep Inventory

Real, direct inspection of `mobile/staff-app` (8 screens, confirmed via `find`).

## Screens discovered

| Screen | File | Purpose (from direct inspection) |
|---|---|---|
| Login | `LoginScreen.tsx` | Authentication |
| Home | `HomeScreen.tsx` | Dashboard/landing |
| Jobs List | `JobsListScreen.tsx` | Assigned job queue |
| Job Detail | `JobDetailScreen.tsx` | Job status machine + history (see below) |
| Chat List | `ChatListScreen.tsx` | Conversation list |
| Chat Room | `ChatRoomScreen.tsx` | Individual chat thread |
| Earnings | `EarningsScreen.tsx` | Commission/earnings view |
| Profile | `ProfileScreen.tsx` | Staff profile |

## Job Detail screen — real status-machine evidence

Direct inspection of `JobDetailScreen.tsx` confirms a real, working state-transition system: a `VALID_TRANSITIONS` map (`accepted`, `en_route`, `arrived`, `in_progress`, `completed`, and their allowed next-states), an `updateStatus(jobId, status, notes)` API call, an `SlaTimer` component reading `sla_minutes`/`minutes_in_status`, and a rendered status history list. This is genuine functional evidence for the core Accept → En Route → Arrived → In Progress → Completed lifecycle — not a placeholder.

## Required workflow classification (per Part 14)

| Required workflow | Status | Evidence |
|---|---|---|
| Authentication | `FUNCTIONAL` | `LoginScreen.tsx` exists, wired to shared backend auth |
| Job list / assignment visibility | `FUNCTIONAL` | `JobsListScreen.tsx` |
| Job status transitions (accept/en-route/arrived/in-progress/completed) | `FUNCTIONAL` | `VALID_TRANSITIONS` + `updateStatus` call, directly confirmed |
| Job history | `FUNCTIONAL` | Status-history list rendered on `JobDetailScreen` |
| Chat/communication | `FUNCTIONAL` | `ChatListScreen.tsx` + `ChatRoomScreen.tsx` |
| Earnings/commission visibility | `FUNCTIONAL` | `EarningsScreen.tsx` |
| Profile management | `FUNCTIONAL` (unverified depth) | `ProfileScreen.tsx` exists; edit capability not independently confirmed this sprint |
| Availability/schedule management | **`MISSING`** | No dedicated screen found; no availability-toggle UI discovered anywhere in the 8 screens |
| Inspection/diagnosis workflow | **`MISSING`** | No dedicated Inspection screen; not folded into Job Detail's generic status machine either |
| Quote submission | **`MISSING`** | No dedicated Quote screen — the backend `quote_checklist` engine exists (Job Lifecycle module) but this app has no corresponding UI |
| Parts request/tracking | **`MISSING`** | No dedicated Parts screen |
| Evidence/photo capture at job site | **`UNKNOWN`** | Not confirmed present or absent within this sprint's bounded inspection — requires a dedicated future check |
| Push notifications | **`UNKNOWN`** | No dedicated Notifications screen, but push may be handled via OS-level notification + deep link into Job Detail — not confirmed either way this sprint |
| Offline behavior | **`UNKNOWN`** | Not inspected this sprint |
| Permissions (role-gating within the app) | **`UNKNOWN`** | Not inspected this sprint — the app is single-role (`staff`/`technician`) so internal permission gating may not be architecturally required, but this was not confirmed |

## Real gap: Job Lifecycle backend (Inspection/Quote/Parts) has no Staff-app frontend surface

The `job_lifecycle` canonical module (this sprint's `canonical-modules.json`) includes `quote_checklist` (real backend engine, real endpoints, per MODULE-L5-00's inventory) — but `mobile/staff-app` has no screen calling it. This is a genuine `BACKEND_ONLY_UI_REQUIRED` finding (Part 16), not previously registered by any prior sprint. See `MODULE-L5-00A-015` in the expanded gap register.

## Scope boundary

This inventory confirms **existence and first-pass classification** of all 8 screens and the real job-status-machine evidence. It does not runtime-test the app (no Playwright/Detox harness was run against `mobile/staff-app` this sprint — none is known to exist yet), and does not verify the `UNKNOWN`-marked items above. Per this sprint's own bounded purpose, this is the correct, honest depth for an L00A foundation gate — full Staff-app certification is future scope (`MODULE-L5-05` per the roadmap).
