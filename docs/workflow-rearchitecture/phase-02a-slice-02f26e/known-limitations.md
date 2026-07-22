# Known Limitations — Slice 2F-26E

1. **Required strata cannot all be represented.** The mission lists 24 strata;
   the 99 remaining mixed-persona routes support 5. Trusted callback, internal
   branch, explicit deny, customer self-service, parent-derived tenant and
   several others have **no members** in that population. This is a property
   of the population, not of the sampling. It will not improve in a later
   slice without widening beyond the mixed-persona set.

2. **Both holdouts are burned.** 2F-26D's 24 and 2F-26E's 24 are now
   development sets. 75 unsampled mixed-persona routes remain, enough for one
   more holdout of this size — after that, independent validation of this
   population is exhausted.

3. **Burned-sample 24/24 is not evidence of correctness.** The classifier was
   tuned against it.

4. **Two known classifier defects remain open**, deliberately unfixed:
   alias-blind parameter scanning, and actor identity read as scoping
   evidence.

5. **Capability granularity is under-specified.** Two disagreements came from
   the capability column carrying a judgement it was not defined to carry.
   The field needs the same treatment the tenant-direction taxonomy received.

6. **Side-effect detection is regex-plus-qualified-call**, not a full data-flow
   analysis. It found a real mutating GET the manual pass missed, but it can
   still miss writes behind dynamic dispatch.

7. **Security observations are static-reading only.** None was executed
   against a live tenant pair; none should be cited as a proven vulnerability.

8. **The 2F-26B resolver is still on disk and unmodified** (`b1e61c218e745194`).
   The new model supersedes it but does not delete it; 2F-26C/26D artifacts
   still reference it.
