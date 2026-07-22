# Authorization Integrity Check — Slice 2E

## Extended `scripts/workflow_rearchitecture/check_role_integrity.py`

Added 4 checks beyond Slice 2D's original (invalid `users.role`):

1. **Unknown `staff_permissions.permission_key` values** — compares every distinct `permission_key` in the table against the real set of `P.*` constant values (loaded programmatically via `_known_permission_keys()`, not a hardcoded duplicate list — avoids drift as `P` grows). Inert today (confirmed 0 found), but surfaces a typo'd grant an admin believes took effect but didn't.
2. **Cross-tenant `staff_permissions` rows** — `staff_permissions.tenant_id IS DISTINCT FROM` the owning user's actual `tenant_id`. Confirmed 0 found — expected, since the write path always derives `tenant_id` from the target user, but checked directly rather than assumed.
3. **Orphaned permission rows** — `staff_permissions` rows whose `user_id` no longer exists in `users`. Confirmed 0 found.
4. **Invalid `access_scope` values** — non-null values outside the known valid set (`global`, `operations`, `finance`, `compliance`, `support`, `tenant_scoped`, `customer_support_limited`). Confirmed 0 found.

## Live run this slice
```
$ python scripts/workflow_rearchitecture/check_role_integrity.py --detail
{
  "checks": {
    "invalid_role_count": 1,
    "unknown_permission_key_count": 0,
    "cross_tenant_staff_permission_count": 0,
    "orphaned_permission_row_count": 0,
    "invalid_access_scope_count": 0
  },
  "invalid_role_accounts": [{"email": "readonly@demo-ac-services.local", "role": "tenant_readonly", "is_active": true}],
  "status": "integrity_violation",
  "total_violations": 1
}
```
Exit code 1, correctly, since 1 violation exists.

## Requirements checklist
| Requirement | Status |
|---|---|
| No automatic remediation | Yes — purely read-only, zero `UPDATE`/`INSERT`/`DELETE` statements |
| No sensitive details in public health responses | Yes — account emails only appear with the explicit `--detail` opt-in |
| Detailed output available only to authorized operational tooling | Enforced by the `--detail` flag being a deliberate, explicit CLI choice, not a default — this script is not exposed via any HTTP endpoint, so "authorized" means "has shell/CI access to run it," consistent with Slice 2D's decision not to wire it into a public endpoint |
| Exit code suitable for CI/ops | Yes — 0 clean, 1 any violation |
| Machine-readable mode | Yes — JSON output always |
| Tests | Yes — `tests/test_phase2e_effective_permissions.py::TestAuthorizationIntegrityScript` |

## Not implemented
"Users with role and scope combinations that cannot be enforced" (the brief's last listed check) — this would require encoding which role/access_scope combinations are meaningful vs. contradictory, which itself depends on resolving the read-only mutation-guard coverage gap first (a combination like `role=staff, access_scope=customer_support_limited` is only meaningfully "enforced" once the guard covers all mutation routes — see `tenant-readonly-implementation.md`). Deferred alongside that larger gap.
