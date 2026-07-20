# Remediation Dry-Run Report

All runs below were executed live against the real configured database this slice. None mutated data (confirmed independently after each run via the DB role-distribution query, unchanged throughout).

## Run 1 — default dry-run, no mapping
```
python scripts/workflow_rearchitecture/remediate_invalid_roles.py
```
Result: reports both accounts under `unmapped_invalid_accounts`, `changes: []`, `errors: []`. Confirms the tool correctly discovers the current invalid-role population without requiring foreknowledge of which accounts are affected.

## Run 2 — apply attempt with an incomplete mapping (1 of 2 accounts)
```
python scripts/workflow_rearchitecture/remediate_invalid_roles.py \
  --mapping 72640932-ef3c-4ce5-92a1-6609bff35ee0=staff --apply --confirm
```
Result: **refused, exit code 1.** `errors: ["Refusing to apply: invalid-role accounts exist that are not covered by --mapping..."]`. Confirms the "fail closed on unexpected/unmapped records" guarantee.

## Run 3 — non-canonical target role rejected
```
python scripts/workflow_rearchitecture/remediate_invalid_roles.py \
  --mapping 72640932-ef3c-4ce5-92a1-6609bff35ee0=tenant_manager
```
Result: **refused before any DB connection, exit code 1**, with the exact list of the 10 canonical roles printed. Confirms the tool cannot be used to reintroduce the very placeholder it's meant to remove.

## Run 4 — platform role attempted on a tenant-scoped account
```
python scripts/workflow_rearchitecture/remediate_invalid_roles.py \
  --mapping 72640932-ef3c-4ce5-92a1-6609bff35ee0=super_admin \
  --allow 72640932-ef3c-4ce5-92a1-6609bff35ee0 --apply --confirm
```
Result: **refused, exit code 1**, with an explicit message naming the account's real `tenant_id` and explaining platform roles cannot be assigned to tenant-scoped accounts. Confirms rule "do not grant super_admin" / "do not treat platform roles as tenant roles" is mechanically enforced, not just documented.

## Run 5 — `--apply` without `--confirm`
```
python scripts/workflow_rearchitecture/remediate_invalid_roles.py \
  --mapping 72640932-ef3c-4ce5-92a1-6609bff35ee0=staff --apply
```
Result: **refused immediately, exit code 2**, before any database connection is opened. Confirms the two-flag confirmation requirement.

## No dry-run with a complete, valid, non-platform mapping was executed
Because no mapping decision was approved this slice (both accounts remain `MANUAL_ROLE_CONFIRMATION_REQUIRED`), a dry-run showing a real "changes" preview for both accounts together was not generated — doing so would require picking a target role for account 2, which has no safe target. If account 1's mapping is approved in a future slice, a dry-run with `--mapping <id>=staff --allow <id>` (restricting scope to only that one account) would be the next step, and would need to be reviewed before adding `--apply --confirm`.
