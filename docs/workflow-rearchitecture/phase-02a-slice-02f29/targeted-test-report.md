# Targeted Test Report - Slice 2F-29

`tests/test_phase2f29_m01_identity_closure.py` - **43 passed**.

Coverage of the WS13 matrix:
- access scope on all six tenant mutations; impersonate deliberately excluded;
  non-Set-A routes asserted untouched
- foreign-tenant target -> NotFound; **missing and foreign targets proven
  indistinguishable** (the anti-oracle property)
- unknown permission key rejected on update AND on invite, with `db.add`
  asserted not called (no partial write)
- known permission key accepted (positive control)
- StaffPermission grant / explicit deny / unrelated grant / unknown role
- wildcard override cannot widen
- impersonation: actor server-derived, non-super_admin rejected, target
  role/tenant from the target record
- API keys: tenant-scoped mutation, raw secret only on create, hashed storage,
  separate subsystem untouched
- self-service: all five bound to the token principal, credential proof present
- alternate routes already protected
- canonical accounting 226/259/33 with 2F-29 provenance on all 12 rows
