# Role Remediation Plan

**Status: `ROLE_REMEDIATION_POLICY_BLOCKED`.** No plan is executed this
slice. Per `manual-role-confirmation-request.md`, both demo accounts
require a human decision this investigation cannot supply.

Conditional plan, to be executed **only after** human approval is recorded
in a committed decision artifact:

```
python scripts/workflow_rearchitecture/remediate_invalid_roles.py \
  --mapping <manager_user_id>=staff \
  --allow <manager_user_id> \
  --apply --confirm \
  --reason "Slice 2F-38 remediation, approved by <name> on <date>, see <decision artifact path>"
```

For `readonly@demo-ac-services.local`, the plan depends entirely on which
of the three options in `manual-role-confirmation-request.md` a human
selects — no single command can be pre-written until that choice is made.

`role-remediation-execution.md` (required artifact) is intentionally a
stub: no execution occurred.
