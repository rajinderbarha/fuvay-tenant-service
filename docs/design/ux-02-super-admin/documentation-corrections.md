# Documentation Corrections

No prior UX-02 documentation existed to correct — this phase's docs are the first full set for
UX-02. The one correction made mid-phase was to this phase's own file hygiene:
`frontend/super-admin/tsconfig.tsbuildinfo` (a generated TypeScript incremental-build cache file)
had been accidentally left trackable; it was `git rm --cached` and added to `.gitignore` early in
this session so it never gets committed as if it were meaningful source.

If a future engineer finds a factual error in any UX-02 doc (e.g. a component prop name that
drifted after this phase), record the correction here with a date and the corrected file, rather
than silently editing history.
