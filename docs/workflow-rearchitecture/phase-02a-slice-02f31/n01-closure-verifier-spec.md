# N01 Closure Verifier Spec - Slice 2F-31

`scripts/workflow_rearchitecture/verify_n01_2f31.py` - 20 conditions (N01-N20):
frozen Set A/B/C counts and hashes unchanged; every Set B route adjudicated;
no Set C route gained access-scope; all 6 role-guarded Set A routes scoped;
`require_technician` fully replaced by the same-role-set access-scope guard;
`MediaAccessService.assert_can_delete`/`assert_can_view` preserved; client
tenant cannot widen upload authority; `delete_file` scopes by tenant AND id
with no existence oracle; the non-allow-listed `media/router.py` untouched;
all 3 Set B routes present canonically and correctly left UNPROTECTED (not
fabricated as protected); coverage arithmetic exact (233/262/29); no unrelated
canonical row changed; no application-wide closure claim.

Each condition has an executed negative fixture (`--selftest`).
