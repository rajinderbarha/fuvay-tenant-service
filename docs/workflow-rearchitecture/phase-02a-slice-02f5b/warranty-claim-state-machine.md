# Warranty Claim State Machine — Workstream 4

## Statuses observed
`pending`, `pending_review`, `awaiting_documents`, `approved`, `rejected`, `settled`.

## Transitions

| Action | Precondition | Result | Permission | Granted to |
|---|---|---|---|---|
| `assign_reviewer` | none (advances only if currently `pending`) | `status=pending_review`, `assigned_reviewer_id` set | `FINANCE_CLAIMS_ASSIGN` | super_admin only |
| `request_documents` | none | `status=awaiting_documents` | `FINANCE_CLAIMS_ASSIGN` | super_admin only |
| `approve_claim` | delegated to `package_commerce._commerce.approve_claim` (not traced this slice) | delegated | `FINANCE_CLAIMS_APPROVE` | super_admin only |
| `reject_claim` | delegated to `package_commerce._commerce.reject_claim` (not traced) | delegated | `FINANCE_CLAIMS_REJECT` | super_admin only |
| `settle_claim` | `status != "approved"` rejected (pre-existing, blocks double-settlement and settling non-approved claims) | `status=settled`, `settled_amount=amount_approved` | `FINANCE_CLAIMS_SETTLE` | super_admin only |

## Verification result
`settle_claim`'s guard is the only precondition independently confirmed at
the `finance_hub` layer (`service.py:616`, unmodified, regression-tested).
It correctly blocks re-settlement and settlement of anything other than an
`approved` claim. `assign_reviewer` and `request_documents` have no status
precondition — reviewed and judged acceptable, since they are non-terminal,
reversible, metadata-oriented actions (not a final-state or money-moving
transition), consistent with the same judgment applied to `reject_deposit`.

`approve_claim` and `reject_claim` delegate entirely into
`package_commerce`'s service — their internal state validation was **not**
traced this slice, per the "do not modify package_commerce.admin_router"
and out-of-scope constraints. This is a genuine, disclosed limitation
(see `known-limitations.md`), not a defect finding.

## Persona note
All 5 warranty-claim mutations are reachable only via `super_admin`'s
`P.ALL` wildcard (`FINANCE_CLAIMS_*` granted to no canonical role). No
grant was made this slice, per the interim policy and the explicit
out-of-scope instruction "do not grant FINANCE_CLAIMS_* permissions."
