# Auth / Session / Logout Smoke Report (Part 9)

All via Playwright real Chrome, `admin-shell-e2e02.spec.ts`:

1. **Logged-out redirect**: navigating directly to `/admin/dashboard` with no token redirects to
   `/login` — PASS (`AdminShellInner`'s effect checks `localStorage["serviceos_admin_token"]` and
   force-navigates if absent).
2. **Login reaches dashboard**: `admin@serviceos.in` / `Password123!` via UI form reaches an
   admin route with sidebar+header rendered — PASS.
3. **Logout**: clicking the logout icon button calls `authApi.logout()` then clears the token and
   navigates to `/login` — PASS, confirmed back at `/login` after click.
4. **Corrupted/invalid token**: set `localStorage["serviceos_admin_token"] = "corrupted.invalid.token"`
   then navigate to `/admin/dashboard` — actual behavior observed: redirected back to `/login`
   (not a dedicated "session expired" banner/message, just a silent bounce to the login screen).
   This is a real, minor gap vs the spec's phrasing ("shows session-expired state") — the effect
   only checks presence of a token string, not its validity; the real 401 from the first API call
   (`getEffectiveMenu()`) is swallowed (`.catch(() => {})`) rather than triggering an explicit
   "session expired, please log in again" state. Documented as a gap, not fixed (would require
   adding 401-interceptor logic across `lib/api.ts`, broader than shell-only scope).
5. **Role label**: topbar shows literal text "Platform", not the actual role name — see Part 4.
6. **No token visible in UI text**: asserted `bodyText` does not match a raw JWT pattern on the
   login/dashboard screenshot — PASS in both the pre-existing foundation spec and the new one.

Evidence: `frontend/e2e-admin-tenant/evidence/e2e02/shell-dashboard.png`,
`corrupted-token.png`, `corrupted-token-url.txt`.
