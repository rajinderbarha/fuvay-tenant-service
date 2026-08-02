export interface DeliveryChannelDTO {
  supported: boolean;
  enabled: boolean;
  configurable: boolean;
  os_permission?: string;
  locked_reason?: string;
  frequency?: string;
}

export interface PreferenceEventDTO {
  event_group: string;
  code: string;
  label: string;
  description: string;
  push_enabled: boolean;
  configurable: boolean;
  mandatory: boolean;
}

export interface QuietHoursDTO {
  supported: boolean;
  enabled: boolean;
  start_local_time: string | null;
  end_local_time: string | null;
  timezone: string;
  critical_events_bypass: boolean;
}

export interface NotificationPreferencesDetailDTO {
  timezone: string;
  delivery: {
    push: DeliveryChannelDTO;
    in_app: DeliveryChannelDTO;
    email_summary: DeliveryChannelDTO;
  };
  events: PreferenceEventDTO[];
  quiet_hours: QuietHoursDTO;
  version: number;
}
