# Route Classification Contract

13 categories as specified in this slice's mission. One genuine taxonomy
observation from real classification work (not a category invention):

## `CUSTOMER_SELF_SERVICE_MUTATION` broadened for self-account operations

Routes like `logout`, `mfa/*`, `password/change`, `sessions/{id}` require
only `Depends(get_current_user)` and act exclusively on the caller's own
account/session — no arbitrary ID is ever trusted, and the "resource"
being mutated is the principal's own identity/session record. This
matches the category's defining criteria (WS7: "authenticated principal,
no arbitrary ID trust, owns the affected resource") even though these
routes are reachable by any authenticated role, not only customers. Given
the 13-category list is fixed and none of the other 12 fit better
(`PLATFORM_INTERNAL_MUTATION` implies an internal-only caller, which these
are not), this slice classifies them as `CUSTOMER_SELF_SERVICE_MUTATION`
under a documented broadening rather than inventing a 14th category. This
is recorded explicitly here so it is a visible interpretation, not a
silent stretch — see each row's evidence column in
`final-route-classification.csv`.
