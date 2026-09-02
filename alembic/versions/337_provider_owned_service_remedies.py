"""Provider-owned technician assurance, remedies, warranty evidence, and SLA penalties.

Revision ID: 337
Revises: 336
"""
from alembic import op


revision = "337"
down_revision = "336"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE service_jobs
          ADD COLUMN IF NOT EXISTS warranty_certificate_number VARCHAR(80),
          ADD COLUMN IF NOT EXISTS warranty_certificate_snapshot JSONB,
          ADD COLUMN IF NOT EXISTS warranty_certificate_issued_at TIMESTAMPTZ
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_service_jobs_warranty_certificate_number
          ON service_jobs (warranty_certificate_number)
          WHERE warranty_certificate_number IS NOT NULL
    """)

    op.execute("""
        ALTER TABLE customer_complaints
          ADD COLUMN IF NOT EXISTS provider_sla_penalty_charged NUMERIC(12,2),
          ADD COLUMN IF NOT EXISTS provider_sla_penalized_at TIMESTAMPTZ
    """)
    op.execute("""
        ALTER TABLE complaint_policies
          ADD COLUMN IF NOT EXISTS provider_sla_breach_penalty NUMERIC(12,2)
          NOT NULL DEFAULT 50.00
    """)

    # Existing cases return to the provider/customer conversation. Historical
    # AI/admin records remain in the audit tables, but are no longer actionable.
    op.execute("""
        UPDATE complaint_policies
           SET require_admin_review = FALSE,
               ai_settlement_enabled = FALSE,
               ai_auto_start_on_provider_failure = FALSE,
               updated_at = now()
    """)
    op.execute("""
        UPDATE customer_complaints
           SET status = 'awaiting_provider_response', updated_at = now()
         WHERE status = 'under_admin_review' OR status LIKE 'ai_%'
    """)
    op.execute("""
        UPDATE warranty_claims
           SET status = 'provider_action_required',
               provider_response_due_at = now() + INTERVAL '24 hours',
               updated_at = now()
         WHERE status = 'admin_review'
    """)
    op.execute("""
        UPDATE refund_requests
           SET status = 'provider_review',
               provider_response_due_at = now() + INTERVAL '24 hours',
               updated_at = now()
         WHERE status = 'admin_review'
    """)

    # Publish the material policy change and require a fresh acceptance. Only
    # the prior Terms row is archived; privacy and other documents stay live.
    op.execute("""
        UPDATE legal_document_versions
           SET status = 'archived', archived_at = now(), updated_at = now()
         WHERE doc_type = 'terms_of_service'
           AND audience = 'all' AND locale = 'en' AND status = 'published'
    """)
    op.execute("""
        INSERT INTO legal_document_versions
            (doc_type, audience, locale, version, title, summary, body,
             status, effective_at, published_at, requires_reacceptance,
             change_note, meta)
        VALUES (
            'terms_of_service', 'all', 'en', '2.0',
            'Terms of Service',
            'Provider responsibility, paid technician seats, direct remedies, warranty evidence, and service-level penalties.',
            $terms$## Provider and technician responsibility

The service provider is an independent business and is responsible for its employees, contractors, and technicians. The provider must perform the identity, background, qualification, and skills checks it considers necessary before assigning a technician. ServiceOS does not verify or certify individual technicians.

## Technician seats and bookability

Technician capacity comes only from active, paid technician-seat packages published by the platform administrator. Package seat limits and expiry dates are enforced when a provider adds or activates technicians and when bookability is calculated. Buying credits alone does not create technician seats.

## No security deposit

ServiceOS does not collect, hold, or promise recovery from a provider security deposit. Any activation credit, package credit, usage credit, service charge, refund, or penalty is a separate ledger entry governed by its displayed terms.

## Booking and service delivery

The provider is responsible for accepting, assigning, supervising, performing, and completing booked work. A technician may perform the field work, but the provider remains responsible for workmanship, customer communication, and resolution.

## Warranty evidence

After qualifying work is completed, the customer receives a downloadable warranty certificate containing the job, warranty period, and responsible provider details. The certificate is an immutable evidence snapshot for that completed job and does not make ServiceOS the warrantor.

## Complaints, refunds, rework, and settlement

The customer and provider handle service complaints and warranty cases directly. The provider may inspect the work and propose rework, refund, service credit, or another lawful settlement. A settlement takes effect only when the customer and provider agree. ServiceOS supplies workflow and records but does not adjudicate the merits of customer-provider disputes and does not provide AI settlement.

## Service-level obligations and account health

The provider must respond within the configured booking, service, complaint, refund, and warranty time limits. A missed service-level deadline may deduct usage credits from the provider, lower account health and ranking, restrict bookability, or suspend access under the applicable policy. Idempotent ledger records provide evidence of each deduction.

## Acceptable use and contact

Users must provide accurate information, protect credentials, follow applicable law, and avoid misuse of the service. Questions may be sent to support@serviceos.in.$terms$,
            'published', TIMESTAMPTZ '2026-09-01 00:00:00+00', now(), TRUE,
            'Replaced admin/AI dispute adjudication with direct provider-customer remedies; clarified provider technician responsibility, paid seats, warranty evidence, no deposit, and SLA credit penalties.',
            '{"policy_model":"provider_customer_direct_resolution","warranty_certificate_terms":"2026-09-01"}'::jsonb
        )
        ON CONFLICT ON CONSTRAINT uq_legal_doc_version DO UPDATE
          SET title = EXCLUDED.title,
              summary = EXCLUDED.summary,
              body = EXCLUDED.body,
              status = 'published',
              effective_at = EXCLUDED.effective_at,
              published_at = now(),
              archived_at = NULL,
              requires_reacceptance = TRUE,
              change_note = EXCLUDED.change_note,
              meta = EXCLUDED.meta,
              updated_at = now()
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE legal_document_versions
           SET status = 'archived', archived_at = now(), updated_at = now()
         WHERE doc_type = 'terms_of_service' AND audience = 'all'
           AND locale = 'en' AND version = '2.0'
    """)
    op.execute("""
        UPDATE legal_document_versions
           SET status = 'published', archived_at = NULL, updated_at = now()
         WHERE doc_type = 'terms_of_service' AND audience = 'all'
           AND locale = 'en' AND version = '1.0'
    """)
    op.execute("DROP INDEX IF EXISTS uq_service_jobs_warranty_certificate_number")
    op.execute("ALTER TABLE service_jobs DROP COLUMN IF EXISTS warranty_certificate_issued_at")
    op.execute("ALTER TABLE service_jobs DROP COLUMN IF EXISTS warranty_certificate_snapshot")
    op.execute("ALTER TABLE service_jobs DROP COLUMN IF EXISTS warranty_certificate_number")
    op.execute("ALTER TABLE customer_complaints DROP COLUMN IF EXISTS provider_sla_penalized_at")
    op.execute("ALTER TABLE customer_complaints DROP COLUMN IF EXISTS provider_sla_penalty_charged")
    op.execute("ALTER TABLE complaint_policies DROP COLUMN IF EXISTS provider_sla_breach_penalty")
