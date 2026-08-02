import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { ScheduleDetailDTO, TimeOffRequestDTO, BlockedTimeDTO } from "./types";

export function getSchedule(from: string, to: string, signal?: AbortSignal): Promise<ApiResult<ScheduleDetailDTO>> {
  return authenticatedRequest<ScheduleDetailDTO>(`/v1/staff/me/schedule`, { method: "GET", query: { from, to }, signal });
}

export function createBlockedTime(body: { date: string; start_time: string; end_time: string; reason?: string }): Promise<ApiResult<BlockedTimeDTO>> {
  return authenticatedRequest<BlockedTimeDTO>(`/v1/staff/me/schedule/blocked-time`, { method: "POST", body });
}

export function removeBlockedTime(blockId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/me/schedule/blocked-time/${blockId}`, { method: "DELETE" });
}

export function listTimeOff(signal?: AbortSignal): Promise<ApiResult<TimeOffRequestDTO[]>> {
  return authenticatedRequest<TimeOffRequestDTO[]>(`/v1/staff/me/time-off`, { method: "GET", signal });
}

export function submitTimeOff(body: {
  start_date: string; end_date: string; is_full_day: boolean;
  start_time?: string; end_time?: string; reason_category: string; note?: string;
}): Promise<ApiResult<TimeOffRequestDTO>> {
  return authenticatedRequest<TimeOffRequestDTO>(`/v1/staff/me/time-off`, { method: "POST", body });
}

export function cancelTimeOff(requestId: string): Promise<ApiResult<TimeOffRequestDTO>> {
  return authenticatedRequest<TimeOffRequestDTO>(`/v1/staff/me/time-off/${requestId}/cancel`, { method: "POST", unsafeToRetry: true });
}
