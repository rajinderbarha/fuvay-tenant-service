# Design Governance Rules (UX-02)

1. **Nav visibility is never an authorization boundary.** Every `readOnlyBehavior`/`canonicalRoles`
   field on a nav item is a UX convenience. Real access control is enforced server-side
   (`app.core.permissions.ROLE_PERMISSIONS`) regardless of what the frontend shows or hides.
2. **Only 5 canonical admin roles exist**: `super_admin`, `admin_operations`, `admin_finance`,
   `admin_security`, `admin_readonly`. Never invent a new role name in UI code, fixtures, or docs.
3. **No raw hex colors in feature components.** All UX-02 components use design-system CSS custom
   properties (`var(--border)`, `var(--brand)`, etc.) or design-system components — never inline
   hex literals.
4. **No second status-color system.** All status presentation goes through the existing
   `StatusBadge` from `@serviceos/design-system`; new status vocabularies (e.g. security
   observation statuses) extend its existing tone-mapping rather than introducing a parallel one.
5. **Readiness states are dev metadata, never shown to real users.** `ReadinessTag` only appears in
   dev-showcase pages and internal docs — production pages never render a raw `MOCK_DESIGN_ONLY`
   string to an end user.
6. **Finance presentation must never conflate** platform package credit, commission, security
   deposit, and ordinary job payments. No payout/withdrawal UI, because ServiceOS does not process
   ordinary on-site job payments.
7. **Security status language must never overstate.** A static observation is `observation` or
   `needs_verification`, never presented as a confirmed live incident.
8. **No fabricated build/test success anywhere in this doc set.** Every claim of "tested" or
   "built" is qualified by whether it was actually executed.
