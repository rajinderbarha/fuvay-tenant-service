# ServiceBooking Provenance Contract

New types in `lib/ux04/types.ts`: `SourceBookingReference` and
`JobProvenance`.

```ts
interface SourceBookingReference {
  sourceModel: "service_booking";
  sourceBookingId: string;
  resultingModel: "service_job";
  resultingServiceJobId: string;
}
interface JobProvenance {
  source: SourceBookingReference;
  sourceAdapter: string;
  serviceJobOnlySections: string[];
}
```

## Why this exists

UX-04A represented the ServiceBooking pipeline's "Booking Detail" by
reusing `ServiceJobFixture` directly (hiding job-specific sections) — an
honest but weak representation, because it gave the ServiceBooking side no
id of its own distinct from the ServiceJob id. This contract fixes that:
`SourceBookingReference` always carries BOTH ids, typed so a caller cannot
accidentally read one where the other is expected (`sourceBookingId` vs.
`resultingServiceJobId` are different field names, not a single shared
`id`).

## Known limitation, stated honestly

UX-03's fixture layer never generated a real, independent ServiceBooking
id — there is no backend-confirmed ServiceBooking record distinct from
its resulting ServiceJob in this codebase's design-fixture layer. Rather
than reuse the ServiceJob id under a different field name (which would
still silently conflate the two if a caller ever compared them), this
pass's `jobProvenanceFixture.source.sourceBookingId` is a clearly-labeled
**provisional** id (`"svcbk_provisional_7001"`, distinct prefix, not
derivable from or equal to `"sj_7001"`) — explicit that it is a
placeholder for a real backend-confirmed ServiceBooking id, not a stand-in
disguised as real data. This keeps the contract's TYPE guarantee (two
distinct fields, never substitutable) fully real and test-verified, while
being honest that the underlying VALUE is still provisional pending a real
backend contract (`product-decisions-required.md` item 7, carried
forward).

## Test coverage

`lib/ux04/__tests__/provenance.test.ts` (5 tests) proves: both ids are
present and never equal; `sourceModel`/`resultingModel` are always their
fixed literal values; pipeline labels stay distinct between field_ops.Job
and ServiceJob fixtures; `serviceJobOnlySections` keys never appear as
top-level keys on `FieldOpsJobDetailView`; `BookingFixture` rows never
carry ServiceBooking-shaped metadata keys.
