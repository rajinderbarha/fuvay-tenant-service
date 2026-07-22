# Product Decisions Required

Carried forward and narrowed from 2F-15B:

1. **Recovery of missing-history legacy Bookings.** Unchanged — any Booking row with no creation-history row, or an unrecorded/non-customer creation actor, fails closed by design. Recovering or re-attributing such rows (if any exist) requires a product decision this slice has no authority to make (data migration/audit, out of scope).

2. **First-ever assisted booking for a brand-new phone-order customer with zero prior relationship evidence.** Unchanged — this tension remains unresolved by design.

3. **Tenant-local customer directory / verified invitation workflow.** Would be the durable fix for both items above; out of scope.

4. **Historical creation-actor account-state re-validation.** This slice's actor-binding fix proves the creation actor WAS the Booking's own customer at creation time, but does not retroactively re-verify that customer's account is STILL active/non-deleted today (only the account being acted upon in the CURRENT request is re-validated). Whether a historical creation event by a since-deactivated customer account should continue to count as trustworthy provenance is a product question, not addressed this slice (see `known-limitations.md`).

5. **New provenance column / legacy-data remediation migration / database-level uniqueness constraint on `BookingStatusHistory`'s creation row.** Not added this slice — the actor-binding fix relies exclusively on the pre-existing `changed_by`/`changed_by_role`/`from_status` columns. If a future audit ever finds a genuine writer path capable of producing conflicting/duplicate creation rows, closing that would require its own migration-authorized slice.

6. **Database-level concurrency hardening.** Unchanged from 2F-15B — the recheck-based provenance pattern has the same theoretical TOCTOU characteristic as every other read-then-write authorization check in this codebase; not addressed this slice.
