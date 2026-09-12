-- Purge all job and booking transactional data (test mode).
--
-- WHAT THIS DELETES
--   Every booking, job, and record that hangs off one: drafts and their event
--   log, assignments, execution events, quotes, completion proofs, checklists,
--   the customer platform-fee charges raised against them, and the reviews
--   written about them.
--
-- WHAT THIS KEEPS -- deliberately
--   Configuration:  job_types, service_job_workflow, categories, services,
--                   checklist templates, verticals, monetization + finance
--                   policies, top-up plans.
--   Accounts:       tenants, users, staff rosters, customers.
--   Non-job money:  usage_credit_ledger rows with no job_id (top-ups and
--                   manual adjustments), and customer credits not tied to a
--                   booking. Only job-linked financial rows are removed, so a
--                   provider's purchase history survives the purge.
--
-- The schema declares no foreign keys between these tables -- integrity is
-- enforced in the application -- so order does not matter for correctness.
-- Children are still deleted first so a partial run leaves nothing orphaned.
--
-- Runs in one transaction: it either all happens or none of it does.

BEGIN;

-- ── Records that exist only to describe a job or booking ────────────────────
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
DELETE FROM service_job_dimensions;
DELETE FROM job_checklist_responses;
DELETE FROM job_checklist_instances;

-- ── The customer-facing side of a booking ──────────────────────────────────
DELETE FROM customer_booking_confirmations;
DELETE FROM customer_platform_fee_charges;
DELETE FROM customer_reviews;
DELETE FROM service_invoice_items;
DELETE FROM service_payment_records;
DELETE FROM service_invoices;
DELETE FROM booking_reschedule_requests;
DELETE FROM booking_option_selections;
DELETE FROM booking_status_history;
DELETE FROM booking_notes;

-- ── Money: ONLY rows tied to a job or booking ──────────────────────────────
-- A provider's top-ups and an admin's manual adjustments are not job data and
-- are what their balance is built from, so they stay.
DELETE FROM usage_credit_ledger    WHERE job_id IS NOT NULL OR booking_id IS NOT NULL;
DELETE FROM customer_credit_ledger WHERE booking_id IS NOT NULL;
DELETE FROM customer_service_credits WHERE booking_id IS NOT NULL OR job_id IS NOT NULL;
DELETE FROM finance_audit_logs     WHERE booking_id IS NOT NULL;  -- no job_id column
DELETE FROM stock_transactions     WHERE job_id IS NOT NULL;
DELETE FROM messaging_handoff_links WHERE draft_id IS NOT NULL;  -- links to a draft, not a job

-- ── Audit of the creation pipeline ─────────────────────────────────────────
DELETE FROM final_creation_audit_logs;

-- ── The jobs and bookings themselves, then the drafts they came from ───────
DELETE FROM service_jobs;
DELETE FROM service_bookings;
DELETE FROM home_service_booking_draft_events;
DELETE FROM home_service_booking_drafts;
DELETE FROM customer_booking_drafts;

-- ── Retired field_ops tables, empty in this deployment but purged anyway ────
DELETE FROM job_status_history;
DELETE FROM job_media;
DELETE FROM job_notes;
DELETE FROM job_quotes;
DELETE FROM jobs;
DELETE FROM bookings;

COMMIT;
