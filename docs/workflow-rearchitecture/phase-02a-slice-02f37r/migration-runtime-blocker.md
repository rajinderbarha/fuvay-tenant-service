# Migration 144 Runtime Blocker (preserved, not applied this slice)

`alembic/versions/144_users_role_canonical_check.py` is present on the
recovered branch (`532190d`, classified `SHARED_AUTHORIZATION_INFRASTRUCTURE`,
unmodified content — a schema-only `CHECK` constraint migration that fails
closed rather than silently remapping invalid role values). It was **not
applied** in this slice.

No PostgreSQL, Redis, or running Docker daemon was available in this
environment during this slice (unchanged from the prior 2F-38 and 2F-37R
findings). Migration 144 apply/rollback/reapply evidence remains unproven
here. This is a Slice 2F-38 concern once restarted from the committed
baseline this slice produces.
