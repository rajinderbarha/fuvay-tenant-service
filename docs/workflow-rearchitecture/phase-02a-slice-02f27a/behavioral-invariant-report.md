# Behavioral Invariant Report - Slice 2F-27A

No application authorization behaviour changed (zero app/ files modified). Both
added routes retain their existing require_permission(P.TENANT_UPDATE) guard;
they are recorded as UNPROTECTED because that guard is not access-scope-aware
and enforces no principal-vs-target ownership. Canaries and StaffPermission
semantics re-asserted.
