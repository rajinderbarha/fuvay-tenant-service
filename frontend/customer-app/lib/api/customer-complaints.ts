/**
 * Customer Complaints API module.
 *
 * MODULE-L5-02 bug #34: the customer app had NO complaint surface at all — not a
 * single reference to "complaint" anywhere in it. The person who actually FILES
 * a complaint could not file one, read it, accept or reject a proposed
 * resolution, request a refund, or answer a settlement proposal from the app,
 * even though every endpoint below exists and works.
 *
 * Real router: app/engines/complaints/customer_router.py
 *   GET  /v1/customer/complaints/check-eligible?record_type&record_id
 *   POST /v1/customer/complaints
 *   GET  /v1/customer/complaints
 *   GET  /v1/customer/complaints/{id}
 *   GET  /v1/customer/complaints/{id}/messages
 *   POST /v1/customer/complaints/{id}/messages
 *   POST /v1/customer/complaints/{id}/cancel
 *   POST /v1/customer/complaints/{id}/resolutions/{resolution_id}/accept
 *   POST /v1/customer/complaints/{id}/resolutions/{resolution_id}/reject
 *   POST /v1/customer/complaints/{id}/refund
 *   GET  /v1/customer/complaints/{id}/settlement-proposals
 *   POST /v1/customer/complaints/{id}/settlement-proposals/{proposal_id}/respond
 */
import { apiFetch } from "./client";

export interface Complaint {
  id: string;
  complaint_number: string;
  status: string;
  sla_status?: string | null;
  priority?: string | null;
  complaint_type: string;
  title?: string | null;
  description: string;
  record_type: string;
  record_id: string;
  requested_resolution?: string | null;
  resolved_at?: string | null;
  created_at: string;
}

export interface ComplaintMessage {
  id: string;
  sender_type: string;
  message_text: string;
  created_at: string;
}

export interface ComplaintResolution {
  id: string;
  resolution_type: string;
  status: string;
  description: string;
}

export interface SettlementProposal {
  id: string;
  proposal_type: string;
  status: string;
  proposed_by: string;
  proposal_amount?: number | string | null;
  description: string;
  customer_response?: string | null;
  tenant_response?: string | null;
}

export interface EligibilityResult {
  eligible: boolean;
  reason?: string | null;
}

// ── Eligibility + creation ───────────────────────────────────────────────────

export function checkComplaintEligibility(
  recordType: string, recordId: string,
): Promise<EligibilityResult> {
  const qs = new URLSearchParams({ record_type: recordType, record_id: recordId });
  return apiFetch<EligibilityResult>(`/v1/customer/complaints/check-eligible?${qs}`);
}

export function createComplaint(payload: {
  record_type: string;
  record_id: string;
  complaint_type: string;
  description: string;
  title?: string;
  requested_resolution?: string;
}): Promise<Complaint> {
  return apiFetch<Complaint>("/v1/customer/complaints", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Read ─────────────────────────────────────────────────────────────────────

export function listComplaints(status?: string): Promise<Complaint[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch<Complaint[]>(`/v1/customer/complaints${qs}`);
}

export function getComplaint(id: string): Promise<Complaint> {
  return apiFetch<Complaint>(`/v1/customer/complaints/${id}`);
}

export function getComplaintMessages(id: string): Promise<ComplaintMessage[]> {
  return apiFetch<ComplaintMessage[]>(`/v1/customer/complaints/${id}/messages`);
}

/**
 * bug #35: this endpoint did not exist — the customer had accept/reject but no
 * way to SEE what resolution had been offered, nor to obtain the resolution_id
 * those endpoints require. Added to the customer router alongside this module.
 */
export function getComplaintResolutions(id: string): Promise<ComplaintResolution[]> {
  return apiFetch<ComplaintResolution[]>(`/v1/customer/complaints/${id}/resolutions`);
}

export function getSettlementProposals(id: string): Promise<SettlementProposal[]> {
  return apiFetch<SettlementProposal[]>(`/v1/customer/complaints/${id}/settlement-proposals`);
}

export interface AISession {
  id: string;
  status: string;
  customer_questions?: string[] | null;
  customer_answers?: string[] | null;
  awaiting_your_answers?: boolean;
}

/** bug #37/#34: the AI settlement asks the customer clarifying questions; they
 *  must be able to see and answer them from the app. */
export function getAISession(id: string): Promise<AISession | null> {
  return apiFetch<AISession | null>(`/v1/customer/complaints/${id}/ai-session`);
}

export function submitAIAnswers(id: string, answers: string[]): Promise<AISession> {
  return apiFetch<AISession>(`/v1/customer/complaints/${id}/ai-session/answers`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

// ── Actions ──────────────────────────────────────────────────────────────────

export function addComplaintMessage(id: string, messageText: string): Promise<ComplaintMessage> {
  return apiFetch<ComplaintMessage>(`/v1/customer/complaints/${id}/messages`, {
    method: "POST",
    body: JSON.stringify({ message_text: messageText }),
  });
}

export function cancelComplaint(id: string, reason: string): Promise<Complaint> {
  return apiFetch<Complaint>(`/v1/customer/complaints/${id}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

/** Accepting a *rework* resolution creates a rework request (bug #28). */
export function acceptResolution(id: string, resolutionId: string): Promise<ComplaintResolution> {
  return apiFetch<ComplaintResolution>(
    `/v1/customer/complaints/${id}/resolutions/${resolutionId}/accept`,
    { method: "POST", body: JSON.stringify({}) },
  );
}

export function rejectResolution(
  id: string, resolutionId: string, reason: string,
): Promise<ComplaintResolution> {
  return apiFetch<ComplaintResolution>(
    `/v1/customer/complaints/${id}/resolutions/${resolutionId}/reject`,
    { method: "POST", body: JSON.stringify({ reason }) },
  );
}

export function requestRefund(id: string, payload: {
  refund_type: string;
  reason: string;
  requested_amount?: number;
  refund_method?: string;
}): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/v1/customer/complaints/${id}/refund`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** A settlement only takes effect once BOTH parties accept (bug #30). */
export function respondToSettlement(
  id: string, proposalId: string, response: string, counterDescription?: string,
): Promise<SettlementProposal> {
  return apiFetch<SettlementProposal>(
    `/v1/customer/complaints/${id}/settlement-proposals/${proposalId}/respond`,
    {
      method: "POST",
      body: JSON.stringify({
        response,
        ...(counterDescription ? { counter_description: counterDescription } : {}),
      }),
    },
  );
}
