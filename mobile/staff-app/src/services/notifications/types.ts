export type NotificationFilter = "all" | "unread" | "action_required";
export type NotificationCategory = "jobs" | "schedule" | "payments" | "account";
export type NotificationSeverity = "info" | "success" | "warning" | "critical";
export type DayGroup = "today" | "yesterday" | "earlier";

export interface NotificationDestinationDTO {
  type: "job" | "schedule" | "security";
  id: string | null;
  section: "estimate" | "payment" | null;
}

export interface NotificationItemDTO {
  id: string;
  event_type: string;
  category: NotificationCategory;
  severity: NotificationSeverity;
  title: string;
  body: string;
  is_read: boolean;
  action_required: boolean;
  created_at: string;
  destination: NotificationDestinationDTO | null;
  day_group: DayGroup;
}

export interface NotificationCountsDTO {
  all: number;
  unread: number;
  action_required: number;
}

export interface NotificationInboxDTO {
  items: NotificationItemDTO[];
  counts: NotificationCountsDTO;
  next_cursor: string | null;
}
