export type ScheduleItemType = "assigned_job" | "available_slot" | "blocked_time" | "approved_leave" | "pending_leave";

export interface ScheduleItemDTO {
  type: ScheduleItemType;
  job_id?: string;
  job_reference?: string;
  time_label?: string | null;
  workflow_status?: string;
  duration_minutes?: number;
  id?: string;
  start_time?: string | null;
  end_time?: string | null;
  reason?: string | null;
  reason_category?: string;
  source?: "staff" | "tenant" | "system";
  is_full_day?: boolean;
}

export interface ScheduleDayDTO {
  date: string;
  day_of_week: number;
  working_hours_label: string | null;
  assigned_job_count: number;
  open_slot_count: number;
  pending_leave_count: number;
  items: ScheduleItemDTO[];
}

export interface ScheduleDetailDTO {
  timezone: string;
  days: ScheduleDayDTO[];
  pending_time_off_count: number;
  last_synced_at: string;
}

export type TimeOffStatus = "pending" | "approved" | "rejected" | "cancelled";

export interface TimeOffRequestDTO {
  id: string;
  start_date: string;
  end_date: string;
  is_full_day: boolean;
  start_time: string | null;
  end_time: string | null;
  reason_category: string;
  note: string | null;
  status: TimeOffStatus;
  decision_note: string | null;
  created_at: string | null;
}

export interface BlockedTimeDTO {
  id: string;
  date: string;
  start_time: string;
  end_time: string;
  reason: string | null;
  source: "staff" | "tenant" | "system";
}
