# Canonical Role Validation Contract

## Single mechanism, reused, no drift possible

Both fixed seed paths (`canonical_seed_final_l5_01.py::get_or_create_user`,
`seed_demo_users.py::upsert_user`) derive their accepted-role set from the
same single authoritative source:

```python
from app.core.permissions import ROLE_PERMISSIONS
CANONICAL_ROLES = frozenset(ROLE_PERMISSIONS.keys())
```

Neither defines a second, independently-maintained role list. If a role
were ever added to or removed from `ROLE_PERMISSIONS`, both seed guards
update automatically — they cannot silently drift out of sync with the
application's actual runtime role registry.

## Requirements verified

| Requirement | Status |
|---|---|
| Accept only the 10 canonical roles | PASS — `CANONICAL_ROLES == frozenset(ROLE_PERMISSIONS.keys())` |
| Reject unknown roles | PASS — `role not in CANONICAL_ROLES` → `ValueError` |
| Reject empty roles | PASS — `not role` check |
| Reject aliases | PASS — aliases are not in `ROLE_PERMISSIONS`, so rejected by the same check; explicitly tested for 10 alias strings in `test_phase2f39_seed_role_guard.py` |
| No silent normalization | PASS — exact string match only, no case-folding, no substitution |
| No default-to-privileged-role behavior | PASS — both fixes raise rather than defaulting; `canonical_seed_final_l5_01.py`'s prior `data.get("role", "tenant_manager")`-style pattern (found in `admin_service.py`, a different, already-safe file) was investigated separately in Slice 2F-38 and confirmed harmless there |
| Controlled error | PASS — `ValueError` with an explicit message naming the rejected value and the valid set |
| Consistent across seeds/bootstrap tools | PASS for the 2 live gaps found; `seed_admin_roles_final_l5_05l.py` was confirmed safe by construction (fixed literals only) rather than retrofitted with the same helper, since it never accepts external input |
| No circular imports | PASS — `app.core.permissions` has no dependency on either seed script; verified via successful `import` in both fixed files |
| No weakened application runtime validation | PASS — `app/core/permissions.py` and `app/engines/tenant_engine/admin_service.py` were not modified |

No shared importable helper module was created (e.g.
`scripts/workflow_rearchitecture/role_guard.py`) — each fix is a small,
local, inlined check reusing the same import. This was a deliberate
choice given the small number of call sites (2) found; if a third live
gap is found in a future slice, extracting a shared helper becomes
worthwhile.
