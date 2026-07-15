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
// MODULE-L5-36: this modeled a flat field_ops-style Job (customer_name/phone/
// address inline, job_value, closing_notes, payment fields) -- but field_ops'
// `jobs` table has zero rows platform-wide (confirmed via direct query).
// Every real job lives in `service_jobs` (home_service_assignment +
// execution engines), which has a narrower shape (no phone number or price
// exposed to staff at all -- ServiceJob itself has neither, and the safe
// booking view deliberately excludes pricing/contact details from staff
// visibility) and requires a separate assignment-timeline vs execution-
// lifecycle action set. Rewired the whole job surface to the real engines.
export interface Job {
  id:string; job_number:string; booking_id:string; tenant_id:string|null;
  customer_id:string|null; assigned_staff_id:string|null;
  scheduled_date:string|null; scheduled_time_window:string|null;
  city:string|null; zipcode:string|null;
  status:string; assignment_status:string; failure_reason:string|null;
  completion_data:Record<string, unknown>|null;
  created_at:string; updated_at:string;
}
export interface JobAssignment {
  id:string; job_id:string; booking_id:string; assigned_staff_member_id:string;
  assignment_status:string; assignment_type:string; rejection_reason:string|null;
  scheduled_date:string|null; scheduled_time_window:string|null;
}
export interface BookingSummary {
  id:string; booking_number:string; customer_name:string|null;
  city:string|null; zipcode:string|null;
  preferred_date:string|null; preferred_time_window:string|null;
  issue_summary:string|null;
}
export interface JobDetail { job:Job; assignment:JobAssignment|null; booking:BookingSummary|null; }
export interface JobListResponse { jobs:Job[]; count:number; }
export interface ExecutionEvent {
  id:string; job_id:string; event_type:string;
  old_status:string|null; new_status:string|null; notes:string|null; actor_role:string|null;
}
// MODULE-L5-34: this modeled a richer chat concept (room_id, participant_name,
// last_message preview, unread_count) than the real staff chat backend
// (app/engines/platform_notifications, built in MODULE-L5-19) provides --
// and called /v1/chat/rooms/*, which doesn't exist at all (the real chat
// engine only exposes /v1/chat/conversations*, and staff chat specifically
// lives at /v1/staff/chat/*). Threads carry record_type/record_id (what the
// conversation is about) and last_message_at, not a participant name or
// message preview; there is no per-thread unread count.
export interface ChatThread {
  id:string; thread_number:string; tenant_id:string|null; customer_id:string|null;
  record_type:string; record_id:string; status:string;
  last_message_at:string|null; created_at:string;
}
export interface ChatMessage {
  id:string; thread_id:string; sender_user_id:string|null; sender_type:string;
  message_type:string; message_text:string|null; visibility:string;
  delivery_status:string; created_at:string;
}
export interface ChatThreadListResponse { items:ChatThread[]; total:number; }
export interface ChatMessageListResponse{ items:ChatMessage[]; total:number; }
// MODULE-L5-37: in-app notifications. The staff app had no notification
// surface at all -- job-assignment/booking notifications raised server-side
// (MODULE-L5-25/etc.) were never fetched or shown on mobile, so a technician
// had no way to learn a job was assigned to them except by polling the Jobs
// tab. Real endpoints: /v1/staff/notifications*.
export interface StaffNotification {
  id:string; notification_type:string; title:string; body:string|null;
  action_url:string|null; action_label:string|null;
  source_record_type:string|null; source_record_id:string|null;
  severity:string; read_status:string; read_at:string|null; created_at:string;
}
export interface NotificationListResponse { items:StaffNotification[]; total:number; unread_count:number|null; }

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login:  (phone:string, password:string) =>
    apiFetch<{ access_token:string; refresh_token:string; staff:StaffUser }>(
      "/v1/auth/staff/login", { method:"POST", body:JSON.stringify({ phone, password }) }, true),
  me:     () => apiFetch<StaffUser>("/v1/auth/me"),
  logout: () => apiFetch<void>("/v1/auth/logout", { method:"POST" }),
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
// MODULE-L5-36: home_service_assignment's staff_router wraps every outcome
// in its own envelope rather than using real HTTP status codes: an error
// (caught ValueError) becomes {success:false, error:{code,message}}, and
// accept/reject's success case becomes {success:true, data:{...}} -- a
// second data layer on top of apiFetch's own `json.data` unwrap. get_thread's
// success case has neither key (the detail object itself). This unwraps all
// three shapes into one consistent value or a thrown ServiceOSError.
function _unwrapAssignmentResult<T>(raw: unknown): T {
  if (raw && typeof raw === "object" && "success" in raw) {
    const wrapped = raw as { success:boolean; error?:{ code:string; message:string }; data?:T };
    if (!wrapped.success) throw new ServiceOSError(wrapped.error!.code, wrapped.error!.message);
    return wrapped.data as T;
  }
  return raw as T;
}

