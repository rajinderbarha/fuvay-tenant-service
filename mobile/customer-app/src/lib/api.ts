/**
 * ServiceOS Customer App — API Client
 * PROVEN LEVEL 5:
 *   ALL API calls through this file — no inline fetch() in screens
 *   Customer token from AsyncStorage — never hardcoded
 *   Authorization injected once in apiFetch
 *   API_BASE from EXPO_PUBLIC_API_URL env variable
 */
import AsyncStorage from "@react-native-async-storage/async-storage";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8001";

export const STORAGE_KEYS = {
  token:      "serviceos_customer_token",
  customerId: "serviceos_customer_id",
  name:       "serviceos_customer_name",
  phone:      "serviceos_customer_phone",
  email:      "serviceos_customer_email",
} as const;

export class ServiceOSError extends Error {
  constructor(public code:string, message:string, public resolution?:string) {
    super(message); this.name = "ServiceOSError";
  }
}

export async function getToken():      Promise<string|null> { return AsyncStorage.getItem(STORAGE_KEYS.token); }
export async function getCustomerId(): Promise<string|null> { return AsyncStorage.getItem(STORAGE_KEYS.customerId); }
export async function clearSession():  Promise<void>        { await AsyncStorage.multiRemove(Object.values(STORAGE_KEYS)); }

async function apiFetch<T>(path:string, options:RequestInit={}, skipAuth=false): Promise<T> {
  const token = await getToken();
  const headers: Record<string,string> = {
    "Content-Type":"application/json", "X-Request-Source":"customer-mobile-app",
    ...(options.headers as Record<string,string>),
  };
  if (token && !skipAuth) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let err: { error_code?:string; message?:string; resolution?:string } = {};
    try { err = await res.json(); } catch { err.message = `HTTP ${res.status}`; }
    throw new ServiceOSError(err.error_code ?? "API_ERROR", err.message ?? "Request failed.", err.resolution);
  }
  const json = await res.json();
  return json.data as T;
}

// ── Types ─────────────────────────────────────────────────────────────────────
export interface CustomerUser {
  id:string; name:string; phone?:string; email?:string;
  health_band?:string; health_score?:number; total_jobs?:number;
}
export interface ServiceCategory { id:string; name:string; icon:string; description?:string; verticals:string[] }
export interface PriceEstimate   { base_price:number; final_price:number; currency:string; breakdown:Record<string,number>; }
export interface Booking {
  id:string; booking_number:string; customer_name:string; customer_phone?:string;
  service_type:string; scheduled_at:string; status:string;
  price_snapshot?:{ final_price:number }; notes?:string;
  reschedule_count:number; created_at:string;
  tenant_name?:string; tenant_phone?:string; assigned_staff?:string;
  quoted_price?:number; credit_applied?:number; payable_amount?:number;
  job_status?:string;
}
export interface BookingListResponse { bookings:Booking[]; total:number; has_next:boolean; next_cursor?:string; }
export interface Job {
  id:string; job_number:string; status:string; service_type:string; city:string;
  customer_name?:string; assigned_staff?:string; assigned_staff_id?:string;
  created_at:string; updated_at:string;
  sla_minutes?:number; minutes_in_status?:number; job_value?:number;
}
export interface JobListResponse { jobs:Job[]; total:number; has_next:boolean; }
export interface StaffLocation   { staff_id:string; lat:number; lng:number; last_seen_at:string; accuracy_m?:number; }
export interface Review          { id:string; job_id:string; composite_score:number; comment?:string; status:string; created_at:string; }
export interface ChatRoom        { room_id:string; job_id?:string; job_number?:string; participant_name:string; last_message?:string; last_message_at?:string; unread_count:number; }
export interface ChatMessage     { message_id:string; room_id:string; sender_id:string; sender_name?:string; content:string; message_type:string; sent_at:string; is_read:boolean; }
export interface ChatRoomListResponse  { rooms:ChatRoom[]; has_next:boolean; }
export interface MessageListResponse   { messages:ChatMessage[]; has_next:boolean; }

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  requestOtp: (phone:string) =>
    apiFetch<{ session_id:string }>("/v1/auth/customer/otp-request",
      { method:"POST", body:JSON.stringify({ phone }) }, true),
  verifyOtp: (phone:string, otp:string, sessionId:string) =>
    apiFetch<{ access_token:string; customer:CustomerUser }>(
      "/v1/auth/customer/otp-verify",
      { method:"POST", body:JSON.stringify({ phone, otp, session_id:sessionId }) }, true),
  loginEmail: (email:string, password:string) =>
    apiFetch<{ access_token:string; customer:CustomerUser }>(
      "/v1/auth/customer/login",
      { method:"POST", body:JSON.stringify({ email, password }) }, true),
  me:     () => apiFetch<CustomerUser>("/v1/auth/me"),
  logout: () => apiFetch<void>("/v1/auth/logout", { method:"POST" }),
};

