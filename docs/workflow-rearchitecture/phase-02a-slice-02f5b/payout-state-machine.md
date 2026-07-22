# Payout State Machine — Workstream 4

## Statuses
`pending`, `approved`, `processing`, `completed`, `rejected`, `failed`.

## Guard mechanism
All 5 payout mutations use the shared `_require_status(self, p, allowed_tuple)`
helper (`finance_hub/service.py:693`, unmodified this slice):

```python
def _require_status(self, p, allowed):
    if p.status not in allowed:
        raise ServiceOSException("CONFLICT", f"Payout is '{p.status}'; expected one of {allowed} for this action.")
```

## Transitions

| Action | Allowed from | Result | Permission | Granted to |
|---|---|---|---|---|
| `approve_payout` | `pending` | `approved` | `FINANCE_PAYOUTS_APPROVE` | super_admin only |
| `reject_payout` | `pending`, `approved` | `rejected` | `FINANCE_PAYOUTS_REJECT` | super_admin only |
| `mark_processing` | `approved` | `processing` | `FINANCE_PAYOUTS_PROCESS` | super_admin only |
| `mark_completed` | `processing` | `completed` | `FINANCE_PAYOUTS_COMPLETE` | super_admin only |
| `mark_failed` | `processing`, `approved` | `failed` | `FINANCE_PAYOUTS_PROCESS` | super_admin only |

## Verification result
All 5 preconditions confirmed present and unmodified via direct source
read + regression test (`TestExistingStateMachineGuardsUnchanged`). No
path exists to double-complete (`mark_completed` requires `processing`,
which is only reachable from `approved`, which is only reachable from
`pending` — each transition consumed exactly once per payout unless
explicitly reset, and no reset path exists in this router). No defect
found in the payout state machine this slice.

## Persona note
All 5 payout mutations are reachable only via `super_admin`'s `P.ALL`
wildcard (`FINANCE_PAYOUTS_*` is granted to no canonical role). Per the
approved interim policy, this slice **did not** grant these permissions
to `admin_finance` — flagged as an open product decision in
`product-decisions-required.md`.
