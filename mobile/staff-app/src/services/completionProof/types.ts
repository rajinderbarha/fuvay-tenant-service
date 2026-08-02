import { ChecklistItemDTO } from "../inspection/types";

export interface CompletionProofJobDTO {
  job_id: string;
  job_reference: string;
  workflow_status: string;
  is_terminal: boolean;
}

export interface WorkSummaryDTO {
  work_finished_at: string | null;
  work_session_id: string | null;
  approved_quote_id: string | null;
  approved_quote_version: number | null;
}

export type ProofStatus = "draft" | "submitted";
export type HandoverStatus = "not_requested" | "requested" | "customer_unavailable" | "acknowledged" | "concern_reported";

export interface CompletionProofDTO {
  proof_id: string;
  job_id: string;
  status: ProofStatus;
  resolution_summary: string | null;
  final_service_notes: string | null;
  before_photo_ids: string[];
  after_photo_ids: string[];
  handover_status: HandoverStatus;
  handover_requested_at: string | null;
  handover_last_reminder_at: string | null;
  submitted_by: string | null;
  submitted_at: string | null;
}

export interface CompletionProofDefinitionDTO {
  final_checks: ChecklistItemDTO[];
  customer_handover_required: boolean;
}

export type PartsUsedStatus =
  | "requested" | "business_approved" | "customer_approval_pending"
  | "customer_approved" | "business_rejected" | "customer_rejected" | "installed" | "cancelled";

export interface PartUsedDTO {
  parts_request_id: string;
  part_name: string;
  quantity: number;
  estimated_cost: number;
  status: PartsUsedStatus;
}

export interface CompletionReadinessDTO {
  can_submit: boolean;
  missing_check_ids: string[];
  missing_evidence_categories: string[];
  unresolved_parts: string[];
  blockers: string[];
}

export interface CompletionProofDetailDTO {
  job: CompletionProofJobDTO;
  work_summary: WorkSummaryDTO;
  proof: CompletionProofDTO;
  definition: CompletionProofDefinitionDTO;
  parts_used: PartUsedDTO[];
  readiness: CompletionReadinessDTO;
  final_checks_progress: { required_total: number; required_completed: number };
  allowed_actions: string[];
}
