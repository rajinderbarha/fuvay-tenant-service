# Route Enumeration Method

Same tooling as prior tranches (`inventory_mutation_routes.py`, re-run
fresh), plus a scripted bulk-extraction pass: for each of the 149
remaining classifier-`UNVERIFIED` routes, a Python script located the
`async def {endpoint}(` definition in its module's source and extracted
every `Depends(...)` call in the following ~600 characters (covering the
full function signature). This is faster than the fully manual,
line-by-line reading used for smaller batches in prior tranches, at the
cost of depth — flagged explicitly in `known-limitations.md`. Where a
guard pattern looked ambiguous or risky (bare `get_current_user`, or a
guard mismatch matching a previously-confirmed defect class), the actual
router and service source was read directly, not inferred from the
bulk scan alone — this is how the 2 real defects
(`chat.router::delete_message`, `compliance.router::record_consent`/
`withdraw_consent`) were found.
