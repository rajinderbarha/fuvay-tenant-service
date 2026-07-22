# Product Decisions Required — Slice 2F-25

## 1. Retire or migrate the legacy review engine — PRIMARY
Two live review stacks now exist, both secured. `customer_reviews` is
canonical; `app.engines.review` is superseded but still writable (reply, flag,
resolve, review-requests) with a live tenant-portal caller. Options: migrate
records and retire; keep as a read-only archive; or maintain both. Classified
`MIGRATION_REQUIRED_PRODUCT_DECISION`. No migration was invented here.

## 2. The broken legacy reply contract
The tenant portal posts `{ reply_text }`; the route reads `body["reply"]` — a
500. Fixing it would *enable* a currently-dead write path into the superseded
table, which is likely the wrong direction. Decide whether to repair, remove
the UI control, or retire the route.

## 3. `resolve` called by the tenant portal
The portal exposes a resolve action, but the route is `require_super_admin`,
so tenant users get 403. Either the control should be hidden for tenants, or
the persona is wrong. A UI/persona decision.

## 4. Three unscoped non-content reads
`GET /aggregates/{entity_type}/{entity_id}`,
`GET /requests/jobs/{job_id}` and `GET /customers/{customer_id}` (for
non-customer roles) remain unscoped. They expose aggregate figures and request
status, not review content. Tightening them needs a decision about which
personas may read another party's aggregate/request data.

## 5. Should `staff` hold `P.TENANT_UPDATE` for review actions?
The three tenant mutations use the existing `P.TENANT_UPDATE`. Whether that is
the right permission for review reply/flag — as opposed to a narrower
reputation permission — is a product question. No new permission was added.

## 6. Prefix convention for the canonical inventory
This slice showed that the prefix-based Design A sweep can miss genuine tenant
mutations on generic prefixes. Whether to re-sweep the whole application on a
persona basis rather than a prefix basis is a methodology decision with real
cost. Recorded in `known-limitations.md` as a coverage-completeness caveat.

## Carried forward
Package Commerce payment integration and duplicate-pending index (2F-22);
compliance export worker (2F-20); customer_reviews staff persona and customer
flagging policy (2F-24); the `tenant-readonly-decision.md` conclusion behind
the Slice-2D canaries.
