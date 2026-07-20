# CUSTOMER-L5-02 — Known Gaps (Deepened Pass)

Supplements the cross-sprint `known-gaps.md`. Items here are specific to
this deepened CUSTOMER-L5-02 pass; items already listed in `known-gaps.md`
(signup UI, avatar upload, phone re-verification, localization of auth
strings, etc.) are not repeated.

## P0 — must close before a real production launch

1. **No live runtime certification was performed** — see
   `CUSTOMER-L5-02-runtime-evidence.md`. This is the single largest reason
   the gate decision is PARTIAL rather than PASS. Everything else in this
   document is secondary to this.

## P1

2. **Account-disabled and wrong-code OTP errors are indistinguishable to
   the customer.** Both map to `ApiError.category === "unauthorized"` —
   the backend itself doesn't differentiate them in this contract (see
   failure matrix). A disabled customer sees "Incorrect or expired code"
   forever with no path forward. Closing this requires either a backend
   contract change (a distinct error code) or accepting the ambiguity as a
   permanent product tradeoff — not decided this pass.
3. **Consent and account-deletion are MISSING_BACKEND**, not deferred by
   choice — see `CUSTOMER-L5-02-profile-contract.md`. No UI was built for
   either, per the explicit instruction not to fabricate a contract that
   doesn't exist.
4. **Signup UI was not built** even though `POST /v1/auth/register/customer`
   is real and wired into `auth-api.ts` — the OTP-verify flow this sprint
   implements already auto-activates an *existing* customer;
   whether/how a brand-new phone number should trigger the register
   endpoint (vs. `/otp/verify` returning a "no account found" error) is a
   product-flow decision not made this pass. `authApi.registerCustomer` is
   tested-by-construction (typed, matches the real contract) but has zero
   call sites.
5. **Multi-tenant/marketplace isolation is UNVERIFIED**, not proven false
   or true — this environment only has one marketplace to test against.

## P2

6. **No analytics events wired** for any auth/profile action — consistent
   with every previous sprint's identical gap (no vendor authorized).
7. **`useSessions`/`profile-queries.ts` query keys have no per-customer
   dimension.** Mitigated (not eliminated) by `queryClient.clear()` on
   logout/logout-all — the cache is fully wiped between sessions, but the
   underlying query-key design itself remains generic rather than
   customer-scoped. A defense-in-depth improvement, not required given the
   clear-on-logout fix, but noted for consistency with CUSTOMER-L5-03's
   own query-key guidance.
8. **No dedicated "session expired" screen.** An expired/revoked session
   is handled by silently clearing local state and letting the normal
   guest experience take over (`BaselineLandingScreen`'s "Sign in" button)
   rather than a screen explaining *why* the customer was signed out.
9. **Offline-specific error copy is missing** — `network_error` currently
   shares the same generic message as `server_error`/`timeout` in
   `useOtpFlow.ts#safeErrorMessage`.
10. **No component tests** for the three new/modified screens
    (`OtpLoginScreen`, `ProfileScreen`, `SessionsScreen`).
11. **Profile update has no dirty-state/conflict detection** — `full_name`
    saves unconditionally on button press; there is no distinct-from-
    original-value check, and the backend has no version/ETag field to
    detect a concurrent edit from another device (see failure matrix —
    MISSING_BACKEND for conflict detection specifically).
12. **`useLogout`/`useLogoutAll`'s `queryClient.clear()` call has no
    dedicated automated test** confirming cache clearing specifically
    (the existing tests confirm session clearing, which is the
    security-critical part, but not the cache-clearing line itself).

## Deliberately Not Attempted (per sprint brief's own prohibitions)

- No password-based login (not requested, OTP-only is the real supported
  flow).
- No social sign-in (unsupported by backend).
- No fake session listing or fake account deletion.
- No claim of "Level 5" status for the app as a whole.
