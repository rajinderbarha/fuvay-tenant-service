# Known Limitations — Slice 2F-12A

1. **Cancellation is business-wide, not assignment-limited, for canonical
   staff** — this is the VERIFIED, intentional, approved (2F-3B
   cross-module) policy, not a limitation in the defect sense; recorded
   here for completeness. A canonical staff member of the correct tenant
   may cancel any same-tenant appointment, not only their own assigned
   ones. This differs from the 7 execution mutations (assigned-actor-only)
   by deliberate design (cancellation is an administrative action;
   execution actions require the assigned coach).
2. **`actor_role="provider"` is a coarse audit label** (not the granular
   tenant_owner/staff role) — consistent with the sibling `cancel_job`,
   documented, not changed.
3. **Cancellation reason has no maximum-length validation** — matches the
   sibling `cancel_job`; no defect proven, not changed.
4. **No notification is sent on cancellation** — no notification
   infrastructure exists in this module; pre-existing, not built.
5. **No frontend surface exists** for the cancel route — backend-only in
   terms of active UI callers.
6. **`app.engines.coaching_appointment`'s own authorization was
   documented, not hardened** — out of scope.
