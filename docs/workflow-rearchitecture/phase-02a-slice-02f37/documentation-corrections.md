# Documentation Corrections

## Frozen-contract conflict discovered and resolved

This slice's verbose mission prompt (Workstreams 7-12) instructed active
remediation of the N01 domain-integrity backlog, directly contradicting
the actual frozen Slice 2F-34 `slice-2f37-implementation-contract.md`
(which explicitly forbids touching N01 media files and instructs
freezing, not remediating, the backlog). This is not a "correction" to
a prior slice's artifact — the frozen contract itself is authoritative
and was followed as written. See `n01-final-status.md` for the full
reasoning; `frozen-scope-verification.md` documents the conflict.

## Self-caught adjudication error (corrected before any test was written)

`POST /v1/bookings`-style cross-checking during this slice surfaced no
equivalent error, but a parallel check on `POST /v1/pricing/tenants/{tenant_id}/rules`
was initially mis-classified during triage (drafted as excluded, then
corrected to `TENANT_PROVIDER_MUTATION_ADD` after confirming it has no
existing customer-facing alias) — caught during the held-route
adjudication pass itself, before any canonical CSV write.

## Cascading historical test rebaselines

18 pre-existing historical test files (2F-14A through 2F-27A, including
all 4 classifier-corpus files 2F-26E/F/G/H) asserted the live canonical
CSV's total/protected/unprotected counts and classifier
tenant_direction/persona exceptions inline; each was individually
updated at its exact assertion line to the new 313/313/0 figures and
extended exception sets, with attribution comments. No frozen point-in-
time slice artifact was rewritten. See the exact list of exemption
additions in each file's own diff (not duplicated here to avoid
rewriting historical evidence by reference).
