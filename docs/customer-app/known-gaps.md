# Customer App — Known Gaps

Only real deferred work. Nothing in this list is required sprint scope
being avoided — see the relevant sprint's repository-audit /
baseline-verification doc for why each item was scoped out. Updated after
each sprint; items are marked with the sprint that introduced them.

## P1 — should be addressed early in the next relevant sprint

1. **Auth token still in `AsyncStorage`, not `secure-storage.ts`.**
   `AuthContext`/`src/lib/api.ts` were not migrated in this sprint (auth is
   explicitly out of scope for CUSTOMER-L5-00). The secure-storage adapter
   is built and tested; wiring it into the real login flow belongs to the
   authentication sprint.
2. **Existing 19 screens are not migrated onto the new design-system
   primitives.** They continue to use the pre-existing flat `theme.ts` and
   ad hoc `Button`/`Card`/`Skeleton` components. Migrating them is a
   screen-by-screen effort with no automated coverage to verify against
   today (none existed before this sprint) — doing it blind in this sprint
   would risk regressions in a dozen live user flows.
3. **`AppNavigator.tsx`/`TabNavigator.tsx` still use untyped string route
   names**, not `route-names.ts`/`route-types.ts`. Migrating 19 screens'
   navigation calls to typed routes is deferred alongside item 2.
4. **No device-level accessibility verification** (TalkBack/VoiceOver) was
   performed — only automated `accessibilityRole`/`State`/`Label`
   assertions in Jest. No physical device or simulator was available in
   this environment.

## P2 — real but lower urgency

5. **`AIChatResponse` interface and AI chat API object are duplicated** in
   `src/lib/api.ts` (`aiChatApi` vs `aiApi`, two `AIChatResponse` type
   declarations). Pre-existing, not introduced by this sprint. Flagged for
   a future cleanup pass on that file.
6. **No `@react-native-community/netinfo`** — connectivity detection uses a
   lightweight HTTP reachability probe (`useConnectivity`), not native
   connection-type awareness. Sufficient for an offline banner; revisit if
   a later sprint needs wifi/cellular distinction.
7. **`BottomSheet` is `Modal`-based**, not a gesture-driven sheet
   (no drag-to-dismiss/snap points). Sufficient for the showcase and any
   simple confirmation-style sheet; a real gesture library should be added
   once a feature needs it.
8. **No E2E test runner** (Detox/Maestro) configured. Out of scope for an
   architecture-baseline sprint.
9. **No crash-reporting or analytics vendor is wired.** The adapters exist
   (`setCrashReportingAdapter`/`setAnalyticsAdapter` in
   `observability/logger.ts`) but no concrete SDK (Sentry, Firebase, etc.)
   was specified/authorized to install in this sprint.
10. **iOS build/config validation was not run** — this development
    environment is Windows and has no Xcode. Only Metro bundling /
    TypeScript / Jest were exercised. Android build validation likewise
    requires the Android SDK, which is not installed here — see the final
    implementation report for exactly what ran vs. what is a documented
    limitation.

## P1 — introduced by CUSTOMER-L5-01

11. **Grace-period version policy is not wired end-to-end.**
    `version-policy.ts#evaluateVersionPolicy` implements and tests
    `belowMinimumSinceIso`-based grace periods, but `startup-service.ts`
    does not yet persist "when did this device first fall below the
    minimum version" or pass it in — so a configured grace period is
    currently inert in the running app even though the policy function
    supports it. Needs a small persisted timestamp in
    `preference-storage.ts` plus one wiring change once a real grace-period
    product requirement exists.
12. **Universal links / Android App Links are not functional.** Only the
    custom `serviceos://` scheme works end-to-end. `app.serviceos.in` in
    `deep-link-parser.ts`'s trusted-host list is a placeholder — no real
    domain, no `apple-app-site-association`/`assetlinks.json`, no
    `ios.associatedDomains`/`android.intentFilters` native config. See
    `deep-linking.md` §7.
13. **No React component tests for the new system screens**
    (Startup/StartupError/Offline/Maintenance/MandatoryUpdate/
    UnsupportedBuild/AppUnavailable/BaselineLanding). Deprioritized in favor
    of the pure-logic layer (state machine, resolver, validators, policy
    evaluators) — see `CUSTOMER-L5-01-testing-evidence.md`.
14. **No integration test exercises `runStartup()` end-to-end** against a
    mocked network — each piece it orchestrates is unit-tested in isolation
    instead.
15. **Config integrity has no cryptographic signature** — see
    `remote-configuration.md` §2. Origin + environment + marketplace
    binding is the full trust model today; a config can never return
    `"trusted"`, only `"unverified"` or `"rejected"`.

## P2 — introduced by CUSTOMER-L5-01

16. **Total startup timeout (12s) is documented but not separately
    enforced as its own timer** — only the individual per-operation
    timeouts (e.g. 8s remote-config fetch) actually fire. See
    `startup-failure-matrix.md`.
17. **Optional-update dismissal banner (`OptionalUpdatePrompt`) is built
    but not mounted anywhere** — no screen currently renders it, since the
    only production screen this sprint (`BaselineLandingScreen`) doesn't
    have a natural place for a promotional-adjacent banner yet. It is
    exported and tested-by-construction (pure logic reused from
    `version-policy.ts`) but needs a real Home screen to live on.
