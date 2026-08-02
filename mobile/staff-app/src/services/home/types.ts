/**
 * DTOs matching the real backend projection verbatim
 * (app/engines/execution/mobile_home_service.py / mobile_home_router.py).
 */
export type AvailabilityState = "available" | "busy" | "offline";

export interface TechnicianDTO {
  id: string;
  display_name: string;
  status: string;
}

export interface AvailabilityDTO {
  state: AvailabilityState;
  updated_at: string | null;
}

export interface ShiftSummaryDTO {
  jobs_today: number;
  completed: number;
  remaining: number;
}

export interface NextRequiredActionDTO {
  key: string | null;
  label: string | null;
  allowed: boolean;
}

export interface BlockerDTO {
  code: string;
  message: string | null;
}

export interface CurrentJobDTO {
  job_id: string;
  job_reference: string;
  offering_id: string | null;
  service_label: string | null;
  job_type_id: string | null;
  job_type_label: string | null;
  workflow_status: string;
  scheduled_date: string | null;
  scheduled_time_window: string | null;
  locality_label: string | null;
  customer_alias: string;
  next_required_action: NextRequiredActionDTO;
  blocker: BlockerDTO | null;
  entity_version: number | null;
  workflow_version: number | null;
}

export interface ScheduleRowDTO {
  job_id: string;
  job_reference: string;
  job_type_id: string | null;
  workflow_status: string;
  scheduled_time_window: string | null;
  locality_label: string | null;
}

export interface ActionRequiredItemDTO {
  key: string;
  label: string;
  job_id: string;
  job_reference: string;
}

export interface MobileHomeDTO {
  technician: TechnicianDTO;
  availability: AvailabilityDTO;
  shift_summary: ShiftSummaryDTO;
  current_job: CurrentJobDTO | null;
  today_schedule: ScheduleRowDTO[];
  action_required: ActionRequiredItemDTO[];
  unread_notification_count: number;
  server_timestamp: string;
}
