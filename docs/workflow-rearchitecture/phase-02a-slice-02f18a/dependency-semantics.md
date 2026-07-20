# Dependency Semantics

Directly invoked (not just introspected) in
`tests/test_phase2f18a_platform_notifications_technician_privacy.py::TestDependencySemantics`.

## `require_owner_or_office_staff_mutation` (`app/core/permissions.py`)
| Behavior | Result |
|---|---|
| Admitted roles | `super_admin`, `tenant_owner`, `staff` |
| Technician | **Rejected** (`test_owner_or_office_staff_mutation_rejects_technician`) — deliberately excluded, not an oversight |
| Customer | Rejected (`test_owner_or_office_staff_mutation_rejects_customer`) |
| Read-only access_scope (`customer_support_limited`) | Rejected for non-super_admin (`test_owner_or_office_staff_mutation_denies_readonly_scope`) |
| Prohibited role alias (`office_staff`) | Rejected — the allow-list check (`user.role not in (...)`) never matches an alias string regardless of how descriptive it looks (`test_owner_or_office_staff_mutation_rejects_unknown_role`) |
| Super admin | Admitted, exempt from the access-scope check (existing behavior, unchanged) |
| Unknown role/scope | Fails closed (allow-list, not deny-list) |

## `require_staff_or_technician_only` (`app/dependencies/auth.py`)
| Behavior | Result |
|---|---|
| Admitted roles | `staff`, `technician` only |
| Technician | **Admitted** (`test_staff_or_technician_only_admits_technician`) — this is the dependency that lets technicians reach `staff_chat_router`/`staff_notif_router` at all |
| Tenant owner | Rejected (`test_staff_or_technician_only_rejects_tenant_owner`) — deliberately narrower than `require_staff_or_above` |
| Customer | Rejected |
| Prohibited alias (`manager`) | Rejected |
| Access-scope (readonly) check | **NOT present on this dependency** — confirmed by direct code read (`app/dependencies/auth.py`), unchanged from 2F-18's `known-limitations.md` item 2. A technician cannot use a missing `access_scope` field to bypass anything, because this dependency never checks `access_scope` for ANY caller (staff included) — it is a role-only gate by design, matching `field_ops.staff_router`'s established convention. Object-level authorization (the actual "can this technician touch this record" question) is enforced separately by `chat_service.validate_thread_access`'s `RECIP_TECHNICIAN` branch, not by this dependency. |
| Super admin | Rejected (excluded by design, per the dependency's own docstring) |

## `require_customer` (`app/dependencies/auth.py`)
| Behavior | Result |
|---|---|
| Admitted roles | `customer` only |
| Tenant owner | Rejected (`test_require_customer_rejects_tenant_owner`) — proves tenant roles cannot enter the customer ownership branch via this dependency |
| Customer | Admitted (`test_require_customer_admits_customer`) |

## StaffPermission / explicit deny precedence
Not directly exercised by this module — none of the three dependencies
above consult `StaffPermission` at all (they are role-only or role+access-scope
checks, not the granular `P`-permission-string system used elsewhere in the
codebase). This is consistent with 2F-18's finding that
`platform_notifications` participates in no granular permission-string RBAC.
No change made or needed.
