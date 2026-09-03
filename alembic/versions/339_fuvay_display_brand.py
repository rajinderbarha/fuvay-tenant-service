"""Publish the Fuvay product name in persisted user-facing content.

Revision ID: 339
Revises: 338

The lowercase ``serviceos:*`` identifiers, storage keys, package names, and
historical/audit records are compatibility contracts and intentionally remain
unchanged.  Published legal text is immutable, so it is superseded with a new
version instead of being edited in place.
"""
from alembic import op


revision = "339"
down_revision = "338"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Mutable template/configuration records should render the current product
    # name for both upgraded and newly installed environments.
    op.execute("""
        UPDATE notification_templates
           SET title = replace(title, 'ServiceOS', 'Fuvay'),
               body = replace(body, 'ServiceOS', 'Fuvay'),
               subject = replace(subject, 'ServiceOS', 'Fuvay'),
               html_body = replace(html_body, 'ServiceOS', 'Fuvay'),
               plain_text_body = replace(plain_text_body, 'ServiceOS', 'Fuvay'),
               updated_at = now()
         WHERE COALESCE(title, '') LIKE '%ServiceOS%'
            OR COALESCE(body, '') LIKE '%ServiceOS%'
            OR COALESCE(subject, '') LIKE '%ServiceOS%'
            OR COALESCE(html_body, '') LIKE '%ServiceOS%'
            OR COALESCE(plain_text_body, '') LIKE '%ServiceOS%'
    """)
    op.execute("""
        UPDATE notif_event_templates
           SET template_name = replace(template_name, 'ServiceOS', 'Fuvay'),
               subject_template = replace(subject_template, 'ServiceOS', 'Fuvay'),
               body_template = replace(body_template, 'ServiceOS', 'Fuvay'),
               updated_at = now()
         WHERE COALESCE(template_name, '') LIKE '%ServiceOS%'
            OR COALESCE(subject_template, '') LIKE '%ServiceOS%'
            OR COALESCE(body_template, '') LIKE '%ServiceOS%'
    """)
    op.execute("""
        UPDATE support_knowledge_articles
           SET title = replace(title, 'ServiceOS', 'Fuvay'),
               summary = replace(summary, 'ServiceOS', 'Fuvay'),
               body = replace(body, 'ServiceOS', 'Fuvay'),
               updated_at = now()
         WHERE COALESCE(title, '') LIKE '%ServiceOS%'
            OR COALESCE(summary, '') LIKE '%ServiceOS%'
            OR COALESCE(body, '') LIKE '%ServiceOS%'
    """)
    op.execute("""
        UPDATE tenant_assistant_configs
           SET tagline = replace(tagline, 'ServiceOS', 'Fuvay'),
               system_prompt = replace(system_prompt, 'ServiceOS', 'Fuvay'),
               out_of_scope_message = replace(out_of_scope_message, 'ServiceOS', 'Fuvay'),
               no_answer_message = replace(no_answer_message, 'ServiceOS', 'Fuvay'),
               updated_at = now()
         WHERE COALESCE(tagline, '') LIKE '%ServiceOS%'
            OR COALESCE(system_prompt, '') LIKE '%ServiceOS%'
            OR COALESCE(out_of_scope_message, '') LIKE '%ServiceOS%'
            OR COALESCE(no_answer_message, '') LIKE '%ServiceOS%'
    """)
    op.execute("""
        UPDATE marketing_campaign_rules
           SET rule_config = replace(rule_config::text, 'ServiceOS', 'Fuvay')::jsonb,
               updated_at = now()
         WHERE rule_config::text LIKE '%ServiceOS%'
    """)

    # These messages were never delivered because no provider was configured.
    # Delivered messages remain untouched as historical evidence.
    op.execute("""
        UPDATE notification_outbox
           SET title = replace(title, 'ServiceOS', 'Fuvay'),
               body = replace(body, 'ServiceOS', 'Fuvay'),
               updated_at = now()
         WHERE delivery_status = 'provider_not_configured'
           AND (title LIKE '%ServiceOS%' OR body LIKE '%ServiceOS%')
    """)

    # Supersede only currently governing documents.  Old versions remain
    # intact for consent evidence.  A brand-only update does not force an
    # existing user to re-accept; new users consent to the new document id.
    op.execute("""
        WITH current_docs AS (
            SELECT DISTINCT ON (doc_type, audience, locale)
                   id, doc_type, audience, locale, version, title, summary,
                   body, body_format, created_by, published_by, meta
              FROM legal_document_versions
             WHERE status = 'published'
               AND effective_at <= now()
               AND (title LIKE '%ServiceOS%'
                    OR COALESCE(summary, '') LIKE '%ServiceOS%'
                    OR body LIKE '%ServiceOS%')
             ORDER BY doc_type, audience, locale, effective_at DESC
        ), inserted AS (
            INSERT INTO legal_document_versions
                (id, doc_type, audience, locale, version, title, summary, body,
                 body_format, status, effective_at, published_at, archived_at,
                 requires_reacceptance, change_note, created_by, published_by,
                 meta, created_at, updated_at)
            SELECT gen_random_uuid(), doc_type, audience, locale,
                   CASE WHEN length(version) <= 14
                        THEN version || '-fuvay'
                        ELSE left(version, 14) || '-fuvay' END,
                   replace(title, 'ServiceOS', 'Fuvay'),
                   replace(summary, 'ServiceOS', 'Fuvay'),
                   replace(body, 'ServiceOS', 'Fuvay'),
                   body_format, 'published', now(), now(), NULL, FALSE,
                   'Product display name updated from ServiceOS to Fuvay.',
                   created_by, published_by,
                   COALESCE(meta, '{}'::jsonb) || jsonb_build_object(
                       'brand_migration', '339', 'supersedes_id', id::text
                   ),
                   now(), now()
              FROM current_docs
            ON CONFLICT ON CONSTRAINT uq_legal_doc_version DO UPDATE
              SET title = EXCLUDED.title,
                  summary = EXCLUDED.summary,
                  body = EXCLUDED.body,
                  body_format = EXCLUDED.body_format,
                  status = 'published',
                  effective_at = EXCLUDED.effective_at,
                  published_at = now(),
                  archived_at = NULL,
                  requires_reacceptance = FALSE,
                  change_note = EXCLUDED.change_note,
                  meta = EXCLUDED.meta,
                  updated_at = now()
            RETURNING (meta->>'supersedes_id')::uuid AS supersedes_id
        )
        UPDATE legal_document_versions old
           SET status = 'archived', archived_at = now(), updated_at = now()
          FROM inserted new
         WHERE old.id = new.supersedes_id
           AND old.status = 'published'
    """)


