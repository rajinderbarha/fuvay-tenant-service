# M01 Closure Verifier Spec - Slice 2F-29

`scripts/workflow_rearchitecture/verify_m01_2f29.py` - 27 conditions
(M01-M27): frozen Set A count/hash, Set B empty, Set C hash, all routes still
mounted, auth/security API-key subsystems separate, access scope on all six
tenant mutations, impersonation actor/subject server-derived and audited,
target ownership on update_permissions and deactivate_staff, no existence
oracle, permission-registry validation on both write paths, StaffPermission
grant/deny/unknown-role semantics preserved, API-key tenant scoping, raw-secret
containment, hashed storage, NotFound on foreign key, self-service routes bound
to the token principal, credential proof required, denominator unchanged,
protected count equals 214 + closed, no canonical row added, and no
application-wide closure claim in the documentation.

Each condition has an executed negative fixture (`--selftest`).
