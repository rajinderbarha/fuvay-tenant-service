# No Partial Persistence Proof — Slice 2F-22

## Structural argument

Every rejection in this path occurs **before** any `db.add()` or
`db.commit()`. The handler's only commit is the final
`await db.commit()` after the service method returns successfully.

Ordering inside `create_package_assignment`:

1. `_load_package` — raises `PACKAGE_NOT_FOUND` (read only)
2. `is_active` check — raises `PACKAGE_INACTIVE` (read only)
3. **`payment_authority` gate (2F-22)** — raises `PAYMENT_AUTHORITY_REQUIRED`
4. **`payment_reference` gate (2F-22)** — raises
   `PAYMENT_REFERENCE_WITHOUT_PAYMENT`
5. duplicate guard — raises `PACKAGE_ALREADY_PENDING` (read only)
6. `TenantPackageAssignment(...)` constructed
7. `db.add()` + `db.flush()`
8. audit event
9. handler `db.commit()`

Steps 1–5 are all reads and raises. The first write is step 7.

Schema-level rejections (`mark_paid`, `amount`, any unknown field) occur even
earlier — during FastAPI request validation, before the handler function is
entered at all.

## Empirical proof

`TestServiceLayerPaymentAuthority`'s three fail-closed tests construct the
service with **`db=None`**:

```python
svc = pkg_service.PackageCommerceService(db=None)
with pytest.raises(ServiceOSException) as exc:
    await svc.create_package_assignment(..., is_paid=True)
assert exc.value.error_code == "PAYMENT_AUTHORITY_REQUIRED"
```

Had the guard sat after any database interaction, the test would fail with
`AttributeError: 'NoneType' object has no attribute ...` instead of the
expected domain error. The guards therefore provably execute before the
session is touched.

## For every rejected request

| Artifact | State after rejection |
|---|---|
| purchase / assignment row | none created |
| paid status | none |
| active package | none |
| `starts_at` / `expires_at` | untouched (NULL) |
| wallet balance | unchanged |
| credit ledger entry | none |
| entitlement | none |
| storage quota | unchanged |
| commission rate | unchanged |
| module activation | none |
| invoice / payment record | none (never reached by this path) |
| notification | none — this route emits none at all |
| audit success event | none — `_pkg_audit` runs only after `db.add()`/`flush()` |
| commit | never reached |
| pre-existing state | unchanged |

## Transaction coherence

The handler owns the transaction boundary: the service `flush()`es, the
handler `commit()`s. A failure anywhere before the commit leaves the session
uncommitted, and no partial row survives. The signup caller additionally
wraps its call in a `SAVEPOINT` (`db.begin_nested()`) so an assignment
failure cannot poison account creation — pre-existing, unchanged, and
verified as still present.
