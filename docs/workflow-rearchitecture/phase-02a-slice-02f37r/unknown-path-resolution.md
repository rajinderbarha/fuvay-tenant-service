# Unknown Path Resolution

Initial automated classification (`classify_2f37ra.py`) produced 5 UNKNOWN
paths out of 3,001. All 5 resolved without ambiguity:

| Path | Resolution | Basis |
|---|---|---|
| `.fullreg.txt` | GENERATED_OR_CACHE_FILE | Root-level stray output file, not referenced by any source, doc, or test |
| `bash.exe.stackdump` | GENERATED_OR_CACHE_FILE | Windows crash-dump artifact from a shell crash, not repository content |
| `frontend/tenant-portal/next-env.d.ts` | GENERATED_OR_CACHE_FILE | Next.js auto-generated type-reference file |
| `frontend/tenant-portal/app/staff/my-work/page.tsx` | UNRELATED_PRE_EXISTING_DIRTY_FILE | Tenant-portal frontend, no authorization program reference; consistent with the previously-confirmed pattern of leftover MODULE-L5-era frontend edits sitting uncommitted alongside the authorization program |
| `frontend/tenant-portal/lib/api.persona.test.ts` | UNRELATED_PRE_EXISTING_DIRTY_FILE | Same as above |

## Post-hoc correction (caught by verifier, not by classification)

Two files were initially classified `UNRELATED_PRE_EXISTING_DIRTY_FILE` and
excluded from the backend recovery commit, then **restored** after
`verify_2f37.py` failed application boot:

| Path | Initial (wrong) label | Corrected label | Why the correction was needed |
|---|---|---|---|
| `app/engines/execution/my_work_router.py` | UNRELATED_PRE_EXISTING_DIRTY_FILE | SHARED_AUTHORIZATION_INFRASTRUCTURE | `app/main.py`'s `_mount_routers()` imports this module unconditionally at startup; excluding it raised `ModuleNotFoundError` during the verifier's `route_index()` call, which imports `app.main`. |
| `app/engines/execution/my_work_service.py` | UNRELATED_PRE_EXISTING_DIRTY_FILE | SHARED_AUTHORIZATION_INFRASTRUCTURE | Imported by `my_work_router.py`. |

This is recorded as a real classification defect this slice found and fixed
during its own verification pass, not a hidden or silently-corrected error —
see the two commits `29dd931` (initial, broken) and `532190d` (correction) on
`security/phase-2f-authorization-recovered`. It demonstrates why Workstream 7
insists the consolidated commit's correctness must rest on independent
verifier/regression evidence rather than on trusting path-based
classification alone: the classification here was plausible-looking and
still wrong until checked against actual runtime behavior.

No other file in the 683-path exclusion list was found to be load-bearing
for application boot or for any passing verifier condition — `verify_2f37.py`
21/21 PASS after the correction confirms the remaining exclusions are safe.
