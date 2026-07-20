# Deferred Items — Slice 2F-26

| Item | Reason deferred | Next step |
|---|---|---|
| Implement authorization for the 26 newly discovered unprotected routes | This is an inventory slice; implementation explicitly out of scope | Module-selection slice, then implementation slices |
| Adjudicate the 123 MIXED_PERSONA mutations | Largest remaining classification population | Follow-up inventory slice |
| Resolve the 7 held single-evidence candidates | Two-source rule not met | Same follow-up |
| Re-examine the 55 classifier disagreements | Retained; tool limitation, not capability absence | Deepen AST following, or hand-adjudicate |
| Deepen AST following beyond depth-2 / cross-engine | Precision-vs-recall tradeoff chosen deliberately | Tooling slice |
| Object-ownership audit of the 28 additions | Requires per-route implementation work | Implementation slices |
| Narrow the swallowed `except Exception` in job close | Behaviour change, out of scope | Small hardening slice |
| Decide whether query-logging routes belong in the denominator | Policy | Product decision #2 |
| Re-verify the 145 read-only POST/PUT/PATCH routes | Excluded on side-effect evidence | Optional |
| Slice-2D canaries | Explicitly prohibited | Requires `tenant-readonly-decision.md` |

## Remaining queue
**11 modules / 43 routes** — `rebuilt-unprotected-module-queue.csv`. No module
was selected.
