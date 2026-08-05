/**
 * Customer Privacy & Data Rights API module (DPDP / GDPR self-service).
 *
 * MODULE-L5-15: the customer_router at /v1/me/compliance/* lets a customer
 * exercise its data rights — export, erasure, correction, consent withdrawal,
 * grievances — but the customer app had NO surface or client for any of it, so
 * a customer could not actually exercise a single right from the app.
 *
 * Real router: app/engines/compliance/customer_router.py (prefix /v1/me/compliance)
 *   GET  /requests            POST /requests
 *   GET  /requests/{id}       POST /requests/{id}/cancel   POST /requests/{id}/add-note
 *   GET  /consents            POST /consents/{type}/withdraw
 *   GET  /exports/{id}/download
 */
import { apiFetch } from "./client";

export interface ComplianceRequest {
  id?: string;
  request_id?: string;
  request_number: string;
  request_type: string;
  status: string;
  status_label?: string;
  sla_status?: string | null;
  sla_label?: string | null;
  submitted_at?: string | null;
  due_at?: string | null;
  message?: string;
}

export interface ConsentRecord {
  consent_type: string;
  status: string;
  granted_at?: string | null;
  withdrawn_at?: string | null;
}

// Customer-facing request types (mirror CUSTOMER_ALLOWED_REQUEST_TYPES) with the
// human labels shown in the app.
export const REQUEST_TYPES: {
  value: string; label: string; needsReason?: boolean; needsPassword?: boolean;
}[] = [
  { value: "data_export",          label: "Export my data" },
  { value: "right_to_erasure",     label: "Delete my account & data", needsReason: true, needsPassword: true },
  { value: "data_correction",      label: "Correct my data",          needsReason: true },
  { value: "consent_withdrawal",   label: "Withdraw a consent" },
  { value: "processing_objection", label: "Object to data processing" },
  { value: "grievance",            label: "Raise a privacy grievance", needsReason: true },
];

export async function listPrivacyRequests(): Promise<ComplianceRequest[]> {
  const d = await apiFetch<{ requests: ComplianceRequest[] }>("/v1/me/compliance/requests");
  return d.requests ?? [];
}

export async function createPrivacyRequest(
  requestType: string, reason: string, password?: string,
): Promise<ComplianceRequest> {
  return apiFetch<ComplianceRequest>("/v1/me/compliance/requests", {
    method: "POST",
    body: JSON.stringify({
      request_type: requestType, reason, confirm_understanding: true,
      ...(password ? { password } : {}),
    }),
  });
}

export async function getPrivacyRequest(id: string): Promise<ComplianceRequest> {
  return apiFetch<ComplianceRequest>(`/v1/me/compliance/requests/${id}`);
}

export async function cancelPrivacyRequest(id: string): Promise<unknown> {
  return apiFetch(`/v1/me/compliance/requests/${id}/cancel`, { method: "POST", body: "{}" });
}

export async function listMyConsents(): Promise<ConsentRecord[]> {
  const d = await apiFetch<{ records?: ConsentRecord[]; items?: ConsentRecord[] }>(
    "/v1/me/compliance/consents");
  return d.records ?? d.items ?? [];
}

export async function withdrawConsent(consentType: string, reason: string): Promise<unknown> {
  return apiFetch(`/v1/me/compliance/consents/${encodeURIComponent(consentType)}/withdraw`, {
    method: "POST", body: JSON.stringify({ reason }),
  });
}
