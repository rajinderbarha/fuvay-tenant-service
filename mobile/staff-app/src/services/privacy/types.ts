export type PrivacyStatusCode = "up_to_date" | "request_in_progress" | "review_required" | "unavailable";

export interface PrivacyStatusDTO {
  code: PrivacyStatusCode;
  label: string;
}

export interface RequestSummaryDTO {
  id: string;
  request_number: string;
  request_type: string;
  status: string;
  status_label: string;
  sla_status: string | null;
  verification_status: string | null;
  submitted_at: string | null;
  due_at: string | null;
  completed_at: string | null;
  reason: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface PrivacySummaryDTO {
  privacy_status: PrivacyStatusDTO;
  policy: { version: string; effective_from: string | null };
  request_counts: { open: number; completed: number };
  recent_request: RequestSummaryDTO | null;
}

export interface ConsentPurposeDTO {
  purpose_code: string;
  label: string;
  description: string;
  legal_or_policy_basis: string;
  required: boolean;
  enabled: boolean;
  configurable: boolean;
  policy_version: string;
  last_changed_at: string | null;
}

export interface ConsentHistoryItemDTO {
  id: string;
  consent_type: string;
  action: "granted" | "withdrawn" | "expired" | "updated";
  policy_version: string;
  granted_at: string | null;
  withdrawn_at: string | null;
  created_at: string;
}

export type PrivacyRequestType = "data_correction" | "consent_withdrawal" | "processing_objection" | "grievance" | "staff_data_export" | "staff_data_erasure";

export interface RequestDetailDTO extends RequestSummaryDTO {
  audit_trail: { action: string; created_at: string }[];
  export?: { export_id: string; status: string; expires_at: string | null; is_expired: boolean };
}

export interface ExportStatusDTO {
  export_id: string;
  status: string;
  expires_at: string | null;
  downloaded_at: string | null;
  download_url: string | null;
}
