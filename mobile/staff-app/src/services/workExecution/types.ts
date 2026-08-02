/** DTOs matching app/engines/execution/mobile_work_execution_service.py verbatim. */

export interface WorkExecutionJobDTO {
  job_id: string;
  job_reference: string;
  workflow_status: string;
  is_terminal: boolean;
}

export interface ApprovedScopeDTO {
  quote_id: string;
  version_number: number;
  approved_total: string;
  currency: string;
  approved_at: string | null;
  scope_locked: true;
}

export type WorkSessionState = "active" | "paused" | "finished";

export interface WorkSessionDTO {
  session_id: string;
  job_id: string;
  state: WorkSessionState;
  started_at: string | null;
  paused_at: string | null;
  pause_reason: string | null;
  accumulated_seconds: number;
  finished_at: string | null;
}

import { ChecklistItemDTO } from "../inspection/types";

/** Same wire shape as Phase K's inspection checklist items -- both come
 * from the identical ChecklistItem.to_dict() (checklist_catalog engine). */
export interface WorkChecklistDTO {
  items: ChecklistItemDTO[];
  required_total: number;
  required_completed: number;
  instance_id?: string;
}

export type PartsRequestStatus =
  | "requested" | "business_approved" | "customer_approval_pending"
  | "customer_approved" | "business_rejected" | "customer_rejected" | "installed" | "cancelled";

export interface PartsRequestDTO {
  parts_request_id: string;
  job_id: string;
  part_name: string;
  quantity: number;
  estimated_cost: number;
  reason: string;
  technician_note: string | null;
  customer_approval_required: boolean;
  status: PartsRequestStatus;
  rejection_reason: string | null;
  created_at: string | null;
}

export interface WorkReadinessDTO {
  can_finish_work: boolean;
  missing_checklist_item_ids: string[];
  pending_part_request_ids: string[];
  missing_evidence_categories: string[];
  blockers: string[];
}

export interface WorkExecutionDetailDTO {
  job: WorkExecutionJobDTO;
  approved_scope: ApprovedScopeDTO | null;
  work_session: WorkSessionDTO | null;
  checklist: WorkChecklistDTO;
  parts: PartsRequestDTO[];
  readiness: WorkReadinessDTO;
  allowed_actions: string[];
}
