# Qualifying Relationship Predicate (Final, Post-2F-14G)

## Disposition: PROVENANCE_AWARE_HYBRID

A customer has an established relationship with a tenant when **at least one** of:

1. A `Booking` exists with `tenant_id == principal tenant AND customer_id == requested customer
   AND status IN (confirmed, scheduled, dispatching, in_progress, completed,
   converted_to_job)`.
2. A `field_ops.Job` exists with `tenant_id == principal tenant AND customer_id == requested
   customer AND (booking_id IS NOT NULL OR parent_job_id IS NOT NULL)`.

## Why PROVENANCE_AWARE_HYBRID (not ANY_HISTORICAL, not ACTIVE_OR_COMPLETED_ONLY, not
## CUSTOMER_ORIGINATED_ONLY)

- **Not `ANY_HISTORICAL_SAME_TENANT_RELATIONSHIP`** (Slice 2F-14F's original predicate): proven
  exploitable — a tenant_owner could fabricate a `PENDING_CONFIRMATION` Booking for an unrelated
  real customer with zero validation and zero customer participation, immediately satisfying it.
- **Not `ACTIVE_OR_COMPLETED_RELATIONSHIP_ONLY`** in the naive sense: this slice's actual
  predicate IS effectively "only statuses reachable via confirmation," which happens to overlap
  heavily with "active or completed," but the justification is provenance-based (structural
  reachability through `BS.CONFIRMED`), not merely "is this booking currently active" — `cancelled`
  is excluded even though a cancelled booking might have been active moments before, precisely
  because *current* status alone can't prove it passed through confirmation.
- **Not `CUSTOMER_ORIGINATED_RELATIONSHIP_ONLY`**: would incorrectly exclude every
  tenant-assisted booking and every legitimately tenant-created repair/follow-up Job, which are
  real, evidenced product capabilities (e.g. a tenant_owner confirming a phone-booked customer's
  request) — over-restrictive relative to the evidence.
- **Chosen: `PROVENANCE_AWARE_HYBRID`** — combines Booking **status** (proving the tenant's own
  confirmation gate was passed) with Job **lineage fields** (`booking_id`/`parent_job_id`,
  proving structural derivation from an already-validated source) — the narrowest predicate
  supported by existing data that closes the proven bootstrap vector without requiring a new
  model, migration, or invented provenance marker.

## Explicitly not fully closed (disclosed)

The residual gap — a tenant_owner can self-confirm their own fabricated Booking — is NOT closed
by this predicate, since `BS.CONFIRMED` alone cannot distinguish a genuinely customer-engaged
confirmation from a self-serving one without modifying `BookingService.confirm_booking` itself
(out of this slice's scope). See known-limitations.md and relationship-evidence-threat-model.md.
