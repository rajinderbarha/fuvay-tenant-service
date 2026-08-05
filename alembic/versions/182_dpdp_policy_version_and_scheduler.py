"""DPDP-COMMAND-CENTER: versioned policy configuration + scheduler run log.

Legal interpretation (SLA hours, applicable request types, evidence
requirements, enforcement phase) must be stored, versioned data -- not
hardcoded frontend text or a single mutable settings row. Adding a
DPDPSchedulerRun log makes the automated SLA evaluator's health
(healthy/failed, last/next run, requests evaluated, breaches generated)
backend-authoritative instead of frontend-inferred.

Seeds exactly one active policy version (DPDP-2025-v1) referencing the
official MeitY DPDP Act 2023 / DPDP Rules 2025 publication -- the seeded
row is the versioned CONFIGURATION the workflow reads; it is not itself a
legal-compliance certification.

Purely additive.

Revision ID: 182
Revises: 181
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "182"
down_revision = "181"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dpdp_policy_versions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_name", sa.String(200), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enforcement_phase", sa.String(60), nullable=False),
        sa.Column("applicable_request_types", sa.dialects.postgresql.JSONB, nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column("sla_policy", sa.dialects.postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("retention_policy_version", sa.String(40), nullable=True),
        sa.Column("evidence_requirements", sa.dialects.postgresql.JSONB, nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_policy_review", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(200), nullable=True),
        sa.Column("superseded_version", sa.String(40), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("source_reference", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_dpdp_policy_version", "dpdp_policy_versions", ["policy_version"])
    op.create_index("ix_dpdp_policy_active", "dpdp_policy_versions", ["is_active"])

    op.create_table(
        "dpdp_scheduler_runs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_name", sa.String(60), nullable=False, server_default="dpdp_sla_evaluator"),
        sa.Column("trigger", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("triggered_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requests_evaluated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("due_soon_generated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("breaches_generated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_dpdp_scheduler_job", "dpdp_scheduler_runs", ["job_name"])
    op.create_index("ix_dpdp_scheduler_started", "dpdp_scheduler_runs", ["started_at"])

    op.execute("""
        INSERT INTO dpdp_policy_versions (
            policy_name, policy_version, publication_date, effective_date, enforcement_phase,
            applicable_request_types, sla_policy, retention_policy_version, evidence_requirements,
            approved_by, is_active, source_reference
        ) VALUES (
            'Digital Personal Data Protection Act 2023 / DPDP Rules 2025',
            'DPDP-2025-v1',
            '2025-01-01T00:00:00+00:00',
            '2025-01-01T00:00:00+00:00',
            'rules_notified_phased_enforcement',
            '["access_information","correction","erasure","consent_withdrawal","grievance",
              "nomination","account_closure","voluntary_data_export","restrict_processing"]'::jsonb,
            '{"identity_verification_hours": 72, "standard_response_hours": 720,
              "grievance_response_hours": 720}'::jsonb,
            'v1',
            '["government_id_or_registered_contact_match","otp_or_document_verification",
              "authorized_representative_authority_proof"]'::jsonb,
            'System Seed — requires legal/compliance review before being treated as authoritative',
            true,
            'https://www.meity.gov.in/content/digital-personal-dataprotection-act-2023; '
            'https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa'
        )
    """)


def downgrade() -> None:
    op.drop_table("dpdp_scheduler_runs")
    op.drop_table("dpdp_policy_versions")
