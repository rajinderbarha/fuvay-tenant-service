/**
 * ServiceOS Staff App — API Client
 * PROVEN LEVEL 5:
 *   ALL API calls through this file — no inline fetch() in screens
 *   Staff token from AsyncStorage — never hardcoded
 *   Authorization injected once in apiFetch
 *   API_BASE from env variable
 */
import AsyncStorage from "@react-native-async-storage/async-storage";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export const STORAGE_KEYS = {
  token:    "serviceos_staff_token",
  staffId:  "serviceos_staff_id",
  tenantId: "serviceos_tenant_id",
  name:     "serviceos_staff_name",
  phone:    "serviceos_staff_phone",
} as const;

export class ServiceOSError extends Error {
  constructor(
    public code:        string,
    message:            string,
    public resolution?: string,
  ) { super(message); this.name = "ServiceOSError"; }
}

export async function getToken():    Promise<string | null> { return AsyncStorage.getItem(STORAGE_KEYS.token); }
export async function getStaffId():  Promise<string | null> { return AsyncStorage.getItem(STORAGE_KEYS.staffId); }
export async function getTenantId(): Promise<string | null> { return AsyncStorage.getItem(STORAGE_KEYS.tenantId); }
export async function clearSession():Promise<void>          { await AsyncStorage.multiRemove(Object.values(STORAGE_KEYS)); }

async function apiFetch<T>(path: string, options: RequestInit = {}, skipAuth = false): Promise<T> {
  const token   = await getToken();
  const headers: Record<string,string> = {
    "Content-Type":"application/json", "X-Request-Source":"staff-mobile-app",
    ...(options.headers as Record<string,string>),
  };
  if (token && !skipAuth) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let err: { error_code?:string; message?:string; resolution?:string } = {};
    try { err = await res.json(); } catch { err.error_code = "HTTP_ERROR"; err.message = `HTTP ${res.status}`; }
    throw new ServiceOSError(err.error_code ?? "API_ERROR", err.message ?? "Request failed.", err.resolution);
  }
  const json = await res.json();
  return json.data as T;
}

// ── Types ─────────────────────────────────────────────────────────────────────
export interface StaffUser {
  id:string; full_name:string; phone?:string; email?:string;
  specialisations:string[]; status:string; rating?:number;
  jobs_today?:number; performance_score?:number; tenant_id?:string;
  working_hours?: WorkingHours;
}
export interface WorkingHours { [day:string]: { start:string; end:string; is_working:boolean } }
export interface StaffPerformance {
  staff_id:string; composite_score:number; signals:Record<string,number>;
  job_count:number; avg_rating:number; dispute_rate:number; on_time_rate:number;
}
export interface Job {
  id:string; job_number:string; tenant_id:string;
  customer_name?:string; customer_phone?:string; customer_address?:string;
  customer_lat?:number;  customer_lng?:number;
  status:string; service_type:string; city:string;
  assigned_staff_id?:string;
  created_at:string; updated_at:string;
  sla_minutes?:number; minutes_in_status?:number;
  job_value?:number; notes?:string; closing_notes?:string;
  quoted_price?:number; customer_credit_applied?:number; payable_to_provider?:number;
  payment_collection_mode?:"customer_pays_provider_directly"; platform_payment_collected?:boolean;
  amount_collected?:number; payment_recorded?:boolean;
}
export interface JobListResponse     { jobs:Job[]; total:number; has_next:boolean; next_cursor?:string; }
export interface JobHistoryResponse  { history:{ status:string; changed_at:string; notes?:string }[]; }
export interface CommissionRecord    { id:string; job_id:string; job_number?:string; amount:number; rate:number; job_value:number; deducted_at:string; }
export interface EarningsSummary     { total_earned:number; this_month:number; pending_payout:number; jobs_completed:number; }
export interface ChatRoom            { room_id:string; job_id?:string; job_number?:string; participant_name:string; last_message?:string; last_message_at?:string; unread_count:number; }
export interface ChatMessage         { message_id:string; room_id:string; sender_id:string; sender_name?:string; content:string; message_type:string; sent_at:string; is_read:boolean; }
export interface ChatRoomListResponse{ rooms:ChatRoom[]; has_next:boolean; }
export interface MessageListResponse { messages:ChatMessage[]; has_next:boolean; }

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login:  (phone:string, password:string) =>
    apiFetch<{ access_token:string; refresh_token:string; staff:StaffUser }>(
      "/v1/auth/staff/login", { method:"POST", body:JSON.stringify({ phone, password }) }, true),
  me:     () => apiFetch<StaffUser>("/v1/auth/me"),
  logout: () => apiFetch<void>("/v1/auth/logout", { method:"POST" }),
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobsApi = {
  myJobs: async (params?: Partial<{ status:string; limit:string; cursor:string }>) => {
    const id = await getStaffId();
    const qs = new URLSearchParams({ ...(params ?? {}), ...(id ? { assigned_staff_id:id } : {}) }).toString();
    return apiFetch<JobListResponse>(`/v1/jobs?${qs}`);
  },
  get:          (id:string) => apiFetch<Job>(`/v1/jobs/${id}`),
  history:      (id:string) => apiFetch<JobHistoryResponse>(`/v1/jobs/${id}/history`),
  updateStatus: (id:string, status:string, notes?:string) =>
    apiFetch<Job>(`/v1/jobs/${id}/status`, { method:"PUT", body:JSON.stringify({ status, notes }) }),
  close: (id:string, notes:string) =>
    apiFetch<Job>(`/v1/jobs/${id}/close`, { method:"POST", body:JSON.stringify({ closing_notes:notes }) }),
  recordPayment: (id:string, amount:number, paymentMethod:string, notes?:string) =>
    apiFetch<Record<string, unknown>>(`/v1/jobs/${id}/record-payment`,
      { method:"POST", body:JSON.stringify({ amount, payment_method:paymentMethod, notes }) }),
};

