-- Purge every booking/job and all booking-scoped operational data.
--
-- This is intentionally a test/staging maintenance operation.  It preserves:
--   * providers, staff, customers and authentication records
--   * catalog, service/type/brand/question/pricing configuration
--   * provider top-ups and admin credit adjustments unrelated to a job
--   * notification templates/preferences and complaint/review policies
--
-- IMPORTANT: service_job_dimensions is catalog blueprint configuration.  It
-- must never be included in a booking purge.
--
-- The purge is atomic and fails closed.  Verification at the end raises an
-- exception (and rolls everything back) if any core booking record survives.

\set ON_ERROR_STOP on

BEGIN;
SET LOCAL lock_timeout = '15s';
SET LOCAL statement_timeout = '10min';

-- Snapshot every identifier before deleting parents.  Most historical tables
-- deliberately have no database foreign keys, so application relationships
-- must be removed explicitly.
CREATE TEMP TABLE _purge_booking_ids (id text PRIMARY KEY) ON COMMIT DROP;
CREATE TEMP TABLE _purge_job_ids (id text PRIMARY KEY) ON COMMIT DROP;
CREATE TEMP TABLE _purge_draft_ids (id text PRIMARY KEY) ON COMMIT DROP;
CREATE TEMP TABLE _purge_record_ids (id text PRIMARY KEY) ON COMMIT DROP;
CREATE TEMP TABLE _purge_ai_session_ids (id text PRIMARY KEY) ON COMMIT DROP;

INSERT INTO _purge_booking_ids SELECT id::text FROM service_bookings ON CONFLICT DO NOTHING;
INSERT INTO _purge_booking_ids SELECT id::text FROM bookings ON CONFLICT DO NOTHING;
INSERT INTO _purge_job_ids SELECT id::text FROM service_jobs ON CONFLICT DO NOTHING;
INSERT INTO _purge_job_ids SELECT id::text FROM jobs ON CONFLICT DO NOTHING;
INSERT INTO _purge_draft_ids SELECT id::text FROM home_service_booking_drafts ON CONFLICT DO NOTHING;
INSERT INTO _purge_draft_ids SELECT id::text FROM customer_booking_drafts ON CONFLICT DO NOTHING;

INSERT INTO _purge_record_ids SELECT id FROM _purge_booking_ids ON CONFLICT DO NOTHING;
INSERT INTO _purge_record_ids SELECT id FROM _purge_job_ids ON CONFLICT DO NOTHING;
INSERT INTO _purge_record_ids SELECT id FROM _purge_draft_ids ON CONFLICT DO NOTHING;
INSERT INTO _purge_record_ids SELECT id::text FROM customer_complaints ON CONFLICT DO NOTHING;
INSERT INTO _purge_record_ids SELECT id::text FROM customer_reviews ON CONFLICT DO NOTHING;
INSERT INTO _purge_record_ids SELECT id::text FROM reviews ON CONFLICT DO NOTHING;
INSERT INTO _purge_record_ids SELECT id::text FROM warranty_claims ON CONFLICT DO NOTHING;
INSERT INTO _purge_record_ids SELECT id::text FROM service_invoices ON CONFLICT DO NOTHING;
INSERT INTO _purge_record_ids SELECT id::text FROM service_payment_records ON CONFLICT DO NOTHING;
INSERT INTO _purge_record_ids SELECT id::text FROM service_job_quotes ON CONFLICT DO NOTHING;

