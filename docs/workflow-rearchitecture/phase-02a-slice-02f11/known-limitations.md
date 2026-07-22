# Known Limitations — Slice 2F-11

1. **Technician is admitted on the 3 read routes but excluded from all
   11 mutations** — a deliberate, evidence-neutral asymmetry (see
   `product-decisions-required.md` item 1), not a proven defect.
2. **This module implements only lead-execution lifecycle tracking** —
   no property, listing, media, viewing-as-a-distinct-record, or offer
   capability exists to protect, verify, or align frontend controls for.
   Every workstream targeting those capabilities is honestly reported as
   `UNSUPPORTED_CAPABILITY` throughout this slice's documentation.
3. **`app.engines.real_estate_lead` (lead draft/intake creation) was not
   audited this slice** — a distinct module, out of scope per "do not
   begin another real-estate module."
4. **`app.engines.final_records`'s read-only lead list/detail routes were
   not independently re-verified beyond confirming they contain no
   mutation** — a lightweight grep-based check, not a full authorization
   audit (those routers' own closures, if any, are out of this slice's
   scope).
5. **The historical 182-route CSV total does not match a direct raw
   row-count** (185 rows found) — a pre-existing discrepancy, not
   investigated or reconciled this slice (see `global-coverage-update.md`).
6. **Global tenant-mutation remaining-module-count was not recomputed**
   this slice — would require a platform-wide re-audit beyond this
   module's scope.
