# Slice 2F-35 Verification Report (WS18)

Final run, `python scripts/workflow_rearchitecture/verify_2f35.py`:

```
Slice 2F-35 verifier

  PASS  R01 Set A/B/C frozen hashes unchanged
  PASS  R02 every Set B route received a final adjudication
  PASS  R03 no Set C route was newly protected by this slice
  PASS  R04 both Set A routes are protected
  PASS  R05 all 11 routes have mutation access-scope guard live
  PASS  R06 delete_endpoint does not mutate by endpoint_id alone (tenant predicate present)
  PASS  R07 rag KB lookup scoped by tenant for closed methods
  PASS  R08 client tenant cannot widen rotate_api_key authority
  PASS  R09 client tenant cannot widen generate_document authority
  PASS  R10 every service rejects missing/untrusted tenant context
  PASS  R11 foreign objects create no existence oracle
  PASS  R12 no alternate-route bypass to a closed mutation method
  PASS  R13 field_ops internal caller passes trusted tenant context
  PASS  R14 coverage arithmetic is 252/273 (241+2+9 / 264+9)
  PASS  R15 unprotected count is 21
  PASS  R16 M01 sample route remains VERIFIED (no regression)
  PASS  R17 N01 sample route remains VERIFIED (no regression)
  PASS  R18 geo sample route remains VERIFIED (no regression)
  PASS  R19 no Slice 2F-36/37 application file changed
  PASS  R20 no document claims application-wide closure
  PASS  R21 canonical hash matches the post-closure frozen value
  PASS  R22 matrix hash matches the post-closure frozen value

VERIFIER PASSED (critical authorization batch scope only -- not application-wide)
```

22/22 conditions pass.