export const jobsApi = {
  // MODULE-L5-36: rewired from the dead field_ops /v1/jobs* surface to the
  // real, live /v1/staff/service-jobs (home_service_assignment for list/
  // detail/accept/reject/assignment-timeline; execution for the post-accept
  // work lifecycle below).
  myJobs: () => apiFetch<JobListResponse>(`/v1/staff/service-jobs`),
  get: async (id:string) =>
    _unwrapAssignmentResult<JobDetail>(await apiFetch<unknown>(`/v1/staff/service-jobs/${id}`)),
  accept: async (id:string) =>
    _unwrapAssignmentResult<{ job_id:string; status:string }>(
      await apiFetch<unknown>(`/v1/staff/service-jobs/${id}/accept`, { method:"POST" })),
  reject: async (id:string, reason:string) =>
    _unwrapAssignmentResult<{ job_id:string; status:string }>(
      await apiFetch<unknown>(`/v1/staff/service-jobs/${id}/reject`, { method:"POST", body:JSON.stringify({ reason }) })),
  assignmentTimeline: (id:string) =>
    apiFetch<{ items:unknown[] }>(`/v1/staff/service-jobs/${id}/assignment-timeline`),

  // Execution lifecycle (app/engines/execution/home_service_router.py) --
  // real work-in-progress steps between "accepted" and "completed".
  onTheWay:          (id:string) => apiFetch<Job>(`/v1/staff/service-jobs/${id}/on-the-way`, { method:"POST" }),
  reachedSite:       (id:string) => apiFetch<Job>(`/v1/staff/service-jobs/${id}/reached-site`, { method:"POST" }),
  startInspection:   (id:string) => apiFetch<Job>(`/v1/staff/service-jobs/${id}/start-inspection`, { method:"POST" }),
  completeInspection:(id:string) => apiFetch<Job>(`/v1/staff/service-jobs/${id}/complete-inspection`, { method:"POST" }),
  startService:      (id:string) => apiFetch<Job>(`/v1/staff/service-jobs/${id}/start-service`, { method:"POST" }),
  workDone:          (id:string) => apiFetch<Job>(`/v1/staff/service-jobs/${id}/work-done`, { method:"POST" }),
  // Single validated completion action -- replaces the old separate
  // "close job" + "record payment" flow. work_summary and collected_amount
  // are both required by the service layer (WORK_SUMMARY_REQUIRED /
  // COLLECTED_AMOUNT_REQUIRED if missing).
  complete: (id:string, workSummary:string, collectedAmount:number) =>
    apiFetch<Job>(`/v1/staff/service-jobs/${id}/complete`, {
      method:"POST",
      body:JSON.stringify({
        work_summary:workSummary, collected_amount:collectedAmount,
        payment_mode:"customer_pays_provider_directly",
      }),
    }),
  timeline: (id:string) => apiFetch<{ items:ExecutionEvent[] }>(`/v1/staff/service-jobs/${id}/timeline`),
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
// MODULE-L5-34: rewired to the real staff chat surface built in
// MODULE-L5-19 (/v1/staff/chat/threads*) -- /v1/chat/rooms* never existed.
export const chatApi = {
  listThreads: (limit=30) => apiFetch<ChatThreadListResponse>(`/v1/staff/chat/threads?limit=${limit}`),
  getMessages: (threadId:string, limit=50) =>
    apiFetch<ChatMessageListResponse>(`/v1/staff/chat/threads/${threadId}/messages?limit=${limit}`),
  sendMessage: (threadId:string, messageText:string) =>
    apiFetch<ChatMessage>(`/v1/staff/chat/threads/${threadId}/messages`,
      { method:"POST", body:JSON.stringify({ message_text:messageText, message_type:"text" }) }),
  markRead:    (threadId:string) => apiFetch<{ messages_marked_read:number }>(`/v1/staff/chat/threads/${threadId}/read`, { method:"POST" }),
};

// ── Notifications (MODULE-L5-37) ────────────────────────────────────────────────
export const notificationsApi = {
  list:        (limit=30) => apiFetch<NotificationListResponse>(`/v1/staff/notifications?limit=${limit}`),
  unreadCount: () => apiFetch<{ unread_count:number }>(`/v1/staff/notifications/unread-count`),
  markRead:    (id:string) => apiFetch<StaffNotification>(`/v1/staff/notifications/${id}/read`, { method:"POST" }),
  markAllRead: () => apiFetch<{ marked_read:number }>(`/v1/staff/notifications/mark-all-read`, { method:"POST" }),
};

