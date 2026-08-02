/** DTOs matching app/engines/execution/mobile_inspection_service.py verbatim. */

export interface InspectionJobDTO {
  job_id: string;
  job_reference: string;
  service_label: string | null;
  workflow_status: string;
  is_terminal: boolean;
}

export interface CustomerReportDTO {
  issue_label: string | null;
  answers: unknown[];
  notes: string | null;
}

export type ChecklistItemType =
  | "CHECKBOX" | "YES_NO" | "SHORT_TEXT" | "LONG_TEXT" | "NUMBER" | "MEASUREMENT"
  | "SINGLE_SELECT" | "MULTI_SELECT" | "PHOTO" | "DOCUMENT" | "SIGNATURE";

export interface SelectOption {
  value: string;
  label: string;
}

export interface EvidenceFileDTO {
  file_id: string;
  uploader_id?: string;
  uploaded_at?: string;
  content_type?: string;
  size_bytes?: number;
}

export interface ChecklistResponseDTO {
  id: string;
  job_checklist_instance_id: string;
  checklist_item_id: string;
  response_value: Record<string, unknown> | null;
  evidence: EvidenceFileDTO[] | null;
  validation_result: { valid: boolean; errors?: string[] } | null;
}

export interface ChecklistItemDTO {
  id: string;
  checklist_section_id: string;
  item_type: ChecklistItemType;
  label: string;
  help_text: string | null;
  is_required: boolean;
  evidence_required: boolean;
  min_evidence_count: number;
  max_evidence_count: number;
  allowed_file_types: string[] | null;
  measurement_unit: string | null;
  select_options: SelectOption[] | null;
  validation_rules: Record<string, unknown> | null;
  display_order: number;
  condition_rules: Record<string, unknown> | null;
  failure_behavior: string | null;
  customer_visible: boolean;
  response: ChecklistResponseDTO | null;
}

export interface ChecklistSectionDTO {
  section_id: string;
  title: string;
  display_order: number;
  items: ChecklistItemDTO[];
}

export interface InspectionInstanceDTO {
  instance_id: string;
  state: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED" | "WAIVED";
  started_at: string | null;
  completed_at: string | null;
}

export interface InspectionReadinessDTO {
  total_required: number;
  completed_required: number;
  missing_item_ids: string[];
  missing_evidence_item_ids: string[];
  can_complete: boolean;
  blockers: string[];
}

export interface InspectionDetailDTO {
  job: InspectionJobDTO;
  customer_report: CustomerReportDTO;
  instance: InspectionInstanceDTO | null;
  sections: ChecklistSectionDTO[];
  readiness: InspectionReadinessDTO;
  allowed_actions: string[];
  definition_status: "AVAILABLE" | "UNAVAILABLE";
}