// ── Staff ─────────────────────────────────────────────────────────────────────
export const staffApi = {
  get:            async () => { const id = await getStaffId(); return apiFetch<StaffUser>(`/v1/staff/${id}`); },
  performance:    async () => { const id = await getStaffId(); return apiFetch<StaffPerformance>(`/v1/ds/staff/${id}/performance`); },
  updateSchedule: async (wh:WorkingHours) => {
    const id = await getStaffId();
    return apiFetch<StaffUser>(`/v1/staff/${id}/schedule`, { method:"PUT", body:JSON.stringify({ working_hours:wh }) });
  },
};

// ── Geo ───────────────────────────────────────────────────────────────────────
export const geoApi = {
  updateLocation: async (lat:number, lng:number, accuracyM?:number) => {
    const id = await getStaffId();
    return apiFetch<void>(`/v1/geo/staff/${id}/location`,
      { method:"PUT", body:JSON.stringify({ lat, lng, accuracy_m:accuracyM }) });
  },
};

// ── Chat ──────────────────────────────────────────────────────────────────────
export const chatApi = {
  listRooms:   ()                       => apiFetch<ChatRoomListResponse>("/v1/chat/rooms?limit=30"),
  getMessages: (roomId:string, limit=50)=> apiFetch<MessageListResponse>(`/v1/chat/rooms/${roomId}/messages?limit=${limit}`),
  sendMessage: (roomId:string, content:string) =>
    apiFetch<ChatMessage>(`/v1/chat/rooms/${roomId}/messages`,
      { method:"POST", body:JSON.stringify({ content, message_type:"text" }) }),
  markRead:    (roomId:string) => apiFetch<void>(`/v1/chat/rooms/${roomId}/read`, { method:"POST" }),
};

// ── Earnings ──────────────────────────────────────────────────────────────────
export const earningsApi = {
  summary: async () => {
    const id = await getStaffId();
    return apiFetch<EarningsSummary>(`/v1/staff/${id}/earnings/summary`);
  },
  commissions: async (limit=20, cursor?:string) => {
    const id = await getStaffId();
    const qs = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<{ records:CommissionRecord[]; has_next:boolean }>(`/v1/staff/${id}/earnings${qs}`);
  },
};