INSERT INTO _purge_ai_session_ids
SELECT ai_session_id::text FROM home_service_booking_drafts WHERE ai_session_id IS NOT NULL
ON CONFLICT DO NOTHING;
INSERT INTO _purge_ai_session_ids
SELECT ai_session_id::text FROM service_bookings WHERE ai_session_id IS NOT NULL
ON CONFLICT DO NOTHING;
INSERT INTO _purge_ai_session_ids
SELECT ai_session_id::text FROM messaging_threads WHERE ai_session_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- Booking/job chats and generated notifications.  Global notification
-- settings and unrelated notices remain untouched.
CREATE TEMP TABLE _purge_chat_thread_ids (id text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO _purge_chat_thread_ids
SELECT id::text
FROM chat_threads
WHERE record_id::text IN (SELECT id FROM _purge_record_ids)
   OR lower(record_type) IN ('booking', 'service_booking', 'job', 'service_job',
                             'complaint', 'review', 'warranty_claim')
ON CONFLICT DO NOTHING;

DELETE FROM chat_message_reads WHERE thread_id::text IN (SELECT id FROM _purge_chat_thread_ids);
DELETE FROM chat_messages WHERE thread_id::text IN (SELECT id FROM _purge_chat_thread_ids);
DELETE FROM chat_thread_participants WHERE thread_id::text IN (SELECT id FROM _purge_chat_thread_ids);
DELETE FROM chat_threads WHERE id::text IN (SELECT id FROM _purge_chat_thread_ids);

CREATE TEMP TABLE _purge_notification_event_ids (id text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO _purge_notification_event_ids
SELECT id::text FROM notification_events
WHERE source_record_id::text IN (SELECT id FROM _purge_record_ids)
ON CONFLICT DO NOTHING;

CREATE TEMP TABLE _purge_outbox_ids (id text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO _purge_outbox_ids
SELECT id::text FROM notification_outbox
WHERE notification_event_id::text IN (SELECT id FROM _purge_notification_event_ids)
   OR (
       payload::text ~* '(booking|job|complaint|review|warranty)'
       AND EXISTS (
           SELECT 1 FROM _purge_record_ids p
           WHERE notification_outbox.payload::text LIKE '%' || p.id || '%'
       )
   )
ON CONFLICT DO NOTHING;

DELETE FROM in_app_notifications
WHERE outbox_id::text IN (SELECT id FROM _purge_outbox_ids)
   OR source_record_id::text IN (SELECT id FROM _purge_record_ids);
DELETE FROM notification_outbox WHERE id::text IN (SELECT id FROM _purge_outbox_ids);
DELETE FROM notification_events WHERE id::text IN (SELECT id FROM _purge_notification_event_ids);

-- Documents and database media records attached to the purged records.  Media
-- configuration and provider/catalog artwork are not touched.
CREATE TEMP TABLE _purge_document_ids (id text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO _purge_document_ids
SELECT id::text FROM documents
WHERE entity_id IN (SELECT id FROM _purge_record_ids)
ON CONFLICT DO NOTHING;
DELETE FROM document_events WHERE document_id::text IN (SELECT id FROM _purge_document_ids);
DELETE FROM documents WHERE id::text IN (SELECT id FROM _purge_document_ids);

DELETE FROM media_files WHERE entity_id IN (SELECT id FROM _purge_record_ids);
DELETE FROM media_upload_sessions WHERE entity_id IN (SELECT id FROM _purge_record_ids);
DELETE FROM media_assets
WHERE linked_record_id IN (SELECT id FROM _purge_record_ids)
   OR (
       lower(owner_type) IN ('booking', 'service_booking', 'job', 'service_job',
                             'complaint', 'review', 'warranty_claim')
       AND owner_id::text IN (SELECT id FROM _purge_record_ids)
   );

-- Complaint, rework, refund and warranty records.
DELETE FROM settlement_proposals;
DELETE FROM complaint_resolutions;
DELETE FROM complaint_events;
DELETE FROM complaint_media;
DELETE FROM complaint_messages;
DELETE FROM service_rework_requests;
DELETE FROM refund_requests;
DELETE FROM customer_complaints;
DELETE FROM warranty_claims;

-- Reviews and every derived rating projection.  Policies remain configured;
-- summaries will rebuild from future reviews.
DELETE FROM review_events;
DELETE FROM review_flags;
DELETE FROM review_replies;
DELETE FROM customer_reviews;
DELETE FROM review_status_history;
DELETE FROM review_requests;
DELETE FROM reviews;
DELETE FROM tenant_rating_summaries;
DELETE FROM staff_rating_summaries;
DELETE FROM review_aggregates;
DELETE FROM customer_behavior_assessments;
DELETE FROM customer_health_scores;

-- Quote, checklist, execution, assignment and dispatch lifecycle.
DELETE FROM service_job_quote_events;
DELETE FROM service_job_quote_items;
DELETE FROM service_job_quotes;
DELETE FROM service_job_assignment_events;
DELETE FROM service_job_assignments;
DELETE FROM service_job_execution_events;
DELETE FROM service_job_execution_notes;
DELETE FROM service_job_completion_proofs;
DELETE FROM service_job_checklist_items;
DELETE FROM service_job_checklists;
DELETE FROM service_job_media_uploads;
DELETE FROM service_job_parts_requests;
DELETE FROM service_job_work_sessions;
DELETE FROM job_checklist_responses;
DELETE FROM job_checklist_instances;
DELETE FROM dispatch_escalation_logs;
DELETE FROM dispatch_records;
DELETE FROM technician_live_locations;
DELETE FROM masked_call_sessions;

-- Customer-facing booking records.
DELETE FROM customer_booking_confirmations;
DELETE FROM booking_reschedule_requests;
DELETE FROM booking_option_selections;
DELETE FROM booking_status_history;
DELETE FROM booking_notes;
DELETE FROM price_snapshots;
DELETE FROM credit_reservations;

-- Restore provider usage-credit balances before removing job-linked ledger
-- entries.  Top-ups and manual adjustments are deliberately retained.
UPDATE tenant_billing AS billing
SET credit_balance = billing.credit_balance - linked.net_delta
FROM (
  SELECT tenant_id, SUM(credit_delta) AS net_delta
  FROM usage_credit_ledger
  WHERE job_id IS NOT NULL OR booking_id IS NOT NULL
  GROUP BY tenant_id
) AS linked
WHERE billing.tenant_id = linked.tenant_id;
DELETE FROM usage_credit_ledger WHERE job_id IS NOT NULL OR booking_id IS NOT NULL;

-- The newer wallet ledger also records booking/invoice/commission references.
-- Reverse only those transactions, leaving purchased credits intact.
CREATE TEMP TABLE _purge_wallet_transactions ON COMMIT DROP AS
SELECT id, tenant_id, amount
FROM wallet_transactions
WHERE reference_id IN (SELECT id FROM _purge_record_ids)
   OR (
       lower(coalesce(reference_type, '')) IN
           ('booking', 'job', 'invoice', 'payment', 'commission', 'complaint', 'warranty')
       AND reference_id IS NOT NULL
   );

UPDATE tenant_wallets AS wallet
SET credit_balance = greatest(0, wallet.credit_balance - linked.net_amount),
    lifetime_consumed = greatest(0, wallet.lifetime_consumed - linked.debit_amount),
    reserved_balance = 0
FROM (
  SELECT tenant_id,
         coalesce(SUM(amount), 0) AS net_amount,
         coalesce(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0) AS debit_amount
  FROM _purge_wallet_transactions
  GROUP BY tenant_id
) AS linked
WHERE wallet.tenant_id = linked.tenant_id;
DELETE FROM wallet_transactions WHERE id IN (SELECT id FROM _purge_wallet_transactions);

-- Customer credits tied to purged work.  Standalone purchases remain.
CREATE TEMP TABLE _purge_customer_transactions ON COMMIT DROP AS
SELECT id, customer_id, tenant_id, amount
FROM customer_transactions
WHERE reference_id IN (SELECT id FROM _purge_record_ids)
   OR (
       lower(coalesce(reference_type, '')) IN
           ('booking', 'job', 'invoice', 'payment', 'complaint', 'warranty')
       AND reference_id IS NOT NULL
   );

UPDATE customer_credit_balances AS balance
SET credit_balance = greatest(0, balance.credit_balance - linked.net_amount),
    lifetime_consumed = greatest(0, balance.lifetime_consumed - linked.debit_amount),
    reserved_amount = 0
FROM (
  SELECT customer_id, tenant_id,
         coalesce(SUM(amount), 0) AS net_amount,
         coalesce(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0) AS debit_amount
  FROM _purge_customer_transactions
  GROUP BY customer_id, tenant_id
) AS linked
WHERE balance.customer_id = linked.customer_id
  AND balance.tenant_id = linked.tenant_id;
DELETE FROM customer_transactions WHERE id IN (SELECT id FROM _purge_customer_transactions);

DELETE FROM customer_credit_ledger WHERE booking_id IS NOT NULL;
DELETE FROM customer_service_credits WHERE booking_id IS NOT NULL OR job_id IS NOT NULL;
DELETE FROM finance_audit_logs WHERE booking_id IS NOT NULL;
DELETE FROM tenant_penalties WHERE booking_id IS NOT NULL OR job_id IS NOT NULL;
DELETE FROM dispute_settlements WHERE booking_id IS NOT NULL OR job_id IS NOT NULL;
DELETE FROM stock_reservations WHERE job_id IS NOT NULL;
DELETE FROM stock_transactions WHERE job_id IS NOT NULL;

-- Invoices, payments and commissions are wholly booking/job scoped here.
DELETE FROM customer_platform_fee_charges;
DELETE FROM service_invoice_items;
DELETE FROM svc_commission_records;
DELETE FROM commission_records;
DELETE FROM service_payment_records;
DELETE FROM service_invoices;
DELETE FROM financial_events
WHERE record_id::text IN (SELECT id FROM _purge_record_ids)
   OR lower(record_type) IN ('booking', 'job', 'invoice', 'payment', 'commission');

DELETE FROM refund_records
WHERE payment_id::text IN (
    SELECT id::text FROM payment_records
    WHERE booking_id IS NOT NULL OR job_id IS NOT NULL
);
DELETE FROM invoice_records WHERE booking_id IS NOT NULL OR job_id IS NOT NULL;
DELETE FROM payment_records WHERE booking_id IS NOT NULL OR job_id IS NOT NULL;

-- Booking creation audit and roots.
DELETE FROM final_creation_audit_logs;
DELETE FROM service_jobs;
DELETE FROM service_bookings;
DELETE FROM home_service_booking_draft_events;
DELETE FROM home_service_booking_drafts;
DELETE FROM customer_booking_drafts;

-- Retired field-ops booking tables.
DELETE FROM job_status_history;
DELETE FROM job_media;
DELETE FROM job_notes;
DELETE FROM job_quotes;
DELETE FROM jobs;
DELETE FROM bookings;

-- Remove AI state that belonged to booking conversations, while preserving the
-- Instagram/WhatsApp identity mapping needed for future conversations.
DELETE FROM messaging_handoff_links
WHERE draft_id::text IN (SELECT id FROM _purge_draft_ids);
DELETE FROM ai_action_logs
WHERE draft_id::text IN (SELECT id FROM _purge_draft_ids);
DELETE FROM ai_tool_call_logs
WHERE session_id::text IN (SELECT id FROM _purge_ai_session_ids);
DELETE FROM ai_llm_call_logs
WHERE session_id::text IN (SELECT id FROM _purge_ai_session_ids);
DELETE FROM ai_conversation_audit_logs
WHERE session_id::text IN (SELECT id FROM _purge_ai_session_ids);
DELETE FROM ai_workflow_states
WHERE session_id::text IN (SELECT id FROM _purge_ai_session_ids);
DELETE FROM ai_conversation_messages
WHERE session_id::text IN (SELECT id FROM _purge_ai_session_ids);
DELETE FROM ai_conversation_sessions
WHERE id::text IN (SELECT id FROM _purge_ai_session_ids);

UPDATE messaging_threads
SET ai_session_id = NULL,
    tenant_id = NULL,
    last_options = NULL,
    human_handoff = FALSE
WHERE ai_session_id IS NOT NULL
   OR tenant_id IS NOT NULL
   OR last_options IS NOT NULL
   OR human_handoff IS TRUE;

-- Fail closed: any survivor aborts and rolls back the entire purge.
DO $$
DECLARE
    survivors bigint;
BEGIN
    SELECT
        (SELECT count(*) FROM service_bookings)
      + (SELECT count(*) FROM service_jobs)
      + (SELECT count(*) FROM home_service_booking_drafts)
      + (SELECT count(*) FROM customer_booking_drafts)
      + (SELECT count(*) FROM customer_reviews)
      + (SELECT count(*) FROM reviews)
      + (SELECT count(*) FROM customer_complaints)
      + (SELECT count(*) FROM warranty_claims)
      + (SELECT count(*) FROM service_invoices)
      + (SELECT count(*) FROM service_payment_records)
    INTO survivors;

    IF survivors <> 0 THEN
        RAISE EXCEPTION 'Booking purge verification failed: % core rows remain', survivors;
    END IF;
END $$;

COMMIT;

SELECT
    (SELECT count(*) FROM service_bookings) AS service_bookings,
    (SELECT count(*) FROM service_jobs) AS service_jobs,
    (SELECT count(*) FROM home_service_booking_drafts) AS home_service_drafts,
    (SELECT count(*) FROM customer_booking_drafts) AS customer_booking_drafts,
    (SELECT count(*) FROM customer_reviews) AS customer_reviews,
    (SELECT count(*) FROM customer_complaints) AS complaints,
    (SELECT count(*) FROM warranty_claims) AS warranty_claims,
    (SELECT count(*) FROM service_invoices) AS service_invoices;
