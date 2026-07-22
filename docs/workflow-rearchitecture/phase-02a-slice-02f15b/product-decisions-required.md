# Product Decisions Required

Carried forward from 2F-15A, narrowed by this slice's provenance proof work:

1. **Recovery of missing-history legacy Bookings.** Any Booking row (if any exist) with no creation-history row at all, or with an unrecorded/ambiguous creation actor, now demonstrably fails closed at runtime (see `missing-history-legacy-behavior.md`) — this is a correct security posture, but it means such rows can NEVER establish relationship authority or convert to a Job until a product decision is made about how to recover or re-attribute them (a data migration/audit, explicitly out of scope this slice).

2. **First-ever assisted booking for a brand-new phone-order customer with zero prior relationship evidence.** Unchanged from 2F-15A — this exact tension remains unresolved by design, requiring either an onboarding/invitation flow or a deliberate first-booking exception, neither of which this slice has authority to invent.

3. **Tenant-local customer directory / verified invitation workflow.** Would be the durable fix for both items above; explicitly out of scope for this slice (and all prior slices in this initiative).

4. **New provenance column / legacy-data remediation migration.** This slice deliberately did NOT add either — the entire creation-provenance mechanism proven this slice relies exclusively on the pre-existing `BookingStatusHistory.changed_by_role` field. If a future slice determines the existing mechanism is insufficient (e.g. because a genuine gap in writer coverage is found), that would require its own dedicated migration-authorized slice.

5. **Database-level concurrency hardening.** Not evaluated this slice (out of scope) — the provenance re-check pattern (rather than a persisted trust flag) reduces but does not eliminate a theoretical TOCTOU window between the independent-evidence check and the subsequent Booking/Job write, matching the same characteristic already present in every prior slice's read-then-write authorization checks in this codebase.
