"""one identity per person: unique email/phone for tenants, customers and staff

A tenant owner's email existed twice in `users` -- once as the owner, once as a customer
created later by the same person signing up on the customer side. Nothing stopped it,
because `users` had no uniqueness on email or phone at all.

That was not a cosmetic duplicate. `AuthService._get_user_by_email` resolves the login
account with `scalar_one_or_none()`, which RAISES when two rows match, so every login
attempt for that address became a 500 before the password was even checked. The account
was completely locked out and the error said nothing about why.

Tenants, customers and staff are all rows in `users` -- there is no separate customers
table -- so one constraint per column covers all three, which is exactly the scope
required: the same person must not be able to exist twice.

Indexes, not table constraints, because both need to be conditional:

* email is compared case-insensitively everywhere (the login lookup lowercases before
  querying), so the index is on lower(email). A plain UNIQUE(email) would happily accept
  Bob@x.com alongside bob@x.com and leave the same 500 in place.
* phone and email are both optional; a partial index skips NULL and '' so accounts
  legitimately without one do not collide with each other.

Staff get a per-TENANT constraint rather than a global one. Two providers may each employ
someone reachable on the same number, and a global unique would wrongly refuse the second
provider's hire; what must not happen is one provider holding the same person twice.

Revision ID: 243
Revises: 242
"""
from alembic import op

revision = "243"
down_revision = "242"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Data prep: the one collision left in this database. Two tenant_owner accounts share
    # a phone -- the real Guramrit business, and an abandoned signup with no business name
    # and zero jobs, bookings, staff or services. The phone is cleared from the abandoned
    # one rather than the row being deleted, because that tenant is still referenced by 18
    # tables (billing, branding, engines, deposits, audit) and removing it is a separate
    # decision from making the constraint hold.
    op.execute("""
        UPDATE users u SET phone = NULL
        WHERE u.role = 'tenant_owner'
          AND u.phone IS NOT NULL
          AND EXISTS (
            SELECT 1 FROM tenants t
            WHERE t.id = u.tenant_id
              AND t.business_name IS NULL
              AND t.verification_status = 'not_started'
          )
          AND EXISTS (
            SELECT 1 FROM users other
            WHERE other.phone = u.phone AND other.id <> u.id
          )
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower
        ON users (lower(email)) WHERE email IS NOT NULL AND email <> ''
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_phone
        ON users (phone) WHERE phone IS NOT NULL AND phone <> ''
    """)

    # Same rule for the provider's own roster rows, scoped to the tenant.
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_team_member_email_per_tenant
        ON provider_team_members (tenant_id, lower(email))
        WHERE deleted_at IS NULL AND email IS NOT NULL AND email <> ''
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_team_member_phone_per_tenant
        ON provider_team_members (tenant_id, phone)
        WHERE deleted_at IS NULL AND phone IS NOT NULL AND phone <> ''
    """)
    # A user account may back at most one active roster row. Without this, re-inviting an
    # existing technician creates a second team member for one person, and every capacity
    # and availability count that groups by staff row silently doubles them.
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_team_member_user
        ON provider_team_members (user_id)
        WHERE deleted_at IS NULL AND user_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_team_member_user")
    op.execute("DROP INDEX IF EXISTS uq_team_member_phone_per_tenant")
    op.execute("DROP INDEX IF EXISTS uq_team_member_email_per_tenant")
    op.execute("DROP INDEX IF EXISTS uq_users_phone")
    op.execute("DROP INDEX IF EXISTS uq_users_email_lower")
    # The cleared phone is not restored: re-introducing a known duplicate on the way
    # down would leave the database in the exact state this migration exists to prevent.
