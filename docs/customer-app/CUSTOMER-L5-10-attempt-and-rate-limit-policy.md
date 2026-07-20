# CUSTOMER-L5-10 — Attempt and Rate-Limit Policy

## There Is No Attempt Limit or Rate Limit for This Flow

Exhaustively verified this sprint:

- `BargainRule.max_attempts` is a real column but is never read anywhere
  in `app/engines/home_service_booking/` — only stored/echoed by the
  admin-only `BargainRule` CRUD (`admin_catalog/service.py:2696`), and
  belongs to the same feature-flagged-off manual-bargain module documented
  in `counteroffer-contract.md`.
- `app/core/security.py:44-61`'s `RATE_LIMITS` table covers exactly:
  `auth:login`, `auth:login_phone`, `auth:otp_send`, `auth:otp_verify`,
  `auth:password_reset`, `auth:refresh`, `auth:mfa_verify`,
  `auth:register`, `api:read`, `api:write`, `api:ai`, `api:export`,
  `webhook:delivery`. No `home_service_booking`, `pricing`, or
  `bargain`-related key exists.
- `rate_limiter.check_and_raise`/`.check(` is called from exactly 4 files:
  `app/engines/auth/router.py`, `app/engines/enterprise_grid/router.py`,
  `app/engines/platform_commerce/router.py`, `app/engines/rag/router.py`.
  `home_service_booking/customer_router.py`'s `confirm_price_choice` route
  has no `rate_limiter` dependency — its only two dependencies are
  `Depends(_svc)` and `Depends(get_current_user)`.
- No app-wide rate-limiting middleware exists in `app/main.py`.
- No `cooldown`/`Retry-After`/`attempts_remaining` field of any kind
  exists in `confirm-price-choice`'s response.

## Consequence for This Sprint's UI

No attempt counter, no cooldown timer, no "please wait before trying
again" message, and no `Retry-After`-aware backoff logic were built — none
of them have any real backend behavior to reflect. The only
"repeat-submission" behavior this sprint implements is the plain,
real-behavior-matching fact that `confirm-price-choice` is safely
re-callable at will (documented in `bargain-architecture.md`) — the UI's
only self-imposed limit is a simple duplicate-tap guard
(`disabled={isConfirming}`), which exists purely for UX responsiveness,
not because the backend enforces any submission cap.

## Abuse Prevention — Honest Accounting

Per §57's requirement to "inspect backend controls for repeated low
offers... automation... rapid submissions," the finding is that this
specific flow has none. This is not a gap this sprint introduced or can
fix — the backend genuinely applies no rate limiting or abuse-specific
control to `confirm-price-choice` or `match-and-price` today. This is
documented prominently as a real, disclosed backend limitation in
`known-gaps.md`, since it is a legitimate product/security concern (a
customer could, in principle, call `match-and-price` and
`confirm-price-choice` repeatedly with no backend-side throttling) — but
building a fake client-side rate limiter to paper over a real,
server-side gap would be misleading, not a fix, and was therefore not
done.
