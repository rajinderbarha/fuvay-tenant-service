# Test Quality Report - Slice 2F-29

- **Every positive has a negative control**: a known permission key is accepted
  as well as an unknown one rejected; impersonation succeeds only for
  super_admin and is asserted rejected for tenant_owner; non-Set-A auth routes
  are asserted *unchanged* so the fix cannot silently spread.
- **The anti-oracle property is tested as a property**, not as a message:
  missing and foreign targets are asserted to produce the *same* error code.
- **No-partial-write is asserted behaviourally** (`db.add.assert_not_called()`),
  not by reading source.
- Access-scope enforcement is read from the **live dependency chain**, not from
  a source string match.
- Model separation is asserted from real SQLAlchemy `__tablename__` values.
- Frozen scope hashes are asserted, so a scope change breaks the suite.
- Every verifier condition has an executed negative fixture.
