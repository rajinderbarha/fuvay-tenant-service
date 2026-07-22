# Known Limitations

- No live database/server verification was performed (unit tests + static route introspection only), consistent with every prior slice in this initiative.
- Provenance checks rely on `BookingStatusHistory.changed_by_role` recorded at creation time. If this history row is ever missing (e.g. a hypothetical direct DB insert bypassing the service layer), the Booking is treated conservatively as non-customer-originated (fails closed), which is correct for security but has not been tested against an actual production data audit.
- The "independent relationship evidence" check only looks at OTHER Bookings/Jobs for the same tenant+customer; it does not (and per this slice's out-of-scope list, should not) build any new customer-directory or cross-tenant identity model.
- `add_note`'s customer-exclusion is evidence-based (no live caller found), not derived from an explicit product decision that customers should never add booking notes — if such a feature is added later, it needs its own dual-persona treatment (see `add-note-authorization.md`).
- Coverage denominator (220) reflects only the routes accumulated across this initiative's own slice history, not a full-codebase audit.
