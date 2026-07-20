# Known Limitations

1. **The 200 already-protected rows were not individually re-walked this
   slice** — only the 26 unprotected rows were directly re-verified
   against the live mounted application. The 200 were re-confirmed only
   in aggregate (total row count, `VERIFIED` set membership count) via
   the canonical CSV, consistent with this slice's discovery/reconciliation
   scope (Workstream 1-2 explicitly target "remaining rows," not the
   full 226). No evidence surfaced during this investigation suggesting
   any of the 200 needed re-verification.

2. **Frontend/mobile caller investigation for the selected module was
   explicitly deferred** to the implementation slice, per this slice's
   own mission scope (a discovery/selection slice does not need caller
   evidence to select a module, only to plan its eventual fix).

3. **The out-of-router compliance-export-generation worker was not
   located** during this investigation — flagged in
   `product-decisions-required.md` item 3 for the implementation slice to
   resolve before claiming `generate_export`'s full closure (only the
   QUEUEING route itself is in this slice's evidence base).

4. **`admin_catalog`'s three sub-routers were kept as three separate
   module entries** (not merged into one), per Workstream 4's explicit
   instruction not to group unrelated routers solely because they share
   an engine directory — even though they are recommended for BUNDLING in
   a future slice's SCHEDULING, they remain distinct MODULES in this
   slice's grouping/risk-scoring/queue documents.

5. **Live-database tests were not run** (no Postgres instance available
   in this environment) — consistent with every prior slice; this
   slice's own new suite is fully mock/introspection-based and required
   no database at all.
