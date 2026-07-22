# Product Decisions Required

Workstream 3/7. These are genuine open questions this slice deliberately did
NOT resolve — resolving them would mean inventing product behavior, which is
explicitly out of scope. Each is `BLOCKED_PENDING_PRODUCT_DECISION` (or, for
#5, additionally an engineering gap) until a product owner decides.

## 1. Should tenants be able to voluntarily pause their own business?
No such feature exists today (only platform-initiated `suspend` exists,
which also flips marketplace discoverability and invalidates sessions).
If wanted, this would need to be a **new, separate** endpoint/permission
(e.g. `tenant:pause_self`) distinct from the existing `tenant:suspend`
platform action — not a permission grant on the existing endpoint, since the
existing endpoint's side effects (session invalidation, "suspended" status
used elsewhere for compliance reporting) may not be appropriate for a
voluntary pause.

## 2. Should tenant_owner ever be granted `tenant:suspend`/`tenant:reinstate`/`tenant:terminate`/`tenant:plan:manage`?
Current evidence (frontend-exposure-audit.md) shows these are exclusively
platform-operations actions today, with real audit/compliance implications
(suspension affects marketplace discoverability platform-wide; termination
schedules irreversible data handling). Granting tenant_owner direct
self-service access to any of these would be a policy change with billing,
compliance, and possibly legal implications (especially termination and plan
changes affecting active bookings/staff/customers) — this slice does not
recommend a default answer, only documents that the technical guard is
ready (`require_tenant_mutation_permission`) whichever way the decision goes.

## 3. Should there be a distinct "cancel subscription" capability?
`downgrade_plan` can move a tenant to the lowest tier but there is no
endpoint that stops billing/cancels a subscription outright. If tenant-owner
self-service cancellation is wanted, it needs its own endpoint and permission
— reusing `tenant:plan:manage` would conflate "downgrade" with "cancel,"
which have different billing/refund/data-retention implications.

## 4. Should the "90-day scheduled tenant-schema deletion" that `confirm_termination`'s response message promises actually be implemented?
No scheduled job, Celery task, or cron trigger implementing this was found
anywhere in the codebase. Today, `confirm_termination` only flips
`tenant.status` to `"terminated"` — no data is deleted, scheduled, or
queued for deletion. This is a **customer-facing promise that is not
currently kept by the system** and should be resolved one of two ways:
(a) build the missing scheduled-deletion job, or (b) correct the response
message to stop claiming a behavior that doesn't exist. Neither was done
this slice (new engineering behavior is out of scope for a policy-closure
slice) — flagged here as the most operationally significant finding.

## 5. Should the GDPR/DPDP deletion-request execution mechanism be built?
`request_gdpr_deletion` only writes an audit-log row today; it claims "PII
will be anonymized within 72 hours" but no anonymization job exists. This is
simultaneously a product decision (who approves an erasure request? is
approval required at all, or is it auto-approved as the current code
implies?) and an engineering gap (the execution mechanism must be built
regardless of the approval-policy answer). **This is a compliance-relevant
gap** — DPDP/GDPR erasure requests that are acknowledged but never executed
are a real regulatory exposure, not merely a missing feature. Recommended
next step: escalate to whoever owns compliance/legal review before any
future slice touches this endpoint's behavior.

## 6. Should suspend/reinstate/terminate distinguish reason categories with different authorization or workflow requirements?
Today `suspend_tenant` accepts a free-text `reason` and an unenforced
`reason_category`, with no branching logic based on category (e.g. a
payment-failure suspension vs. a fraud-risk suspension are handled
identically). If different categories should require different approval
levels or trigger different downstream workflows (e.g. legal review for
fraud, automatic reinstatement eligibility for payment-failure once paid),
that is new product behavior, not decided or implemented here.
