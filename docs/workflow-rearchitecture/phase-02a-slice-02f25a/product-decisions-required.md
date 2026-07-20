# Product Decisions Required — Slice 2F-25A

## 1. Should provider aggregate ratings be public?
`get_aggregate` is now tenant-scoped because no public-entity allow-list
exists. Public provider ratings are a normal marketplace feature; building one
requires an explicit allow-list of public `entity_type` values plus proof that
hidden/rejected reviews do not contribute. **Not invented here.**

## 2. Job-status gating for review requests
`create_request` does not check the Job's status. The internal caller only
fires on job close, but the HTTP route would accept any job in the tenant.
Which job states may solicit a review is a product decision.

## 3. Same-tenant granularity
Two places permit any principal of the owning tenant to read tenant-wide data:
`get_review_request` (any tenant principal sees any of its tenant's request
statuses) and `list_by_customer` (any tenant principal sees its tenant's
reviews for a given customer). Narrowing to an explicit tenant-customer or
assignment relationship would be new policy.

## 4. Technician access
Technicians currently fall under the tenant predicate rather than an
assignment check. Whether technicians should see only their assigned jobs'
review data is undecided.

## 5. Hidden/rejected review states in customer lists
`list_by_customer` returns `status` as-is, including flagged/removed states,
for the tenant's own rows. Whether to filter is a product decision.

## 6. Retire or migrate the legacy engine — carried from 2F-25
Still the primary open question. Two secured review stacks now coexist.

## 7. The broken legacy reply contract — carried from 2F-25
Portal sends `reply_text`; route reads `body["reply"]` (500). Repair, remove
the control, or retire the route.

## 8. Application-wide persona sweep
2F-25 proved the prefix convention can miss genuine tenant mutations. A
persona-based sweep is the only way to turn CURRENT_CANONICAL_COVERAGE into a
proven application-wide figure. Real cost; explicitly out of scope here.
