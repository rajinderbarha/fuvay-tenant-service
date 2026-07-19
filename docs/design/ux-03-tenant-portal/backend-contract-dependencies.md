# Backend Contract Dependencies

| UX-03 concept | Real backend anchor | Verified this phase |
|---|---|---|
| Canonical roles | `app/core/permissions.py::ROLE_PERMISSIONS` keys | yes (read) |
| StaffPermission | `app/engines/auth/models.py::StaffPermission`, `app/engines/auth/service.py::_get_staff_permissions` | yes (read) |
| Permission keys | `app/core/permissions.py::P` class constants | yes (read, used real strings in fixtures) |
| Booking pipeline | booking engine (`app/engines/booking/`) -> field_ops.Job | referenced from task brief, not re-derived from source this phase |
| ServiceJob pipeline | field_ops engine (`app/engines/field_ops/`) | referenced from task brief |
| PartsRequest | field_ops + inventory engines | referenced from task brief |
| Finance (package/credit/commission/deposit) | `app/engines/finance_hub/` | not read this phase; contract unverified |
| Geo/service areas | `app/engines/geo/` | not read this phase; "frozen slice" status taken from task brief |
| Media | `app/engines/media/` | not read this phase; N01 backlog note taken from memory index |

Where "not read this phase" appears, treat the corresponding
readiness-state-registry.csv rows as engineering estimates, not confirmed
contracts.
