# Screen & Route Inventory (definitive, UX-05B)

Single source of truth for every screen/route in `mobile/staff-app`, replacing the need to cross-reference 6+
rounds of incremental docs. Compiled directly from `src/navigation/AppNavigator.tsx`,
`src/navigation/ux05/TechnicianTabNavigator.tsx`, and `src/navigation/ux05/StaffTabNavigator.tsx` — not
reconstructed from memory.

**Status legend**: `IMPLEMENTED` (real data, real backend, production-wired) · `MOCK_DESIGN_ONLY` (real UI/logic,
fixture data, honestly labeled, no live endpoint) · `API_CONTRACT_REQUIRED` (blocked on a missing backend
endpoint, cannot be closed from the frontend) · `PARTIAL` (some real, some mock, mixed) · `DEV_ONLY` (never
reachable from production nav, `navigation.navigate()`-only, for internal review).

## Unauthenticated
| Screen | Route | Status | Notes |
|---|---|---|---|
| `LoginScreen` | `Login` | IMPLEMENTED | Real `/v1/auth/login`, fixed in UX-05B FIX 1 |

## Technician role — `TechnicianTabNavigator` (production, 5 tabs)
| Screen | Route | Status | Notes |
|---|---|---|---|
| `HomeScreen` | `Home` | IMPLEMENTED | Real `groupJobs()`-based Active Job / Needs Your Action / Today's Schedule; one honest `MOCK_DESIGN_ONLY` placeholder row (pending parts/checklist summary, no aggregation endpoint) |
| `JobsListScreen` | `MyWork` | IMPLEMENTED | Real `jobsApi.myJobs()`, All/Current/Today/Upcoming/Needs Action/Completed tabs via `groupJobs()` |
| `ScheduleScreen` (`src/screens/ux05/`) | `Schedule` | IMPLEMENTED | Real jobs list, Today/Upcoming grouping; Day/Agenda views not built |
| `NotificationsScreen` | `NotificationsTab` | IMPLEMENTED | Real `notificationsApi` |
| `ProfileScreen` | `Profile` | PARTIAL | Real `specialisations`/role/schedule editor/`ThemeToggle`; areas/certifications/recent-activity honestly labeled not-yet-available (fixed copy in UX-05B FIX 2) |

## Staff role — `StaffTabNavigator` (production, 5 tabs)
| Screen | Route | Status | Notes |
|---|---|---|---|
| `StaffHomeScreen` (`src/screens/ux05/`) | `StaffHome` | API_CONTRACT_REQUIRED | No live staff work-queue-summary endpoint; honest "coming soon" copy (fixed UX-05B item 8), zero fabricated data |
| `StaffWorkQueueScreen` (`src/screens/ux05/`) | `WorkQueue` | API_CONTRACT_REQUIRED | Same blocker; shows intended group labels only, honest "coming soon" copy (fixed UX-05B item 8) |
| `ScheduleScreen` | `Schedule` | IMPLEMENTED | Same real screen as technician tab |
| `NotificationsScreen` | `NotificationsTab` | IMPLEMENTED | Same real screen as technician tab |
| `StaffMoreScreen` (`src/screens/ux05/`) | `More` | IMPLEMENTED | Permission-gated entry list (fail-closed `deriveRole`/`hasPermission`), Sign Out |

