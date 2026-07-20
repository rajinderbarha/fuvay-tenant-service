# UX-05 Workstream Reconciliation (Round 7)

Mirrors UX-04A's reconciliation pattern: every numbered workstream from the original UX-05 brief gets one
explicit disposition, based on what's actually built and verified across six rounds (not aspirational). This is
what makes `STAFF_TECHNICIAN_APP_DESIGN_COMPLETE` claimable for the achievable subset, honestly separated from
what's genuinely blocked outside this phase's control.

**Dispositions used**: `IMPLEMENTED` (built, wired into real navigation, tested), `MOCK_DESIGN_ONLY` (built,
honestly fixture-backed, no live endpoint exists), `API_CONTRACT_REQUIRED` (blocked on a real, missing backend
endpoint — not closeable from the frontend), `PRODUCT_DECISION_REQUIRED` (needs a decision outside this phase's
authority), `NOT_APPLICABLE` (out of scope per a product correction), `PARTIAL` (real progress, real remaining
work, not a backend blocker), `DEFERRED` (not started, no blocker, just not reached).

| # | Workstream | Disposition | Evidence |
|---|---|---|---|
| 1 | Existing app audit (CSV) | IMPLEMENTED | `existing-screen-route-audit.csv` |
| 2 | IA + role-aware navigation | IMPLEMENTED | `RoleAwareTabNavigator`/`TechnicianTabNavigator`/`StaffTabNavigator`, mounted in `AppNavigator`, fail-closed |
| 3 | Auth/session states | PARTIAL (real progress Round 7) | Login/loading/logout real; **Session Expired is now REAL** — `ServiceOSError` carries the actual HTTP status, `AuthContext`'s initial `/me` check sets `sessionExpired=true` only on a genuine 401, `LoginScreen` shows a real banner driven by this. Tenant-suspended/account-disabled/reauth-required remain showcase-only (no live tenant-status/account-status-beyond-`StaffUser.status` field exists) |
| 4 | Configurable role-aware Home | PARTIAL | `HomeScreen` recomposed on real `groupJobs()` (technician); `StaffHomeScreen` is `API_CONTRACT_REQUIRED` (see #38) |
| 5 | Technician My Work | IMPLEMENTED | `JobsListScreen` wired to real `groupJobs()`, Current/Today/Upcoming/Needs Action/Completed tabs, real data |
| 6 | Staff Work Queue | API_CONTRACT_REQUIRED | `StaffWorkQueueScreen` exists, correctly shows restricted/empty — no live work-queue endpoint exists in `lib/api.ts` |
| 7 | Schedule | PARTIAL | `ScheduleScreen` real (Today/Upcoming, live `jobsApi` data); Day/Agenda views and conflict-detection logic not built |
| 8 | Pipeline-aware Job Detail | IMPLEMENTED (real-evidence-corrected) | `JobDetailScreen` extended with `PipelineBadge`/`CustomerContactCard`/`AddressCard`; single-pipeline correction documented in `pipeline-aware-job-detail.md` — no field_ops.Job surface built because none has live data |
| 9 | Current Job mode | IMPLEMENTED | `CurrentJobScreen`, sticky `NextActionBar`, real transitions |
| 10 | Status transition flows | IMPLEMENTED | Pre-existing `JobDetailScreen` transition grid + `CurrentJobScreen`'s `NextActionBar`, both real, using `lib/transitions.ts`'s real state machine |
| 11 | Customer/address access | IMPLEMENTED | `CustomerContactCard`/`AddressCard`, wired into `JobDetailScreen` + `CurrentJobScreen`; Call action correctly disabled (no phone data exists) |
| 12 | Inspection workflow | MOCK_DESIGN_ONLY | `InspectionForm` + `InspectionChecklistShowcaseScreen`, real draft persistence (AsyncStorage), no live inspection-content endpoint |
| 13 | Checklist execution | MOCK_DESIGN_ONLY | `ChecklistSection`/`ChecklistProgress`, real progress/validation logic (`checklist.ts`, tested), real draft persistence, no live endpoint |
| 14 | Parts Request creation | MOCK_DESIGN_ONLY | `PartsRequestShowcaseScreen`, no live parts-request endpoint anywhere in `lib/api.ts` |
| 15 | Parts Request tracking | MOCK_DESIGN_ONLY | `PartsRequestStatusCard`, technician-only `add_note` action type-enforced; same endpoint gap as #14 |
| 16 | Staff Parts Approval | API_CONTRACT_REQUIRED + PRODUCT_DECISION_REQUIRED | `StaffPartsApprovalShowcaseScreen` correctly fail-closed-restricted for every real account (no live role/permission field on `StaffUser` — see #38) |
| 17 | Quote presentation | MOCK_DESIGN_ONLY | `QuoteShowcaseScreen`, confirmed via full `lib/api.ts` re-read that no quote endpoint exists anywhere |
| 18 | Job notes | MOCK_DESIGN_ONLY | `JobNoteComposer`, internal/technician/customer_visible distinction enforced in both composition and display, no live endpoint |
| 19 | Job media | MOCK_DESIGN_ONLY | `MediaCaptureGrid`, never renders storage keys/signed URLs, never marks uploaded before backend confirmation (guards against a lying affordance even in mock form), no live endpoint |
| 20 | Notifications/action inbox | IMPLEMENTED | Real pre-existing `notificationsApi`; `NotificationsScreen` now uses the real `NotificationCard` + reactive theme (Round 6) |
| 21 | Availability/work-status | MOCK_DESIGN_ONLY | `AvailabilityControl`, confirmed no live work-status endpoint distinct from account/job status; wired into real `ProfileScreen` |
| 22 | Profile | PARTIAL | Extended with real `specialisations`, role/designation, `AvailabilityControl`, `ThemeToggle`; areas/certifications/recent-activity honestly `MOCK_DESIGN_ONLY` (no endpoint) |
| 23 | Offline/weak-network states | IMPLEMENTED (detection) + MOCK_DESIGN_ONLY (matrix enforcement) | Real `useNetworkStatus` (NetInfo, native+web), `NetworkStatusBanner` wired into production shell; `offline-operation-matrix.csv` documents the intended per-operation rule but no operation actually auto-replays/queues yet (correctly, per the hard constraint) |
| 24 | Readiness metadata | IMPLEMENTED | `ActionReadinessView`/`readiness` field present on every view model in `types/ux05.ts`; `readiness-state-registry.csv` |
| 25 | Typed view models | IMPLEMENTED | `src/types/ux05.ts`, all 20 named view models, real-evidence single-pipeline correction |
| 26 | Frontend adapter contracts | IMPLEMENTED | `frontend-adapter-contract.md` (Round 7) — formal route/shape/permission/offline/readiness table for every real adapter (auth, home, my-work, schedule, job-detail, status-transition, notifications, chat, profile) and every MOCK_DESIGN_ONLY adapter (inspection, checklist, quote, parts, notes, media, availability, staff work-queue, StaffPermission fetch) |
| 27 | Shared mobile components | PARTIAL | 17 components built (`shared-mobile-component-inventory.csv`); ~5 more named in the brief (MobileAppShell, MobileStatusTimeline, ChecklistProgress separate from ChecklistSection, SyncConflictPanel, OfflineDraftBanner) not built as distinct components |
| 28 | System states | PARTIAL | `SystemStatesShowcaseScreen` covers Session Expired (real, see #3)/Reauthentication Required/Tenant Suspended/Account Disabled/Read-only/Restricted; 5 of 6 remain presentation-only (no live tenant/account-status field) |
| 29 | Light/dark themes | PARTIAL (substantially advanced Round 7) | Real mechanism (Round 5): `ThemeContext`, dark palette, `ThemeToggle`. Reactive as of Round 7: `AppNavigator`, both tab navigators, `HomeScreen`, `JobsListScreen`, `ScheduleScreen`, `CurrentJobScreen`, `ProfileScreen`, `NotificationsScreen`, `PipelineBadge`, `PermissionRestrictedState`, `NetworkStatusBanner`, `NotificationCard`, `AvailabilityControl`, `ScheduleCard`, `CustomerContactCard`, `AddressCard` — 9 screens + 7 components. Still static-light-only: `JobDetailScreen` (largest remaining screen, has real-money modals — deliberately not touched this round without dedicated regression coverage), `LoginScreen`, most dev showcase screens, `Card`/`Button`/`StatCard`/`Skeleton`/`JobStatusBadge` (shared pre-existing components), `WorkItemCard`/`PartsRequestStatusCard`/`ChecklistSection`/`InspectionForm`/`JobNoteComposer`/`MediaCaptureGrid` (ux05 components) |
| 30 | Accessibility | PARTIAL | Real fixes: 4 touch-target corrections, `accessibilityRole`/`accessibilityLabel` on 9+ components, color-independent status, real `PixelRatio.getFontScale()` reading + confirmed no `allowFontScaling={false}` anywhere (Round 7, `AccessibilityShowcaseScreen`). Not done: focus-order audit, text-scaling device stress test, live screen-reader session (all require a device/emulator not available here) |
| 31 | Localization readiness | NOT_APPLICABLE | Round 6 product correction: Super Admin/Tenant/Staff/Technician apps are single-language by design; multilingual is DeepSeek-customer-chat-only. See `localization-readiness-report.md`. The Round 5 spot-check code/tests were kept (harmless) but this is a closed line item, not open scope |
| 32 | Development showcase screens (~30) | PARTIAL | 12 built (`development-showcase-inventory.csv`): Parts Request, Inspection & Checklist, Notes & Media, Staff Parts Approval, Current Job, Quote, Offline States, System States (6 sub-states), Theme, Localization, Accessibility |
| 33 | Unit/component tests | IMPLEMENTED (for what's built) | 43 tests, real behavioral assertions (role fail-closed, explicit-deny, pipeline non-collapse, My Work classification, checklist validation, RNTL renders, draft-persistence restart simulation, localization non-truncation) |
| 34 | Runtime testing | IMPLEMENTED (Login-screen scope) | Real Playwright verification against the Expo web bundle, unblocked in Round 4, re-verified every round since including after Round 6's changes — zero errors. Scope limited to the unauthenticated Login screen (no `linking` config exists to deep-link into authenticated routes in-browser — see #26/`runtime-test-report.md`) |
| 35 | Offline testing | PARTIAL | Real network-state detection + real draft persistence with a genuine restart-simulation test; the fuller deterministic-scenario matrix from the brief (network-drop-during-draft, interrupted-media-upload, etc.) not individually built/tested |
| 36 | Build/regression verification | IMPLEMENTED | Install/typecheck/tests/build/runtime all proven real in WSL every round; `git diff --stat` non-change check against `7488335` re-confirmed empty every round; lint honestly `NOT_CONFIGURED` (real finding, not fabricated) |
| 37 | Non-change audit | IMPLEMENTED | `backend-non-change-report.md`, `frontend-file-allow-list.md`, re-verified fresh every round including after the Round 4→5 concurrent-process branch incident (never touched this branch) |
| 38 | Documentation (72 files) | PARTIAL | 45 files in `docs/design/ux-05-staff-technician-app/` by end of Round 7 (real `ls` count, not estimated) — of 72 originally listed, minus 31's closure removing the remaining planned localization docs from the target |

## The two genuine backend-contract blockers (not closeable from the frontend)
1. **No StaffPermission-fetch endpoint** and **no role field on `StaffUser`** — blocks #6, #16, and any real
   staff-vs-technician distinction. `deriveRole()` fails closed to `technician` for every real account today;
   this is correct, safe behavior, not a bug, but it means `StaffHomeScreen`/`StaffWorkQueueScreen`/
   `StaffPartsApprovalShowcaseScreen` cannot show real content until the backend exposes this. **This is a
   backend team decision, outside this design phase's authority.**
2. **No content endpoint for inspection/checklist/quote/parts-request/notes/media** — every one of #12/13/14/
   15/17/18/19 is fully designed, componentized, and tested against fixture data, but has nothing real to call.
   **This is a backend team decision** (whether/how to build these endpoints), also outside this phase's
   authority.

Neither blocker is a reason to withhold `DESIGN_COMPLETE` for the frontend-achievable subset — forcing a fake
completion by inventing endpoints or fabricating data would violate the no-fabrication hard constraint. The
correct outcome, per the coordinator's framing, is exactly what this table shows: clean, honest
`API_CONTRACT_REQUIRED`/`PRODUCT_DECISION_REQUIRED` dispositions on the blocked items, `IMPLEMENTED` everywhere
that's genuinely true.

## What remains genuinely open (frontend-achievable, not backend-blocked)
- Dark-theme conversion of `JobDetailScreen` (the largest remaining screen, deliberately deferred to avoid
  touching the real money-collection modal without dedicated regression coverage), `LoginScreen`, remaining dev
  showcases, and the pre-existing shared components (`Card`/`Button`/`StatCard`/`Skeleton`/`JobStatusBadge`) plus
  6 more ux05 components (`WorkItemCard`, `PartsRequestStatusCard`, `ChecklistSection`, `InspectionForm`,
  `JobNoteComposer`, `MediaCaptureGrid`) — mechanical, proven pattern, real remaining work.
- ~18 more showcase screens (breadth, not depth — the underlying components mostly already exist).
- ~27 more documentation files (real writing work; some no longer needed at all per #31's closure).
- Tenant-suspended/account-disabled/reauthentication-required real trigger wiring — would need backend fields
  (a real tenant-status flag, an account-disabled distinct from `StaffUser.status`) not confirmed to exist.
