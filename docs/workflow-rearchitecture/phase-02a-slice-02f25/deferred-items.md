# Deferred Items — Slice 2F-25

| Item | Reason deferred | Next step |
|---|---|---|
| Migrate/retire the legacy review engine | Migration and record movement explicitly out of scope | Product decision — #1 |
| Repair the broken legacy reply contract | Would enable a dead write path into the superseded table | Product decision — #2 |
| Tenant-portal `resolve` control (403 for tenants) | Frontend/persona decision | Product decision — #3 |
| Scope the three remaining non-content reads | Needs a persona decision about aggregate/request visibility | Product decision — #4 |
| Application-wide persona-based route re-sweep | Out of scope; this slice reconciled one engine | Dedicated inventory slice — see `known-limitations.md` #1 |
| Narrower reputation permission for review actions | Would require a new permission | Product decision — #5 |
| Remove the unreachable `create_review` service method | Cleanup | Optional cleanup slice |
| Live E2E authorization tests | No DB/server available | Run where a live stack exists |
| Slice-2D canaries | Explicitly prohibited | Requires `tenant-readonly-decision.md` conclusion |
| Package Commerce / compliance / customer_reviews carried items | Prior slices' product decisions | As recorded in those slices |

## Remaining authorization queue
**7 modules / 17 routes** remain unprotected —
`remaining-module-queue-update.csv`. No new module was begun.
