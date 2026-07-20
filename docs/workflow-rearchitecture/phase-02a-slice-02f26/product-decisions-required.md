# Product Decisions Required — Slice 2F-26

## 1. Which of the 26 newly discovered unprotected routes is implemented first
`auth.router` (12) carries the highest identity impact — MFA, passwords,
staff permissions, API keys, impersonation. Module selection is explicitly
**not** this slice's job, but the queue is now ranked for whoever does it.

## 2. Is `POST /v1/rag/query` a coverage-relevant mutation?
It persists a query record (tenant-scoped). It is counted because it writes
tenant data, but its *capability* is "run a query", not "mutate business
state". Whether query-logging belongs in the authorization denominator is a
policy question.

## 3. Mutating GETs as a design pattern
31 exist. `GET .../deposit` lazily creates a row. Whether lazy creation on a
read is acceptable, or should move to an explicit initialise call, is a design
decision with authorization consequences.

## 4. The 145 read-only POST/PUT/PATCH routes
Declared as mutations by HTTP method but with no detected persistent effect
(previews, calculations, validations). They are excluded from the denominator.
Whether any should be re-verified individually is a scope decision.

## 5. The 123 MIXED_PERSONA mutations
Bare-authenticated routes with no clear tenant-derivation evidence. Each needs
adjudication before it can be called tenant, customer or internal. This is the
largest remaining classification population.

## 6. Narrow the swallowed `except Exception` in job close
Recommended in `swallowed-exception-risk-audit.md`; not implemented.

## Carried forward
Package Commerce payment integration; compliance export worker;
customer_reviews staff persona and customer flagging policy; legacy review
engine retirement; `tenant-readonly-decision.md` behind the Slice-2D canaries.
