"""Legal Documents — versioned store for the Terms, Privacy Notice and friends.

Revision ID: 316
Revises: 315

Before this, the Terms of Service and Privacy Notice existed only as hardcoded
JSX in the tenant portal (``app/terms/page.tsx``, ``app/privacy/page.tsx``).
Nothing else could read them: the customer mobile app's legal links point at
``EXPO_PUBLIC_TERMS_URL`` / ``EXPO_PUBLIC_PRIVACY_URL``, which are unset, and
``ProfileScreen`` hardcodes both to ``null`` so the rows are hidden entirely.
There was also no way to answer "which text did this person accept?" —
``consent_records`` stamps ``policy_version`` from ``dpdp_policy_versions``,
which is the data-protection PROCESS policy (SLA phases, request types), not
the Terms anyone actually read.

This creates the store and seeds the two live documents as v1.0, carrying the
exact wording the tenant portal has been serving so nothing changes for anyone
who reads them today.

Deliberately NOT created here: an acceptance table. ``consent_records`` is
already the immutable consent ledger and carries ip/user_agent/source; signup
stamps the document versions into its existing ``meta`` JSONB column, which
needs no schema change.
"""
from alembic import op

revision = "316"
down_revision = "315"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS legal_document_versions (
            id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            doc_type               VARCHAR(40)  NOT NULL,
            audience               VARCHAR(20)  NOT NULL DEFAULT 'all',
            locale                 VARCHAR(10)  NOT NULL DEFAULT 'en',
            version                VARCHAR(20)  NOT NULL,
            title                  VARCHAR(200) NOT NULL,
            summary                TEXT,
            body                   TEXT         NOT NULL,
            body_format            VARCHAR(20)  NOT NULL DEFAULT 'markdown',
            status                 VARCHAR(20)  NOT NULL DEFAULT 'draft',
            effective_at           TIMESTAMPTZ,
            published_at           TIMESTAMPTZ,
            archived_at            TIMESTAMPTZ,
            requires_reacceptance  BOOLEAN      NOT NULL DEFAULT FALSE,
            change_note            TEXT,
            created_by             UUID,
            published_by           UUID,
            meta                   JSONB        NOT NULL DEFAULT '{}'::jsonb,
            created_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT uq_legal_doc_version
                UNIQUE (doc_type, audience, locale, version)
        )
    """)
    # Serves the hot path: resolve the live version for a type+audience+locale
    # ordered by effective_at, which every public read performs.
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_legal_doc_live
            ON legal_document_versions (doc_type, audience, locale, effective_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_legal_doc_status
            ON legal_document_versions (status)
    """)

    # ── Seed the two documents the tenant portal already serves ──────────────
    # Effective 2026-08-11 — the "Last updated" date the hardcoded pages show.
    # Backdating it (rather than using now()) keeps the record honest: these
    # terms have been in force since that date, they are not new today.
    op.execute("""
        INSERT INTO legal_document_versions
            (doc_type, audience, locale, version, title, summary, body,
             status, effective_at, published_at, change_note)
        VALUES (
            'terms_of_service', 'all', 'en', '1.0',
            'Terms of Service',
            'These terms govern use of the ServiceOS business workspace and related services.',
            $md$## Your account

You must provide accurate information, keep login credentials secure, and be authorized to act for the business you register.

## Business setup and review

Creating an account creates a draft workspace. Business information is submitted for administrative review only after you complete setup and explicitly submit it.

## Acceptable use

You may not misuse the service, interfere with its operation, upload unlawful or malicious material, or access data belonging to another user or business.

## Payments and activation

No package or payment is required during signup. Applicable deposits, credits, commissions, or package terms are disclosed before activation or purchase.

## Suspension and termination

ServiceOS may restrict access when required for security, legal compliance, fraud prevention, or a material breach of these terms.

## Contact

Questions? Contact support@serviceos.in.$md$,
            'published',
            TIMESTAMPTZ '2026-08-11 00:00:00+00',
            now(),
            'Migrated verbatim from the hardcoded tenant-portal /terms page.'
        )
        ON CONFLICT ON CONSTRAINT uq_legal_doc_version DO NOTHING
    """)

    op.execute("""
        INSERT INTO legal_document_versions
            (doc_type, audience, locale, version, title, summary, body,
             status, effective_at, published_at, change_note)
        VALUES (
            'privacy_policy', 'all', 'en', '1.0',
            'Privacy Notice',
            'This notice explains how ServiceOS handles information provided during signup and business operations.',
            $md$## Information we collect

We collect owner contact details, verification data, business identity information, documents, service configuration, and operational records needed to provide the workspace.

## How we use information

We use information to create and secure accounts, verify businesses, operate requested services, prevent fraud, provide support, and meet legal obligations.

## Consent

Required authorization and terms consent are recorded when you create the workspace. Optional marketing consent is recorded separately and can be withdrawn.

## Sharing and retention

Information is shared only with authorized processors, service providers, or authorities where necessary. Records are retained according to security, operational, and legal requirements.

## Your choices

You may request access, correction, or other applicable privacy rights through ServiceOS support. Some records must be retained for legal or security reasons.

## Contact

Questions? Contact support@serviceos.in.$md$,
            'published',
            TIMESTAMPTZ '2026-08-11 00:00:00+00',
            now(),
            'Migrated verbatim from the hardcoded tenant-portal /privacy page.'
        )
        ON CONFLICT ON CONSTRAINT uq_legal_doc_version DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS legal_document_versions")
