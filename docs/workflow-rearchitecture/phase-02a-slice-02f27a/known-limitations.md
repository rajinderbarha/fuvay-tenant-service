# Known Limitations - Slice 2F-27A

1. Both added routes are UNPROTECTED; this slice records them, it does not fix
   their authorization (out of scope).
2. The other 59 mixed-persona add-candidates remain unadjudicated
   (PENDING_INDEPENDENT_OR_MODULE_LEVEL_ADJUDICATION).
3. The enforcement matrix is module-aggregated, not per-route; its historical
   TOTAL row uses a different (182) convention and was not force-reconciled.
4. The repo has ONE canonical tenant-mutation inventory CSV, not two; the
   mission's 'both CSVs' wording is addressed in documentation-corrections.md.
