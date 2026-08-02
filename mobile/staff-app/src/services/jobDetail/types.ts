/** DTOs matching app/engines/execution/mobile_job_detail_service.py verbatim. */
export interface JobIdentityDTO {
  job_id: string;
  job_reference: string;
  tenant_id: string;
  assigned_technician_id: string | null;
  offering_id: string | null;
  service_label: string | null;
  job_type_id: string | null;
  job_type_label: string | null;
  workflow_status: string;
  scheduled_date: string | null;
  scheduled_time_window: string | null;
  safe_locality: string | null;
  is_terminal: boolean;
  booking_reference: string | null;
}

export interface CustomerContactDTO {
  customer_alias: string;
  call_relay_available: boolean;
  call_relay_reason: string | null;
  message_relay_available: boolean;
  message_relay_reason: string | null;
}

export type WorkflowStageState = "completed" | "current" | "upcoming" | "blocked" | "skipped";

export interface WorkflowStageDTO {
  key: string;
  label: string;
  state: WorkflowStageState;
  completed_at: string | null;
}

export interface NextActionDTO {
  key: string | null;
  label: string | null;
  allowed: boolean;
  route_key: string | null;
}

export interface BlockerDTO {
  code: string;
  message: string | null;
}

export interface RequirementRouteDTO {
  route_key: string;
}

export interface ChecklistRequirementDTO extends RequirementRouteDTO {
  required: boolean;
  total_items: number;
  completed_items: number;
  blocking_items: string[];
}

export interface PhotosRequirementDTO extends RequirementRouteDTO {
  required: boolean | null;
  uploaded_count: number;
}

export interface EstimateRequirementDTO extends RequirementRouteDTO {
  required: boolean;
  quote_id: string | null;
  version: number | null;
  state: string | null;
}

export interface PartsRequirementDTO extends RequirementRouteDTO {
  requested: boolean;
  approval_state: string | null;
}

export interface CompletionRequirementDTO extends RequirementRouteDTO {
  required: boolean;
  state: string;
}

export interface PaymentRequirementDTO extends RequirementRouteDTO {
  required: boolean;
  state: string | null;
}

export interface RequirementsDTO {
  checklist: ChecklistRequirementDTO;
  photos: PhotosRequirementDTO;
  estimate: EstimateRequirementDTO;
  parts: PartsRequirementDTO;
  completion_proof: CompletionRequirementDTO;
  payment_confirmation: PaymentRequirementDTO;
}

export interface VisitFeeDTO {
  required: boolean;
  amount: number | null;
  currency: string | null;
  disposition: "not_tracked" | "unavailable";
  policy_note: string | null;
}

export interface JobDetailsDTO {
  type_required: boolean | null;
  brand_required: boolean | null;
  type_brand_value: string | null;
  issue_summary: string | null;
}

export interface JobMobileDetailDTO {
  job: JobIdentityDTO;
  customer: CustomerContactDTO;
  workflow: { stages: WorkflowStageDTO[] };
  next_required_action: NextActionDTO;
  requirements: RequirementsDTO;
  visit_fee: VisitFeeDTO;
  job_details: JobDetailsDTO;
  allowed_actions: string[];
  blocker: BlockerDTO | null;
  versions: { entity_version: number | null; workflow_version: number | null };
  server_timestamp: string;
}

export interface TimelineEntryDTO {
  event_type: string;
  label: string;
  notes: string | null;
  created_at: string | null;
}

export interface JobTimelineDTO {
  job_id: string;
  entries: TimelineEntryDTO[];
  server_timestamp: string;
}
