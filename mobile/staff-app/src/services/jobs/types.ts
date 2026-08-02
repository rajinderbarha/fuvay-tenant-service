/** DTOs matching app/engines/execution/mobile_jobs_service.py verbatim. */
export type JobsView = "today" | "active" | "upcoming" | "completed" | "archive";

export interface JobActionDTO {
  key: string | null;
  label: string | null;
  allowed: boolean;
}

export interface JobBlockerDTO {
  code: string;
  message: string | null;
}

export interface JobListItemDTO {
  job_id: string;
  job_reference: string;
  offering_id: string | null;
  service_label: string | null;
  job_type_id: string | null;
  job_type_label: string | null;
  workflow_status: string;
  scheduled_date: string | null;
  scheduled_time_window: string | null;
  safe_locality: string | null;
  customer_alias: string;
  next_required_action: JobActionDTO;
  allowed_actions: string[];
  blocker: JobBlockerDTO | null;
  payment_confirmation_state: string | null;
  entity_version: number | null;
  workflow_version: number | null;
  updated_at: string | null;
}

export type CountsByView = Record<JobsView, number>;

export interface MobileJobsDTO {
  results: JobListItemDTO[];
  next_cursor: string | null;
  has_more: boolean;
  counts_by_view: CountsByView;
  applied_filters: Record<string, unknown>;
  server_timestamp: string;
}

export interface JobsQueryParams {
  view: JobsView;
  search?: string;
  workflowStatus?: string;
  actionRequired?: boolean;
}
