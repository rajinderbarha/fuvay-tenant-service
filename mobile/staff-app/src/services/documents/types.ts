export interface DocumentsReadinessDTO {
  percentage: number;
  complete: number;
  required: number;
  action_needed: number;
  pending: number;
  verified: number;
}

export type DocumentReviewStatus = "missing" | "pending_review" | "verified" | "rejected" | "changes_requested" | "superseded";
export type DocumentDisplayCondition = "expiring_soon" | "expired" | null;
export type DocumentAllowedAction = "upload" | "view" | "replace" | "history";

export interface DocumentRequirementDTO {
  requirement_id: string;
  code: string;
  label: string;
  required: boolean;
  requires_expiry: boolean;
  requires_document_number: boolean;
  current_document_id: string | null;
  current_version: number | null;
  review_status: DocumentReviewStatus;
  display_condition: DocumentDisplayCondition;
  submitted_at: string | null;
  verified_at: string | null;
  expires_at: string | null;
  days_until_expiry: number | null;
  reviewer_note: string | null;
  allowed_actions: DocumentAllowedAction[];
}

export interface DocumentsDetailDTO {
  readiness: DocumentsReadinessDTO;
  requirements: DocumentRequirementDTO[];
}

export interface DocumentVersionDTO {
  id: string;
  doc_type: string;
  version: number;
  status: DocumentReviewStatus;
  document_number: string | null;
  issue_date: string | null;
  expiry_date: string | null;
  submitted_at: string | null;
  verified_at: string | null;
  rejection_reason: string | null;
  review_notes: string | null;
  media_asset_id: string | null;
  is_current: boolean;
}

export type DocumentFilter = "all" | "action_needed" | "pending" | "verified";