**Note**: `deriveRole()` fails closed to `"technician"` for every real account today (no live role field on
`StaffUser`) — so in practice, no real user currently lands on `StaffTabNavigator` at all. It exists, is wired,
and is honest about its blockers, but is currently unreachable in the live app. This is intentional, safe
behavior (see `workstream-reconciliation.md` #4/#38), not a frontend gap.

## Shared authenticated stack screens (reachable from either role's tabs)
| Screen | Route | Status | Notes |
|---|---|---|---|
| `JobDetailScreen` | `JobDetail` | IMPLEMENTED | Real `jobsApi.get/accept/reject/...`, real money-collection "Complete Job" modal; theme-converted + regression-tested in UX-05B item 2 |
| `ChatRoomScreen` | `ChatRoom` | IMPLEMENTED | Real `chatApi` (staff chat threads) |
| `NotificationsScreen` | `Notifications` (stack, from bell icon) | IMPLEMENTED | Same screen, different entry point than the tab |

## Dev-only showcases — `DEV_ONLY`, never linked from production nav/tabs (confirmed via `AppNavigator.tsx`'s own comment: "reachable only by direct `navigation.navigate()` call")
| Screen | Route | Status | Notes |
|---|---|---|---|
| `PartsRequestShowcaseScreen` | `ShowcasePartsRequest` | MOCK_DESIGN_ONLY | No live parts-request endpoint |
| `InspectionChecklistShowcaseScreen` | `ShowcaseInspectionChecklist` | MOCK_DESIGN_ONLY | Real progress/validation logic + real `usePersistedDraft` (AsyncStorage), no live content endpoint |
| `JobNotesMediaShowcaseScreen` | `ShowcaseJobNotesMedia` | MOCK_DESIGN_ONLY | No live notes/media endpoint; draft is `useState`-only (not persisted, disclosed gap) |
| `StaffPartsApprovalShowcaseScreen` | `ShowcaseStaffPartsApproval` | API_CONTRACT_REQUIRED + PRODUCT_DECISION_REQUIRED | Correctly fail-closed-restricted for every real account today |
| `CurrentJobScreen` (`src/screens/ux05/`) | `CurrentJob` | IMPLEMENTED (real data) but DEV_ONLY route | Real single-job focused view + sticky `NextActionBar`; not currently linked from Home/My Work despite using real data — an open wiring gap, not a data gap |
| `QuoteShowcaseScreen` | `ShowcaseQuote` | MOCK_DESIGN_ONLY | No quote endpoint exists anywhere in `lib/api.ts` (confirmed) |
| `OfflineStatesShowcaseScreen` | `ShowcaseOfflineStates` | MOCK_DESIGN_ONLY (composition of real components) | 6 offline/sync scenarios using real `NetworkStatusBanner`/`PermissionRestrictedState` |
| `SystemStatesShowcaseScreen` | `ShowcaseSystemStates` | PARTIAL | Session Expired is real (driven by an actual 401); Reauth/Tenant Suspended/Account Disabled/Read-only/Restricted are presentation-only, no live trigger field exists |
| `ThemeShowcaseScreen` | `ShowcaseTheme` | IMPLEMENTED | Real `ThemeContext`/`useAppTheme()` demo |
| `LocalizationShowcaseScreen` | `ShowcaseLocalization` | MOCK_DESIGN_ONLY (harmless spot-check, `NOT_APPLICABLE` as an open workstream) | Real Hindi/Punjabi long-text layout spot-check; localization itself is out of scope per Round 6 product correction |
| `AccessibilityShowcaseScreen` | `ShowcaseAccessibility` | IMPLEMENTED | Real `PixelRatio.getFontScale()` reading, `allowFontScaling` audit demo |

**Showcase count**: 11 dev-only showcase routes registered in `AppNavigator.tsx` today (of the original ~30
target from the brief). See `development-showcase-inventory.csv` for the fuller historical breakdown including
components not given their own dedicated screen route.

## Total counts
- **Production-reachable screens**: 9 distinct screen components across both tab navigators + the shared stack
  (`HomeScreen`, `JobsListScreen`, `ScheduleScreen`, `NotificationsScreen`, `ProfileScreen`, `StaffHomeScreen`,
  `StaffWorkQueueScreen`, `StaffMoreScreen`, `JobDetailScreen`, `ChatRoomScreen`, `LoginScreen` — 11 total
  counting the unauthenticated and shared-stack entries once each).
- **Dev-only showcase routes**: 11.
- **Backend-blocked (frontend-complete, honest placeholder)**: `StaffHomeScreen`, `StaffWorkQueueScreen` — the
  2 screens item 8 explicitly excludes from the `DESIGN_COMPLETE` bar.
