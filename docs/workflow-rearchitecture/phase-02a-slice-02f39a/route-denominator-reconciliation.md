# Route Denominator Reconciliation

| Metric | Before (2F-38/39) | After (2F-39A) |
|---|---|---|
| Mounted route records | 2,320 | 2,320 (unchanged) |
| Total auto-detected mutation-like records | 1,186 | 1,186 (unchanged — auto-classifier not re-run per-route after manual classification; manual classification supersedes the auto label for the 32 `auth.router` routes) |
| Confirmed canonical tenant/provider mutations | 313 | **321** (+8, see `canonical-mutation-additions.csv`) |
| Confirmed platform-admin mutations (this slice's evidence only) | not separately tracked | 2 (`impersonate`, `end_impersonation`) |
| Confirmed public/callback mutations (this slice's evidence only) | not separately tracked | 9 (`login`, `register_customer`, password-reset ×2, otp ×2, `refresh_token`, `introspect_token`, `accept_invite` — see `final-route-classification.csv`) |
| Confirmed customer-self-service mutations (broadened, this slice's evidence only) | not separately tracked | 13 |
| Classifier-`UNVERIFIED` / genuinely unresolved | 261 | **229** (-32, all of `auth.router` resolved) |

**313/313 is no longer the accurate canonical denominator.** The honest,
evidence-backed figure after this slice is **321 canonical tenant/provider
mutations, 321 protected, 0 unprotected** for the routes actually
inspected. `verify_2f37.py`'s own hardcoded 313/313 expectation was not
updated this slice (that script is Slice 2F-37's frozen verifier, out of
this slice's file-ownership scope to rewrite arbitrarily) — see
`known-limitations.md` for this reconciliation gap.
