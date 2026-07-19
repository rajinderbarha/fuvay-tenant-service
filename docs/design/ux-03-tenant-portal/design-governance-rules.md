# Design Governance Rules (Tenant Portal)

1. Nav visibility is never an authorization boundary — the backend
   (`app/core/permissions.py`) is the sole enforcement point. Every
   `Ux03NavItem` carries this caveat implicitly; it is stated explicitly in
   `lib/ux03/nav-ia.ts`'s file header.
2. Only `tenant_owner`, `staff`, `technician` are canonical tenant roles.
   Job titles are descriptive labels, never authorization. Enforced by
   `nav-ia.test.ts`.
3. `StaffPermission` denial is explicit and must render distinctly from
   absence-of-grant; a grant never overrides an explicit deny anywhere in
   the UI.
4. Booking (`field_ops.Job`) and ServiceJob pipelines are never merged;
   every row/detail carries a `PipelineBadge`.
5. `PartsRequest` is ServiceJob-only; technicians never get install
   authority.
6. Package credit, commission, and security deposit are three separate
   concepts, never one balance; no payout/withdrawal/settlement UI.
7. Tenant prices must show platform min/max and flag below-minimum values.
8. Customer cancel/reschedule on the canonical booking pipelines is
   unresolved — never presented as production-ready.
9. Geo/service-area mutation defaults to read-only/mock unless a specific
   action is confirmed inside the frozen-slice authorization scope.
10. Media never surfaces storage keys, signed URLs, or credentials.
11. Audit/activity views are tenant-scoped only — never platform-wide.
12. No raw hex colors in feature components — design-system tokens only
    (verified by inspection of every new file this phase: all colors are
    `var(--...)` references).
13. No duplicate status registry — `statusRegistry` in
    `@serviceos/design-system` is the single source; new keys are additive
    only.