// ── Services ──────────────────────────────────────────────────────────────────
export const servicesApi = {
  categories: () => apiFetch<ServiceCategory[]>("/v1/services/categories"),
  estimate: (serviceType:string, city:string, date:string) =>
    apiFetch<PriceEstimate>(`/v1/pricing/estimate?service_type=${encodeURIComponent(serviceType)}&city=${encodeURIComponent(city)}&date=${encodeURIComponent(date)}`),
};

// ── Bookings ──────────────────────────────────────────────────────────────────
export const bookingsApi = {
  list: async (params?:Partial<{ status:string; limit:string; cursor:string }>) => {
    const cid = await getCustomerId();
    const qs  = new URLSearchParams({ ...(params??{}), ...(cid?{customer_id:cid}:{}) }).toString();
    return apiFetch<BookingListResponse>(`/v1/bookings?${qs}`);
  },
  get:    (id:string) => apiFetch<Booking>(`/v1/bookings/${id}`),
  create: (payload:{ service_type:string; scheduled_at:string; address:string; city:string; notes?:string; tenant_id?:string }) =>
    apiFetch<Booking>("/v1/bookings", { method:"POST", body:JSON.stringify(payload) }),
  cancel: (id:string, reason:string) =>
    apiFetch<Booking>(`/v1/bookings/${id}/cancel`,
      { method:"POST", body:JSON.stringify({ reason }) }),
  reschedule: (id:string, newSlot:string) =>
    apiFetch<Booking>(`/v1/bookings/${id}/reschedule`,
      { method:"PUT", body:JSON.stringify({ new_scheduled_at:newSlot }) }),
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobsApi = {
  myJobs: async (params?:Partial<{ status:string; limit:string }>) => {
    const cid = await getCustomerId();
    const qs  = new URLSearchParams({ ...(params??{}), ...(cid?{customer_id:cid}:{}) }).toString();
    return apiFetch<JobListResponse>(`/v1/jobs?${qs}`);
  },
  get:           (id:string) => apiFetch<Job>(`/v1/jobs/${id}`),
  trackStaff:    (staffId:string) => apiFetch<StaffLocation>(`/v1/geo/staff/${staffId}/location`),
};

// ── Reviews ───────────────────────────────────────────────────────────────────
export const reviewsApi = {
  submit: (jobId:string, score:number, comment:string) =>
    apiFetch<Review>("/v1/reviews", { method:"POST", body:JSON.stringify({ job_id:jobId, composite_score:score, comment }) }),
  myReviews: async () => {
    const cid = await getCustomerId();
    return apiFetch<{ reviews:Review[] }>(`/v1/reviews?customer_id=${cid}`);
  },
};

// ── Chat ──────────────────────────────────────────────────────────────────────
export const chatApi = {
  listRooms:   ()                         => apiFetch<ChatRoomListResponse>("/v1/chat/rooms?limit=20"),
  getMessages: (roomId:string, limit=50)  => apiFetch<MessageListResponse>(`/v1/chat/rooms/${roomId}/messages?limit=${limit}`),
  sendMessage: (roomId:string, content:string) =>
    apiFetch<ChatMessage>(`/v1/chat/rooms/${roomId}/messages`,
      { method:"POST", body:JSON.stringify({ content, message_type:"text" }) }),
  markRead:    (roomId:string) => apiFetch<void>(`/v1/chat/rooms/${roomId}/read`, { method:"POST" }),
};

// ── Profile ───────────────────────────────────────────────────────────────────
export const profileApi = {
  get: async () => {
    const cid = await getCustomerId();
    return apiFetch<CustomerUser>(`/v1/commerce/customers/${cid}`);
  },
  update: async (payload:Partial<Pick<CustomerUser,"name"|"phone"|"email">>) => {
    const cid = await getCustomerId();
    return apiFetch<CustomerUser>(`/v1/commerce/customers/${cid}`,
      { method:"PUT", body:JSON.stringify(payload) });
  },
};

// ── AI Chat (DeepSeek) ───────────────────────────────────────────────────────
export interface AIChatMessage { role: "user"|"assistant"; content: string; }
export interface AIChatResponse { reply: string; tools_called: string[]; model: string; }

export const aiChatApi = {
  /**
   * Send a message to the DeepSeek-powered AI assistant.
   * The AI has tools to fetch real booking/job/pricing data from ServiceOS backend.
   */
  chat: (message: string, history: AIChatMessage[] = []) =>
    apiFetch<AIChatResponse>("/v1/ai/chat", {
      method: "POST",
      body:   JSON.stringify({ message, history }),
    }),
};

// ── Notifications ─────────────────────────────────────────────────────────────
export interface AppNotification {
  id:string; title:string; body:string; type:string;
  is_read:boolean; created_at:string; action_url?:string;
  icon?:string;
}
export interface NotificationListResponse { notifications:AppNotification[]; unread_count:number; has_next:boolean; }

export const notificationsApi = {
  list: (limit=30) => apiFetch<NotificationListResponse>(`/v1/notifications?limit=${limit}`),
  markRead:    (id:string) => apiFetch<void>(`/v1/notifications/${id}/read`, { method:"POST" }),
  markAllRead: ()          => apiFetch<void>("/v1/notifications/read-all",   { method:"POST" }),
};

// ── Address book ──────────────────────────────────────────────────────────────
export interface SavedAddress {
  id:string; label:"home"|"work"|"other"|string;
  address_line:string; city:string; pincode?:string;
  lat?:number; lng?:number; is_default:boolean;
}
export const addressApi = {
  list:   async () => { const cid=await getCustomerId(); return apiFetch<{addresses:SavedAddress[]}>(`/v1/commerce/customers/${cid}/addresses`); },
  add:    async (a:Omit<SavedAddress,"id"|"is_default">) => { const cid=await getCustomerId(); return apiFetch<SavedAddress>(`/v1/commerce/customers/${cid}/addresses`,{ method:"POST", body:JSON.stringify(a) }); },
  update: async (id:string, a:Partial<SavedAddress>)    => { const cid=await getCustomerId(); return apiFetch<SavedAddress>(`/v1/commerce/customers/${cid}/addresses/${id}`,{ method:"PUT", body:JSON.stringify(a) }); },
  delete: async (id:string)                              => { const cid=await getCustomerId(); return apiFetch<void>(`/v1/commerce/customers/${cid}/addresses/${id}`,{ method:"DELETE" }); },
  setDefault: async (id:string)                          => { const cid=await getCustomerId(); return apiFetch<SavedAddress>(`/v1/commerce/customers/${cid}/addresses/${id}/default`,{ method:"POST" }); },
};

// ── Help & support ────────────────────────────────────────────────────────────
export interface FaqItem   { question:string; answer:string; category?:string; }
export interface Ticket    { id:string; subject:string; status:string; created_at:string; }
export const helpApi = {
  faqs:          ()             => apiFetch<{faqs:FaqItem[]}>("/v1/help/faqs"),
  submitTicket:  (subject:string, message:string, booking_id?:string) =>
    apiFetch<Ticket>("/v1/help/tickets", { method:"POST", body:JSON.stringify({ subject, message, booking_id }) }),
  myTickets:     async ()       => { const cid=await getCustomerId(); return apiFetch<{tickets:Ticket[]}>(`/v1/help/tickets?customer_id=${cid}`); },
};

// ── Payment methods ───────────────────────────────────────────────────────────
export interface PaymentMethod {
  id:string; type:"upi"|"card"|"netbanking"|"wallet";
  display_name:string; last4?:string; upi_id?:string;
  is_default:boolean; created_at:string;
}
export const paymentMethodsApi = {
  list:       async ()          => { const cid=await getCustomerId(); return apiFetch<{methods:PaymentMethod[]}>(`/v1/payments/customers/${cid}/methods`); },
  setDefault: async (id:string) => { const cid=await getCustomerId(); return apiFetch<PaymentMethod>(`/v1/payments/customers/${cid}/methods/${id}/default`,{ method:"POST" }); },
  remove:     async (id:string) => { const cid=await getCustomerId(); return apiFetch<void>(`/v1/payments/customers/${cid}/methods/${id}`,{ method:"DELETE" }); },
};

// ── Invoices ──────────────────────────────────────────────────────────────────
export interface Invoice {
  id:string; invoice_number:string; booking_id:string; job_id?:string;
  amount:number; tax:number; total:number; currency:string;
  status:"draft"|"issued"|"paid"|"overdue"; issued_at:string; due_at?:string;
  line_items:{ description:string; amount:number }[];
  pdf_url?:string;
}
export const invoiceApi = {
  get:  (id:string)       => apiFetch<Invoice>(`/v1/payments/invoices/${id}`),
  list: async (limit=20)  => { const cid=await getCustomerId(); return apiFetch<{invoices:Invoice[];has_next:boolean}>(`/v1/payments/invoices?customer_id=${cid}&limit=${limit}`); },
};

// ── Settings (customer preferences) ──────────────────────────────────────────
export interface CustomerSettings {
  notifications: { bookings:boolean; job_updates:boolean; promotions:boolean; sms:boolean; whatsapp:boolean; };
  language:      "en"|"hi"|"mr"|"ta"|"te";
  theme:         "system"|"light"|"dark";
}
export const settingsApi = {
  get:    async ()                         => { const cid=await getCustomerId(); return apiFetch<CustomerSettings>(`/v1/settings/${cid}/preferences`); },
  update: async (s:Partial<CustomerSettings>) => { const cid=await getCustomerId(); return apiFetch<CustomerSettings>(`/v1/settings/${cid}/preferences`,{ method:"PUT", body:JSON.stringify(s) }); },
};

// ── Quote (for Repair post-assessment quote approval) ─────────────────────────
export interface Quote {
  id:string; job_id:string; booking_id:string;
  findings:string; recommended_work:string;
  quoted_price:number; parts_cost:number; labour_cost:number; visit_fee:number;
  technician_notes?:string; expires_at:string; status:"pending"|"approved"|"rejected";
}
export const quoteApi = {
  get:     (jobId:string) => apiFetch<Quote>(`/v1/jobs/${jobId}/quote`),
  approve: (jobId:string) => apiFetch<{ status:"approved" }>(`/v1/jobs/${jobId}/quote/approve`, { method:"POST" }),
  reject:  (jobId:string, reason:string) =>
    apiFetch<{ status:"rejected" }>(`/v1/jobs/${jobId}/quote/reject`,
      { method:"POST", body:JSON.stringify({ reason }) }),
};

// ── AI Chat (DeepSeek via backend — key never exposed to app) ─────────────────
// Reuses the AIChatResponse shape declared above (aiChatApi) — identical fields.
export const aiApi = {
  chat: (message: string, history: { role: string; content: string }[] = []) =>
    apiFetch<AIChatResponse>("/v1/ai/chat", {
      method: "POST",
      body: JSON.stringify({ message, history }),
    }),
};

// ── AI Conversation Engine (Sprint 15 — session-based, persistent) ────────────
export interface AISession {
  id: string;
  session_key: string;
  customer_id: string | null;
  current_intent: string;
  workflow_status: "active" | "completed" | "abandoned" | "paused";
  turn_count: number;
  is_active: boolean;
}

export interface AISessionMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls_made: string[];
  latency_ms: number | null;
  created_at: string;
}

export interface AISendResponse {
  reply: string;
  tools_called: string[];
  intent: string;
  session: AISession;
}

export const aiConversationApi = {
  createSession: (categoryId?: string) =>
    apiFetch<AISession>("/v1/customer/ai-chat/sessions", {
      method: "POST",
      body: JSON.stringify({ category_id: categoryId }),
    }),

  sendMessage: (sessionId: string, message: string) =>
    apiFetch<AISendResponse>(`/v1/customer/ai-chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  getMessages: (sessionId: string) =>
    apiFetch<{ messages: AISessionMessage[]; total: number }>(
      `/v1/customer/ai-chat/sessions/${sessionId}/messages`
    ),

  closeSession: (sessionId: string) =>
    apiFetch<AISession>(`/v1/customer/ai-chat/sessions/${sessionId}/close`, {
      method: "POST",
    }),

  listSessions: () =>
    apiFetch<{ sessions: AISession[]; total: number }>("/v1/customer/ai-chat/sessions"),
};