18. **`unsupported-os` version-policy outcome is unreachable** — the schema
    has no OS-version field yet, so this compiled outcome exists for future
    use but nothing produces it today.
19. **No `AppUnavailableScreen`/`UnsupportedBuildScreen` copy differentiates
    by specific reason** (region vs. tenant-suspended vs. schema
    incompatibility all show the same generic message) — the route params
    (`{ reasonKey: string }`) support per-reason copy but no caller
    currently passes a specific one.

## P1 — introduced by CUSTOMER-L5-02

20. **Pre-existing `LegacyApp` login screen calls non-existent backend
    paths.** `src/lib/api.ts#authApi` calls `/v1/auth/customer/otp-request`
    etc., which do not exist on the real backend (`/v1/auth/otp/send` is
    the real path). Discovered, not fixed — the legacy screen and its
    `AuthContext` are out of this sprint's scope; the new
    `features/auth/api/auth-api.ts` uses the verified real paths instead.
    See `CUSTOMER-L5-02-backend-contract-audit.md`.
21. **No component tests for `OtpLoginScreen`/`ProfileScreen`.**
    Deprioritized in favor of the pure-logic layer (validation, session
    mapping, session store, session bootstrap) — same rationale as
    CUSTOMER-L5-01 item 13.
22. **`AuthPlaceholderState` values `"expired"`/`"locked"` are unreachable.**
    Only `"unknown"`/`"guest"`/`"authenticated"` are produced by
    `bootstrapSession()` this sprint. The backend's `ACCOUNT_LOCKED` error
    exists but only on the email+password login path, which the OTP-based
    customer flow doesn't use.

## P2 — introduced by CUSTOMER-L5-02

23a. **`OtpLoginScreen`/`ProfileScreen`/`BaselineLandingScreen`'s new
    auth-related strings are not yet localized** (hardcoded English) —
    CUSTOMER-L5-00's i18next infrastructure and `startup`/`common`
    namespaces are in place and proven; a dedicated `auth` namespace with
    en/hi/pa translations was not added this sprint due to time, unlike
    CUSTOMER-L5-01's system screens which are fully localized. This is a
    real gap, not a design decision.
23. **No avatar upload, phone-number change, or MFA setup** — see
    `customer-profile.md` "Not Implemented This Sprint".
24. **No "sign out everywhere" (`/v1/auth/logout-all`) UI.**
25. **`useLogout` doesn't clear TanStack Query caches** — harmless today
    (no customer-specific query data exists yet), but must be added
    (`queryClient.clear()` or scoped `removeQueries`) once a later sprint
    introduces cached customer-specific data (bookings, recent activity).

## P1 — introduced by CUSTOMER-L5-03

26. **Home's locale is hardcoded to `"en"`** (`useHomeCategories("en")` in
    `HomeScreen.tsx`) rather than reading the active i18next locale —
    the query key already has a `locale` dimension ready for this, but no
    call site threads the real value through yet.
27. **No component tests for `HomeScreen`/`CategoryCard`/`CategoryGrid`.**
    Same rationale as every previous sprint.
28. **No analytics events wired** (`home_viewed`, `category_selected`,
    etc.) — no vendor authorized yet, consistent with every previous
    sprint's same gap for its own screens.
29. **Category press does not navigate anywhere** — shows a toast instead.
    Correct for this sprint (no category-detail screen exists — CUSTOMER-
    L5-04), but is a real functional gap once that screen exists and this
    wiring needs to be revisited.

## P2 — introduced by CUSTOMER-L5-03

30. **No disk cache for category data** — TanStack Query in-memory cache
    only. See `home-cache-and-refresh-policy.md` for the reasoning and the
    reusable pattern (`remote-config-cache.ts`) to follow if this becomes
    necessary.
31. **No semantic icon mapping** — every category shows the same generic
    fallback icon, since the backend returns an image URL, not a compiled
    semantic icon key. See `catalogue-and-discovery.md` "Icon Policy".
32. **`offeringSummarySchema`/`homeApi.listOfferings` are built and tested
    but unused** — no service-detail screen exists yet to call them from.
33. **Home doesn't refresh on app-resume-after-interval or locale/logout
    changes** — see `home-cache-and-refresh-policy.md`.

## Explicitly Not Started (correctly out of scope per sprint brief)

CUSTOMER-L5-00: customer authentication, service discovery, booking,
provider matching, pricing, bargain, payments, tracking, notifications,
rewards, support workflows.

CUSTOMER-L5-01: complete authentication/OTP, customer profile, home
discovery, booking, pricing, provider matching, bargain, payment, tracking,
notification-center, rewards, review, support workflows — only their route
identifiers and access-policy placeholders were reserved.

CUSTOMER-L5-02: signup with password, email verification, MFA, password
reset, session/device management UI, avatar upload.

CUSTOMER-L5-03: category listing/filtering, service detail, full search,
booking assistant, diagnostic questions, media upload, address creation,
serviceability selection, provider matching, pricing, bargaining, booking
review, tracking, parts approval, notifications inbox, rewards, reviews,
support cases, marketplace modules (no backend contract exists), campaigns,
recommendations, recent activity (no backend contract exists for any of
these three).

CUSTOMER-L5-02: signup with password, email verification, MFA, password
reset, session/device management UI, avatar upload — real OTP login,
secure token storage, and basic profile view/edit were implemented; the
rest is deferred (see P1/P2 items above).