def downgrade() -> None:
    # Legal versions cannot be deleted or rewritten after a user may have
    # accepted them.  Restore the prior governing rows and archive the Fuvay
    # versions while keeping both documents available for consent evidence.
    op.execute("""
        UPDATE legal_document_versions old
           SET status = 'published', archived_at = NULL, updated_at = now()
          FROM legal_document_versions branded
         WHERE branded.meta @> '{"brand_migration":"339"}'::jsonb
           AND old.id::text = branded.meta->>'supersedes_id'
    """)
    op.execute("""
        UPDATE legal_document_versions
           SET status = 'archived', archived_at = now(), updated_at = now()
         WHERE meta @> '{"brand_migration":"339"}'::jsonb
    """)

    # Mutable current content can safely return to the previous display name.
    op.execute("""
        UPDATE notification_templates
           SET title = replace(title, 'Fuvay', 'ServiceOS'),
               body = replace(body, 'Fuvay', 'ServiceOS'),
               subject = replace(subject, 'Fuvay', 'ServiceOS'),
               html_body = replace(html_body, 'Fuvay', 'ServiceOS'),
               plain_text_body = replace(plain_text_body, 'Fuvay', 'ServiceOS'),
               updated_at = now()
    """)
    op.execute("""
        UPDATE notif_event_templates
           SET template_name = replace(template_name, 'Fuvay', 'ServiceOS'),
               subject_template = replace(subject_template, 'Fuvay', 'ServiceOS'),
               body_template = replace(body_template, 'Fuvay', 'ServiceOS'),
               updated_at = now()
    """)
    op.execute("""
        UPDATE support_knowledge_articles
           SET title = replace(title, 'Fuvay', 'ServiceOS'),
               summary = replace(summary, 'Fuvay', 'ServiceOS'),
               body = replace(body, 'Fuvay', 'ServiceOS'),
               updated_at = now()
    """)
    op.execute("""
        UPDATE tenant_assistant_configs
           SET tagline = replace(tagline, 'Fuvay', 'ServiceOS'),
               system_prompt = replace(system_prompt, 'Fuvay', 'ServiceOS'),
               out_of_scope_message = replace(out_of_scope_message, 'Fuvay', 'ServiceOS'),
               no_answer_message = replace(no_answer_message, 'Fuvay', 'ServiceOS'),
               updated_at = now()
    """)
    op.execute("""
        UPDATE marketing_campaign_rules
           SET rule_config = replace(rule_config::text, 'Fuvay', 'ServiceOS')::jsonb,
               updated_at = now()
         WHERE rule_config::text LIKE '%Fuvay%'
    """)
    op.execute("""
        UPDATE notification_outbox
           SET title = replace(title, 'Fuvay', 'ServiceOS'),
               body = replace(body, 'Fuvay', 'ServiceOS'),
               updated_at = now()
         WHERE delivery_status = 'provider_not_configured'
    """)
