# Slice 2F-36 Verification Report

Final run, `python scripts/workflow_rearchitecture/verify_2f36.py`:

```
Slice 2F-36 verifier

  PASS  R01 Set A/B/C frozen hashes unchanged
  PASS  R02 every Set A route is present and protected
  PASS  R03 all 28 Set B routes received a final disposition (adjudicated in held-route-adjudication.csv)
  PASS  R04 every canonically-added Set B route is protected
  PASS  R05 all 18+24 routes have mutation access-scope guard live
  PASS  R06 set_default re-checks owner_user_id before mutating is_default
  PASS  R07 every touched service has a _require_trusted_tenant helper
  PASS  R08 every _require_trusted_tenant rejects missing tenant context
  PASS  R09 appointment ownership check is non-oracular (NotFoundException, not a distinct 403)
  PASS  R10 dispatch_job cross-checks the job's own tenant before advancing it
  PASS  R11 catalog update_item checks tenant ownership before mutating
  PASS  R12 reservation confirm/release predicate the lookup by tenant_id (not just status)
  PASS  R13 every touched router passes actor_tenant_id into its service constructor
  PASS  R14 coverage arithmetic is 294/297 (252+18+24 / 273+24)
  PASS  R15 unprotected count is 3
  PASS  R16 M01 sample route remains VERIFIED (no regression)
  PASS  R17 N01 sample route remains VERIFIED (no regression)
  PASS  R18 geo sample route remains VERIFIED (no regression)
  PASS  R18b Slice 2F-35 sample routes remain VERIFIED (no regression)
  PASS  R19 no Set C route was newly protected by this slice
  PASS  R20 no Slice 2F-35/37-exclusive application file carries a 2F-36 marker
  PASS  R21 no document claims application-wide closure
  PASS  R22 canonical hash matches the post-closure frozen value
  PASS  R23 matrix hash matches the post-closure frozen value

VERIFIER PASSED (enterprise/tenant-admin/operational batch scope only -- not application-wide)
```

23/23 conditions pass.
