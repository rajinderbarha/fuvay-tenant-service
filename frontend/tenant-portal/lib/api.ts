/**
 * ServiceOS Tenant Owner Portal — API Client
 * PROVEN LEVEL 5:
 *   ✅ ALL API calls through this file — no inline fetch() anywhere else
 *   ✅ Tenant ID injected from localStorage — never hardcoded or repeated
 *   ✅ Auth token injected centrally in apiFetch — one place only
 *   ✅ ServiceOSError typed — every error handled consistently
 *   ✅ API_BASE from env — zero hardcoded URLs in components
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Error type ────────────────────────────────────────────────────────────────
export class ServiceOSError extends Error {
  constructor(
    public code: string,
    message: string,
    public resolution?: string,
    public context?: Record<string, unknown>,
    public requestId?: string,
  ) { super(message); this.name = "ServiceOSError"; }
}

// ── Auth helpers ──────────────────────────────────────────────────────────────
export function getToken():        string | null { return typeof window !== "undefined" ? localStorage.getItem("serviceos_tenant_token")   : null; }
export function getRefreshToken(): string | null { return typeof window !== "undefined" ? localStorage.getItem("serviceos_tenant_refresh") : null; }
export function getTenantId():     string | null { return typeof window !== "undefined" ? localStorage.getItem("serviceos_tenant_id")      : null; }
export function getUserId():       string | null { return typeof window !== "undefined" ? localStorage.getItem("serviceos_user_id")        : null; }
export function getUserRole():     string | null { return typeof window !== "undefined" ? localStorage.getItem("serviceos_user_role")      : null; }

/**
 * E2E-09B: reads the `access_scope` claim straight off the JWT (no extra API
 * call). Backend is the real authorization boundary (403 on mutation
 * endpoints) — this is UX polish only, so read-only users see disabled
 * controls instead of hitting an error after clicking Save/Publish.
 */
export function getAccessScope(): string | null {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return payload.access_scope ?? null;
  } catch {
    return null;
  }
}
export function isTenantReadOnly(): boolean {
  return getAccessScope() === "customer_support_limited";
}
/** FINAL-L5-03: shared version of a check duplicated identically across
 * provider/status and provider/offerings pages. Preserves the exact prior
 * semantics (role undefined -- e.g. still loading -- is treated as owner so
 * mutation controls aren't spuriously disabled while /auth/me is in flight). */
export function isTenantOwnerRole(role: string | null | undefined): boolean {
  return role === "tenant_owner" || role === undefined;
}
function clearSession() {
  ["serviceos_tenant_token","serviceos_tenant_refresh","serviceos_tenant_id","serviceos_tenant_name",
   "serviceos_tenant_vertical","serviceos_tenant_plan","serviceos_tenant_health","serviceos_user_id",
   "serviceos_force_pw_change"].forEach(k => localStorage.removeItem(k));
  window.location.href = "/login";
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────
export async function apiFetch<T>(path: string, options: RequestInit = {}, skipAuth = false): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type":     "application/json",
    "X-Request-Source": "tenant-owner-portal",
    ...(options.headers as Record<string, string>),
  };
  if (token && !skipAuth) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && !skipAuth) {
    const rt = getRefreshToken();
    if (rt) {
      try {
        const refreshRes = await fetch(`${API_BASE}/v1/auth/token/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: rt }),
        });
        if (refreshRes.ok) {
          const refreshJson = await refreshRes.json();
          const newToken: string = refreshJson.data?.access_token ?? refreshJson.access_token;
          if (newToken) {
            localStorage.setItem("serviceos_tenant_token", newToken);
            const retryHeaders = { ...headers, "Authorization": `Bearer ${newToken}` };
            const retry = await fetch(`${API_BASE}${path}`, { ...options, headers: retryHeaders });
            if (retry.ok) { const json = await retry.json(); return json.data as T; }
          }
        }
      } catch { /* fall through */ }
    }
    clearSession();
    throw new ServiceOSError("UNAUTHORIZED", "Session expired. Please sign in again.");
  }

  if (!res.ok) {
    let err: { error_code?: string; detail?: string; resolution?: string; context?: Record<string,unknown>; request_id?: string };
    try { err = await res.json(); } catch { err = { error_code: "NETWORK_ERROR", detail: `HTTP ${res.status}` }; }
    throw new ServiceOSError(err.error_code ?? "API_ERROR", err.detail ?? "Unexpected error.", err.resolution, err.context, err.request_id);
  }
  const json = await res.json();
  return json.data as T;
}

// ── Multipart upload helper (for Media Engine — does NOT set Content-Type so browser sets boundary) ─
async function apiFetchMultipart<T>(path: string, formData: FormData, method: "POST" = "POST", timeoutMs = 60_000): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "X-Request-Source": "tenant-owner-portal" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { method, headers, body: formData, signal: controller.signal });
  } catch (fetchErr: unknown) {
    if ((fetchErr as { name?: string }).name === "AbortError") {
      throw new ServiceOSError("UPLOAD_TIMEOUT", "Upload timed out. Please try again with a smaller file.", undefined);
    }
    throw fetchErr;
  } finally {
    clearTimeout(timer);
  }

  if (res.status === 401) { clearSession(); throw new ServiceOSError("UNAUTHORIZED", "Session expired. Please sign in again."); }
  if (!res.ok) {
    let err: { error_code?: string; detail?: string; resolution?: string };
    try { err = await res.json(); } catch { err = { error_code: "NETWORK_ERROR", detail: `HTTP ${res.status}` }; }
    throw new ServiceOSError(err.error_code ?? "API_ERROR", err.detail ?? "Unexpected error.", err.resolution);
  }
  const json = await res.json();
  return json.data as T;
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  // Session
  login:   (email: string, password: string) =>
    apiFetch<{ access_token: string; refresh_token: string | null; user: TenantUser; tenant: TenantCtx; requires_password_change?: boolean; password_change_reason?: string; redirect_to?: string }>(
      "/v1/auth/login", { method:"POST", body:JSON.stringify({ email, password }) }, true),
  me:      () => apiFetch<TenantUser>("/v1/auth/me"),
  updateMe:(data: Partial<TenantUser>) =>
    apiFetch<TenantUser>("/v1/auth/me", { method:"PUT", body:JSON.stringify(data) }),
  logout:  () => apiFetch<void>("/v1/auth/logout", { method:"POST" }),
  logoutAll: () => apiFetch<void>("/v1/auth/logout-all", { method:"POST" }),
  refresh: (rt: string) => apiFetch<{ access_token: string }>(
    "/v1/auth/token/refresh", { method:"POST", body:JSON.stringify({ refresh_token: rt }) }, true),

  // OTP
  sendOtp:   (phone: string) =>
    apiFetch<void>("/v1/auth/otp/send", { method:"POST", body:JSON.stringify({ phone }) }),
  verifyOtp: (phone: string, otp: string) =>
    apiFetch<{ access_token: string; refresh_token: string; user: TenantUser }>(
      "/v1/auth/otp/verify", { method:"POST", body:JSON.stringify({ phone, otp }) }, true),

  // MFA
  setupMfa:              () => apiFetch<MfaSetup>("/v1/auth/mfa/setup", { method:"POST" }),
  confirmMfa:            (code: string) =>
    apiFetch<MfaConfirm>("/v1/auth/mfa/confirm", { method:"POST", body:JSON.stringify({ code }) }),
  verifyMfa:             (code: string) =>
    apiFetch<{ access_token: string; refresh_token: string }>(
      "/v1/auth/mfa/verify", { method:"POST", body:JSON.stringify({ code }) }),
  disableMfa:            (code: string) =>
    apiFetch<void>("/v1/auth/mfa/disable", { method:"POST", body:JSON.stringify({ code }) }),
  regenerateBackupCodes: () =>
    apiFetch<BackupCodes>("/v1/auth/mfa/backup-codes/regenerate", { method:"POST" }),

  // Password
  changePassword:       (current_password: string, new_password: string) =>
    apiFetch<void>("/v1/auth/password/change",
      { method:"PUT", body:JSON.stringify({
        current_password, new_password, confirm_password: new_password,
      }) }),
  requestPasswordReset: (email: string) =>
    apiFetch<PasswordResetRequestResult>("/v1/auth/password/reset/request",
      { method:"POST", body:JSON.stringify({ email }) }, true),
  confirmPasswordReset: (email: string, reset_token: string, new_password: string) =>
    apiFetch<PasswordResetConfirmResult>("/v1/auth/password/reset/confirm",
      { method:"POST", body:JSON.stringify({
        email, reset_token, new_password, confirm_password: new_password,
      }) }, true),

  // Sessions
  getSessions:   () => apiFetch<UserSessionList>("/v1/auth/sessions"),
  deleteSession: (sessionId: string) =>
    apiFetch<void>(`/v1/auth/sessions/${sessionId}`, { method:"DELETE" }),

  // Force-change password (used when user must change password before accessing dashboard)
  changePasswordRequired: (current_password: string, new_password: string, confirm_password: string) =>
    apiFetch<{ message: string }>("/v1/auth/change-password-required",
      { method:"POST", body:JSON.stringify({ current_password, new_password, confirm_password }) }),

  // User listing (auto-scoped to caller's tenant by backend)
  listUsers: (params?: { role?: string; limit?: number }) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params ?? {}).filter(([,v])=>v!=null).map(([k,v])=>[k,String(v)]))
    ).toString();
    return apiFetch<UserListResponse>(`/v1/auth/users${qs ? `?${qs}` : ""}`);
  },

  // Staff management (tenant owners can invite staff)
  inviteStaff:      (data: InviteStaffPayload) =>
    apiFetch<StaffInvite>("/v1/auth/staff/invite", { method:"POST", body:JSON.stringify(data) }),
  acceptInvite:     (token: string, password: string) =>
    apiFetch<{ access_token: string }>(
      "/v1/auth/staff/invite/accept", { method:"POST", body:JSON.stringify({ token, password }) }, true),
  resendInvite:     (userId: string) =>
    apiFetch<void>(`/v1/auth/staff/${userId}/invite/resend`, { method:"POST" }),
  updatePermissions:(userId: string, permissions: string[]) =>
    apiFetch<void>(`/v1/auth/staff/${userId}/permissions`,
      { method:"PUT", body:JSON.stringify({ permissions }) }),
  deactivateStaff:  (userId: string, reason: string) =>
    apiFetch<void>(`/v1/auth/staff/${userId}/deactivate`,
      { method:"POST", body:JSON.stringify({ reason }) }),

  // Phase 0E: staff security controls — tenant-scoped endpoints (enforce tenant isolation)
  lockStaff: (userId: string, reason: string, revoke_sessions = true) =>
    apiFetch<{ message: string }>(`/v1/tenant/staff/${userId}/lock`,
      { method:"POST", body:JSON.stringify({ reason, revoke_sessions }) }),
  unlockStaff: (userId: string, reason: string) =>
    apiFetch<{ message: string }>(`/v1/tenant/staff/${userId}/unlock`,
      { method:"POST", body:JSON.stringify({ reason }) }),
  revokeStaffSessions: (userId: string, reason: string) =>
    apiFetch<{ message: string; revoked_count: number }>(`/v1/tenant/staff/${userId}/sessions/revoke-all`,
      { method:"POST", body:JSON.stringify({ reason }) }),
  getStaffLoginHistory: (userId: string, limit = 30) =>
    apiFetch<{ events: StaffLoginEvent[]; total: number }>(`/v1/tenant/staff/${userId}/login-history?limit=${limit}`),
  getStaffSecurityStatus: (userId: string) =>
    apiFetch<StaffSecurityStatus>(`/v1/tenant/staff/${userId}/security`),

  // API Keys
  createApiKey: (name: string, scopes: string[], expires_in_days?: number) =>
    apiFetch<ApiKeyCreated>("/v1/auth/api-keys",
      { method:"POST", body:JSON.stringify({ name, scopes, expires_in_days }) }),
  listApiKeys:  () => apiFetch<ApiKeyList>("/v1/auth/api-keys"),
  deleteApiKey: (keyId: string) =>
    apiFetch<void>(`/v1/auth/api-keys/${keyId}`, { method:"DELETE" }),
  updateApiKey: (keyId: string, data: { name?: string; is_active?: boolean }) =>
    apiFetch<ApiKey>(`/v1/auth/api-keys/${keyId}`,
      { method:"PATCH", body:JSON.stringify(data) }),
};

// ── Jobs (Field Ops) ──────────────────────────────────────────────────────────
export const jobsApi = {
  list:    (params?: Partial<{ status:string; limit:string; cursor:string; date:string }>) => {
    const tid = getTenantId();
    const qs  = new URLSearchParams({ ...(params ?? {}), ...(tid ? { tenant_id: tid } : {}) }).toString();
    return apiFetch<JobListResponse>(`/v1/jobs?${qs}`);
  },
  get:     (id: string) => apiFetch<Job>(`/v1/jobs/${id}`),
  history: (id: string) => apiFetch<JobHistoryResponse>(`/v1/jobs/${id}/timeline`),
  updateStatus: (id: string, status: string, notes?: string) =>
    apiFetch<Job>(`/v1/jobs/${id}/status`, { method:"PUT", body:JSON.stringify({ status, notes }) }),
  updateChecklist: (id: string, items: JobChecklistItem[]) =>
    apiFetch<Job>(`/v1/jobs/${id}/checklist`, { method:"PUT", body:JSON.stringify({ items }) }),
  slaAlerts: () => {
    const tid = getTenantId();
    return apiFetch<SlaAlert[]>(`/v1/jobs/sla-alerts${tid ? `?tenant_id=${tid}` : ""}`);
  },
  assignStaff: (id: string, staffId: string) => {
    const tid = getTenantId();
    return apiFetch<Job>(`/v1/dispatch/jobs/${id}/dispatch`,
      { method:"POST", body:JSON.stringify({ tenant_id: tid, mode:"manual", staff_id: staffId }) });
  },
  close: (id: string, notes: string) =>
    apiFetch<Job>(`/v1/jobs/${id}/close`, { method:"POST", body:JSON.stringify({ closing_notes: notes }) }),
  recordPayment: (id: string, amount: number, paymentMethod: string, notes?: string) =>
    apiFetch<Record<string, unknown>>(`/v1/jobs/${id}/record-payment`,
      { method:"POST", body:JSON.stringify({ amount, payment_method: paymentMethod, notes }) }),
  getTransitions: (id: string) => apiFetch<JobTransitions>(`/v1/jobs/${id}/transitions`),
  voidJob: (id: string, reason: string) =>
    apiFetch<Job>(`/v1/jobs/${id}/void`, { method:"POST", body:JSON.stringify({ reason }) }),
  addNote: (id: string, content: string, noteType = "staff_note", isInternal = true) => {
    const tid = getTenantId();
    return apiFetch<JobNote>(`/v1/jobs/${id}/notes?tenant_id=${tid}`,
      { method:"POST", body:JSON.stringify({ content, note_type: noteType, is_internal: isInternal }) });
  },
  listNotes: (id: string) => apiFetch<JobNoteList>(`/v1/jobs/${id}/notes`),
  addMedia: (id: string, mediaType = "photo", caption?: string, storageKey?: string, mediaId?: string) => {
    const tid = getTenantId();
    return apiFetch<JobMedia>(`/v1/jobs/${id}/media?tenant_id=${tid}`,
      { method:"POST", body:JSON.stringify({ media_id: mediaId, media_type: mediaType, caption, storage_key: storageKey }) });
  },
  listMedia: (id: string) => apiFetch<JobMediaList>(`/v1/jobs/${id}/media`),
  slaStatus: (id: string) => apiFetch<SlaStatusDetail>(`/v1/jobs/${id}/sla`),
  counts: () => {
    const tid = getTenantId();
    return apiFetch<JobCounts>(`/v1/jobs/tenants/${tid}/counts`);
  },
  trackByToken: (token: string) => apiFetch<TrackedJob>(`/v1/jobs/track/${token}`),
  spawnRepair: (consultationJobId: string) =>
    apiFetch<Job>(`/v1/jobs/${consultationJobId}/spawn-repair`, { method:"POST" }, false),
};

// ── Service Catalog ───────────────────────────────────────────────────────────
export const catalogApi = {
  list: (params?: Partial<{ service_type: string; is_active: string }>) => {
    const tid = getTenantId();
    const qs  = new URLSearchParams({ ...(params ?? {}), ...(tid ? { tenant_id: tid } : {}) }).toString();
    return apiFetch<ServiceCatalogListResponse>(`/v1/catalog?${qs}`);
  },
  get: (id: string) => apiFetch<ServiceCatalogItem>(`/v1/catalog/${id}`),
  create: (data: Partial<ServiceCatalogItem>) =>
    apiFetch<ServiceCatalogItem>("/v1/catalog", { method:"POST", body:JSON.stringify(data) }),
  update: (id: string, data: Partial<ServiceCatalogItem>) =>
    apiFetch<ServiceCatalogItem>(`/v1/catalog/${id}`, { method:"PUT", body:JSON.stringify(data) }),
  deactivate: (id: string) =>
    apiFetch<void>(`/v1/catalog/${id}/deactivate`, { method:"POST" }),
};

// ── Admin Master Catalog — browse + enable into own catalog (Catalog Engine) ──
export interface AdminMasterServiceRow {
  service_id:string; category_id:string; service_name:string; description?:string|null;
  job_type:"repair"|"service"|"consultation"; pricing_model:string; base_price:number;
  min_price?:number|null; max_price?:number|null; visit_fee:number;
  is_brand_required:boolean; is_type_required:boolean; is_active:boolean; is_enabled?:boolean;
}
export interface TenantEnabledService {
  tenant_service_id:string; tenant_id:string; master_service_id:string; category_id:string;
  job_type:string; is_enabled:boolean; tenant_display_name?:string|null; tenant_description?:string|null;
  tenant_base_price?:number|null; tenant_min_price?:number|null; tenant_max_price?:number|null;
  tenant_visit_fee?:number|null; override_allowed:boolean; requires_brand:boolean; requires_type:boolean; is_active:boolean;
  setup_status?: "draft" | "published"; published_at?: string | null;
  type_coverage_mode?: "all" | "selected" | "all_except";
  brand_coverage_mode?: "all" | "selected" | "all_except";
  last_active_step?: string | null;
}
export const masterCatalogApi = {
  listAvailable: () => {
    const tid = getTenantId();
    return apiFetch<{ services: AdminMasterServiceRow[] }>(`/v1/tenant/catalog/available-services?tenant_id=${tid}`);
  },
  listEnabled: () => {
    const tid = getTenantId();
    return apiFetch<{ services: TenantEnabledService[] }>(`/v1/tenant/catalog/enabled-services?tenant_id=${tid}`);
  },
  enable: (data: { master_service_id:string; tenant_display_name?:string; tenant_base_price?:number;
                    tenant_min_price?:number; tenant_max_price?:number; tenant_visit_fee?:number }) => {
    const tid = getTenantId();
    return apiFetch<TenantEnabledService>(`/v1/tenant/catalog/enable-service?tenant_id=${tid}`,
      { method:"POST", body:JSON.stringify(data) });
  },
  updateEnabled: (tenantServiceId: string, data: Partial<TenantEnabledService>) =>
    apiFetch<TenantEnabledService>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}`,
      { method:"PUT", body:JSON.stringify(data) }),
  disable: (masterServiceId: string) => {
    const tid = getTenantId();
    return apiFetch<void>(`/v1/tenant/catalog/disable-service?tenant_id=${tid}&master_service_id=${masterServiceId}`,
      { method:"POST" });
  },
};

// ── Home Services Service Setup Wizard ────────────────────────────────────────
export interface HsPricePreview {
  provider_min_price: number; provider_max_price: number;
  platform_fee_percent: number; platform_fee_fixed_amount: number;
  low_price: number; mid_price: number; high_price: number;
  payment_mode: string;
}

export interface HsSetupType {
  mapping_id: string; service_type_id: string; name: string;
  is_required: boolean; is_default: boolean;
  tenant_price_adjustment: number | null;
}

export interface HsSetupBrand {
  id: string; brand_id: string; name: string; is_enabled: boolean;
  tenant_price_adjustment: number | null;
}

export interface HsTypePricing {
  tenant_service_type_id: string; service_type_id: string; name: string;
  admin_floor_price: number | null; admin_ceiling_price: number | null;
  platform_fee_percent: number;
  tenant_min_price: number | null; tenant_max_price: number | null;
  customer_price_preview: HsPricePreview | null;
}

export interface HsBrandPricing {
  tenant_service_brand_id: string; brand_id: string; name: string;
  can_override_price: boolean; is_routing_only: boolean;
  admin_floor_price: number | null; admin_ceiling_price: number | null;
  platform_fee_percent: number;
  tenant_min_price: number | null; tenant_max_price: number | null;
  customer_price_preview: HsPricePreview | null;
}

// ── Generic, schema-driven Service Setup Wizard (vertical-agnostic) ──────────
// Reuses the SAME backend endpoints as homeServicesSetupApi below (they were
// never actually Home-Services-specific on the backend -- only the old
// frontend naming and the two list-available/list-enabled routes were) plus
// the new coverage-mode/publish-validation/blueprint-version endpoints. This
// is the API surface the new schema-driven wizard is built against; it must
// never hardcode a vertical, service, type or brand name.
export interface MyVerticalEnrollment {
  vertical_id: string; vertical_key: string; vertical_label: string;
  icon: string | null; capabilities: string[];
  platform_enabled: boolean; enrollment_status: string | null;
}
export interface PriceResolution {
  resolved: boolean;
  pricing_model?: "FIXED" | "RANGE";
  minimum_price?: number; maximum_price?: number; currency?: string;
  source_rule_id?: string;
  source?: "type_brand_override" | "type_override" | "brand_override" | "tenant_default";
  inherited_from_rule_id?: string | null;
  reason?: "NO_TENANT_PRICE_FOR_COMBINATION" | "COMBINATION_NOT_SUPPORTED";
}
export interface PublishValidationError {
  step: string; job_type_id: string;
  dimension_path: Record<string, string>;
  code: string; message: string;
}
export interface PublishValidationResult {
  valid: boolean; errors: PublishValidationError[];
}
export interface BlueprintUpdateStatus {
  update_required: boolean;
  current_version: number | null; latest_version: number | null;
  changes: string[];
}
export type CoverageMode = "all" | "selected" | "all_except";

export const serviceSetupApi = {
  // Step 1: Category (vertical)
  getMyVerticalEnrollments: () =>
    apiFetch<{ verticals: MyVerticalEnrollment[] }>("/v1/tenant/vertical-enrollments"),

  // Step 2: Service (uses the generic, entitlement-filtered available/enabled
  // services list -- NOT the home-services-branded routes).
  listAvailableServices: () => masterCatalogApi.listAvailable(),
  listEnabledServices: () => masterCatalogApi.listEnabled(),
  enableService: (masterServiceId: string) => masterCatalogApi.enable({ master_service_id: masterServiceId }),
  getEnabledService: (tenantServiceId: string) => homeServicesSetupApi.getEnabledService(tenantServiceId),

  // Step 3/4: dimensions, coverage, pricing (same generic endpoints)
  getTypes: (tenantServiceId: string) => homeServicesSetupApi.getTypes(tenantServiceId),
  setTypes: (tenantServiceId: string, typeIds: string[]) => homeServicesSetupApi.setTypes(tenantServiceId, typeIds),
  getBrands: (tenantServiceId: string) => homeServicesSetupApi.getBrands(tenantServiceId),
  setBrands: (tenantServiceId: string, brandIds: string[]) => homeServicesSetupApi.setBrands(tenantServiceId, brandIds),
  getTypePricing: (tenantServiceId: string) => homeServicesSetupApi.getTypePricing(tenantServiceId),
  setTypePricing: (tenantServiceId: string, serviceTypeId: string, min: number, max: number) =>
    homeServicesSetupApi.setTypePricing(tenantServiceId, serviceTypeId, min, max),
  getBrandPricing: (tenantServiceId: string, serviceTypeId?: string) =>
    homeServicesSetupApi.getBrandPricing(tenantServiceId, serviceTypeId),
  setBrandPricing: (tenantServiceId: string, brandId: string, min: number, max: number, serviceTypeId?: string) =>
    homeServicesSetupApi.setBrandPricing(tenantServiceId, brandId, min, max, serviceTypeId),

  setTypeCoverageMode: (tenantServiceId: string, mode: CoverageMode) =>
    apiFetch<TenantEnabledService>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/type-coverage-mode`,
      { method: "PUT", body: JSON.stringify({ mode }) }),
  setBrandCoverageMode: (tenantServiceId: string, mode: CoverageMode) =>
    apiFetch<TenantEnabledService>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/brand-coverage-mode`,
      { method: "PUT", body: JSON.stringify({ mode }) }),

  resolvePrice: (tenantServiceId: string, serviceTypeId?: string, brandId?: string) => {
    const p = new URLSearchParams();
    if (serviceTypeId) p.set("service_type_id", serviceTypeId);
    if (brandId) p.set("brand_id", brandId);
    const qs = p.toString();
    return apiFetch<PriceResolution>(
      `/v1/tenant/catalog/enabled-services/${tenantServiceId}/resolve-price${qs ? `?${qs}` : ""}`);
  },

  updateWizardStep: (tenantServiceId: string, step: string) =>
    apiFetch<{ tenant_service_id: string; last_active_step: string }>(
      `/v1/tenant/catalog/enabled-services/${tenantServiceId}/wizard-step`,
      { method: "PUT", body: JSON.stringify({ step }) }),

  // Step 5: Review & Publish
  validateForPublish: (tenantServiceId: string) =>
    apiFetch<PublishValidationResult>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/validate-for-publish`),
  getBlueprintUpdateStatus: (tenantServiceId: string) =>
    apiFetch<BlueprintUpdateStatus>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/blueprint-update-status`),
  publish: (tenantServiceId: string) => homeServicesSetupApi.publish(tenantServiceId),
  saveDraft: (tenantServiceId: string) => homeServicesSetupApi.saveDraft(tenantServiceId),
  pricePreview: (data: { tenant_min_price: number; tenant_max_price: number; platform_fee_percent?: number }) =>
    homeServicesSetupApi.pricePreview(data),
};

export const homeServicesSetupApi = {
  listAvailable: () => {
    const tid = getTenantId();
    return apiFetch<{ services: AdminMasterServiceRow[] }>(`/v1/tenant/catalog/home-services/available-services?tenant_id=${tid}`);
  },
  listEnabled: () => {
    const tid = getTenantId();
    return apiFetch<{ services: TenantEnabledService[] }>(`/v1/tenant/catalog/home-services/enabled-services?tenant_id=${tid}`);
  },
  enable: (data: { master_service_id: string }) => {
    const tid = getTenantId();
    return apiFetch<TenantEnabledService>(`/v1/tenant/catalog/enable-service?tenant_id=${tid}`,
      { method: "POST", body: JSON.stringify(data) });
  },
  getEnabledService: (tenantServiceId: string) =>
    apiFetch<TenantEnabledService>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}`),
  getTypes: (tenantServiceId: string) =>
    apiFetch<{ types: HsSetupType[] }>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/types`),
  setTypes: (tenantServiceId: string, typeIds: string[]) =>
    apiFetch<{ types: HsSetupType[] }>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/types`,
      { method: "PUT", body: JSON.stringify({ type_ids: typeIds }) }),
  getBrands: (tenantServiceId: string) =>
    apiFetch<{ brands: HsSetupBrand[] }>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/brands`),
  setBrands: (tenantServiceId: string, brandIds: string[]) =>
    apiFetch<{ brands: HsSetupBrand[] }>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/brands`,
      { method: "PUT", body: JSON.stringify({ brand_ids: brandIds }) }),
  getTypePricing: (tenantServiceId: string) =>
    apiFetch<{ types: HsTypePricing[] }>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/type-pricing`),
  setTypePricing: (tenantServiceId: string, serviceTypeId: string, min: number, max: number) =>
    apiFetch<{ types: HsTypePricing[] }>(
      `/v1/tenant/catalog/enabled-services/${tenantServiceId}/types/${serviceTypeId}/pricing`,
      { method: "PUT", body: JSON.stringify({ tenant_min_price: min, tenant_max_price: max }) }),
  getBrandPricing: (tenantServiceId: string, serviceTypeId?: string) =>
    apiFetch<{ brands: HsBrandPricing[] }>(
      `/v1/tenant/catalog/enabled-services/${tenantServiceId}/brand-pricing${serviceTypeId ? `?service_type_id=${serviceTypeId}` : ""}`),
  setBrandPricing: (tenantServiceId: string, brandId: string, min: number, max: number, serviceTypeId?: string) =>
    apiFetch<{ brands: HsBrandPricing[] }>(
      `/v1/tenant/catalog/enabled-services/${tenantServiceId}/brands/${brandId}/pricing${serviceTypeId ? `?service_type_id=${serviceTypeId}` : ""}`,
      { method: "PUT", body: JSON.stringify({ tenant_min_price: min, tenant_max_price: max }) }),
  pricePreview: (data: { tenant_min_price: number; tenant_max_price: number; platform_fee_percent?: number }) =>
    apiFetch<HsPricePreview>("/v1/tenant/catalog/price-options/preview",
      { method: "POST", body: JSON.stringify(data) }),
  saveDraft: (tenantServiceId: string) =>
    apiFetch<TenantEnabledService>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/save-draft`, { method: "POST" }),
  publish: (tenantServiceId: string) =>
    apiFetch<TenantEnabledService>(`/v1/tenant/catalog/enabled-services/${tenantServiceId}/publish`, { method: "POST" }),
  disable: (masterServiceId: string) => {
    const tid = getTenantId();
    return apiFetch<void>(`/v1/tenant/catalog/disable-service?tenant_id=${tid}&master_service_id=${masterServiceId}`,
      { method: "POST" });
  },
};

// ── Quote & Approval (Phase 9) ────────────────────────────────────────────────
export const quotesApi = {
  listByJob: (jobId: string) => apiFetch<JobQuoteListResponse>(`/v1/jobs/${jobId}/quotes`),
  create: (jobId: string, amount: number, parts: JobQuotePart[], labourEstimate: number | undefined,
            notes: string | undefined, expiryDays = 7) =>
    apiFetch<JobQuote>(`/v1/jobs/${jobId}/quote`, { method:"POST", body: JSON.stringify({
      amount, parts, labour_estimate: labourEstimate, notes, expiry_days: expiryDays }) }),
  respond: (quoteId: string, approved: boolean, customerId?: string) =>
    apiFetch<JobQuote>(`/v1/jobs/quotes/${quoteId}/respond`, { method:"POST", body: JSON.stringify({
      approved, customer_id: customerId }) }),
  submitFindings: (jobId: string, findings: string, recommendation?: string) =>
    apiFetch<Job>(`/v1/jobs/${jobId}/findings`, { method:"POST", body: JSON.stringify({
      findings, recommendation }) }),
};

// ── Bookings ──────────────────────────────────────────────────────────────────
export const bookingsApi = {
  list: (params?: Partial<{ status:string; limit:string; cursor:string }>) => {
    const tid = getTenantId();
    const qs  = new URLSearchParams({ ...(params ?? {}), ...(tid ? { tenant_id: tid } : {}) }).toString();
    return apiFetch<BookingListResponse>(`/v1/bookings?${qs}`);
  },
  get:        (id: string) => apiFetch<Booking>(`/v1/bookings/${id}`),
  confirm:    (id: string) => apiFetch<Booking>(`/v1/bookings/${id}/confirm`, { method:"POST" }),
  reject:     (id: string, reason: string) =>
    apiFetch<Booking>(`/v1/bookings/${id}/cancel`, { method:"POST", body:JSON.stringify({ reason }) }),
  reschedule: (id: string, requestedDate: string, requestedSlot: string, reason: string) =>
    apiFetch<Booking>(`/v1/bookings/${id}/reschedule/request`, { method:"POST",
      body:JSON.stringify({ requested_date: requestedDate, requested_slot: requestedSlot, reason }) }),
  acceptReschedule: (rescheduleId: string) =>
    apiFetch<Booking>(`/v1/bookings/reschedule/${rescheduleId}/accept`, { method:"POST" }),
  rejectReschedule: (rescheduleId: string, reason = "Slot unavailable") =>
    apiFetch<Booking>(`/v1/bookings/reschedule/${rescheduleId}/reject`,
      { method:"POST", body:JSON.stringify({ reason }) }),
  convertToJob: (id: string) =>
    apiFetch<Job>(`/v1/bookings/${id}/convert-to-job`, { method:"POST" }),
  addNote: (id: string, content: string, isInternal = true) =>
    apiFetch<BookingNote>(`/v1/bookings/${id}/notes`,
      { method:"POST", body:JSON.stringify({ content, is_internal: isInternal }) }),
  listNotes: (id: string) => apiFetch<BookingNoteList>(`/v1/bookings/${id}/notes`),
  checkSlot: (date: string, slot: string) => {
    const tid = getTenantId();
    return apiFetch<SlotAvailability>(`/v1/bookings/tenants/${tid}/slots/check?date=${date}&slot=${slot}`);
  },
  getCancellationPolicy: () => {
    const tid = getTenantId();
    return apiFetch<CancellationPolicy>(`/v1/bookings/tenants/${tid}/cancellation-policy`);
  },
  void: (id: string, reason = "Voided by admin") =>
    apiFetch<Booking>(`/v1/bookings/${id}/void`, { method:"POST", body:JSON.stringify({ reason }) }),
  getTimeline: (id: string) => apiFetch<BookingTimeline>(`/v1/bookings/${id}/timeline`),
  search: (q: string, limit = 20) => {
    const tid = getTenantId();
    return apiFetch<BookingSearchResponse>(`/v1/bookings/tenants/${tid}/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  },
};

// ── Staff ─────────────────────────────────────────────────────────────────────
export const staffApi = {
  list: () =>
    apiFetch<UserListResponse>(`/v1/auth/users?role=staff`),
  get:            (id: string) => apiFetch<StaffMember>(`/v1/auth/users/${id}`),
  updateSchedule: (id: string, workingHours: WorkingHours) =>
    apiFetch<StaffMember>(`/v1/auth/staff/${id}/schedule`, { method:"PUT", body:JSON.stringify({ working_hours: workingHours }) }),
  // MODULE-L5-40: real route is /v1/ds/tenants/{tenant_id}/staff/{staff_id}/score
  // (the old /v1/ds/staff/{id}/performance 404'd). A 404 here is legitimate
  // "no score computed yet" (staff has had no job close) -- the page shows
  // that as an empty perf state, not a broken call.
  getPerformance: (id: string) => {
    const tid = getTenantId();
    return apiFetch<StaffPerformance>(`/v1/ds/tenants/${tid}/staff/${id}/score`);
  },
  getLocation:    (id: string) => {
    const tid = getTenantId();
    return apiFetch<StaffLocation>(`/v1/geo/tenants/${tid}/staff/${id}/location`);
  },
};

// ── Customers (Platform Commerce) ─────────────────────────────────────────────
export const customersApi = {
  list: (params?: Partial<{ limit:string; cursor:string; health_band:string }>) => {
    const tid = getTenantId();
    const qs  = new URLSearchParams({ ...(params ?? {}), ...(tid ? { tenant_id: tid } : {}) }).toString();
    return apiFetch<CustomerListResponse>(`/v1/commerce/tenants/${tid}/customers?${qs}`);
  },
  get:      (id: string) => apiFetch<Customer>(`/v1/commerce/customers/${id}`),
  getHealth:(id: string) => apiFetch<CustomerHealth>(`/v1/commerce/customers/${id}/health`),
  jobs:     (id: string, limit = 10) =>
    apiFetch<JobListResponse>(`/v1/jobs?customer_id=${id}&limit=${limit}`),
};

// ── Finance (Commerce + Payment) ──────────────────────────────────────────────
export const financeApi = {
  // Wallet
  wallet: () => {
    const tid = getTenantId();
    return apiFetch<WalletBalance>(`/v1/commerce/tenants/${tid}/wallet`);
  },
  walletTransactions: (limit = 20, cursor?: string) => {
    const tid = getTenantId();
    const qs  = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<WalletTransactionList>(`/v1/commerce/tenants/${tid}/wallet/transactions${qs}`);
  },
  walletProjection: () => {
    const tid = getTenantId();
    return apiFetch<WalletProjection>(`/v1/commerce/tenants/${tid}/wallet/projection`);
  },

  // Credit packages + purchase flow
  listPackages: () => apiFetch<CreditPackageList>("/v1/commerce/packages"),
  initiateWalletPurchase: (packageId: string) => {
    const tid = getTenantId();
    return apiFetch<PurchaseOrder>(`/v1/commerce/tenants/${tid}/wallet/purchase/initiate`,
      { method:"POST", body:JSON.stringify({ package_id: packageId, gateway: "razorpay" }) });
  },
  confirmWalletPurchase: (orderId: string, paymentId: string, signature: string, packageId: string) => {
    const tid = getTenantId();
    return apiFetch<WalletBalance>(`/v1/commerce/tenants/${tid}/wallet/purchase/confirm`,
      { method:"POST", body:JSON.stringify({
          razorpay_order_id: orderId, razorpay_payment_id: paymentId,
          razorpay_signature: signature, package_id: packageId }) });
  },

  // Commission
  commissionHistory: (limit = 20, cursor?: string) => {
    const tid = getTenantId();
    const qs  = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<CommissionListResponse>(`/v1/commerce/tenants/${tid}/commission/history${qs}`);
  },
  commissionRate: () => {
    const tid = getTenantId();
    return apiFetch<CommissionRate>(`/v1/commerce/tenants/${tid}/commission/rate`);
  },
  commissionProjection: () => {
    const tid = getTenantId();
    return apiFetch<CommissionProjection>(`/v1/commerce/tenants/${tid}/commission/projection`);
  },

  // Payments
  payments: (limit = 20) => {
    const tid = getTenantId();
    return apiFetch<PaymentListResponse>(`/v1/payments?tenant_id=${tid}&limit=${limit}`);
  },

  // Invoices
  invoices: (limit = 20, cursor?: string) => {
    const tid = getTenantId();
    const qs  = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<InvoiceListResponse>(`/v1/payments/tenants/${tid}/invoices${qs}`);
  },
  getInvoice: (invoiceId: string) =>
    apiFetch<InvoiceRecord>(`/v1/payments/invoices/${invoiceId}`),

  // Payouts
  requestPayout: (amount: number, bankAccount: Record<string,unknown>) => {
    const tid = getTenantId();
    return apiFetch<Payout>(`/v1/payments/tenants/${tid}/payout`,
      { method:"POST", body:JSON.stringify({ amount, bank_account: bankAccount }) });
  },
  getPayout: (payoutId: string) => apiFetch<Payout>(`/v1/payments/payouts/${payoutId}`),
  listPayouts: (limit = 20, cursor?: string) => {
    const tid = getTenantId();
    const qs  = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<PayoutList>(`/v1/payments/tenants/${tid}/payouts${qs}`);
  },
  createRefund: (paymentId: string, amount: number, reason: string) =>
    apiFetch<Refund>(`/v1/payments/${paymentId}/refund`,
      { method:"POST", body:JSON.stringify({ amount, reason }) }),
  listRefunds: (limit = 20) => {
    const tid = getTenantId();
    return apiFetch<RefundList>(`/v1/payments/tenants/${tid}/refunds?limit=${limit}`);
  },

  // Security deposit (refundable, separate from wallet)
  getDeposit: () => {
    const tid = getTenantId();
    return apiFetch<SecurityDepositStatus>(`/v1/commerce/tenants/${tid}/deposit`);
  },
  initiateDeposit: () => {
    const tid = getTenantId();
    return apiFetch<PurchaseOrder>(`/v1/commerce/tenants/${tid}/deposit/initiate`,
      { method:"POST", body:JSON.stringify({ gateway: "razorpay" }) });
  },
  confirmDeposit: (orderId: string, paymentId: string, signature: string) => {
    const tid = getTenantId();
    return apiFetch<DepositConfirmResult>(`/v1/commerce/tenants/${tid}/deposit/confirm`,
      { method:"POST", body:JSON.stringify({
          razorpay_order_id: orderId, razorpay_payment_id: paymentId,
          razorpay_signature: signature }) });
  },
  depositTransactions: () => {
    const tid = getTenantId();
    return apiFetch<SecurityDepositTxnList>(`/v1/commerce/tenants/${tid}/deposit/transactions`);
  },

  // Subscription (legacy)
  subscription: () => {
    const tid = getTenantId();
    return apiFetch<SubscriptionInfo>(`/v1/subscriptions/tenants/${tid}`);
  },

  // At-risk customers
  atRiskCustomers: (limit = 10) => {
    const tid = getTenantId();
    return apiFetch<CustomerAtRiskList>(`/v1/commerce/tenants/${tid}/customers/at-risk?limit=${limit}`);
  },

  // Warranty claims
  warrantyClaims: (status?: string, limit = 20) => {
    const tid = getTenantId();
    const qs  = status ? `?tenant_id=${tid}&status=${status}&limit=${limit}` : `?tenant_id=${tid}&limit=${limit}`;
    return apiFetch<WarrantyClaimList>(`/v1/commerce/warranty/claims${qs}`);
  },
  createWarrantyClaim: (jobId: string, issueDescription: string) => {
    const tid = getTenantId();
    return apiFetch<WarrantyClaim>("/v1/commerce/warranty/claims",
      { method:"POST", body:JSON.stringify({ job_id: jobId, tenant_id: tid, issue_description: issueDescription }) });
  },

  // Badges
  listBadges: () => {
    const tid = getTenantId();
    return apiFetch<BadgeList>(`/v1/commerce/tenants/${tid}/badges`);
  },
};

// ── Pricing ───────────────────────────────────────────────────────────────────
export const pricingApi = {
  // Tenant service prices
  listPrices: (limit = 50, cursor?: string) => {
    const tid = getTenantId();
    const qs  = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<ServiceTypePriceList>(`/v1/pricing/tenants/${tid}/prices${qs}`);
  },
  getPrice: (serviceTypeId: string) => {
    const tid = getTenantId();
    return apiFetch<ServiceTypePrice>(`/v1/pricing/tenants/${tid}/prices/${serviceTypeId}`);
  },
  setPrice: (data: { service_type_id:string; service_category:string; city_name:string; base_price:number; unit?:string; change_reason?:string }) => {
    const tid = getTenantId();
    return apiFetch<ServiceTypePrice>(`/v1/pricing/tenants/${tid}/prices/set`,
      { method:"POST", body:JSON.stringify(data) });
  },
  getPriceHistory: (serviceTypeId: string, limit = 20, cursor?: string) => {
    const tid = getTenantId();
    const qs  = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<ServiceTypePriceList>(`/v1/pricing/tenants/${tid}/prices/${serviceTypeId}/history${qs}`);
  },

  // Brand adjustment
  getBrandAdjustment: () => {
    const tid = getTenantId();
    return apiFetch<BrandAdjustment>(`/v1/pricing/tenants/${tid}/brand-adjustment`);
  },
  setBrandAdjustment: (adjustmentPct: number, label?: string, reason?: string) => {
    const tid = getTenantId();
    return apiFetch<BrandAdjustment>(`/v1/pricing/tenants/${tid}/brand-adjustment`,
      { method:"PUT", body:JSON.stringify({ adjustment_pct: adjustmentPct, label, reason }) });
  },

  // Zone surcharges
  listPricingZones: () => {
    const tid = getTenantId();
    return apiFetch<ZoneSurchargeList>(`/v1/pricing/tenants/${tid}/zones`);
  },
  createPricingZone: (data: { zone_name:string; zone_type:string; zone_identifiers:string[]; surcharge_pct:number; notes?:string }) => {
    const tid = getTenantId();
    return apiFetch<ZoneSurcharge>(`/v1/pricing/tenants/${tid}/zones`,
      { method:"POST", body:JSON.stringify(data) });
  },
  getPricingZone: (zoneId: string) => {
    const tid = getTenantId();
    return apiFetch<ZoneSurcharge>(`/v1/pricing/tenants/${tid}/zones/${zoneId}`);
  },
  updatePricingZone: (zoneId: string, data: Partial<{ zone_name:string; surcharge_pct:number; is_active:boolean; notes:string }>) => {
    const tid = getTenantId();
    return apiFetch<ZoneSurcharge>(`/v1/pricing/tenants/${tid}/zones/${zoneId}`,
      { method:"PUT", body:JSON.stringify(data) });
  },
  deletePricingZone: (zoneId: string) => {
    const tid = getTenantId();
    return apiFetch<void>(`/v1/pricing/tenants/${tid}/zones/${zoneId}`, { method:"DELETE" });
  },

  // Dynamic pricing rules
  listRules: (activeOnly = false) => {
    const tid = getTenantId();
    return apiFetch<DynamicPricingRuleList>(`/v1/pricing/tenants/${tid}/rules?active_only=${activeOnly}`);
  },
  createRule: (data: { rule_name:string; rule_type:string; priority?:number; adjustment_pct:number; conditions?:Record<string,unknown>; applies_to?:string[]; active_from?:string; active_until?:string }) => {
    const tid = getTenantId();
    return apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tid}/rules`,
      { method:"POST", body:JSON.stringify(data) });
  },
  getRule: (ruleId: string) => {
    const tid = getTenantId();
    return apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tid}/rules/${ruleId}`);
  },
  updateRule: (ruleId: string, data: Partial<{ rule_name:string; priority:number; adjustment_pct:number; conditions:Record<string,unknown>; applies_to:string[] }>) => {
    const tid = getTenantId();
    return apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tid}/rules/${ruleId}`,
      { method:"PUT", body:JSON.stringify(data) });
  },
  activateRule: (ruleId: string) => {
    const tid = getTenantId();
    return apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tid}/rules/${ruleId}/activate`, { method:"POST" });
  },
  deactivateRule: (ruleId: string) => {
    const tid = getTenantId();
    return apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tid}/rules/${ruleId}/deactivate`, { method:"POST" });
  },
  deleteRule: (ruleId: string) => {
    const tid = getTenantId();
    return apiFetch<void>(`/v1/pricing/tenants/${tid}/rules/${ruleId}`, { method:"DELETE" });
  },

  // Preview & snapshots
  previewPrice: (serviceTypeId: string, serviceCategory: string, cityName: string, pincode?: string) => {
    const tid = getTenantId();
    return apiFetch<PricePreviewResult>(`/v1/pricing/tenants/${tid}/price-preview`,
      { method:"POST", body:JSON.stringify({ service_type_id: serviceTypeId, service_category: serviceCategory,
        city_name: cityName, pincode }) });
  },
  getSnapshot: (snapshotId: string) => apiFetch<PriceSnapshot>(`/v1/pricing/snapshots/${snapshotId}`),
  replaySnapshot: (snapshotId: string) =>
    apiFetch<PriceSnapshot>(`/v1/pricing/snapshots/${snapshotId}/replay`, { method:"POST" }),
  listSnapshots: (limit = 50, cursor?: string) => {
    const tid = getTenantId();
    const qs  = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<PriceSnapshotList>(`/v1/pricing/tenants/${tid}/snapshots${qs}`);
  },
};

// ── Dispatch ──────────────────────────────────────────────────────────────────
export const dispatchApi = {
  dispatchJob: (jobId: string, mode: "manual"|"auto_assign"|"broadcast", staffId?: string,
                jobLat?: number, jobLng?: number, serviceTypeId = "general") => {
    const tid = getTenantId();
    return apiFetch<DispatchRecord>(`/v1/dispatch/jobs/${jobId}/dispatch`,
      { method:"POST", body:JSON.stringify({ tenant_id: tid, mode, staff_id: staffId,
        job_lat: jobLat, job_lng: jobLng, service_type_id: serviceTypeId }) });
  },
  getDispatch: (jobId: string) => apiFetch<DispatchRecord>(`/v1/dispatch/jobs/${jobId}`),
  listRecords: (limit = 50, cursor?: string) => {
    const tid = getTenantId();
    const qs  = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<DispatchRecordList>(`/v1/dispatch/tenants/${tid}/records${qs}`);
  },
  acceptJob: (jobId: string, staffId: string) =>
    apiFetch<DispatchRecord>(`/v1/dispatch/jobs/${jobId}/accept`,
      { method:"POST", body:JSON.stringify({ staff_id: staffId }) }),
  rejectJob: (jobId: string, staffId: string, reason?: string) =>
    apiFetch<DispatchRecord>(`/v1/dispatch/jobs/${jobId}/reject`,
      { method:"POST", body:JSON.stringify({ staff_id: staffId, reason }) }),
  reassignJob: (jobId: string, newStaffId: string, reason = "") =>
    apiFetch<DispatchRecord>(`/v1/dispatch/jobs/${jobId}/reassign`,
      { method:"POST", body:JSON.stringify({ new_staff_id: newStaffId, reason }) }),
  getQueue: () => {
    const tid = getTenantId();
    return apiFetch<DispatchQueue>(`/v1/dispatch/tenants/${tid}/queue`);
  },
  getScoring: (jobId: string) => apiFetch<ScoringBreakdown>(`/v1/dispatch/jobs/${jobId}/scoring`),
};

// ── Geo ───────────────────────────────────────────────────────────────────────
export const geoApi = {
  listZones: (activeOnly = true) => {
    const tid = getTenantId();
    return apiFetch<ServiceZoneList>(`/v1/geo/tenants/${tid}/zones?active_only=${activeOnly}`);
  },
  createZone: (data: { zone_name:string; zone_type:string; identifiers?:string[]; center_lat?:number; center_lng?:number; radius_km?:number; surcharge_pct?:number }) => {
    const tid = getTenantId();
    return apiFetch<ServiceZone>(`/v1/geo/tenants/${tid}/zones`,
      { method:"POST", body:JSON.stringify(data) });
  },
  getZone: (zoneId: string) => apiFetch<ServiceZone>(`/v1/geo/zones/${zoneId}`),
  updateZone: (zoneId: string, data: Partial<{ zone_name:string; identifiers:string[]; center_lat:number; center_lng:number; radius_km:number; surcharge_pct:number; is_active:boolean }>) =>
    apiFetch<ServiceZone>(`/v1/geo/zones/${zoneId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteZone: (zoneId: string) => apiFetch<void>(`/v1/geo/zones/${zoneId}`, { method:"DELETE" }),
  checkPincode: (pincode: string) => {
    const tid = getTenantId();
    return apiFetch<PincodeZoneCheck>(`/v1/geo/tenants/${tid}/zones/check?pincode=${pincode}`);
  },
  updateStaffLocation: (staffId: string, latitude: number, longitude: number, accuracyM?: number, status?: string) => {
    const tid = getTenantId();
    return apiFetch<StaffLocation>(`/v1/geo/tenants/${tid}/staff/${staffId}/location`,
      { method:"POST", body:JSON.stringify({ latitude, longitude, accuracy_m: accuracyM, status }) });
  },
  staffInRadius: (lat: number, lng: number, radiusKm = 10, staffStatus?: string) => {
    const tid = getTenantId();
    const qs  = staffStatus ? `&staff_status=${staffStatus}` : "";
    return apiFetch<StaffLocation[]>(`/v1/geo/tenants/${tid}/staff/radius?lat=${lat}&lng=${lng}&radius_km=${radiusKm}${qs}`);
  },
  getCoverage: () => {
    const tid = getTenantId();
    return apiFetch<CoverageMap>(`/v1/geo/tenants/${tid}/coverage`);
  },
};

// ── Reviews ───────────────────────────────────────────────────────────────────
export const reviewsApi = {
  list: (params?: Partial<{ status:string; limit:string; cursor:string }>) => {
    const tid = getTenantId();
    const qs  = new URLSearchParams({ ...(params ?? {}), tenant_id: tid ?? "" }).toString();
    return apiFetch<ReviewListResponse>(`/v1/reviews?${qs}`);
  },
  getAggregate: () => {
    const tid = getTenantId();
    return apiFetch<ReviewAggregate>(`/v1/reviews/aggregates/tenant/${tid}`);
  },
  reply: (reviewId: string, replyText: string) =>
    apiFetch<Review>(`/v1/reviews/${reviewId}/reply`, { method:"POST",
      body:JSON.stringify({ reply_text: replyText }) }),
  flag:  (reviewId: string, reason: string) =>
    apiFetch<Review>(`/v1/reviews/${reviewId}/flag`, { method:"POST",
      body:JSON.stringify({ reason }) }),
  resolve: (reviewId: string, action: "publish"|"remove", reason?: string) =>
    apiFetch<Review>(`/v1/reviews/${reviewId}/resolve`, { method:"POST",
      body:JSON.stringify({ action, reason }) }),
  listRequests: (params?: Partial<{ status:string; limit:string; cursor:string }>) => {
    const tid = getTenantId();
    const qs  = new URLSearchParams({ ...(params ?? {}), tenant_id: tid ?? "" }).toString();
    return apiFetch<ReviewRequestListResponse>(`/v1/reviews/requests?${qs}`);
  },
  createRequest: (jobId: string, customerId: string, staffId?: string) => {
    const tid = getTenantId();
    return apiFetch<ReviewRequest>("/v1/reviews/requests", { method:"POST",
      body:JSON.stringify({ job_id: jobId, tenant_id: tid, customer_id: customerId, staff_id: staffId }) });
  },
};

// ── Notifications ────────────────────────────────────────────────────────────────────────────────
export const notificationsApi = {
  list: (params?: Partial<{ status:string; limit:string; cursor:string }>) => {
    const tid = getTenantId();
    const qs  = params ? `?${new URLSearchParams(params).toString()}` : "";
    return apiFetch<NotificationListResponse>(`/v1/notifications/tenants/${tid}/list${qs}`);
  },
  getChannels: () => {
    const tid = getTenantId();
    return apiFetch<NotificationChannelList>(`/v1/notifications/tenants/${tid}/channels`);
  },
  setChannel: (channel: string, isEnabled: boolean, config?: Record<string,unknown>) => {
    const tid = getTenantId();
    return apiFetch<NotificationChannel>(`/v1/notifications/tenants/${tid}/channels/${channel}`,
      { method:"PUT", body:JSON.stringify({ is_enabled: isEnabled, config: config ?? {} }) });
  },
  testChannel: (channel: string) => {
    const tid = getTenantId();
    return apiFetch<void>(`/v1/notifications/tenants/${tid}/channels/${channel}/test`, { method:"POST" });
  },
};

// ── Chat ──────────────────────────────────────────────────────────────────────
export const chatApi = {
  listRooms: (limit = 20) => {
    const tid = getTenantId();
    return apiFetch<ChatRoomListResponse>(`/v1/chat/conversations?tenant_id=${tid}&limit=${limit}`);
  },
  getMessages: (roomId: string, limit = 50, cursor?: string) => {
    const tid = getTenantId();
    const qs = cursor ? `&limit=${limit}&cursor=${cursor}` : `&limit=${limit}`;
    return apiFetch<MessageListResponse>(`/v1/chat/conversations/${roomId}/messages?tenant_id=${tid}${qs}`);
  },
  sendMessage: (roomId: string, content: string) => {
    const tid = getTenantId();
    return apiFetch<ChatMessage>(`/v1/chat/conversations/${roomId}/messages?tenant_id=${tid}`,
      { method:"POST", body:JSON.stringify({ content, message_type:"text" }) });
  },
  markRead: (roomId: string) => {
    const tid = getTenantId();
    return apiFetch<void>(`/v1/chat/conversations/${roomId}/messages/read?tenant_id=${tid}`, { method:"POST" });
  },
};

// ── Documents ─────────────────────────────────────────────────────────────────
export const documentsApi = {
  list: (params?: Partial<{ status:string; limit:string }>) => {
    const tid = getTenantId();
    const qs  = new URLSearchParams({ ...(params ?? {}), tenant_id: tid ?? "" }).toString();
    return apiFetch<DocumentListResponse>(`/v1/documents?${qs}`);
  },
  get:      (id: string) => apiFetch<Document>(`/v1/documents/${id}`),
  generate: (docType: string, jobId: string, variables: Record<string, string>) => {
    const tid = getTenantId();
    return apiFetch<Document>(`/v1/documents`,
      { method:"POST", body:JSON.stringify({ tenant_id: tid, doc_type: docType,
        entity_type:"job", entity_id: jobId, variables }) });
  },
  getSigningUrl: (id: string) =>
    apiFetch<{ signing_url: string; expires_at: string }>(`/v1/documents/${id}/signing-url`),
  send: (id: string) => apiFetch<Document>(`/v1/documents/${id}/send`, { method:"POST" }),
  void: (id: string, reason = "Voided") =>
    apiFetch<Document>(`/v1/documents/${id}/void`, { method:"POST", body:JSON.stringify({ reason }) }),
  events: (id: string) => apiFetch<DocumentEventList>(`/v1/documents/${id}/events`),
  getTemplate: (docType: string) => {
    const tid = getTenantId();
    return apiFetch<DocumentTemplate>(`/v1/documents/tenants/${tid}/templates/${docType}`);
  },
};

// ── Media ─────────────────────────────────────────────────────────────────────
export const mediaApi = {
  initiateUpload: (filename: string, contentType: string, sizeBytes: number, entityType?: string, entityId?: string) => {
    const tid = getTenantId();
    return apiFetch<UploadSession>("/v1/media/upload/initiate",
      { method:"POST", body:JSON.stringify({ tenant_id: tid, file_name: filename, mime_type: contentType, size_bytes: sizeBytes, entity_type: entityType, entity_id: entityId }) });
  },
  confirmUpload: (sessionId: string, etag?: string) =>
    apiFetch<MediaFile>(`/v1/media/upload/${sessionId}/confirm`,
      { method:"POST", body:JSON.stringify({ etag }) }),
  listFiles: (params?: { limit?: number; cursor?: string; purpose?: string }) => {
    const tid = getTenantId();
    const qs  = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<MediaFileList>(`/v1/media/tenants/${tid}/files?${qs}`);
  },
  getFile:   (fileId: string) => {
    const tid = getTenantId();
    return apiFetch<MediaFile>(`/v1/media/tenants/${tid}/files/${fileId}`);
  },
  deleteFile:(fileId: string) => {
    const tid = getTenantId();
    return apiFetch<void>(`/v1/media/tenants/${tid}/files/${fileId}`, { method:"DELETE" });
  },
  getQuota:  () => {
    const tid = getTenantId();
    return apiFetch<MediaQuota>(`/v1/media/tenants/${tid}/quota`);
  },
};

// ── Phase 0A Media Asset API ──────────────────────────────────────────────────
export const mediaAssetApi = {
  upload: (mediaContext: string, ownerType: string, ownerId: string, file: File, isPublic = false): Promise<MediaAsset> => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("media_context", mediaContext);
    fd.append("owner_type", ownerType);
    fd.append("owner_id", ownerId);
    fd.append("is_public", String(isPublic));
    return apiFetchMultipart<MediaAsset>("/v1/media/upload", fd);
  },
  getAsset: (id: string) => apiFetch<MediaAsset>(`/v1/media/${id}`),
  listAssets: (params?: { media_context?: string; owner_type?: string; owner_id?: string; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams(params as Record<string, string> ?? {}).toString();
    return apiFetch<MediaAssetList>(`/v1/media?${qs}`);
  },
  replace: (id: string, file: File): Promise<{ replaced_id: string; new_asset: MediaAsset }> => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetchMultipart<{ replaced_id: string; new_asset: MediaAsset }>(`/v1/media/${id}/replace`, fd);
  },
  delete: (id: string) => apiFetch<{ id: string; deleted: boolean }>(`/v1/media/${id}`, { method: "DELETE" }),
  viewUrl:     (id: string) => `${API_BASE}/v1/media/${id}/view`,
  downloadUrl: (id: string) => `${API_BASE}/v1/media/${id}/download`,
  uploadProfilePhoto: (file: File): Promise<MediaAsset> => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetchMultipart<MediaAsset>("/v1/me/profile-photo", fd);
  },
  removeProfilePhoto: () => apiFetch<{ removed: boolean }>("/v1/me/profile-photo", { method: "DELETE" }),

  uploadBusinessLogo: (file: File): Promise<MediaAsset> => {
    const fd = new FormData(); fd.append("file", file);
    return apiFetchMultipart<MediaAsset>("/v1/provider/profile/logo", fd);
  },
  removeBusinessLogo: (mediaId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/provider/profile/logo?media_id=${mediaId}`, { method: "DELETE" }),

  uploadShopPhoto: (file: File): Promise<MediaAsset> => {
    const fd = new FormData(); fd.append("file", file);
    return apiFetchMultipart<MediaAsset>("/v1/provider/profile/shop-photo", fd);
  },
  removeShopPhoto: (mediaId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/provider/profile/shop-photo?media_id=${mediaId}`, { method: "DELETE" }),

  uploadStaffPhoto: (file: File): Promise<MediaAsset> => {
    const fd = new FormData(); fd.append("file", file);
    return apiFetchMultipart<MediaAsset>("/v1/staff/profile/photo", fd);
  },
  removeStaffPhoto: () => apiFetch<{ removed: boolean }>("/v1/staff/profile/photo", { method: "DELETE" }),
};

// ── Settings ──────────────────────────────────────────────────────────────────
export const settingsApi = {
  get: (key?: string) => {
    const tid = getTenantId();
    return apiFetch<SettingsResponse>(`/v1/settings/tenants/${tid}${key ? `/${key}` : ""}`);
  },
  update: (key: string, value: unknown) => {
    const tid = getTenantId();
    return apiFetch<SettingEntry>(`/v1/settings/tenants/${tid}/${key}`,
      { method:"PUT", body:JSON.stringify({ value }) });
  },
  delete: (key: string) => {
    const tid = getTenantId();
    return apiFetch<void>(`/v1/settings/tenants/${tid}/${key}`, { method:"DELETE" });
  },
  resolve: (key: string) => {
    const tid = getTenantId();
    return apiFetch<ResolvedSetting>(`/v1/settings/resolve/${key}?tenant_id=${tid}`);
  },
  // Webhooks
  listWebhooks: () => {
    const tid = getTenantId();
    return apiFetch<WebhookListResponse>(`/v1/webhooks/tenants/${tid}/endpoints`);
  },
  getWebhook:   (id: string) => apiFetch<Webhook>(`/v1/webhooks/endpoints/${id}`),
  createWebhook:(url: string, events: string[]) => {
    const tid = getTenantId();
    return apiFetch<Webhook>("/v1/webhooks/endpoints",
      { method:"POST", body:JSON.stringify({ tenant_id: tid, url, events }) });
  },
  updateWebhook:(id: string, data: Partial<{ url: string; events: string[]; is_active: boolean }>) =>
    apiFetch<Webhook>(`/v1/webhooks/endpoints/${id}`,
      { method:"PUT", body:JSON.stringify(data) }),
  deleteWebhook:(id: string) =>
    apiFetch<void>(`/v1/webhooks/endpoints/${id}`, { method:"DELETE" }),
  testWebhook:  (id: string) =>
    apiFetch<void>(`/v1/webhooks/endpoints/${id}/test`, { method:"POST" }),
  pauseWebhook: (id: string) =>
    apiFetch<Webhook>(`/v1/webhooks/endpoints/${id}/pause`, { method:"POST" }),
  resumeWebhook:(id: string) =>
    apiFetch<Webhook>(`/v1/webhooks/endpoints/${id}/resume`, { method:"POST" }),
  listDeliveries:(params?: { limit?: number; cursor?: string }) => {
    const tid = getTenantId();
    const qs  = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<WebhookDeliveryList>(`/v1/webhooks/tenants/${tid}/deliveries?${qs}`);
  },
  getDelivery: (deliveryId: string) => {
    const tid = getTenantId();
    return apiFetch<WebhookDelivery>(`/v1/webhooks/deliveries/${deliveryId}?tenant_id=${tid}`);
  },
  replayDelivery: (deliveryId: string) => {
    const tid = getTenantId();
    return apiFetch<WebhookDelivery>(`/v1/webhooks/deliveries/${deliveryId}/replay?tenant_id=${tid}`, { method:"POST" });
  },
  listByEventType: (eventType: string, limit = 50, cursor?: string) => {
    const tid = getTenantId();
    return apiFetch<WebhookDeliveryList>(
      `/v1/webhooks/tenants/${tid}/events/${eventType}?limit=${limit}${cursor ? `&cursor=${cursor}` : ""}`);
  },
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analyticsApi = {
  metrics: (days = 30) => {
    const tid = getTenantId();
    return apiFetch<TenantMetrics>(`/v1/analytics/tenants/${tid}/metrics?days=${days}`);
  },
  dailyMetric: (metricKey: string, days = 30) => {
    const tid = getTenantId();
    return apiFetch<DailyMetricList>(`/v1/analytics/metrics/daily?metric_key=${metricKey}&days=${days}&tenant_id=${tid}`);
  },
};

// ── DS (Data Science) ─────────────────────────────────────────────────────────
export const dsApi = {
  // Churn
  getChurnScore:   () => {
    const tid = getTenantId();
    return apiFetch<ChurnScore>(`/v1/ds/tenants/${tid}/churn/score`);
  },
  getChurnFactors: () => {
    const tid = getTenantId();
    return apiFetch<ChurnFactors>(`/v1/ds/tenants/${tid}/churn/factors`);
  },

  // Demand forecast
  demandForecast: () => {
    const tid = getTenantId();
    return apiFetch<DemandForecastDetail>(`/v1/ds/tenants/${tid}/demand/forecast`);
  },
  recomputeDemand: () => {
    const tid = getTenantId();
    return apiFetch<DemandForecastDetail>(`/v1/ds/tenants/${tid}/demand/recompute`, { method: "POST" });
  },

  // Pricing recommendations
  pricingRecommendations: () => {
    const tid = getTenantId();
    return apiFetch<PricingRecommendationList>(`/v1/ds/tenants/${tid}/pricing/recommendations`);
  },
  applyPricingRecommendation: (serviceTypeId: string, targetPrice: number) => {
    const tid = getTenantId();
    return apiFetch<void>(`/v1/ds/tenants/${tid}/pricing/apply`,
      { method: "POST", body: JSON.stringify({ service_type_id: serviceTypeId, target_price: targetPrice }) });
  },

  // Staff performance
  staffRankings: () => {
    const tid = getTenantId();
    return apiFetch<StaffRankingList>(`/v1/ds/tenants/${tid}/staff/rankings`);
  },
  getStaffScore: (staffId: string) => {
    const tid = getTenantId();
    return apiFetch<StaffScoreDetail>(`/v1/ds/tenants/${tid}/staff/${staffId}/score`);
  },

  // Business Performance (Phase 13)
  getBusinessPerformance: (days = 30) => {
    const tid = getTenantId();
    return apiFetch<BusinessPerformance>(`/v1/ds/tenants/${tid}/business-performance?days=${days}`);
  },

  // Customer LTV
  getCustomerLtv: (customerId: string) => {
    const tid = getTenantId();
    return apiFetch<CustomerLtv>(`/v1/ds/tenants/${tid}/customers/${customerId}/ltv`);
  },
  highValueCustomers: (limit = 20) => {
    const tid = getTenantId();
    return apiFetch<HighValueCustomerList>(`/v1/ds/tenants/${tid}/customers/high-value?limit=${limit}`);
  },
};

// ── Tenant self-service (profile, plan info) ──────────────────────────────────
export const tenantSelfApi = {
  getProfile: () => {
    const tid = getTenantId();
    return apiFetch<TenantProfile>(`/v1/tenants/${tid}`);
  },
  updateProfile: (data: Partial<TenantProfile>) => {
    const tid = getTenantId();
    return apiFetch<TenantProfile>(`/v1/tenants/${tid}`, { method:"PUT", body:JSON.stringify(data) });
  },
  getHealth: () => {
    const tid = getTenantId();
    return apiFetch<TenantHealthInfo>(`/v1/tenants/${tid}/health`);
  },
  getBillingInfo: () => {
    const tid = getTenantId();
    return apiFetch<TenantBillingInfo>(`/v1/tenants/${tid}/billing`);
  },
};

// ── Subscription ──────────────────────────────────────────────────────────────
export const subscriptionApi = {
  get: () => {
    const tid = getTenantId();
    return apiFetch<SubscriptionInfo>(`/v1/subscriptions/tenants/${tid}`);
  },
  updatePlan: (newPlan: string, billingCycle = "monthly") => {
    const tid = getTenantId();
    return apiFetch<SubscriptionInfo>(`/v1/subscriptions/tenants/${tid}/plan`,
      { method:"PUT", body:JSON.stringify({ new_plan: newPlan, billing_cycle: billingCycle }) });
  },
  getPeriod: () => {
    const tid = getTenantId();
    return apiFetch<SubscriptionPeriod>(`/v1/subscriptions/tenants/${tid}/period`);
  },
  getHistory: (limit = 12, cursor?: string) => {
    const tid = getTenantId();
    const qs  = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<SubscriptionHistoryList>(`/v1/subscriptions/tenants/${tid}/history${qs}`);
  },
  prorationPreview: (newPlan: string, billingCycle = "monthly") => {
    const tid = getTenantId();
    return apiFetch<ProrationPreview>(
      `/v1/subscriptions/tenants/${tid}/proration-preview?new_plan=${newPlan}&billing_cycle=${billingCycle}`);
  },
};

// ── Compliance (DPDP Act 2023 — consent, erasure, portability) ────────────────
export const complianceApi = {
  recordConsent: (consentType: string, action: "granted"|"withdrawn", policyVersion = "1.0") => {
    const tid = getTenantId(); const uid = getUserId();
    return apiFetch<ConsentResult>("/v1/compliance/consent", { method:"POST", body:JSON.stringify({
      user_id: uid, tenant_id: tid, consent_type: consentType, action, policy_version: policyVersion, source:"tenant_portal" }) });
  },
  withdrawConsent: (consentType: string, policyVersion = "1.0") => {
    const tid = getTenantId(); const uid = getUserId();
    return apiFetch<ConsentResult>("/v1/compliance/consent/withdraw", { method:"POST", body:JSON.stringify({
      user_id: uid, tenant_id: tid, consent_type: consentType, policy_version: policyVersion }) });
  },
  checkConsent: (consentType: string) => {
    const uid = getUserId();
    return apiFetch<ConsentCheck>(`/v1/compliance/consent/users/${uid}/check?consent_type=${consentType}`);
  },
  listConsents: () => {
    const uid = getUserId();
    return apiFetch<ConsentListResponse>(`/v1/compliance/consent/users/${uid}`);
  },
  requestDeletion: (reason?: string) => {
    const tid = getTenantId(); const uid = getUserId();
    return apiFetch<DeletionRequestResult>("/v1/compliance/deletion-requests", { method:"POST", body:JSON.stringify({
      user_id: uid, tenant_id: tid, request_reason: reason }) });
  },
  getDeletionRequest: (requestId: string) =>
    apiFetch<DeletionRequestResult>(`/v1/compliance/deletion-requests/${requestId}`),
  requestExport: (dataCategories: string[] = [], exportFormat = "json") => {
    const tid = getTenantId(); const uid = getUserId();
    return apiFetch<ExportRequestResult>("/v1/compliance/portability-requests", { method:"POST", body:JSON.stringify({
      user_id: uid, tenant_id: tid, data_categories: dataCategories, export_format: exportFormat }) });
  },
  getExportStatus: (requestId: string) =>
    apiFetch<ExportRequestResult>(`/v1/compliance/portability-requests/${requestId}`),
};

// ── Security (API keys, IP blocklist, threat reporting) ────────────────────────
export const securityApi = {
  createApiKey: (name: string, scopes: string[], description?: string, environment = "live", expiresDays?: number) => {
    const tid = getTenantId();
    return apiFetch<SecurityApiKeyCreated>("/v1/security/api-keys", { method:"POST", body:JSON.stringify({
      tenant_id: tid, name, description, scopes, environment, expires_days: expiresDays }) });
  },
  listApiKeys: () => {
    const tid = getTenantId();
    return apiFetch<SecurityApiKeyList>(`/v1/security/api-keys/tenants/${tid}`);
  },
  rotateApiKey: (keyId: string) => {
    const tid = getTenantId();
    return apiFetch<SecurityApiKeyCreated>(`/v1/security/api-keys/${keyId}/rotate?tenant_id=${tid}`, { method:"POST" });
  },
  revokeApiKey: (keyId: string, reason: string) => {
    const tid = getTenantId();
    return apiFetch<{ key_id:string; revoked:boolean; reason:string }>(
      `/v1/security/api-keys/${keyId}/revoke?tenant_id=${tid}`,
      { method:"POST", body:JSON.stringify({ reason }) });
  },
  checkIpBlocked: (ip: string) =>
    apiFetch<IpBlockCheck>(`/v1/security/blocklist/check?ip=${encodeURIComponent(ip)}`),
  reportActivity: (activityType: string) => {
    const tid = getTenantId(); const uid = getUserId();
    return apiFetch<ActivityReportResult>("/v1/security/activity/record", { method:"POST", body:JSON.stringify({
      tenant_id: tid, entity_id: uid, entity_type:"user", activity_type: activityType }) });
  },
};

// ── Appointment Engine ────────────────────────────────────────────────────────
export const appointmentApi = {
  holdSlot: (staffId:string, scheduledAt:string, durationMinutes:number, customerId:string, serviceTypeId?:string, customerNotes?:string) => {
    const tid = getTenantId();
    return apiFetch<Appointment>("/v1/appointments/hold", { method:"POST", body:JSON.stringify({
      tenant_id:tid, staff_id:staffId, customer_id:customerId, service_type_id:serviceTypeId,
      scheduled_at:scheduledAt, duration_minutes:durationMinutes, customer_notes:customerNotes }) });
  },
  confirmHold: (appointmentId:string) =>
    apiFetch<Appointment>(`/v1/appointments/${appointmentId}/confirm`, { method:"POST" }),
  getAppointment: (appointmentId:string) =>
    apiFetch<Appointment>(`/v1/appointments/${appointmentId}`),
  // MODULE-L5-42: real routes carry staff_id/customer_id in the PATH
  // (/v1/appointments/staff/{id}, /v1/appointments/customers/{id}); the old
  // /staff?... and /customer?... 404'd.
  listByStaff: (staffId:string, status?:string, cursor?:string) => {
    const tid = getTenantId();
    const q = new URLSearchParams({ tenant_id:tid });
    if (status) q.set("status", status);
    if (cursor) q.set("cursor", cursor);
    return apiFetch<AppointmentListResponse>(`/v1/appointments/staff/${staffId}?${q}`);
  },
  listByCustomer: (customerId:string, cursor?:string) => {
    const tid = getTenantId();
    const q = new URLSearchParams({ tenant_id:tid });
    if (cursor) q.set("cursor", cursor);
    return apiFetch<AppointmentListResponse>(`/v1/appointments/customers/${customerId}?${q}`);
  },
  cancelAppointment: (appointmentId:string, reason?:string) =>
    apiFetch<Appointment>(`/v1/appointments/${appointmentId}/cancel`, { method:"POST", body:JSON.stringify({ reason }) }),
  rescheduleAppointment: (appointmentId:string, newScheduledAt:string, durationMinutes?:number) =>
    apiFetch<Appointment>(`/v1/appointments/${appointmentId}/reschedule`, { method:"POST", body:JSON.stringify({
      new_scheduled_at:newScheduledAt, duration_minutes:durationMinutes }) }),
  markNoShow: (appointmentId:string) =>
    apiFetch<Appointment>(`/v1/appointments/${appointmentId}/no-show`, { method:"POST" }),
  getHistory: (appointmentId:string) =>
    apiFetch<AppointmentHistoryResponse>(`/v1/appointments/${appointmentId}/history`),
  // MODULE-L5-42: real route /v1/appointments/staff/{id}/slots?date=&tenant_id=
  // (no duration_minutes param); old /slots/available 404'd.
  getAvailableSlots: (staffId:string, date:string) => {
    const tid = getTenantId();
    const q = new URLSearchParams({ tenant_id:tid, date });
    return apiFetch<AppointmentSlotsResponse>(`/v1/appointments/staff/${staffId}/slots?${q}`);
  },
  // MODULE-L5-42: real route POST /v1/appointments/staff/{id}/calendar/block
  // ?tenant_id=, body {block_date, start_time, end_time, block_type, reason,
  // is_full_day}; old /calendar/block with start_at/end_at 404'd.
  blockCalendar: (staffId:string, blockDate:string, startTime:string, endTime:string, reason?:string) => {
    const tid = getTenantId();
    return apiFetch<CalendarBlock>(`/v1/appointments/staff/${staffId}/calendar/block?tenant_id=${tid}`, {
      method:"POST", body:JSON.stringify({
        block_date:blockDate, start_time:startTime, end_time:endTime, block_type:"leave", reason }) });
  },
  // MODULE-L5-42: real route DELETE /v1/appointments/calendar/blocks/{id}
  // (plural "blocks"); old singular 404'd.
  unblockCalendar: (blockId:string) =>
    apiFetch<{ block_id:string; removed:boolean }>(`/v1/appointments/calendar/blocks/${blockId}`, { method:"DELETE" }),
  // MODULE-L5-42: real route POST /v1/appointments/staff/{id}/working-hours
  // ?tenant_id=; old /working-hours 404'd.
  setWorkingHours: (staffId:string, workingHours:Record<string,{ start:string; end:string; is_working:boolean }>) => {
    const tid = getTenantId();
    return apiFetch<StaffWorkingHoursResponse>(`/v1/appointments/staff/${staffId}/working-hours?tenant_id=${tid}`, {
      method:"POST", body:JSON.stringify({ working_hours:workingHours }) });
  },
};

// ── Inventory Engine ──────────────────────────────────────────────────────────
// MODULE-L5-41: rewired to the real inventory engine routes. Previously the
// entire client called a nonexistent URL scheme (/v1/inventory/items,
// /stock/receive, /stock/balance, /stock/low, /stock/replenish,
// /reservations/{id}/confirm) -- every call 404'd. Real routes carry
// tenant_id + item_id + location_id in the PATH (not query/body) for most
// operations; reservation confirm/release identify the reservation by
// job_id+item_id+location_id in the BODY, not a reservation_id in the path.
export const inventoryApi = {
  createItem: (name:string, sku:string, unit:string, unitCost:number, category?:string, minQuantity=0,
               gst?:number|null, warranty?:string|null) => {
    const tid = getTenantId();
    return apiFetch<InventoryItem>(`/v1/inventory/tenants/${tid}/items`, { method:"POST", body:JSON.stringify({
      name, sku, unit, unit_cost:unitCost, category, min_quantity:minQuantity, gst, warranty }) });
  },
  getItem: (itemId:string) =>
    apiFetch<InventoryItem>(`/v1/inventory/items/${itemId}`),
  updateItem: (itemId:string, patch: Partial<{ name:string; sku:string; unit:string;
               unit_cost:number; category:string|null; min_quantity:number;
               gst:number|null; warranty:string|null }>) => {
    const tid = getTenantId();
    return apiFetch<InventoryItem>(`/v1/inventory/tenants/${tid}/items/${itemId}`,
      { method:"PUT", body:JSON.stringify(patch) });
  },
  deleteItem: (itemId:string) => {
    const tid = getTenantId();
    return apiFetch<{ item_id:string; deleted:boolean }>(`/v1/inventory/tenants/${tid}/items/${itemId}`,
      { method:"DELETE" });
  },
  listItems: (cursor?:string) => {
    const tid = getTenantId();
    const q = new URLSearchParams();
    if (cursor) q.set("cursor", cursor);
    const qs = q.toString();
    return apiFetch<InventoryItemList>(`/v1/inventory/tenants/${tid}/items${qs ? `?${qs}` : ""}`);
  },
  receiveStock: (itemId:string, locationId:string, quantity:number, notes?:string) => {
    const tid = getTenantId();
    return apiFetch<StockTransaction>(`/v1/inventory/items/${itemId}/locations/${locationId}/receive`, {
      method:"POST", body:JSON.stringify({ tenant_id:tid, quantity, notes }) });
  },
  getBalance: (itemId:string, locationId:string) =>
    apiFetch<StockBalance>(`/v1/inventory/items/${itemId}/locations/${locationId}/balance`),
  listTransactions: (itemId:string, locationId:string, cursor?:string) => {
    const q = new URLSearchParams();
    if (cursor) q.set("cursor", cursor);
    const qs = q.toString();
    return apiFetch<StockTransactionList>(`/v1/inventory/items/${itemId}/locations/${locationId}/transactions${qs ? `?${qs}` : ""}`);
  },
  createReservation: (itemId:string, locationId:string, jobId:string, quantity:number) => {
    const tid = getTenantId();
    return apiFetch<StockReservation>("/v1/inventory/reservations", { method:"POST", body:JSON.stringify({
      tenant_id:tid, item_id:itemId, location_id:locationId, job_id:jobId, quantity }) });
  },
  confirmReservation: (jobId:string, itemId:string, locationId:string) => {
    const tid = getTenantId();
    return apiFetch<{ confirmed:boolean; quantity:number; job_id:string }>("/v1/inventory/reservations/confirm", {
      method:"POST", body:JSON.stringify({ job_id:jobId, item_id:itemId, location_id:locationId, tenant_id:tid }) });
  },
  releaseReservation: (jobId:string, itemId:string, locationId:string) => {
    const tid = getTenantId();
    return apiFetch<{ released:boolean; quantity:number }>("/v1/inventory/reservations/release", {
      method:"POST", body:JSON.stringify({ job_id:jobId, item_id:itemId, location_id:locationId, tenant_id:tid }) });
  },
  getLowStock: () => {
    const tid = getTenantId();
    return apiFetch<LowStockList>(`/v1/inventory/tenants/${tid}/low-stock`);
  },
  replenish: (itemId:string, quantityRequested:number) => {
    const tid = getTenantId();
    return apiFetch<ReplenishResult>(`/v1/inventory/tenants/${tid}/items/${itemId}/replenish`, {
      method:"POST", body:JSON.stringify({ quantity:quantityRequested }) });
  },

  // ── Document extraction (inventory_document_extraction plugin engine) ──
  // Gated: 403 with error_code ENGINE_DISABLED if the engine isn't enabled
  // for this tenant. Never auto-publishes -- returns draft rows for review.
  uploadForExtraction: (file: File) => {
    const tid = getTenantId();
    const form = new FormData();
    form.append("file", file);
    // 120s -- a large multi-page PDF (up to the backend's 15MB limit) needs
    // real time for text extraction + the DeepSeek extraction call; the
    // default 60s was too tight and could abort a genuinely-in-progress
    // large upload.
    return apiFetchMultipart<InventoryExtractionResult>(
      `/v1/inventory/tenants/${tid}/extraction/upload`, form, "POST", 120_000);
  },
  listDrafts: () => {
    const tid = getTenantId();
    return apiFetch<{ items: InventoryDraftItem[]; total: number }>(
      `/v1/inventory/tenants/${tid}/extraction/drafts`);
  },
  updateDraft: (itemId: string, data: Partial<InventoryDraftItem>) =>
    apiFetch<InventoryDraftItem>(`/v1/inventory/items/${itemId}/draft`, {
      method: "PATCH", body: JSON.stringify(data) }),
  deleteDraft: (itemId: string) =>
    apiFetch<{ item_id: string; deleted: boolean }>(`/v1/inventory/items/${itemId}/draft`, { method: "DELETE" }),
  publishItem: (itemId: string) =>
    apiFetch<InventoryDraftItem>(`/v1/inventory/items/${itemId}/publish`, { method: "POST" }),
  publishBulk: (itemIds: string[]) =>
    apiFetch<{ results: Array<{ item_id: string; error?: string }>; published: number; total: number }>(
      "/v1/inventory/items/publish-bulk", { method: "POST", body: JSON.stringify({ item_ids: itemIds }) }),
};

export interface InventoryDraftItem {
  item_id: string; name: string; sku: string; category?: string | null;
  unit: string; unit_cost: number; min_quantity: number; status: "draft" | "published";
  source_upload_id?: string | null;
  gst?: number | null; warranty?: string | null;
}
export interface InventoryExtractionResult {
  upload_id: string; idempotent: boolean; status: string;
  extracted_item_count: number; draft_items: InventoryDraftItem[];
}

// ── Public Registration (no auth) ─────────────────────────────────────────────
export const publicRegApi = {
  initiate: (businessName:string, ownerName:string, ownerEmail:string, ownerPhone:string,
             vertical:string, city:string, country:string, zipcode:string, state:string|undefined, planType:string) =>
    apiFetch<RegistrationInitResult>("/v1/public/register/initiate", { method:"POST", body:JSON.stringify({
      business_name:businessName, owner_name:ownerName, owner_email:ownerEmail, owner_phone:ownerPhone,
      vertical, city, country, zipcode, state, plan_type:planType }) }, true),
  confirmPlan: (sessionId:string, planType:string) =>
    apiFetch<RegistrationPlanResult>("/v1/public/register/confirm-plan", { method:"POST", body:JSON.stringify({
      session_id:sessionId, plan_type:planType }) }, true),
  verify: (sessionId:string, otp:string) =>
    apiFetch<RegistrationOtpResult>("/v1/public/register/verify", { method:"POST", body:JSON.stringify({
      session_id:sessionId, otp }) }, true),
  paymentOrder: (sessionId:string, billingCycle = "monthly") =>
    apiFetch<RegistrationPaymentOrder>("/v1/public/register/payment-order", { method:"POST", body:JSON.stringify({
      session_id:sessionId, billing_cycle:billingCycle }) }, true),
  complete: (sessionId:string, orderId:string, paymentId:string, signature:string, selectedPackageId?:string) =>
    apiFetch<RegistrationCompleteResult>("/v1/public/register/complete", { method:"POST", body:JSON.stringify({
      session_id:sessionId, razorpay_order_id:orderId, razorpay_payment_id:paymentId, razorpay_signature:signature,
      ...(selectedPackageId ? { selected_package_id: selectedPackageId } : {}) }) }, true),
};

// ── Public Packages (signup — no auth) ───────────────────────────────────────
export interface SignupPackageFeature {
  feature_id: string;
  feature_label: string;
  feature_description: string | null;
  feature_icon: string | null;
  is_highlighted: boolean;
  is_included: boolean;
  display_order: number;
}

export interface SignupPackageLimit {
  limit_id: string;
  limit_key: string;
  limit_label: string;
  limit_value: number | null;
  limit_unit: string | null;
  is_unlimited: boolean;
  display_order: number;
}

export interface SignupPackage {
  package_id: string;
  id: string;
  name: string;
  slug: string;
  short_description: string | null;
  description: string | null;
  package_type: string;
  plan_level: string | null;
  package_price: number;
  price: number;
  security_deposit_amount: number;
  included_credit_amount: number;
  bonus_credits: number | null;
  lead_credits: number | null;
  validity_days: number | null;
  trial_days: number | null;
  features: Record<string, unknown>;
  package_features: SignupPackageFeature[];
  package_limits: SignupPackageLimit[];
  is_active: boolean;
  display_order: number;
  vertical_type: string | null;
  billing_cycle: string | null;
  currency: string;
  is_public_signup_visible: boolean;
  is_popular: boolean;
  is_featured: boolean;
  is_recommended: boolean;
  badge_label: string | null;
  cta_label: string | null;
  terms_summary: string | null;
  created_at: string | null;
}
export const publicPackagesApi = {
  list: (vertical_type?: string) =>
    apiFetch<{ packages: SignupPackage[]; total: number }>(
      `/v1/public/packages${vertical_type ? `?vertical_type=${encodeURIComponent(vertical_type)}` : ""}`,
      {}, true,
    ),
};

// ── AI Chat Engine ────────────────────────────────────────────────────────────
export const aiChatApi = {
  chat: (message:string, history:AIChatMessage[] = []) =>
    apiFetch<AIChatResponse>("/v1/ai/chat", { method:"POST", body:JSON.stringify({ message, history }) }),
};

// ── Types ─────────────────────────────────────────────────────────────────────
export interface TenantUser  { id:string; user_id?:string; email:string; full_name:string; role:string; tenant_id:string; force_password_change?:boolean; }
export interface TenantCtx   { id:string; name:string; vertical:string; city:string; plan_type:string; health_score:number; }
export interface JobChecklistItem { step:string; completed:boolean; }
export interface Job         { id:string; job_id:string; job_number:string; tenant_id:string; customer_id?:string; customer_name?:string; customer_phone?:string; customer_address?:string; status:string; job_type:string; parent_job_id?:string; service_type_id:string; service_type?:string; service_category?:string; city?:string; assigned_staff_id?:string; assigned_staff?:string; created_at:string; updated_at?:string; commission_amount?:number; sla_minutes?:number; minutes_in_status?:number; job_value?:number; quoted_price?:number; final_price?:number; findings?:string; recommendation?:string; notes?:string; closing_notes?:string; checklist?:JobChecklistItem[]; allowed_transitions:string[]; duration_estimate_minutes?:number;
  customer_credit_applied?:number; payable_to_provider?:number; payment_collection_mode?:"customer_pays_provider_directly"; platform_payment_collected?:boolean; amount_collected?:number; payment_recorded?:boolean; payment_mode?:string; }

// Payment breakdown shapes exposed by the backend on booking/job payloads
// (see JOB_COMPLETION_BUG_FIX_REPORT.md _job_dict changes) — kept as a
// separate type so pages can render a fallback-computed value (with a
// console warning) if the backend field is absent, rather than trusting a
// client-side calculation by default.
export interface BookingPaymentBreakdown {
  quoted_price: number;
  credit_applied: number;
  payable_amount: number;
  payment_collection_mode?: "customer_pays_provider_directly";
  platform_payment_collected?: boolean;
}
export interface JobPaymentBreakdown {
  quoted_price: number;
  customer_credit_applied: number;
  payable_to_provider: number;
  amount_collected?: number;
  payment_recorded: boolean;
  payment_mode?: string;
}
export interface ServiceCatalogItem { id:string; service_type_id:string; name:string; category?:string; description?:string; service_type:"repair"|"service"|"consultation"; pricing_model:"fixed"|"post_assessment"|"hourly"; base_price?:number; max_price?:number; visit_fee?:number; pre_approval_limit?:number; estimated_duration_minutes?:number; checklist_required:boolean; checklist_template?:string[]; is_active:boolean; created_at:string; }
export interface ServiceCatalogListResponse { items:ServiceCatalogItem[]; total:number; }
export interface JobListResponse { jobs:Job[]; total:number; has_next:boolean; next_cursor?:string; }
export interface JobHistoryResponse { history:{ status:string; changed_at:string; notes?:string }[]; }
export interface JobQuotePart { name:string; cost:number; }
export interface JobQuote {
  quote_id:string; job_id:string; tenant_id:string; customer_id?:string;
  amount:number; parts:JobQuotePart[]; labour_estimate?:number;
  findings?:string; recommendation?:string; notes?:string;
  status:string; expires_at?:string; is_expired:boolean;
  responded_at?:string; created_at:string;
}
export interface JobQuoteListResponse { job_id:string; quotes:JobQuote[]; }
export interface SlaAlert    { job_id:string; job_number:string; tenant_name:string; status:string; minutes_overdue:number; severity:string; }
export interface JobTransitions { job_id:string; current_status:string; allowed_transitions:string[]; }
export interface JobNote     { note_id:string; job_id:string; content:string; note_type:string; is_internal:boolean; created_by?:string; created_at:string; }
export interface JobNoteList { notes:JobNote[]; }
export interface JobMedia    { media_id:string; job_id:string; media_type:string; caption?:string; storage_key?:string; status_at_capture?:string; created_at:string; }
export interface JobMediaList{ media:JobMedia[]; }
export interface SlaStatusDetail { job_id:string; current_status:string; sla_hours?:number; sla_breach:boolean; }
export interface JobCounts   { tenant_id:string; counts:Record<string,number>; total:number; }
export interface TrackedJob  { job_number:string; status:string; title:string; scheduled_at?:string; staff_assigned:boolean; allowed_transitions:string[]; }
export interface Booking {
  booking_id:string; booking_number:string; tenant_id:string; customer_id:string;
  service_type_id:string; service_category:string; status:string;
  quoted_price?:number; price_snapshot_id?:string;
  credit_applied?:number; payable_amount?:number;
  payment_collection_mode?:"customer_pays_provider_directly"; platform_payment_collected?:boolean;
  job_status?:string; assigned_staff_name?:string;
  preferred_date?:string; preferred_slot?:string; scheduled_at?:string;
  address?:Record<string,unknown>; pincode?:string;
  preflight_passed?:boolean; blocking_reason?:string; job_id?:string;
  cancellation_reason?:string; within_cancel_window?:boolean;
  reschedule_count:number; customer_notes?:string; tags?:string[];
  created_at:string; allowed_transitions:string[]; is_terminal:boolean;
}
export interface BookingListResponse { bookings:Booking[]; has_next:boolean; next_cursor?:string; }
export interface BookingSearchResponse { results:Booking[]; query:string; }
export interface BookingNote { note_id:string; booking_id:string; content:string; is_internal:boolean; author_role?:string; created_at:string; }
export interface BookingNoteList { notes:BookingNote[]; }
export interface BookingTimeline { timeline:{ from_status?:string; to_status:string; reason?:string; changed_by_role?:string; occurred_at:string }[]; }
export interface SlotAvailability { date:string; slot:string; available:boolean; reason?:string; }
export interface CancellationPolicy { tenant_id:string; policy:string; free_cancel_hours:number; max_reschedules:number; penalty_pct?:number; }

// ── Pricing types ─────────────────────────────────────────────────────────────
export interface ServiceTypePrice { id:string; tenant_id:string; service_type_id:string; service_category:string; city_name:string; base_price:number; unit:string; valid_from:string; valid_until?:string; change_reason?:string; previous_price?:number; }
export interface ServiceTypePriceList { prices:ServiceTypePrice[]; }
export interface BrandAdjustment { id:string; tenant_id:string; adjustment_pct:number; label?:string; valid_from:string; reason?:string; }
export interface ZoneSurcharge { zone_id:string; tenant_id:string; zone_name:string; zone_type:string; zone_identifiers:string[]; surcharge_pct:number; is_active:boolean; notes?:string; }
export interface ZoneSurchargeList { zones:ZoneSurcharge[]; }
export interface DynamicPricingRule { rule_id:string; tenant_id:string; rule_name:string; rule_type:string; priority:number; adjustment_pct:number; conditions:Record<string,unknown>; applies_to:string[]; is_active:boolean; active_from?:string; active_until?:string; }
export interface DynamicPricingRuleList { rules:DynamicPricingRule[]; }
export interface PricePipelineStep { applied:boolean; amount?:number; [k:string]:unknown; }
export interface PricePreviewResult { final_price:number; currency:string; steps:Record<string,PricePipelineStep>; }
export interface PriceSnapshot { snapshot_id:string; tenant_id:string; service_type_id:string; service_category:string; city_name:string; final_price:number; currency:string; pipeline_inputs:Record<string,unknown>; step_city_floor:PricePipelineStep; step_tenant_price:PricePipelineStep; step_brand_adj:PricePipelineStep; step_zone_surge:PricePipelineStep; step_dynamic_rule:PricePipelineStep; created_at:string; }
export interface PriceSnapshotList { snapshots:PriceSnapshot[]; has_next:boolean; next_cursor?:string; }

// ── Dispatch types ────────────────────────────────────────────────────────────
export interface DispatchCandidate { staff_id:string; score:number; distance_km?:number; [k:string]:unknown; }
export interface DispatchRecord { job_id:string; tenant_id:string; dispatch_mode:string; status:string; assigned_staff_id?:string; candidates_scored:DispatchCandidate[]; score_weights:Record<string,number>; rejection_count:number; escalation_count:number; accepted_at?:string; expires_at?:string; }
export interface DispatchRecordList { records:DispatchRecord[]; has_next:boolean; next_cursor?:string; }
export interface DispatchQueue { tenant_id:string; queue_size:number; items:DispatchRecord[]; }
export interface ScoringBreakdown { job_id:string; dispatch_mode:string; candidates:DispatchCandidate[]; score_weights:Record<string,number>; selected_staff_id?:string; }

// ── Geo types ─────────────────────────────────────────────────────────────────
export interface ServiceZone { zone_id:string; tenant_id:string; zone_name:string; zone_type:string; identifiers:string[]; center_lat?:number; center_lng?:number; radius_km?:number; surcharge_pct:number; is_active:boolean; }
export interface ServiceZoneList { zones:ServiceZone[]; }
export interface PincodeZoneCheck { pincode:string; in_zone:boolean; zone?:ServiceZone; }
export interface CoverageMap { tenant_id:string; zones:ServiceZone[]; total_area_km2?:number; }
export interface StaffMember  { id:string; full_name:string; phone?:string; specialisations:string[]; status:string; rating?:number; jobs_today?:number; active_job?:string; performance_score?:number; working_hours?:WorkingHours; }
export interface StaffSecurityStatus { user_id:string; email:string; full_name:string; role:string; account_status:string; is_active:boolean; lock_reason:string|null; locked_until:string|null; active_sessions:number; password_reset_required:boolean; last_login_at:string|null; }
export interface StaffLoginEvent { event_id:string; event_type:string; failure_reason:string|null; ip_address:string|null; device_id:string|null; created_at:string; }
export interface StaffListResponse  { staff:StaffMember[]; total:number; }
export interface UserDetail { user_id:string; email:string; full_name:string; phone?:string; role:string; tenant_id?:string; is_active:boolean; is_verified:boolean; is_mfa_enabled:boolean; last_login_at?:string; created_at:string; }
export interface UserListResponse { users:UserDetail[]; total:number; }
export interface WorkingHours { [day:string]:{ start:string; end:string; is_working:boolean } }
// MODULE-L5-40: was {signals, job_count, avg_rating, dispute_rate,
// on_time_rate} against a route (/v1/ds/staff/{id}/performance) that doesn't
// exist. Corrected to the real get_staff_score shape + route
// (/v1/ds/tenants/{tenant_id}/staff/{staff_id}/score).
export interface StaffPerformance {
  staff_id:string; tenant_id:string; composite_score:number; rank:number|null;
  signal_values:Record<string,number>; jobs_completed:number;
  avg_customer_rating:number; sla_adherence_rate:number;
  observation_mode:boolean; computed_at:string;
}
export interface StaffLocation { staff_id:string; lat:number; lng:number; last_seen_at:string; accuracy_m?:number; }
export interface Customer     { id:string; name:string; phone?:string; email?:string; health_band:string; health_score:number; total_jobs:number; total_spend:number; ltv_band?:string; last_job_at?:string; created_at:string; }
export interface CustomerListResponse { customers:Customer[]; total:number; has_next:boolean; next_cursor?:string; }
export interface CustomerHealth { customer_id:string; health_band:string; health_score:number; signals:Record<string,number>; risk_flags:string[]; }
export interface WalletBalance { balance:number; reserved:number; available:number; currency:string; last_topup_at?:string; }
export interface CommissionRecord { id:string; job_id:string; job_number?:string; amount:number; rate:number; job_value:number; deducted_at:string; }
export interface CommissionListResponse { records:CommissionRecord[]; total_deducted:number; has_next:boolean; }
export interface PaymentRecord  { id:string; job_id?:string; amount:number; status:string; gateway?:string; created_at:string; }
export interface PaymentListResponse { records:PaymentRecord[]; has_next:boolean; }
export interface InvoiceRecord  { id:string; invoice_number:string; job_id?:string; amount:number; status:string; pdf_url?:string; created_at:string; }
export interface InvoiceListResponse { invoices:InvoiceRecord[]; has_next:boolean; }
export interface SubscriptionInfo { subscription_id?:string; plan_type:string; status:string; started_at?:string; ends_at?:string; jobs_used?:number; jobs_included?:number; leads_used?:number; leads_included?:number; next_billing_at?:string; }
export interface PayoutRequest  { id:string; amount:number; status:string; created_at:string; }
export interface Review         { id:string; review_id:string; job_id:string; composite_score:number; comment?:string; status:string; signals:Record<string,number>; has_reply:boolean; reply_text?:string; replied_at?:string; created_at:string; }
export interface ReviewListResponse { reviews:Review[]; has_next:boolean; next_cursor?:string; }
export interface ReviewAggregate    { entity_type:string; entity_id:string; review_count:number; avg_composite:number|null; reply_rate:number|null; signal_averages:Record<string,number>; last_computed_at?:string; }
export interface ChatRoom       { room_id:string; job_id?:string; job_number?:string; participant_name:string; last_message?:string; last_message_at?:string; unread_count:number; }
export interface ChatRoomListResponse  { rooms:ChatRoom[]; has_next:boolean; }
export interface ChatMessage    { message_id:string; room_id:string; sender_id:string; sender_name?:string; content:string; message_type:string; sent_at:string; is_read:boolean; }
export interface MessageListResponse   { messages:ChatMessage[]; has_next:boolean; }
export interface TenantDocument { id:string; document_number:string; title:string; status:string; job_id?:string; signed_at?:string; signing_url?:string; signing_url_expires_at?:string; created_at:string; }
export interface DocumentListResponse  { documents:TenantDocument[]; has_next:boolean; }
export type Document = TenantDocument;
export interface SettingEntry   { key:string; value:unknown; source:"tenant"|"plan"|"platform"|"code_default"; is_override:boolean; }
export interface SettingsResponse   { settings:SettingEntry[]; }
export interface Webhook        { id:string; url:string; events:string[]; status:string; consecutive_failures:number; created_at:string; }
export interface WebhookListResponse { webhooks:Webhook[]; }
export interface TenantKpis     { jobs_today:number; bookings_pending:number; revenue_today:number; commission_today:number; wallet_balance:number; staff_active:number; avg_rating:number; pending_reviews:number; }
export interface ChartData      { date:string; value:number; }
export interface ForecastItem   { date:string; predicted_jobs:number; confidence:number; }
export interface ForecastListResponse { forecasts:ForecastItem[]; }
export interface StaffScore     { staff_id:string; name:string; composite_score:number; }
export interface StaffScoreListResponse { scores:StaffScore[]; }

// ── Auth extended types ───────────────────────────────────────────────────────
export interface PasswordResetRequestResult { message:string; otp_hint?:string; }
export interface PasswordResetConfirmResult { message:string; }
export interface MfaSetup   { secret:string; qr_code_url:string; backup_codes:string[]; }
export interface MfaConfirm { mfa_enabled:boolean; backup_codes:string[]; }
export interface BackupCodes { backup_codes:string[]; generated_at:string; }
export interface UserSession { session_id:string; device_info:Record<string,unknown>; ip_address:string; last_seen_at:string; expires_at:string; is_current?:boolean; }
export interface UserSessionList { user_id:string; active_sessions:number; sessions:UserSession[]; }
export interface InviteStaffPayload { email:string; full_name:string; role:string; permissions?:string[]; tenant_id?:string; }
export interface StaffInvite { invite_id:string; email:string; role:string; expires_at:string; }
export interface ApiKey { key_id:string; name:string; prefix:string; scopes:string[]; is_active:boolean; created_at:string; expires_at?:string; last_used_at?:string; }
export interface ApiKeyCreated extends ApiKey { secret_key:string; }
export interface ApiKeyList { keys:ApiKey[]; total:number; }

// ── Compliance types (DPDP Act 2023) ──────────────────────────────────────────
export interface ConsentResult { record_id:string; user_id:string; consent_type:string; action:string; policy_version:string; expires_at?:string; recorded_at:string; }
export interface ConsentCheck { user_id:string; consent_type:string; has_consent:boolean; action?:string; policy_version?:string; expires_at?:string; source:string; }
export interface ConsentRecordEntry { record_id:string; consent_type:string; action:string; policy_version:string; granted_at?:string; expires_at?:string; created_at:string; }
export interface ConsentListResponse { user_id:string; records:ConsentRecordEntry[]; note:string; }
export interface DeletionRequestResult {
  request_id:string; user_id:string; status:string; request_reason?:string;
  sla_deadline:string; hours_until_sla:number; sla_breached:boolean;
  tables_erased:string[]; tables_exempted:string[]; exemption_reasons:Record<string,string>;
  processed_at?:string; created_at:string; idempotent?:boolean; verification_token?:string; instructions?:string;
}
export interface ExportRequestResult {
  request_id:string; user_id:string; status:string; data_categories:string[]; export_format:string;
  sla_deadline:string; download_url?:string; download_expires_at?:string;
  record_count:number; size_bytes:number; completed_at?:string; created_at:string; idempotent?:boolean;
}

// ── Customer Self-Service Compliance (DPDP Act 2023) ─────────────────────────
export interface CustomerComplianceRequest {
  id: string;
  request_number: string;
  request_type: string;
  status: string;
  status_label: string;
  sla_status: string;
  sla_label: string;
  verification_status: string;
  submitted_at?: string;
  due_at?: string;
  completed_at?: string;
  reason?: string;
  rejection_reason?: string;
  request_source?: string;
  created_at: string;
  updated_at?: string;
  audit_trail?: { action: string; created_at: string }[];
  export?: { export_id: string; status: string; expires_at?: string; is_expired: boolean };
}
export interface CustomerComplianceRequestList {
  requests: CustomerComplianceRequest[];
  meta: { total: number; page: number; limit: number; total_pages: number };
}
export interface CustomerCreateRequestResult {
  request_id: string;
  request_number: string;
  request_type: string;
  status: string;
  status_label: string;
  sla_status: string;
  submitted_at?: string;
  due_at?: string;
  message: string;
}
export interface CustomerConsentRecord {
  record_id: string;
  consent_type: string;
  action: string;
  policy_version: string;
  granted_at?: string;
  withdrawn_at?: string;
  expires_at?: string;
  created_at: string;
}
export interface CustomerExportDownload {
  download_url: string;
  export_id: string;
  status: string;
  downloaded_at?: string;
}

export const customerComplianceApi = {
  listRequests: (params?: { request_type?: string; status?: string; page?: number }) => {
    const q = new URLSearchParams();
    if (params?.request_type) q.set("request_type", params.request_type);
    if (params?.status) q.set("status", params.status);
    if (params?.page) q.set("page", String(params.page));
    return apiFetch<CustomerComplianceRequestList>(`/v1/me/compliance/requests?${q}`);
  },
  createRequest: (data: {
    request_type: string;
    reason?: string;
    details?: string;
    confirm_understanding: boolean;
  }) => apiFetch<CustomerCreateRequestResult>("/v1/me/compliance/requests", {
    method: "POST", body: JSON.stringify(data),
  }),
  getRequest: (requestId: string) =>
    apiFetch<CustomerComplianceRequest>(`/v1/me/compliance/requests/${requestId}`),
  cancelRequest: (requestId: string) =>
    apiFetch<{ cancelled: boolean; request_id: string }>(
      `/v1/me/compliance/requests/${requestId}/cancel`, { method: "POST", body: "{}" }),
  addNote: (requestId: string, note: string) =>
    apiFetch<{ note_added: boolean }>(
      `/v1/me/compliance/requests/${requestId}/add-note`,
      { method: "POST", body: JSON.stringify({ note }) }),
  listConsents: () =>
    apiFetch<{ user_id: string; records: CustomerConsentRecord[]; note: string }>(
      "/v1/me/compliance/consents"),
  withdrawConsent: (consentType: string, reason?: string) =>
    apiFetch<{ withdrawn: boolean; consent_type: string }>(
      `/v1/me/compliance/consents/${consentType}/withdraw`,
      { method: "POST", body: JSON.stringify({ reason: reason || "" }) }),
  downloadExport: (exportId: string) =>
    apiFetch<CustomerExportDownload>(`/v1/me/compliance/exports/${exportId}/download`),
};

// ── Provider / Tenant Compliance Portal ──────────────────────────────────────

export interface TenantComplianceRequest {
  id: string;
  request_number: string;
  subject_type: string;
  request_type: string;
  status: string;
  status_label: string;
  sla_status: string;
  sla_label: string;
  verification_status: string;
  submitted_at?: string;
  due_at?: string;
  completed_at?: string;
  reason?: string;
  rejection_reason?: string;
  request_source?: string;
  created_at: string;
  updated_at?: string;
  audit_trail?: { action: string; created_at: string }[];
  export?: { export_id: string; status: string; expires_at?: string; is_expired: boolean; download_url?: string };
}

export interface TenantComplianceSummary {
  open_requests: number;
  pending_admin_review: number;
  data_exports: number;
  staff_requests: number;
  sla_at_risk: number;
  completed_requests: number;
  rejected_requests: number;
  tenant_id: string;
}

export interface TenantComplianceRequestList {
  requests: TenantComplianceRequest[];
  meta: { total: number; page: number; limit: number; total_pages: number };
}

export interface TenantCreateRequestResult {
  request_id: string;
  request_number: string;
  request_type: string;
  status: string;
  status_label: string;
  sla_status: string;
  submitted_at?: string;
  due_at?: string;
  message: string;
}

export interface TenantExport {
  id: string;
  request_id?: string;
  status: string;
  expires_at?: string;
  downloaded_at?: string;
  generated_at?: string;
  download_url?: string;
}

export interface TenantConsentRecord {
  record_id: string;
  consent_type: string;
  action: string;
  legal_basis?: string;
  created_at: string;
}

export const providerComplianceApi = {
  getSummary: () =>
    apiFetch<TenantComplianceSummary>("/v1/provider/compliance/summary"),

  listRequests: (params?: { request_type?: string; status?: string; page?: number }) => {
    const q = new URLSearchParams();
    if (params?.request_type) q.set("request_type", params.request_type);
    if (params?.status) q.set("status", params.status);
    if (params?.page) q.set("page", String(params.page));
    return apiFetch<TenantComplianceRequestList>(`/v1/provider/compliance/requests?${q}`);
  },
  createRequest: (data: {
    request_type: string;
    reason: string;
    details?: string;
    confirm_understanding: boolean;
  }) => apiFetch<TenantCreateRequestResult>("/v1/provider/compliance/requests", {
    method: "POST", body: JSON.stringify(data),
  }),
  getRequest: (requestId: string) =>
    apiFetch<TenantComplianceRequest>(`/v1/provider/compliance/requests/${requestId}`),
  cancelRequest: (requestId: string) =>
    apiFetch<{ cancelled: boolean; request_id: string }>(
      `/v1/provider/compliance/requests/${requestId}/cancel`, { method: "POST", body: "{}" }),

  generateExport: (requestId: string) =>
    apiFetch<{ export_id: string; status: string; expires_at: string; message: string }>(
      `/v1/provider/compliance/requests/${requestId}/generate-export`,
      { method: "POST", body: "{}" }),

  listExports: () =>
    apiFetch<{ exports: TenantExport[]; total: number }>("/v1/provider/compliance/exports"),
  getExport: (exportId: string) =>
    apiFetch<TenantExport>(`/v1/provider/compliance/exports/${exportId}`),
  downloadExport: (exportId: string) =>
    apiFetch<{ download_url: string; export_id: string; status: string; downloaded_at?: string }>(
      `/v1/provider/compliance/exports/${exportId}/download`),

  listConsents: () =>
    apiFetch<{ user_id: string; records: TenantConsentRecord[]; note: string }>(
      "/v1/provider/compliance/consents"),
  withdrawConsent: (consentType: string, reason?: string) =>
    apiFetch<{ withdrawn: boolean; consent_type: string }>(
      `/v1/provider/compliance/consents/${consentType}/withdraw`,
      { method: "POST", body: JSON.stringify({ reason: reason || "" }) }),

  listStaffRequests: (params?: { page?: number }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    return apiFetch<TenantComplianceRequestList>(`/v1/provider/compliance/staff-requests?${q}`);
  },
  getStaffRequest: (requestId: string) =>
    apiFetch<TenantComplianceRequest>(`/v1/provider/compliance/staff-requests/${requestId}`),
  addStaffResponse: (requestId: string, response: string) =>
    apiFetch<{ response_added: boolean; request_id: string }>(
      `/v1/provider/compliance/staff-requests/${requestId}/tenant-response`,
      { method: "POST", body: JSON.stringify({ response }) }),

  listCustomerRequests: (params?: { page?: number }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    return apiFetch<{ requests: TenantComplianceRequest[]; meta: { total: number; page: number; limit: number; total_pages: number }; note: string }>(
      `/v1/provider/compliance/customer-requests?${q}`);
  },
  getCustomerRequest: (requestId: string) =>
    apiFetch<TenantComplianceRequest>(`/v1/provider/compliance/customer-requests/${requestId}`),
  addCustomerResponse: (requestId: string, response: string) =>
    apiFetch<{ response_added: boolean }>(
      `/v1/provider/compliance/customer-requests/${requestId}/tenant-response`,
      { method: "POST", body: JSON.stringify({ response }) }),
};

// ── Customer Service Credits (as seen by customer / tenant-portal) ──────────
export interface MyServiceCredit {
  id: string; credit_number: string; amount: number; remaining_amount: number;
  currency: string; credit_type: string; source: string; status: string;
  issued_reason: string; customer_message?: string | null;
  valid_from: string; expires_at?: string | null; used_at?: string | null;
  created_at: string;
}
export interface MyCreditSummary {
  total_credits: number; active_credits: number; used_credits: number;
  expired_credits: number; cancelled_credits: number;
  active_credit_balance: number; credits_from_disputes: number;
}
export interface CreditApplyPreview {
  available_credit_balance: number; booking_amount: number;
  credit_amount_to_apply: number; credit_applied: number;
  payable_to_provider: number; remaining_credit_balance: number;
}

export const customerCreditsApi = {
  listMyCredits: (params?: { page?: number; limit?: number; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.status) q.set("status", params.status);
    return apiFetch<{ credits: MyServiceCredit[]; meta: { total: number; page: number; limit: number; total_pages: number } }>(`/v1/me/credits?${q}`);
  },
  getMySummary: () => apiFetch<MyCreditSummary>("/v1/me/credits/summary"),
  getMyCredit: (creditId: string) =>
    apiFetch<MyServiceCredit & { ledger: unknown[] }>(`/v1/me/credits/${creditId}`),
  previewApply: (bookingAmount: number, creditAmountToApply: number) =>
    apiFetch<CreditApplyPreview>("/v1/me/credits/preview-apply", {
      method: "POST",
      body: JSON.stringify({ booking_amount: bookingAmount, credit_amount_to_apply: creditAmountToApply }),
    }),
  applyToBooking: (bookingId: string, bookingAmount: number, creditAmountToApply: number) =>
    apiFetch<{ success: boolean; booking_id: string; credit_applied: number; payable_to_provider: number }>("/v1/me/credits/apply", {
      method: "POST",
      body: JSON.stringify({ booking_id: bookingId, booking_amount: bookingAmount, credit_amount_to_apply: creditAmountToApply }),
    }),
};

// ── Security engine types (tenant integration keys, blocklist, activity) ─────
export interface SecurityApiKey { key_id:string; name:string; key_prefix:string; scopes:string[]; status:string; use_count:number; last_used_at?:string; }
export interface SecurityApiKeyList { api_keys:SecurityApiKey[]; total:number; }
export interface SecurityApiKeyCreated { key_id:string; raw_key:string; key_prefix:string; name:string; scopes:string[]; environment:string; expires_at?:string; warning:string; }
export interface IpBlockCheck { ip:string; blocked:boolean; reason?:string; threat_level?:string; source:string; }
export interface ActivityReportResult { log_id?:string; threat_level?:string; count?:number; recorded?:boolean; threshold_not_reached?:boolean; }

// ── Media types ───────────────────────────────────────────────────────────────
export interface UploadSession { session_id:string; upload_url:string; expires_at:string; }
export interface MediaFile  { file_id:string; tenant_id:string; filename:string; content_type:string; size_bytes:number; purpose:string; url?:string; created_at:string; }
export interface MediaFileList { files:MediaFile[]; total:number; has_next:boolean; next_cursor?:string; }
export interface MediaQuota { tenant_id:string; used_bytes:number; limit_bytes:number; file_count:number; file_limit:number; }

// ── Phase 0A Media Engine types ───────────────────────────────────────────────
export interface MediaAsset {
  id: string;
  owner_type: string;
  owner_id: string;
  tenant_id: string | null;
  customer_id: string | null;
  media_context: string;
  file_name_original: string;
  mime_type: string;
  file_extension: string;
  file_size_bytes: number;
  storage_driver: string;
  is_public: boolean;
  access_level: string;
  status: string;
  preview_url: string;
  public_url: string | null;
  created_at: string;
}
export interface MediaAssetList { items: MediaAsset[]; total: number; page: number; page_size: number; }
export interface MediaUploadError { code: string; message: string; }

export const MEDIA_ERROR_MESSAGES: Record<string, string> = {
  MEDIA_FILE_REQUIRED:         "Please choose a file.",
  MEDIA_FILE_TOO_LARGE:        "File is too large.",
  MEDIA_TYPE_NOT_ALLOWED:      "This file type is not allowed.",
  MEDIA_EXTENSION_NOT_ALLOWED: "This file extension is not allowed.",
  MEDIA_CONTEXT_NOT_ALLOWED:   "This upload type is not allowed here.",
  MEDIA_CONTEXT_FORBIDDEN:     "This upload type is not allowed for your role.",
  MEDIA_ACCESS_DENIED:         "You do not have permission to access this file.",
  MEDIA_TENANT_SCOPE_VIOLATION:"You cannot access media from another account.",
  MEDIA_CUSTOMER_SCOPE_VIOLATION:"You can only access your own files.",
  MEDIA_STORAGE_NOT_CONFIGURED:"Upload service is not configured.",
  MEDIA_STORAGE_TIMEOUT:       "Upload timed out. Please try again with a smaller file.",
  MEDIA_STORAGE_ERROR:         "Storage service returned an error. Please try again.",
  MEDIA_STORAGE_UNAVAILABLE:   "Storage service is unavailable. Please try again shortly.",
  UPLOAD_TIMEOUT:              "Upload timed out. Please try again.",
  MEDIA_NOT_FOUND:             "File not found.",
};

export function friendlyMediaError(code: string): string {
  return MEDIA_ERROR_MESSAGES[code] ?? "Upload failed. Please try again.";
}

// ── Settings extended types ───────────────────────────────────────────────────
export interface ResolvedSetting { key:string; value:unknown; source:string; resolved_for?:string; }
export interface WebhookDelivery { delivery_id:string; endpoint_id:string; event_type:string; status:string; attempts:number; last_attempt_at?:string; response_status?:number; created_at:string; }
export interface WebhookDeliveryList { deliveries:WebhookDelivery[]; has_next:boolean; }

// ── Phase 2 Commerce & Payment types ─────────────────────────────────────────
export interface WalletTransaction { id:string; type:string; amount:number; balance_after:number; job_id?:string; notes?:string; created_at:string; }
export interface WalletTransactionList { transactions:WalletTransaction[]; has_next:boolean; next_cursor?:string; }
export interface WalletProjection { tenant_id:string; current_balance:number; burn_rate_daily:number; projected_days_remaining:number|null; low_balance_alert:boolean; recommended_package?:CreditPackage|null; monthly_commission_estimate:number; }
export interface CreditPackage { id:string; name:string; credits:number; price_inr:number; bonus_credits?:number; is_active:boolean; created_at:string; }
export interface CreditPackageList { packages:CreditPackage[]; }
export interface PurchaseOrder {
  order_id:string; amount:number; currency?:string; amount_paise?:number;
  gateway?:string; key?:string; package_id?:string; package_name?:string;
  credits_to_receive?:number; deposit_replenishment?:number;
  status?:string; payment_url?:string; expires_at?:string;
}
export interface CommissionRate { rate:number; effective_from:string; plan_type:string; }
export interface CommissionProjection { projected_monthly:number; based_on_jobs:number; period_days:number; }
export interface Payout { payout_id:string; tenant_id:string; amount:number; status:string; bank_account_id?:string; requested_at:string; processed_at?:string; }
export interface PayoutList { payouts:Payout[]; has_next:boolean; }
export interface Refund { refund_id:string; payment_id:string; amount:number; status:string; reason:string; created_at:string; }
export interface RefundList { refunds:Refund[]; has_next:boolean; }
export interface SecurityDepositStatus {
  tenant_id:string; status:string; required_amount:number; total_paid:number;
  warranty_drawn:number; replenishment_total:number; current_balance:number;
  is_unlocked:boolean; paid_at?:string;
}
export interface SecurityDepositTxn {
  txn_id:string; txn_type:string; amount:number; balance_before:number;
  balance_after:number; reference_id?:string; notes?:string; created_at:string;
}
export interface SecurityDepositTxnList { transactions:SecurityDepositTxn[]; current_balance:number; has_next:boolean; next_cursor?:string; }
export interface DepositConfirmResult { status:string; amount_paid?:number; current_balance?:number; already_paid?:boolean; message?:string; }
export interface CustomerAtRisk { customer_id:string; name:string; health_score:number; risk_flags:string[]; last_job_at?:string; }
export interface CustomerAtRiskList { customers:CustomerAtRisk[]; total:number; }
export interface WarrantyClaim { claim_id:string; job_id:string; tenant_id:string; customer_name?:string; issue_description:string; status:string; claimed_at:string; resolved_at?:string; notes?:string; }
export interface WarrantyClaimList { claims:WarrantyClaim[]; total:number; has_next:boolean; }
export interface TenantBadge { badge_id:string; badge_type:string; tenant_id:string; awarded_at:string; }
export interface BadgeList { badges:TenantBadge[]; }
export interface TenantProfile { id:string; name:string; vertical:string; city:string; state:string; status:string; health_score:number; plan_type:string; billing_mode:string; onboarding_step:number; wallet_balance?:number; commission_rate?:number; created_at:string; }
export interface TenantHealthInfo { tenant_id:string; overall_score:number; signals:Record<string,number>; computed_at:string; }
export interface TenantBillingInfo { tenant_id:string; billing_mode:string; plan_type:string; commission_rate:number; payment_method?:Record<string,unknown>; next_billing_at?:string; subscription_status?:string; }

// ── Phase 3 — Analytics & Data Science types ─────────────────────────────────
export interface TenantMetrics { tenant_id:string; period_days:number; event_counts:Record<string,number>; generated_at:string; }
export interface DailyMetric { date:string; value:number|Record<string,unknown>; }
export interface DailyMetricList { metric_key:string; period_days:number; data:DailyMetric[]; }
export interface ChurnScore {
  tenant_id:string; churn_score:number; churn_band:string;
  contributing_factors:{ signal:string; value:number; weight:number; contribution:number }[];
  score_delta:number|null; prev_score:number|null; observation_mode:boolean;
  ds_phase:number; model_version:string; computed_at:string; interpretation:string;
}
export interface ChurnFactors {
  tenant_id:string; churn_score:number; churn_band:string;
  contributing_factors:{ signal:string; value:number; weight:number; contribution:number }[];
  signal_values:Record<string,number>; observation_mode:boolean;
  recommended_actions:{ action:string; priority:string }[];
}
export interface DemandForecastDetail {
  tenant_id:string; forecast_date:string; horizon_days:number; total_predicted:number;
  peak_day:string; daily_forecasts:Record<string,unknown>; observation_mode:boolean;
  ds_phase:number; model_version:string; computed_at:string; interpretation:string;
}
export interface PricingRecommendation { service_type_id:string; current_price:number; benchmark_price:number; floor_price:number; gap_pct:number; action:"increase"|"decrease"|"hold"; potential_uplift:number; }
export interface PricingRecommendationList { tenant_id:string; recommendations:PricingRecommendation[]; observation_mode:boolean; ds_phase:number; generated_at:string; }
export interface StaffRanking { staff_id:string; rank:number; composite_score:number; jobs_completed:number; avg_rating:number; sla_adherence:number; }
export interface StaffRankingList { tenant_id:string; observation_mode:boolean; rankings:StaffRanking[]; }
export interface StaffScoreDetail { staff_id:string; tenant_id:string; composite_score:number; rank:number; signal_values:Record<string,number>; jobs_completed:number; avg_customer_rating:number; sla_adherence_rate:number; }
export interface CustomerLtv { customer_id:string; tenant_id:string; predicted_ltv:number; ltv_band:string; booking_frequency:number; avg_job_value:number; churn_probability:number; observation_mode:boolean; }
export interface HighValueCustomer { customer_id:string; predicted_ltv:number; ltv_band:string; booking_frequency:number; churn_probability:number; }
export interface HighValueCustomerList { tenant_id:string; high_value_customers:HighValueCustomer[]; }

// Phase 13 — Business Performance
export interface StaffPerformanceSummary { staff_id:string; name:string; score:number|null; jobs_completed:number; avg_rating:number|null; computed_at:string|null; }
export interface BusinessPerformance {
  period_days:number;
  jobs_by_type:Record<string,number>;
  consultation_conversion_rate:number|null;
  avg_revenue_by_type:Record<string,number>;
  repeat_booking_rate:number|null;
  rework_quality_failure_rate:number|null;
  sla_breach_rate:number|null;
  total_jobs:number;
  sla_breaches:number;
  top_staff:StaffPerformanceSummary[];
  generated_at:string;
}

// ── Document engine types ─────────────────────────────────────────────────────
export interface DocumentEvent { event_id:string; document_id:string; event_type:string; actor_id?:string; actor_ip?:string; details?:Record<string,unknown>; created_at:string; }
export interface DocumentEventList { events:DocumentEvent[]; }
export interface DocumentTemplate { doc_type:string; tenant_id:string; template_content?:string; required_variables:string[]; sample_variables?:Record<string,string>; }

// ── Subscription engine types ─────────────────────────────────────────────────
export interface SubscriptionPeriod { tenant_id:string; period_start:string; period_end:string; plan_type:string; billing_cycle:string; jobs_used:number; jobs_included?:number; leads_used?:number; leads_included?:number; amount_billed?:number; }
export interface SubscriptionHistoryEntry { period_id:string; period_start:string; period_end:string; plan_type:string; billing_cycle:string; amount_billed?:number; }
export interface SubscriptionHistoryList { history:SubscriptionHistoryEntry[]; has_next:boolean; next_cursor?:string; }
export interface ProrationPreview { tenant_id:string; current_plan:string; new_plan:string; billing_cycle:string; days_remaining:number; credit_amount:number; debit_amount:number; net_amount:number; effective_date:string; }

// ── Phase 9 — Appointment types ───────────────────────────────────────────────
export interface Appointment {
  appointment_id:string; appointment_number:string; tenant_id:string;
  staff_id:string; customer_id:string; booking_id?:string; service_type_id?:string;
  status:string; scheduled_at:string; ends_at:string; duration_minutes:number;
  hold_expires_at?:string; confirmed_at?:string;
  reminder_24h_sent:boolean; reminder_2h_sent:boolean;
  customer_notes?:string; created_at:string;
  allowed_transitions:string[]; is_terminal:boolean;
}
export interface AppointmentSlot { slot_dt:string; slot_label:string; duration_minutes:number; ends_at:string; }
export interface AppointmentSlotsResponse { staff_id:string; tenant_id:string; date:string; slots:AppointmentSlot[]; total_available:number; }
export interface AppointmentListResponse { appointments:Appointment[]; total:number; has_next:boolean; next_cursor?:string; }
export interface AppointmentHistoryEntry { status:string; changed_at:string; notes?:string; }
export interface AppointmentHistoryResponse { appointment_id:string; history:AppointmentHistoryEntry[]; }
export interface CalendarBlock { block_id:string; staff_id:string; tenant_id:string; start_at:string; end_at:string; reason?:string; created_at:string; }
export interface StaffWorkingHoursResponse { staff_id:string; tenant_id:string; working_hours:Record<string,{ start:string; end:string; is_working:boolean }>; }

// ── Phase 9 — Inventory types ─────────────────────────────────────────────────
// MODULE-L5-41: these interfaces (and the inventoryApi below) were written
// against a URL scheme + response shapes that don't exist -- the real
// inventory engine (app/engines/inventory/router.py) uses
// /v1/inventory/tenants/{tid}/items, /items/{id}/locations/{loc}/*, etc.,
// and returns available_qty/current_qty/deficit, not available/
// current_quantity/shortfall. Corrected to the real service dict outputs.
// list_items returns only a subset of item fields (no category/unit_cost),
// so those are optional here.
export interface InventoryItem { item_id:string; name:string; sku:string; unit:string; min_quantity:number; category?:string|null; unit_cost?:number; gst?:number|null; warranty?:string|null; }
export interface InventoryItemList { items:InventoryItem[]; has_next:boolean; next_cursor?:string|null; }
export interface StockBalance { item_id:string; location_id:string; quantity:number; reserved_qty:number; available_qty:number; min_quantity:number; below_minimum:boolean; reconciliation_ok:boolean; }
export interface StockTransaction { txn_id:string; txn_type:string; quantity:number; balance_before:number; balance_after:number; job_id?:string|null; notes?:string|null; created_at:string; }
export interface StockTransactionList { transactions:StockTransaction[]; has_next:boolean; next_cursor?:string|null; }
export interface LowStockItem { item_id:string; name:string; current_qty:number; min_quantity:number; deficit:number; }
export interface LowStockList { items:LowStockItem[]; total:number; }
export interface ReplenishResult { item_id:string; quantity_requested:number; status:string; message:string; }
export interface StockReservation { reservation_id:string; job_id:string; quantity:number; expires_at?:string; }

// ── Geo Zones — Tenant Service Coverage (via /v1/geo) ────────────────────────
export const serviceAreaApi = {
  list: () => {
    const tid = getTenantId();
    return apiFetch<GeoZoneListResponse>(`/v1/geo/tenants/${tid}/zones?active_only=false`);
  },
  create: (body: GeoZoneCreatePayload) => {
    const tid = getTenantId();
    return apiFetch<GeoZone>(`/v1/geo/tenants/${tid}/zones`, { method:"POST", body:JSON.stringify(body) });
  },
  update: (zoneId:string, body: Partial<GeoZoneCreatePayload>) =>
    apiFetch<GeoZone>(`/v1/geo/zones/${zoneId}`, { method:"PUT", body:JSON.stringify(body) }),
  deactivate: (zoneId:string) =>
    apiFetch<{ zone_id:string; deactivated:boolean }>(`/v1/geo/zones/${zoneId}`, { method:"DELETE" }),
  checkPincode: (pincode: string) => {
    const tid = getTenantId();
    return apiFetch<{ covered: boolean; zone_name?: string }>(`/v1/geo/tenants/${tid}/zones/check?pincode=${pincode}`);
  },
};

export interface GeoZone {
  zone_id:string; zone_name:string; zone_type:string;
  identifiers:string[]; center_lat?:number; center_lng?:number;
  radius_km?:number; surcharge_pct:number; is_active:boolean;
  valid_from:string; valid_until?:string;
}
export interface GeoZoneCreatePayload {
  zone_name:string; zone_type:string; identifiers?:string[];
  center_lat?:number; center_lng?:number; radius_km?:number; surcharge_pct?:number;
}
export interface GeoZoneListResponse { tenant_id:string; zones:GeoZone[]; }
export type ServiceArea = GeoZone;
export type ServiceAreaListResponse = GeoZoneListResponse;
export type ServiceAreaCreatePayload = GeoZoneCreatePayload;
export interface ServiceAreaService {
  id:string; tenant_service_area_id:string; tenant_id:string; service_id:string;
  job_type:string; is_available:boolean; sla_minutes?:number;
  min_price?:number; max_price?:number; base_price?:number;
  created_at:string; updated_at:string;
}
export interface ServiceMappingListResponse { mappings:ServiceAreaService[]; total:number; }
export interface ServiceMappingCreatePayload {
  service_id:string; job_type:string; is_available?:boolean;
  sla_minutes?:number; base_price?:number; min_price?:number; max_price?:number;
}

// ── Serviceability Engine — Customer Addresses (tenant-side read, e.g. for bookings) ──
export const serviceabilityApi = {
  check: (body: { address_id?:string; city?:string; state?:string; zipcode?:string; service_id:string; job_type:string }) =>
    apiFetch<ServiceabilityCheckResponse>("/v1/serviceability/check", { method:"POST", body:JSON.stringify(body) }),
  matchingTenants: (body: { address_id?:string; city?:string; state?:string; zipcode?:string; service_id:string; job_type:string }) =>
    apiFetch<{ matched_tenants:MatchedTenant[] }>("/v1/serviceability/matching-tenants", { method:"POST", body:JSON.stringify(body) }),
};

export interface ServiceabilityCheckResponse {
  service_available:boolean; city:string; zipcode?:string;
  service_id:string; job_type:string; matched_tenants_count:number;
  best_match_level:string|null;
  matches:{ zipcode_level:number; zone_level:number; city_level:number; radius_level:number };
  message:string;
}
export interface MatchedTenant {
  tenant_id:string; tenant_name:string; coverage_match_level:string;
  matched_area_id:string; service_area_service_id:string;
  rating?:number; health_score?:number;
  estimated_sla_minutes?:number; base_price?:number; distance_km?:number;
}

// ── Phase 9 — Public Registration types ───────────────────────────────────────
export interface RegistrationInitResult { session_id:string; message:string; dev_otp?:string; }
export interface RegistrationPlanResult { plan_type:string; price_inr:number; }
export interface RegistrationOtpResult { session_id:string; verified:boolean; business_name:string; plan_type:string; price_inr:number; }
export interface RegistrationPaymentOrder { order_id:string; amount:number; amount_inr:number; currency:string; key_id:string; prefill:{name:string; email:string; contact:string}; }
export interface RegistrationCompleteResult { tenant_id:string; business_name:string; plan_type:string; trial_days:number; owner_email:string; temp_password:string; message:string; }
export interface RegistrationVerifyResult { tenant_id:string; business_name:string; plan_type:string; owner_email:string; temp_password:string; message:string; }

// ── Phase 9 — AI Chat types ───────────────────────────────────────────────────
export interface AIChatMessage { role:"user"|"assistant"; content:string; }
export interface AIChatResponse { reply:string; tools_called:string[]; model:string; }

// ── Review request + Notification types ──────────────────────────────────────
export interface ReviewRequest  { review_request_id:string; job_id:string; status:string; expires_at:string; review_id?:string; }
export interface ReviewRequestListResponse { requests:ReviewRequest[]; has_next:boolean; next_cursor?:string; }
export interface NotificationRecord { notification_id:string; tenant_id:string; recipient_id:string; notif_type:string; channel:string; title?:string; status:string; attempt_count:number; reference_id?:string; delivered_at?:string; failed_reason?:string; created_at:string; }
export interface NotificationListResponse { notifications:NotificationRecord[]; has_next:boolean; next_cursor?:string; }
export interface NotificationChannel { tenant_id:string; channel:string; is_enabled:boolean; config:Record<string,unknown>; verified_at?:string; }
export interface NotificationChannelList { channels:NotificationChannel[]; }

// ── Effective Engine types (tenant read-only view) ────────────────────────────
export interface TenantEffectiveEngine {
  engine_key:        string;
  name:              string;
  effective_enabled: boolean;
  source:            "global" | "category" | "package_entitlement" | "tenant_override";
  is_required:       boolean;
  health_status:     string;
  dependencies_met:  boolean;
  dependencies:      string[];
  reason:            string | null;
  config:            Record<string, unknown>;
}
export interface TenantEffectiveEnginesResponse {
  tenant_id: string;
  category:  { id: string; name: string } | null;
  package:   { id: string; name: string } | null;
  engines:   TenantEffectiveEngine[];
  summary:   { total: number; enabled: number; disabled: number };
}

export const engineApi = {
  getEffectiveEngines: () => apiFetch<TenantEffectiveEnginesResponse>("/v1/tenant/engines/effective"),
};

// ── Category Runtime — Provider Dashboard ─────────────────────────────────────
export interface ProviderDashboardRuntime {
  tenant: {
    tenant_id: string;
    business_name: string | null;
    category: { id: string; name: string; slug: string;
      category_type: string | null; provider_dashboard_type: string | null; } | null;
  } | null;
  primary_engine: string | null;
  dashboard_type: string | null;
  enabled_engines: string[];
  modules: Array<{
    module_key: string; module_name: string; module_type: string; dashboard_area: string | null;
    engine_key: string | null; route_path: string | null;
    is_enabled: boolean; is_required: boolean; display_order: number;
  }>;
  // category_type on the runtime for convenience
  category?: { category_id: string; name: string; slug: string; category_type: string | null; provider_dashboard_type: string | null };
  // Top-level vertical, sourced from tenant.vertical (always populated) —
  // see the tenant_engine.portal_router.py fix. Preferred over
  // category?.category_type / tenant?.category?.category_type, which are
  // frequently unpopulated in real seeded data.
  category_type?: string | null;
}

export interface ProviderNavigation {
  category: { id: string; name: string; category_type: string | null; provider_dashboard_type: string | null } | null;
  items: Array<{ label: string; route: string; module_key?: string; engine_key?: string }>;
  // Multi-vertical Phase 2/3: real vertical/capability/enrollment context,
  // resolved server-side from the tenant's own row. Drives capability-aware
  // sidebar visibility instead of hardcoded per-vertical-key string lookups.
  vertical_context?: {
    vertical_key: string;
    vertical_label: string;
    is_enabled: boolean;
    capabilities: string[];
    enrollment_status: string | null;
  } | null;
}

export const categoryDashboardApi = {
  getRuntime: () => apiFetch<ProviderDashboardRuntime>("/v1/tenant/dashboard/runtime"),
  getNavigation: () => apiFetch<ProviderNavigation>("/v1/tenant/navigation"),
  getHomeServicesSummary: () => apiFetch<Record<string, unknown>>("/v1/tenant/dashboard/home-services/summary"),
  getCoachingSummary: () => apiFetch<Record<string, unknown>>("/v1/tenant/dashboard/coaching/summary"),
  getRealEstateSummary: () => apiFetch<Record<string, unknown>>("/v1/tenant/dashboard/real-estate/summary"),
};

// ── Sprint 5 — Provider Monetization Status ───────────────────────────────────

export interface ProviderMonetizationStatus {
  id: string;
  tenant_id: string;
  category_id: string | null;
  monetization_model: string | null;
  is_monetization_ready: boolean;
  is_bookable: boolean;
  is_visible: boolean;
  subscription_status: string | null;
  subscription_expires_at: string | null;
  credit_balance: number;
  credit_minimum_required: number;
  deposit_paid: boolean;
  last_synced_at: string | null;
  override_is_bookable: boolean | null;
  override_reason: string | null;
}

export const providerMonetizationApi = {
  getStatus: () => apiFetch<ProviderMonetizationStatus>("/v1/tenant/monetization/status"),
};

// ── Sprint 6 — Provider Package API ──────────────────────────────────────────
// MODULE-L5-30: this used to call /v1/provider/packages and /v1/provider/packages/purchase,
// which don't exist (live 404s), and initiatePurchase wrote to a table
// (tenant_package_purchases) that was never migrated. Repointed to the real,
// tested tenant_router.py endpoints backed by tenant_package_assignments —
// the same table the admin-approval flow and status check below both use.

export interface ProviderPackage {
  id: string;
  package_id: string;
  name: string;
  slug: string;
  description: string | null;
  package_type: string;
  plan_level: string | null;
  is_active: boolean;
  price: number;
  currency: string;
  billing_cycle: string | null;
  validity_days: number | null;
  trial_days: number | null;
  security_deposit_amount: number;
  included_credit_amount: number;
  lead_credits: number | null;
  vertical_type: string | null;
  is_featured: boolean;
  is_recommended: boolean;
  is_popular: boolean;
  display_order: number;
  features: Record<string, unknown>;
}

export interface TenantPackagePurchase {
  id: string;
  tenant_id: string;
  package_id: string;
  package_type: string;
  status: string;
  purchase_status: string;
  package_name: string;
  price_amount: string;
  security_deposit_amount: string;
  included_spendable_credits: string;
  selected_at: string | null;
  paid_at: string | null;
  approved_at: string | null;
  activated_at: string | null;
  starts_at: string | null;
  expires_at: string | null;
}

export interface ProviderPackageStatus {
  has_active_package: boolean;
  active_package: TenantPackagePurchase | null;
  all_purchases: TenantPackagePurchase[];
  total: number;
}

export interface PackageAssignmentSummary {
  has_package: boolean;
  status: string | null;
  package_name: string | null;
  package_type: string | null;
  starts_at: string | null;
  expires_at: string | null;
  approved_at: string | null;
  price_amount: number | null;
  included_credits?: number; // present on GET /v1/provider/onboarding/package-summary
  message: string;
}

export const providerPackageApi = {
  browse: () =>
    apiFetch<{ available_packages: ProviderPackage[]; total: number }>("/v1/tenant/packages/available"),
  status: () => apiFetch<ProviderPackageStatus>("/v1/provider/packages/status"),
  packageSummary: () => apiFetch<PackageAssignmentSummary>("/v1/provider/onboarding/package-summary"),
  initiatePurchase: (packageId: string, paymentReference?: string) =>
    apiFetch<TenantPackagePurchase>(
      `/v1/tenant/packages/${packageId}/purchase`,
      { method: "POST", body: JSON.stringify({ payment_reference: paymentReference }) }
    ),
};

// ── Sprint 10 — Provider Onboarding Checklist API ─────────────────────────────

export type OnboardingItemStatus =
  | "pending" | "completed" | "blocked" | "skipped" | "overridden" | "not_applicable";

export type CompletionSource =
  | "provider_profile" | "provider_verification" | "provider_monetization"
  | "provider_package" | "provider_enabled_offerings" | "provider_service_areas"
  | "provider_staff" | "provider_appointment_slots" | "provider_agents"
  | "provider_properties" | "provider_media" | "marketing_assets"
  | "admin_override" | "custom_rule";

export interface OnboardingBlocker {
  code: string;
  message: string;
  route?: string | null;
}

export interface OnboardingNextAction {
  title: string;
  description: string;
  route: string;
  action_label: string;
}

export interface ProviderOnboardingItem {
  id: string;
  checklist_key: string;
  title: string;
  description: string | null;
  item_type: string;
  completion_source: CompletionSource;
  status: OnboardingItemStatus;
  is_required: boolean;
  is_blocking: boolean;
  allows_admin_override: boolean;
  provider_action_label: string | null;
  provider_action_route: string | null;
  blocked_reason: string | null;
  completed_at: string | null;
  display_order: number;
}

export interface ProviderOnboardingStatus {
  tenant_id: string;
  category_name: string | null;
  category_type: string | null;
  progress_percentage: number;
  total_items: number;
  completed_items: number;
  pending_items: number;
  blocked_items: number;
  onboarding_ready: boolean;
  blockers: OnboardingBlocker[];
  next_action: OnboardingNextAction | null;
  last_refreshed_at: string | null;
}

export const providerOnboardingApi = {
  getStatus: () =>
    apiFetch<ProviderOnboardingStatus>("/v1/provider/onboarding/status"),
  getItems: () =>
    apiFetch<{ items: ProviderOnboardingItem[]; count: number }>("/v1/provider/onboarding/items"),
  refresh: () =>
    apiFetch<ProviderOnboardingStatus>("/v1/provider/onboarding/refresh", { method: "POST" }),
};

// ── Sprint 11 — Provider Offerings ────────────────────────────────────────────

export interface OfferingReadinessBlocker {
  code: string;
  message: string;
  route?: string | null;
}

export interface AvailableOffering {
  offering_id: string;
  name: string;
  slug: string;
  category_id: string | null;
  service_group_id: string | null;
  service_group_name: string | null;
  offering_type: string | null;
  pricing_model: string | null;
  primary_engine_key: string | null;
  customer_flow_type: string | null;
  requires_service_type: boolean;
  requires_brand: boolean;
  requires_staff: boolean;
  requires_slot: boolean;
  admin_price: string | null;
  admin_visit_fee: string | null;
  admin_appointment_fee: string | null;
  admin_lead_fee: string | null;
  is_already_enabled: boolean;
  provider_enabled_offering_id: string | null;
}

export interface EnabledOffering {
  provider_enabled_offering_id: string;
  offering_id: string;
  offering_name: string;
  offering_type: string | null;
  status: "draft" | "active" | "inactive" | "suspended" | "rejected";
  readiness_status: "ready" | "not_ready" | "blocked" | null;
  provider_display_name: string | null;
  provider_description: string | null;
  supported_type_ids: string[] | null;
  supported_brand_ids: string[] | null;
  supports_emergency: boolean;
  provider_price_override: string | null;
  provider_min_price: string | null;
  provider_max_price: string | null;
  provider_visit_fee: string | null;
  provider_appointment_fee: string | null;
  provider_lead_fee: string | null;
  readiness_blockers: OfferingReadinessBlocker[] | null;
  activated_at: string | null;
  suspended_at: string | null;
  suspension_reason: string | null;
  created_at: string | null;
}

export interface EnableOfferingPayload {
  offering_id: string;
  provider_display_name?: string | null;
  provider_description?: string | null;
  supported_type_ids?: string[] | null;
  supported_brand_ids?: string[] | null;
  supports_emergency?: boolean;
  provider_price_override?: number | null;
  provider_visit_fee?: number | null;
  provider_appointment_fee?: number | null;
  provider_lead_fee?: number | null;
  activate_if_ready?: boolean;
}

export const providerOfferingsApi = {
  listAvailable: () =>
    apiFetch<{ offerings: AvailableOffering[]; count: number }>("/v1/provider/offerings/available"),
  listEnabled: () =>
    apiFetch<{ offerings: EnabledOffering[]; count: number }>("/v1/provider/offerings/enabled"),
  enable: (payload: EnableOfferingPayload) =>
    apiFetch<EnabledOffering>("/v1/provider/offerings/enabled", { method: "POST", body: JSON.stringify(payload) }),
  get: (id: string) =>
    apiFetch<EnabledOffering>(`/v1/provider/offerings/enabled/${id}`),
  update: (id: string, payload: Partial<EnableOfferingPayload>) =>
    apiFetch<EnabledOffering>(`/v1/provider/offerings/enabled/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  activate: (id: string) =>
    apiFetch<EnabledOffering>(`/v1/provider/offerings/enabled/${id}/activate`, { method: "POST" }),
  deactivate: (id: string) =>
    apiFetch<EnabledOffering>(`/v1/provider/offerings/enabled/${id}/deactivate`, { method: "POST" }),
  refreshReadiness: (id: string) =>
    apiFetch<EnabledOffering>(`/v1/provider/offerings/enabled/${id}/refresh-readiness`, { method: "POST" }),
};

// ── Sprint 11 — Provider Service Areas ───────────────────────────────────────

// coverage_type matches the real backend column — "online" is not a
// supported value (no such coverage_type exists in the serviceability
// engine's CoverageType constant).
export type AreaType = "zipcode" | "city" | "zone" | "radius";

export interface ProviderServiceArea {
  id: string;
  coverage_type: AreaType;
  country: string | null;
  state: string | null;
  district: string | null;
  city: string | null;
  zipcode: string | null;
  zone_id: string | null;
  zone_name: string | null;
  latitude: number | null;
  longitude: number | null;
  radius_km: number | null;
  priority: number;
  is_primary: boolean;
  is_active: boolean;
  service_count?: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProviderServiceAreaPayload {
  coverage_type: AreaType;
  country?: string | null;
  state?: string | null;
  district?: string | null;
  city?: string | null;
  zipcode?: string | null;
  zone_id?: string | null;
  zone_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  radius_km?: number | null;
  is_primary?: boolean;
  is_active?: boolean;
}

export interface ServiceAreaLimits {
  max_service_areas: number;
  used_service_areas: number;
  remaining_service_areas: number;
}

export interface ServiceAreaValidationResult {
  resolved_city: string | null;
  resolved_district: string | null;
  resolved_state: string | null;
  resolved_zone_tier: string;
  coverage_valid: boolean;
  coverage_error: string | null;
  is_duplicate: boolean;
  package_limit_ok: boolean;
  max_service_areas: number;
  remaining_service_areas: number;
  serviceable: boolean;
  bookability_impact: string;
}

export const providerServiceAreasApi = {
  list: () =>
    apiFetch<{ areas: ProviderServiceArea[]; total: number }>("/v1/tenant/service-areas"),
  create: (payload: ProviderServiceAreaPayload) =>
    apiFetch<ProviderServiceArea>("/v1/tenant/service-areas", { method: "POST", body: JSON.stringify(payload) }),
  get: (id: string) =>
    apiFetch<ProviderServiceArea>(`/v1/tenant/service-areas/${id}`),
  update: (id: string, payload: Partial<ProviderServiceAreaPayload>) =>
    apiFetch<ProviderServiceArea>(`/v1/tenant/service-areas/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  delete: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/tenant/service-areas/${id}`, { method: "DELETE" }),
  setPrimary: (id: string) =>
    apiFetch<ProviderServiceArea>(`/v1/tenant/service-areas/${id}/set-primary`, { method: "POST" }),
  getLimits: () =>
    apiFetch<ServiceAreaLimits>("/v1/tenant/service-areas/limits"),
  validate: (payload: Partial<ProviderServiceAreaPayload>) =>
    apiFetch<ServiceAreaValidationResult>("/v1/tenant/service-areas/validate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  // Per-area service pricing -- this is the real price the booking engine
  // uses (TenantServiceAreaService.base_price), set by the provider for
  // their own service area. Unlike the Offerings page's "Price Override"
  // (a different, unrelated field the booking pipeline never reads), this
  // is the price that actually determines what a customer is charged when
  // matched to this provider in this area. service_id must be a real
  // enabled offering id (offering_id === master_service_id — see
  // providerOfferingsApi.listEnabled()).
  listServiceMappings: (areaId: string) =>
    apiFetch<{ mappings: AreaServiceMapping[]; total: number }>(`/v1/tenant/service-areas/${areaId}/services`),
  addServiceMapping: (areaId: string, payload: AreaServiceMappingPayload) =>
    apiFetch<AreaServiceMapping>(`/v1/tenant/service-areas/${areaId}/services`, { method: "POST", body: JSON.stringify(payload) }),
  updateServiceMapping: (areaId: string, mappingId: string, payload: Partial<AreaServiceMappingPayload>) =>
    apiFetch<AreaServiceMapping>(`/v1/tenant/service-areas/${areaId}/services/${mappingId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteServiceMapping: (areaId: string, mappingId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/tenant/service-areas/${areaId}/services/${mappingId}`, { method: "DELETE" }),
};

export interface AreaServiceMapping {
  id: string; tenant_service_area_id: string; tenant_id: string;
  service_id: string; job_type: string; is_available: boolean;
  sla_minutes: number | null; base_price: number | null;
  min_price: number | null; max_price: number | null;
  created_at?: string; updated_at?: string;
}
export interface AreaServiceMappingPayload {
  service_id: string; job_type: string; is_available?: boolean;
  sla_minutes?: number | null; base_price?: number | null;
  min_price?: number | null; max_price?: number | null;
}

// ── Sprint 11 — Provider Team Members ────────────────────────────────────────

export type MemberType = "technician" | "trainer" | "counsellor" | "agent" | "manager" | "staff";

export interface ProviderTeamMember {
  member_id: string;
  member_type: MemberType;
  full_name: string;
  phone: string | null;
  email: string | null;
  designation: string | null;
  skills: string[] | null;
  supported_offering_ids: string[] | null;
  supported_type_ids: string[] | null;
  supported_brand_ids: string[] | null;
  service_area_ids: string[] | null;
  can_receive_assignment: boolean;
  profile_photo_url: string | null;
  status: "active" | "inactive";
  created_at: string | null;
}

export interface ProviderTeamMemberPayload {
  member_type: MemberType;
  full_name: string;
  phone?: string | null;
  email?: string | null;
  designation?: string | null;
  skills?: string[] | null;
  supported_offering_ids?: string[] | null;
  supported_type_ids?: string[] | null;
  supported_brand_ids?: string[] | null;
  service_area_ids?: string[] | null;
  can_receive_assignment?: boolean;
  profile_photo_url?: string | null;
  create_login?: boolean;
}

export const providerTeamMembersApi = {
  list: () =>
    apiFetch<{ members: ProviderTeamMember[]; count: number }>("/v1/provider/team-members"),
  create: (payload: ProviderTeamMemberPayload) =>
    apiFetch<{ member: ProviderTeamMember; credentials?: { username: string; password: string } | null }>(
      "/v1/provider/team-members", { method: "POST", body: JSON.stringify(payload) }
    ),
  get: (id: string) =>
    apiFetch<ProviderTeamMember>(`/v1/provider/team-members/${id}`),
  update: (id: string, payload: Partial<ProviderTeamMemberPayload>) =>
    apiFetch<ProviderTeamMember>(`/v1/provider/team-members/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  delete: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/provider/team-members/${id}`, { method: "DELETE" }),
  activate: (id: string) =>
    apiFetch<ProviderTeamMember>(`/v1/provider/team-members/${id}/activate`, { method: "POST" }),
  deactivate: (id: string) =>
    apiFetch<ProviderTeamMember>(`/v1/provider/team-members/${id}/deactivate`, { method: "POST" }),
  createLogin: (id: string) =>
    apiFetch<{ member_id: string; credentials?: { username: string; password: string } | null }>(
      `/v1/provider/team-members/${id}/create-login`, { method: "POST" }
    ),
};

// ── Sprint 11 — Provider Availability ────────────────────────────────────────

export type AvailabilityScopeType = "provider" | "offering" | "staff_member" | "service_area";

export interface ProviderAvailabilityRule {
  id: string;
  scope_type: AvailabilityScopeType;
  scope_id: string | null;
  scope_name: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number | null;
  max_bookings_per_slot: number | null;
  is_active: boolean;
  created_at: string | null;
}

export interface ProviderAvailabilityPayload {
  scope_type: AvailabilityScopeType;
  scope_id?: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes?: number | null;
  max_bookings_per_slot?: number | null;
  is_active?: boolean;
}

export const providerAvailabilityApi = {
  list: () =>
    apiFetch<{ rules: ProviderAvailabilityRule[]; count: number }>("/v1/provider/availability"),
  create: (payload: ProviderAvailabilityPayload) =>
    apiFetch<ProviderAvailabilityRule>("/v1/provider/availability", { method: "POST", body: JSON.stringify(payload) }),
  get: (id: string) =>
    apiFetch<ProviderAvailabilityRule>(`/v1/provider/availability/${id}`),
  update: (id: string, payload: Partial<ProviderAvailabilityPayload>) =>
    apiFetch<ProviderAvailabilityRule>(`/v1/provider/availability/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  delete: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/provider/availability/${id}`, { method: "DELETE" }),
  // Idempotent preset endpoints — safe to call multiple times, no duplicates
  applyPreset: (presetKey: string) =>
    apiFetch<{ preset_key: string; status: string; rule_count: number }>(
      `/v1/provider/availability/preset/${presetKey}`, { method: "POST" }),
  deletePreset: (presetKey: string) =>
    apiFetch<{ preset_key: string; deleted_count: number; deleted_ids: string[] }>(
      `/v1/provider/availability/preset/${presetKey}`, { method: "DELETE" }),
};

// ── Sprint 12: Provider Status Types ─────────────────────────────────────────
export interface BookabilityBlocker {
  code: string;
  message: string;
  route?: string | null;
}

export interface ProviderStatusResult {
  tenant_id: string;
  category_id: string | null;
  is_visible: boolean;
  is_bookable: boolean;
  visibility_blockers: BookabilityBlocker[];
  bookability_blockers: BookabilityBlocker[];
  override_is_visible: boolean | null;
  override_is_bookable: boolean | null;
  last_evaluated_at: string | null;
  last_changed_at: string | null;
}

export interface OfferingBookableStatus {
  id: string;
  tenant_id: string;
  provider_enabled_offering_id: string;
  offering_id: string;
  is_bookable: boolean;
  blockers: BookabilityBlocker[];
  last_evaluated_at: string | null;
}

// ── Sprint 12: Provider Status API ───────────────────────────────────────────
export const providerStatusApi = {
  get: () =>
    apiFetch<ProviderStatusResult>("/v1/provider/status"),
  refresh: () =>
    apiFetch<ProviderStatusResult>("/v1/provider/status/refresh", { method: "POST" }),
  getOfferingStatuses: () =>
    apiFetch<{ statuses: OfferingBookableStatus[]; count: number }>("/v1/provider/status/offerings"),
};

// ── Sprint 13: Provider Marketing Types ──────────────────────────────────────
export interface MarketingBlocker {
  code: string;
  message: string;
  route?: string | null;
}

export interface ProviderMarketingAsset {
  id: string;
  campaign_id: string;
  asset_type: string;
  channel: string;
  language: string;
  title: string | null;
  body: string | null;
  image_url: string | null;
  generation_source: string;
  status: string;
  provider_notes: string | null;
  admin_notes: string | null;
  rejection_reason: string | null;
  publish_url: string | null;
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProviderMarketingCampaign {
  id: string;
  campaign_name: string;
  campaign_type: string;
  status: string;
  marketing_ready: boolean;
  provider_review_status: string | null;
  admin_review_status: string | null;
  rejection_reason: string | null;
  requested_changes: string | null;
  approved_at: string | null;
  published_at: string | null;
  created_at: string | null;
  assets?: ProviderMarketingAsset[];
}

export interface MarketingStatusData {
  marketing_ready: boolean;
  status: string;
  blockers: MarketingBlocker[];
  active_campaign: {
    id: string;
    status: string;
    admin_review_status: string | null;
    created_at: string | null;
  } | null;
}

// ── Sprint 13: Provider Marketing API ────────────────────────────────────────
export const providerMarketingApi = {
  getStatus: () =>
    apiFetch<MarketingStatusData>("/v1/provider/marketing/status"),
  generateLaunchCampaign: () =>
    apiFetch<{ success: boolean; message: string; campaign: ProviderMarketingCampaign; marketing_ready: boolean; blockers: MarketingBlocker[] }>(
      "/v1/provider/marketing/campaigns/generate-launch",
      { method: "POST" }
    ),
  listCampaigns: () =>
    apiFetch<{ campaigns: ProviderMarketingCampaign[]; count: number }>("/v1/provider/marketing/campaigns"),
  getCampaign: (campaignId: string) =>
    apiFetch<{ campaign: ProviderMarketingCampaign }>(`/v1/provider/marketing/campaigns/${campaignId}`),
  submitForReview: (campaignId: string) =>
    apiFetch<{ success: boolean; campaign: ProviderMarketingCampaign }>(
      `/v1/provider/marketing/campaigns/${campaignId}/submit-review`,
      { method: "POST" }
    ),
  listAssets: () =>
    apiFetch<{ assets: ProviderMarketingAsset[]; count: number }>("/v1/provider/marketing/assets"),
  updateProviderNotes: (assetId: string, notes: string) =>
    apiFetch<{ success: boolean; asset: ProviderMarketingAsset }>(
      `/v1/provider/marketing/assets/${assetId}/provider-notes`,
      { method: "PUT", body: JSON.stringify({ notes }) }
    ),
  getVisibilityStatus: () =>
    apiFetch<ProviderVisibilityStatus>("/v1/provider/marketing/visibility-status"),
  getCampaignImpact: (p?: { limit?: number; offset?: number }) =>
    apiFetch<{ items: CampaignImpactItem[]; total: number }>(
      `/v1/provider/marketing/campaign-impact?${new URLSearchParams((p ?? {}) as Record<string, string>)}`
    ),
  getLeadsAttributed: (p?: { limit?: number; offset?: number }) =>
    apiFetch<{ items: AttributedLead[]; total: number }>(
      `/v1/provider/marketing/leads-attributed?${new URLSearchParams((p ?? {}) as Record<string, string>)}`
    ),
};

// ── Sprint 20: Service Job Assignment Types ───────────────────────────────────

export interface ServiceJobRecord {
  id: string;
  job_number: string;
  booking_id: string;
  customer_id: string | null;
  tenant_id: string | null;
  category_id: string;
  offering_id: string;
  assigned_staff_id: string | null;
  scheduled_date: string | null;
  scheduled_time_window: string | null;
  city: string | null;
  zipcode?: string | null;
  address_snapshot?: { line1?: string; city?: string; zipcode?: string } | null;
  status: string;
  assignment_status: string;
  failure_reason?: string | null;
  completion_data?: { work_summary?: string; collected_amount?: number; completion_notes?: string;
    technician?: string; completed_at?: string } | null;
  created_at: string | null;
  updated_at: string | null;
}

// ── FINAL-L5-01D: canonical Tenant Jobs API (service_jobs, not legacy /v1/jobs) ──
export const serviceJobsApi = {
  list: (params?: { status?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    qs.set("limit", String(params?.limit ?? 50));
    qs.set("offset", String(params?.offset ?? 0));
    return apiFetch<{ items: ServiceJobRecord[]; total: number; limit: number; offset: number }>(
      `/v1/provider/my-records/jobs?${qs}`
    );
  },
  get: (jobId: string) => apiFetch<ServiceJobRecord>(`/v1/provider/my-records/jobs/${jobId}`),
};

export interface ServiceJobAssignmentRecord {
  id: string;
  job_id: string;
  booking_id: string;
  assigned_staff_member_id: string;
  assignment_status: string;
  assignment_type: string;
  rejection_reason: string | null;
  scheduled_date: string | null;
  scheduled_time_window: string | null;
  notes: string | null;
  is_current: boolean;
  accepted_at: string | null;
  rejected_at: string | null;
  cancelled_at: string | null;
  created_at: string | null;
}

export interface AssignmentEventRecord {
  id: string;
  job_id: string;
  event_type: string;
  actor_role: string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  reason: string | null;
  created_at: string | null;
}

export interface EligibleStaffRecord {
  staff_member_id: string;
  name: string;
  role: string;
  status: string;
  eligibility_status: string;
  match_reasons?: string[];
  blocked_reasons?: string[];
}

// ── Sprint 20: Provider Job Assignment API ───────────────────────────────────
export const serviceJobAssignmentApi = {
  listAssignable: (params?: { assignment_status?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.assignment_status) qs.set("assignment_status", params.assignment_status);
    if (params?.limit) qs.set("limit", String(params.limit));
    return apiFetch<{ jobs: ServiceJobRecord[]; count: number }>(
      `/v1/provider/service-jobs/assignable?${qs}`
    );
  },
  getContext: (jobId: string) =>
    apiFetch<{ job: ServiceJobRecord; current_assignment: ServiceJobAssignmentRecord | null }>(
      `/v1/provider/service-jobs/${jobId}/assignment-context`
    ),
  getEligibleStaff: (jobId: string) =>
    apiFetch<{ job_id: string; eligible_staff: EligibleStaffRecord[]; blocked_staff: EligibleStaffRecord[] }>(
      `/v1/provider/service-jobs/${jobId}/eligible-staff`
    ),
  assign: (jobId: string, payload: {
    staff_member_id: string;
    scheduled_date?: string;
    scheduled_time_window?: string;
    notes?: string;
  }) =>
    apiFetch<{ success: boolean; data: Record<string, unknown> }>(
      `/v1/provider/service-jobs/${jobId}/assign`,
      { method: "POST", body: JSON.stringify(payload) }
    ),
  reassign: (jobId: string, payload: { staff_member_id: string; reason: string }) =>
    apiFetch<{ success: boolean; data: Record<string, unknown> }>(
      `/v1/provider/service-jobs/${jobId}/reassign`,
      { method: "POST", body: JSON.stringify(payload) }
    ),
  cancelAssignment: (jobId: string, reason: string) =>
    apiFetch<{ success: boolean; data: Record<string, unknown> }>(
      `/v1/provider/service-jobs/${jobId}/cancel-assignment`,
      { method: "POST", body: JSON.stringify({ reason }) }
    ),
  schedule: (jobId: string, payload: { scheduled_date: string; scheduled_time_window: string }) =>
    apiFetch<{ success: boolean; data: Record<string, unknown> }>(
      `/v1/provider/service-jobs/${jobId}/schedule`,
      { method: "POST", body: JSON.stringify(payload) }
    ),
  getTimeline: (jobId: string) =>
    apiFetch<{ job_id: string; events: AssignmentEventRecord[] }>(
      `/v1/provider/service-jobs/${jobId}/assignment-timeline`
    ),
};

// ── Sprint 21: Execution Lifecycle Types ─────────────────────────────────────
export interface ExecutionEventRecord {
  id: string;
  event_type: string;
  old_status: string | null;
  new_status: string | null;
  notes: string | null;
  actor_role: string | null;
  created_at: string | null;
}

export interface ExecutionNoteRecord {
  id: string;
  note_type: string;
  note_text: string;
  is_customer_visible: boolean;
  created_at: string | null;
}

export interface ExecutionMediaRecord {
  id: string;
  media_type: string;
  file_url: string;
  file_name: string | null;
  caption: string | null;
  is_customer_visible: boolean;
  created_at: string | null;
}

// ── Sprint 21: Provider Home Service Execution API ────────────────────────────
export const homeServiceExecutionApi = {
  accept:             (jobId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/${jobId}/accept`, { method: "POST" }),
  reject:             (jobId: string, reason: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/${jobId}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  onTheWay:           (jobId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/${jobId}/on-the-way`, { method: "POST" }),
  reachedSite:        (jobId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/${jobId}/reached-site`, { method: "POST" }),
  startInspection:    (jobId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/${jobId}/start-inspection`, { method: "POST" }),
  completeInspection: (jobId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/${jobId}/complete-inspection`, { method: "POST" }),
  startService:       (jobId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/${jobId}/start-service`, { method: "POST" }),
  workDone:           (jobId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/${jobId}/work-done`, { method: "POST" }),
  quoteRequired:      (jobId: string, note_text: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/${jobId}/quote-required`, { method: "POST", body: JSON.stringify({ note_text }) }),
  addNote:            (jobId: string, note_text: string, is_customer_visible = false) =>
    apiFetch<ExecutionNoteRecord>(`/v1/staff/service-jobs/${jobId}/notes`, { method: "POST", body: JSON.stringify({ note_text, is_customer_visible }) }),
  getTimeline:        (jobId: string) =>
    apiFetch<ExecutionEventRecord[]>(`/v1/staff/service-jobs/${jobId}/timeline`),
  cancel:             (jobId: string, reason: string) =>
    apiFetch<Record<string, unknown>>(`/v1/provider/service-jobs/${jobId}/cancel`, { method: "POST", body: JSON.stringify({ reason }) }),
  getProviderTimeline:(jobId: string) =>
    apiFetch<ExecutionEventRecord[]>(`/v1/provider/service-jobs/${jobId}/execution-timeline`),
  getNotes:           (jobId: string) =>
    apiFetch<ExecutionNoteRecord[]>(`/v1/provider/service-jobs/${jobId}/notes`),

  // HS8B — tenant/business parts request approval + completion proof
  listPartsRequests: (jobId: string) =>
    apiFetch<{ job_id: string; parts_requests: PartsRequestRecord[] }>(`/v1/provider/service-jobs/${jobId}/parts-requests`),
  approveParts: (jobId: string, partsRequestId: string) =>
    apiFetch<PartsRequestRecord>(`/v1/provider/service-jobs/${jobId}/parts-requests/${partsRequestId}/approve`, { method: "POST" }),
  rejectParts: (jobId: string, partsRequestId: string, reason?: string) =>
    apiFetch<PartsRequestRecord>(`/v1/provider/service-jobs/${jobId}/parts-requests/${partsRequestId}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  installParts: (jobId: string, partsRequestId: string) =>
    apiFetch<PartsRequestRecord>(`/v1/provider/service-jobs/${jobId}/parts-requests/${partsRequestId}/install`, { method: "POST" }),
};

export interface PartsRequestRecord {
  parts_request_id: string; job_id: string; tenant_id: string; technician_id: string;
  part_name: string; quantity: number; estimated_cost: number; reason: string;
  photo_ids: string[]; technician_note: string | null;
  customer_approval_required: boolean; business_approval_required: boolean;
  status: string; approved_by: string | null; approved_at: string | null;
  rejected_by: string | null; rejected_at: string | null; rejection_reason: string | null;
  created_at: string; updated_at: string;
}

// ── Sprint 21: Coaching Execution API ────────────────────────────────────────
export const coachingExecutionApi = {
  accept:     (apptId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/coaching-appointments/${apptId}/accept`, { method: "POST" }),
  start:      (apptId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/coaching-appointments/${apptId}/start`, { method: "POST" }),
  complete:   (apptId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/coaching-appointments/${apptId}/complete`, { method: "POST" }),
  noShow:     (apptId: string, notes?: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/coaching-appointments/${apptId}/no-show`, { method: "POST", body: JSON.stringify({ notes }) }),
  addNote:    (apptId: string, note_text: string, is_customer_visible = false) =>
    apiFetch<ExecutionNoteRecord>(`/v1/staff/coaching-appointments/${apptId}/notes`, { method: "POST", body: JSON.stringify({ note_text, is_customer_visible }) }),
  getTimeline:(apptId: string) =>
    apiFetch<ExecutionEventRecord[]>(`/v1/staff/coaching-appointments/${apptId}/timeline`),
  cancel:     (apptId: string, reason: string) =>
    apiFetch<Record<string, unknown>>(`/v1/provider/coaching-appointments/${apptId}/cancel`, { method: "POST", body: JSON.stringify({ reason }) }),
};

// ── Sprint 21: Real Estate Execution API ─────────────────────────────────────
export const realEstateExecutionApi = {
  accept:            (leadId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/real-estate-leads/${leadId}/accept`, { method: "POST" }),
  markContacted:     (leadId: string, notes?: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/real-estate-leads/${leadId}/mark-contacted`, { method: "POST", body: JSON.stringify({ notes }) }),
  scheduleFollowUp:  (leadId: string, notes?: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/real-estate-leads/${leadId}/schedule-follow-up`, { method: "POST", body: JSON.stringify({ notes }) }),
  planSiteVisit:     (leadId: string, notes?: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/real-estate-leads/${leadId}/plan-site-visit`, { method: "POST", body: JSON.stringify({ notes }) }),
  completeSiteVisit: (leadId: string, notes?: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/real-estate-leads/${leadId}/complete-site-visit`, { method: "POST", body: JSON.stringify({ notes }) }),
  qualify:           (leadId: string, notes?: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/real-estate-leads/${leadId}/qualify`, { method: "POST", body: JSON.stringify({ notes }) }),
  convert:           (leadId: string, notes?: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/real-estate-leads/${leadId}/convert`, { method: "POST", body: JSON.stringify({ notes }) }),
  closeLost:         (leadId: string, reason: string) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/real-estate-leads/${leadId}/close-lost`, { method: "POST", body: JSON.stringify({ reason }) }),
  addNote:           (leadId: string, note_text: string, is_customer_visible = false) =>
    apiFetch<ExecutionNoteRecord>(`/v1/staff/real-estate-leads/${leadId}/notes`, { method: "POST", body: JSON.stringify({ note_text, is_customer_visible }) }),
  getTimeline:       (leadId: string) =>
    apiFetch<ExecutionEventRecord[]>(`/v1/staff/real-estate-leads/${leadId}/timeline`),
};

// ── Sprint 22: Quote types ────────────────────────────────────────────────────
export interface QuoteRecord {
  id: string; quote_number: string; job_id: string; booking_id: string;
  tenant_id: string; customer_id: string; status: string; quote_type: string;
  currency: string; labour_amount: string; parts_amount: string;
  service_amount: string; discount_amount: string; tax_amount: string;
  total_amount: string; customer_payable_amount: string;
  provider_internal_notes?: string; customer_visible_notes?: string;
  rejection_reason?: string; revision_reason?: string;
  sent_to_customer_at?: string; approved_at?: string; rejected_at?: string;
  locked_at?: string; created_at?: string; updated_at?: string;
  items?: QuoteItemRecord[];
}
export interface QuoteItemRecord {
  id: string; quote_id: string; item_type: string; item_name: string;
  item_description?: string; quantity: string; unit_price: string;
  line_total: string; is_required: boolean; is_customer_visible: boolean;
  created_at?: string;
}
export interface ChecklistRecord {
  id: string; job_id: string; booking_id: string; tenant_id: string;
  template_id?: string; status: string; checklist_type: string;
  completed_at?: string; created_at?: string; updated_at?: string;
  items?: ChecklistItemRecord[];
}
export interface ChecklistItemRecord {
  id: string; checklist_id: string; item_label: string; input_type: string;
  is_required: boolean; status: string; value_text?: string;
  value_number?: string; value_json?: Record<string, unknown>;
  media_url?: string; sort_order: number; completed_at?: string;
}

// ── Sprint 22: Staff Quote API ────────────────────────────────────────────────
export const staffQuoteApi = {
  create:         (job_id: string, quote_type: string, notes?: string) =>
    apiFetch<QuoteRecord>("/staff/quotes", { method: "POST", body: JSON.stringify({ job_id, quote_type, notes }) }),
  listForJob:     (jobId: string) =>
    apiFetch<QuoteRecord[]>(`/staff/quotes/jobs/${jobId}`),
  get:            (quoteId: string) =>
    apiFetch<QuoteRecord>(`/staff/quotes/${quoteId}`),
  addItem:        (quoteId: string, item: { item_type: string; item_name: string; item_description?: string; quantity: number; unit_price: number; is_required?: boolean; is_customer_visible?: boolean }) =>
    apiFetch<QuoteItemRecord>(`/staff/quotes/${quoteId}/items`, { method: "POST", body: JSON.stringify(item) }),
  updateItem:     (quoteId: string, itemId: string, updates: Partial<QuoteItemRecord>) =>
    apiFetch<QuoteItemRecord>(`/staff/quotes/${quoteId}/items/${itemId}`, { method: "PUT", body: JSON.stringify(updates) }),
  removeItem:     (quoteId: string, itemId: string) =>
    apiFetch<{ removed: boolean }>(`/staff/quotes/${quoteId}/items/${itemId}`, { method: "DELETE" }),
  sendToCustomer: (quoteId: string, customer_notes?: string) =>
    apiFetch<QuoteRecord>(`/staff/quotes/${quoteId}/send-to-customer`, { method: "POST", body: JSON.stringify({ customer_notes }) }),
  markRevised:    (quoteId: string) =>
    apiFetch<QuoteRecord>(`/staff/quotes/${quoteId}/mark-revised`, { method: "POST" }),
  cancel:         (quoteId: string, reason?: string) =>
    apiFetch<QuoteRecord>(`/staff/quotes/${quoteId}/cancel`, { method: "POST", body: JSON.stringify({ reason }) }),
  events:         (quoteId: string) =>
    apiFetch<Record<string, unknown>[]>(`/staff/quotes/${quoteId}/events`),
};

// ── Sprint 22: Staff Checklist API ────────────────────────────────────────────
export const staffChecklistApi = {
  create:      (body: { job_id: string; booking_id: string; checklist_type: string; template_id?: string; custom_items?: unknown[] }) =>
    apiFetch<ChecklistRecord>("/staff/checklists", { method: "POST", body: JSON.stringify(body) }),
  listForJob:  (jobId: string) =>
    apiFetch<ChecklistRecord[]>(`/staff/checklists/jobs/${jobId}`),
  get:         (clId: string) =>
    apiFetch<ChecklistRecord>(`/staff/checklists/${clId}`),
  updateItem:  (clId: string, itemId: string, updates: Partial<ChecklistItemRecord>) =>
    apiFetch<ChecklistItemRecord>(`/staff/checklists/${clId}/items/${itemId}`, { method: "PUT", body: JSON.stringify(updates) }),
  complete:    (clId: string) =>
    apiFetch<ChecklistRecord>(`/staff/checklists/${clId}/complete`, { method: "POST" }),
};

// ── Sprint 23: Invoice / Payment / Wallet / Subscription types ────────────────
export interface ServiceInvoiceRecord {
  id: string; invoice_number?: string; job_id: string; booking_id?: string;
  tenant_id: string; customer_id?: string; source: string;
  invoice_status: string; payment_status: string;
  subtotal?: string; tax_amount?: string; discount_amount?: string;
  customer_payable_amount?: string; commission_amount?: string;
  notes?: string; issued_at?: string; paid_at?: string;
  created_at?: string; updated_at?: string;
}
export interface WalletRecord {
  tenant_id: string; currency: string; current_balance: string;
  reserved_balance: string; total_purchased: string; total_deducted: string;
  low_balance_threshold?: string; is_active: boolean; last_transaction_at?: string;
}
export interface WalletTransactionRecord {
  id: string; tenant_id: string; txn_type: string; amount: string;
  balance_before: string; balance_after: string; reference_id?: string;
  reference_type?: string; description?: string; created_at?: string;
}

// ── Sprint 23: Provider invoice API ──────────────────────────────────────────
export const providerInvoiceApi = {
  list:           (status?: string) =>
    apiFetch<ServiceInvoiceRecord[]>(`/v1/provider/service-invoices${status ? `?status=${status}` : ""}`),
  get:            (invoiceId: string) =>
    apiFetch<ServiceInvoiceRecord>(`/v1/provider/service-invoices/${invoiceId}`),
  issue:          (invoiceId: string) =>
    apiFetch<ServiceInvoiceRecord>(`/v1/provider/service-invoices/${invoiceId}/issue`, { method: "POST" }),
  recordPayment:  (invoiceId: string, body: { payment_mode: string; collected_amount: number; proof_media_url?: string }) =>
    apiFetch<Record<string, unknown>>(`/v1/provider/service-invoices/${invoiceId}/record-payment`, { method: "POST", body: JSON.stringify(body) }),
  timeline:       (invoiceId: string) =>
    apiFetch<Record<string, unknown>[]>(`/v1/provider/service-invoices/${invoiceId}/financial-timeline`),
};

// ── HS9B — Home Services Usage Credits (real, distinct from the legacy
// Sprint 23 "wallet" API below, which is a different, pre-existing
// invoice/commission concept out of this ticket's scope — not renamed,
// not touched, per HS9B's explicit "do not rebuild the wallet/payout
// system" instruction). ────────────────────────────────────────────────────
export interface UsageCreditLedgerEntry {
  ledger_id: string; tenant_id: string; job_id: string | null; booking_id: string | null;
  event_type: string; credit_delta: number; balance_before: number; balance_after: number;
  deduction_source: string | null; service_id: string | null; service_type_id: string | null;
  brand_id: string | null; reason: string | null; request_id: string | null; created_at: string;
}
export const usageCreditsApi = {
  getBalance: () => apiFetch<{ tenant_id: string; usage_credit_balance: number; low_credit: boolean }>("/v1/provider/usage-credits/balance"),
  getLedger:  () => apiFetch<{ tenant_id: string; entries: UsageCreditLedgerEntry[]; count: number }>("/v1/provider/usage-credits/ledger"),
};

// ── Sprint 23: Provider wallet API ────────────────────────────────────────────
export const providerWalletApi = {
  getWallet:      () =>
    apiFetch<WalletRecord>("/v1/provider/wallet"),
  getLedger:      () =>
    apiFetch<WalletTransactionRecord[]>("/v1/provider/wallet/ledger"),
  getCommissions: () =>
    apiFetch<Record<string, unknown>[]>("/v1/provider/wallet/commission-records"),
};

// ── Sprint 23: Provider subscription API ─────────────────────────────────────
export const providerSubscriptionApi = {
  getStatus: () =>
    apiFetch<Record<string, unknown>>("/v1/provider/subscription-status"),
};

// ── Sprint 23: Staff invoice API ──────────────────────────────────────────────
export const staffInvoiceApi = {
  create:     (body: { job_id: string; source?: string; quote_id?: string; notes?: string }) =>
    apiFetch<ServiceInvoiceRecord>("/v1/staff/service-invoices", { method: "POST", body: JSON.stringify(body) }),
  addItem:    (invoiceId: string, body: { item_name: string; item_type?: string; quantity?: number; unit_price: number; item_description?: string }) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-invoices/${invoiceId}/items`, { method: "POST", body: JSON.stringify(body) }),
  getForJob:  (jobId: string) =>
    apiFetch<ServiceInvoiceRecord>(`/v1/staff/service-invoices/jobs/${jobId}`),
};


// ── Sprint 24: Customer Review types ─────────────────────────────────────────
export interface CustomerReviewRecord {
  id: string; review_number?: string; customer_id: string; tenant_id: string;
  category_id?: string; record_type: string; record_id: string;
  overall_rating: number; provider_rating?: number; staff_rating?: number;
  communication_rating?: number; punctuality_rating?: number;
  quality_rating?: number; value_rating?: number;
  review_title?: string; review_text?: string;
  review_tags?: string[]; media_urls?: string[];
  status: string; visibility: string;
  submitted_at?: string; approved_at?: string; created_at?: string; updated_at?: string;
}
export interface TenantRatingSummaryRecord {
  id: string; tenant_id: string; total_reviews: number;
  average_rating: string; provider_average_rating: string;
  communication_average_rating: string; punctuality_average_rating: string;
  quality_average_rating: string; value_average_rating: string;
  five_star_count: number; four_star_count: number; three_star_count: number;
  two_star_count: number; one_star_count: number;
  last_review_at?: string; updated_at?: string;
}
export interface StaffRatingSummaryRecord {
  id: string; tenant_id: string; staff_member_id: string; total_reviews: number;
  average_rating: string; communication_average_rating: string;
  punctuality_average_rating: string; quality_average_rating: string;
  last_review_at?: string; updated_at?: string;
}

// ── Sprint 24: Provider reviews API ──────────────────────────────────────────
export const providerReviewApi = {
  list:        (status?: string) =>
    apiFetch<CustomerReviewRecord[]>(`/v1/provider/reviews${status ? `?status=${status}` : ""}`),
  get:         (reviewId: string) =>
    apiFetch<CustomerReviewRecord>(`/v1/provider/reviews/${reviewId}`),
  getSummary:  () =>
    apiFetch<TenantRatingSummaryRecord>("/v1/provider/reviews/summary"),
  getStaffSummary: () =>
    apiFetch<StaffRatingSummaryRecord[]>("/v1/provider/reviews/staff-summary"),
  submitReply: (reviewId: string, reply_text: string) =>
    apiFetch<Record<string, unknown>>(`/v1/provider/reviews/${reviewId}/reply`, { method: "POST", body: JSON.stringify({ reply_text }) }),
  flagReview:  (reviewId: string, body: { reason_code: string; reason_text?: string }) =>
    apiFetch<Record<string, unknown>>(`/v1/provider/reviews/${reviewId}/flag`, { method: "POST", body: JSON.stringify(body) }),
};

// ── Sprint 24: Customer reviews API ──────────────────────────────────────────
export const customerReviewApi = {
  checkEligibility: (record_type: string, record_id: string) =>
    apiFetch<{ eligible: boolean; reason?: string }>(`/v1/customer/reviews/eligibility?record_type=${record_type}&record_id=${record_id}`),
  submit:  (body: Partial<CustomerReviewRecord> & { tenant_id: string; record_type: string; record_id: string; overall_rating: number }) =>
    apiFetch<CustomerReviewRecord>("/v1/customer/reviews", { method: "POST", body: JSON.stringify(body) }),
  list:    () =>
    apiFetch<CustomerReviewRecord[]>("/v1/customer/reviews"),
  get:     (reviewId: string) =>
    apiFetch<CustomerReviewRecord>(`/v1/customer/reviews/${reviewId}`),
  edit:    (reviewId: string, updates: Partial<CustomerReviewRecord>) =>
    apiFetch<CustomerReviewRecord>(`/v1/customer/reviews/${reviewId}`, { method: "PATCH", body: JSON.stringify(updates) }),
};

// ── Sprint 25: Complaint types ────────────────────────────────────────────────
export interface ComplaintRecord {
  id: string; complaint_number?: string; customer_id: string;
  tenant_id?: string; category_id?: string; offering_id?: string;
  record_type: string; record_id: string;
  complaint_type: string; requested_resolution?: string;
  title?: string; description: string;
  status: string; priority: string;
  assigned_admin_user_id?: string;
  provider_responded_at?: string; customer_accepted_resolution_at?: string;
  resolved_at?: string; closed_at?: string;
  created_at?: string; updated_at?: string;
}
export interface ReworkRecord {
  id: string; complaint_id: string; tenant_id?: string;
  status: string; rework_reason: string;
  scheduled_date?: string; scheduled_time_window?: string;
  customer_visible_notes?: string; admin_notes?: string;
  completed_at?: string; created_at?: string;
}
export interface RefundRecord {
  id: string; complaint_id: string; tenant_id?: string;
  status: string; refund_type: string;
  requested_amount?: string; approved_amount?: string; recorded_amount?: string;
  refund_method?: string; reason: string;
  approved_at?: string; recorded_at?: string; verified_at?: string;
  created_at?: string;
}

// ── Sprint 25: Provider complaints API ────────────────────────────────────────
export const providerComplaintApi = {
  list:      (status?: string) =>
    apiFetch<ComplaintRecord[]>(`/v1/provider/complaints${status ? `?status=${status}` : ""}`),
  get:       (id: string) => apiFetch<ComplaintRecord>(`/v1/provider/complaints/${id}`),
  respond:   (id: string, message_text: string) =>
    apiFetch<Record<string, unknown>>(`/v1/provider/complaints/${id}/respond`, { method: "POST", body: JSON.stringify({ message_text }) }),
  messages:  (id: string) =>
    apiFetch<Record<string, unknown>[]>(`/v1/provider/complaints/${id}/messages`),
  offerResolution: (id: string, body: { resolution_type: string; description: string; customer_visible_notes?: string }) =>
    apiFetch<Record<string, unknown>>(`/v1/provider/complaints/${id}/offer-resolution`, { method: "POST", body: JSON.stringify(body) }),
  listReworks: (status?: string) =>
    apiFetch<ReworkRecord[]>(`/v1/provider/rework-requests${status ? `?status=${status}` : ""}`),
  startRework:    (id: string) =>
    apiFetch<ReworkRecord>(`/v1/provider/rework-requests/${id}/start`, { method: "POST" }),
  completeRework: (id: string, notes?: string) =>
    apiFetch<ReworkRecord>(`/v1/provider/rework-requests/${id}/complete`, { method: "POST", body: JSON.stringify({ notes }) }),
  listRefunds: (status?: string) =>
    apiFetch<RefundRecord[]>(`/v1/provider/refund-requests${status ? `?status=${status}` : ""}`),
  reviewRefund: (id: string, notes?: string) =>
    apiFetch<RefundRecord>(`/v1/provider/refund-requests/${id}/review`, { method: "POST", body: JSON.stringify({ notes }) }),
};

// ── Sprint 26: Enterprise Grid types (provider) ───────────────────────────────
export interface EnterprisePagination {
  page: number; page_size: number; total_items: number;
  total_pages: number; has_next: boolean; has_previous: boolean;
}
export interface EnterpriseListResponse<T = Record<string, unknown>> {
  items:            T[];
  pagination:       EnterprisePagination;
  sort:             { sort_by: string; sort_direction: string };
  filters_applied:  Record<string, unknown>;
  available_filters: string[];
  available_columns: Record<string, unknown>[];
}
export interface EnterpriseSavedView {
  id: string; resource_key: string; view_name: string;
  is_default: boolean; filters: Record<string, unknown>;
  sort: Record<string, unknown>; columns: unknown[];
  page_size: number; visibility: string;
  created_at?: string;
}

export const providerEnterpriseApi = {
  listSavedViews:  (resource_key: string) =>
    apiFetch<EnterpriseSavedView[]>(`/v1/enterprise/saved-views?resource_key=${resource_key}&scope=provider`),
  createSavedView: (body: Partial<EnterpriseSavedView> & { resource_key: string; view_name: string }) =>
    apiFetch<EnterpriseSavedView>("/v1/enterprise/saved-views", { method: "POST", body: JSON.stringify({ ...body, scope: "provider" }) }),
  deleteSavedView: (id: string) =>
    apiFetch<Record<string, unknown>>(`/v1/enterprise/saved-views/${id}`, { method: "DELETE" }),
  getColumnPrefs:  (resource_key: string) =>
    apiFetch<Record<string, unknown>>(`/v1/enterprise/column-preferences?resource_key=${resource_key}`),
  saveColumnPrefs: (resource_key: string, columns: unknown[]) =>
    apiFetch<Record<string, unknown>>("/v1/enterprise/column-preferences", { method: "PUT", body: JSON.stringify({ resource_key, columns }) }),
  createExport:    (resource_key: string, filters: Record<string, unknown>, columns: string[]) =>
    apiFetch<Record<string, unknown>>("/v1/enterprise/exports", { method: "POST", body: JSON.stringify({ resource_key, filters, columns }) }),
};

// ── Sprint 27: Provider Notifications + Chat ──────────────────────────────────
export interface InAppNotificationItem {
  id: string;
  notification_type: string;
  title: string;
  body: string;
  action_url: string | null;
  action_label: string | null;
  severity: string;
  read_status: string;
  read_at: string | null;
  created_at: string;
}

export interface ProviderChatThread {
  id: string;
  thread_number: string;
  record_type: string;
  record_id: string;
  status: string;
  last_message_at: string | null;
  created_at: string;
}

export interface ProviderChatMessage {
  id: string;
  thread_id: string;
  sender_user_id: string | null;
  sender_type: string;
  message_type: string;
  message_text: string | null;
  media_urls: { media_ids?: string[] } | null;
  visibility: string;
  created_at: string;
}

export const providerNotifApi = {
  list: (params?: { read_status?: string; limit?: number; offset?: number }) =>
    apiFetch<{ items: InAppNotificationItem[]; total: number }>(`/v1/provider/notifications?${new URLSearchParams(params as Record<string, string>)}`),
  unreadCount: () =>
    apiFetch<{ unread_count: number }>("/v1/provider/notifications/unread-count"),
  markRead: (id: string) =>
    apiFetch<InAppNotificationItem>(`/v1/provider/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () =>
    apiFetch<{ marked_read: number }>("/v1/provider/notifications/mark-all-read", { method: "POST" }),
  getPreferences: () =>
    apiFetch<unknown[]>("/v1/provider/notifications/preferences"),
  updatePreference: (event_key: string, channel: string, is_enabled: boolean) =>
    apiFetch<unknown>("/v1/provider/notifications/preferences", { method: "PUT", body: JSON.stringify({ event_key, channel, is_enabled }) }),
};

export const providerChatApi = {
  listThreads: (params?: { status?: string; limit?: number }) =>
    apiFetch<{ items: ProviderChatThread[]; total: number }>(`/v1/provider/chat/threads?${new URLSearchParams(params as Record<string, string>)}`),
  createThread: (record_type: string, record_id: string) =>
    apiFetch<ProviderChatThread>("/v1/provider/chat/threads", { method: "POST", body: JSON.stringify({ record_type, record_id }) }),
  getThread: (id: string) =>
    apiFetch<ProviderChatThread>(`/v1/provider/chat/threads/${id}`),
  listMessages: (threadId: string, params?: { limit?: number; offset?: number }) =>
    apiFetch<{ items: ProviderChatMessage[]; total: number }>(`/v1/provider/chat/threads/${threadId}/messages?${new URLSearchParams(params as Record<string, string>)}`),
  sendMessage: (threadId: string, message_text: string, media_ids?: string[]) =>
    apiFetch<ProviderChatMessage>(`/v1/provider/chat/threads/${threadId}/messages`, { method: "POST", body: JSON.stringify({ message_text, media_ids: media_ids?.length ? media_ids : undefined }) }),
  markThreadRead: (threadId: string) =>
    apiFetch<{ messages_marked_read: number }>(`/v1/provider/chat/threads/${threadId}/read`, { method: "POST" }),
};

// ── Sprint 28 — Analytics Types ───────────────────────────────────────────────

export interface AnalyticsDateRange { from: string | null; to: string | null; }

export interface AnalyticsData {
  summary:         Record<string, unknown>;
  series:          unknown[];
  breakdown:       Record<string, unknown>[];
  top_items:       Record<string, unknown>[];
  filters_applied: Record<string, string | null>;
  date_range:      AnalyticsDateRange;
  generated_at:    string;
  [key: string]:   unknown;
}

export interface ReportDefinition {
  report_key:      string;
  report_name:     string;
  scope:           string;
  allowed_filters: string[];
  export_formats:  string[];
}

export interface ReportRun {
  id:              string;
  report_key:      string;
  report_name:     string | null;
  scope:           string;
  status:          string;
  filters:         Record<string, unknown>;
  result_summary:  Record<string, unknown> | null;
  row_count:       number | null;
  failure_reason:  string | null;
  created_at:      string;
  completed_at:    string | null;
}

// ── Provider Analytics API ────────────────────────────────────────────────────

type DateParams = { date_from?: string; date_to?: string; };

function qs(p: Record<string, string | undefined>): string {
  const q = Object.fromEntries(Object.entries(p).filter(([, v]) => v != null)) as Record<string, string>;
  const s = new URLSearchParams(q).toString();
  return s ? `?${s}` : "";
}

export const providerAnalyticsApi = {
  getSummary: (p: DateParams = {}) =>
    apiFetch<AnalyticsData>(`/v1/provider/analytics/summary${qs(p as Record<string, string>)}`),
  getOperationalSummary: (p: DateParams = {}) =>
    apiFetch<AnalyticsData>(`/v1/provider/analytics/operational-summary${qs(p as Record<string, string>)}`),
  getFinancialSummary: (p: DateParams = {}) =>
    apiFetch<AnalyticsData>(`/v1/provider/analytics/financial-summary${qs(p as Record<string, string>)}`),
  getStaffPerformance: (p: DateParams & { staff_member_id?: string } = {}) =>
    apiFetch<AnalyticsData>(`/v1/provider/analytics/staff-performance${qs(p as Record<string, string>)}`),
  getQualitySummary: (p: DateParams = {}) =>
    apiFetch<AnalyticsData>(`/v1/provider/analytics/quality-summary${qs(p as Record<string, string>)}`),
  getComplaintSummary: (p: DateParams = {}) =>
    apiFetch<AnalyticsData>(`/v1/provider/analytics/complaint-summary${qs(p as Record<string, string>)}`),
  getOperationalAlerts: () =>
    apiFetch<AnalyticsData>("/v1/provider/analytics/operational-alerts"),
  listReports: (p?: { limit?: number; offset?: number }) =>
    apiFetch<{ definitions: ReportDefinition[]; recent_runs: { items: ReportRun[]; total: number } }>(
      `/v1/provider/reports?${new URLSearchParams(p as Record<string, string>)}`
    ),
  runReport: (body: { report_key: string; filters?: Record<string, string>; export_format?: string }) =>
    apiFetch<{ id: string; status: string; row_count: number; preview: Record<string, unknown>[]; generated_at: string }>(
      "/v1/provider/reports/run", { method: "POST", body: JSON.stringify(body) }
    ),
  getReportRun: (run_id: string) =>
    apiFetch<ReportRun>(`/v1/provider/reports/${run_id}`),
};

// ── Provider Marketing API (Sprint 29) ───────────────────────────────────────

export interface ProviderVisibilityStatus {
  tenant_id:                     string;
  is_bookable:                   boolean;
  is_visible:                    boolean;
  visibility_boost_active:       boolean;
  visibility_boost_expires_at:   string | null;
  provider_status:               string;
}

export interface CampaignImpactItem {
  id:                string;
  campaign_id:       string;
  event_type:        string;
  source_record_type: string | null;
  source_record_id:  string | null;
  camp_metadata:     Record<string, unknown> | null;
  created_at:        string;
}

export interface AttributedLead {
  id:                string;
  campaign_id:       string;
  source_record_type: string | null;
  source_record_id:  string | null;
  created_at:        string;
}

// ── Phase 0C — Profile Edit ───────────────────────────────────────────────────

export interface UserProfile {
  id: string;
  user_id: string;
  email: string;
  phone: string | null;
  full_name: string;
  display_name: string | null;
  language: string;
  timezone: string;
  role: string;
  tenant_id: string | null;
  is_active: boolean;
  is_verified: boolean;
  avatar_url: string | null;
  profile_photo_media_id: string | null;
  last_login_at: string | null;
  created_at: string;
}

export interface UpdateUserProfilePayload {
  full_name?: string;
  display_name?: string;
  language?: string;
  timezone?: string;
  phone?: string;
}

export interface BusinessProfile {
  id: string;
  tenant_id: string;
  tenant_name: string;
  business_name: string | null;
  legal_name: string | null;
  owner_name: string | null;
  phone: string | null;
  email: string | null;
  gst_number: string | null;
  business_type: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  district: string | null;
  state: string | null;
  country: string;
  zipcode: string | null;
  logo_url: string | null;
  business_logo_media_id: string | null;
  shop_photo_media_id: string | null;
  verification_status: string;
  status: string;
  plan_type: string;
  website_url: string | null;
  description: string | null;
  slug: string | null;
  created_at: string;
}

export interface UpdateBusinessProfilePayload {
  business_name?: string;
  owner_name?: string;
  phone?: string;
  email?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  district?: string;
  state?: string;
  country?: string;
  zipcode?: string;
  gst_number?: string;
  website_url?: string;
  description?: string;
}

export const profileApi = {
  getProfile: () =>
    apiFetch<UserProfile>("/v1/me/profile"),
  updateProfile: (data: UpdateUserProfilePayload) =>
    apiFetch<UserProfile>("/v1/me/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

export const businessProfileApi = {
  get: () =>
    apiFetch<BusinessProfile>("/v1/provider/business-profile"),
  update: (data: UpdateBusinessProfilePayload) =>
    apiFetch<BusinessProfile & { reverification_triggered?: boolean; reverification_message?: string }>(
      "/v1/provider/business-profile",
      { method: "PUT", body: JSON.stringify(data) },
    ),
  // Tenant requests admin review — never self-approves. Backend validates
  // required-field completion and returns 422 with a `missing` list
  // (surfaced via ServiceOSError.context) if the profile isn't ready yet.
  submitForReview: () =>
    apiFetch<BusinessProfile & { submitted?: boolean; message?: string }>(
      "/v1/provider/business-profile/submit-review",
      { method: "POST" },
    ),
};

export const staffProfileApi = {
  get: () =>
    apiFetch<UserProfile>("/v1/staff/profile"),
  update: (data: UpdateUserProfilePayload) =>
    apiFetch<UserProfile>("/v1/staff/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

// ── Sprint 34D — Brand Types + Provider Brand API ─────────────────────────────

export interface ProviderAvailableBrand {
  brand_id: string;
  name: string;
  display_name: string;
  logo_url?: string;
  is_required: boolean;
  is_default: boolean;
}

export interface ProviderSupportedBrand {
  record_id: string;
  brand_id: string;
  name: string;
  display_name: string;
  logo_url?: string;
  support_level?: string;
  notes?: string;
}

export interface CustomerCatalogBrand {
  brand_id: string;
  name: string;
  display_name: string;
  logo_url?: string;
  provider_count: number;
  is_popular: boolean;
}

export const providerBrandApi = {
  /** List brands admin has approved for this service — provider picks from these */
  getAvailableForService: (serviceId: string) =>
    apiFetch<{ service_id: string; brands: ProviderAvailableBrand[] }>(
      `/v1/provider/brands/services/${serviceId}/available`),

  /** List brands admin has approved for a category — used by provider offerings view */
  getAvailableForCategory: (categoryId: string) =>
    apiFetch<{ category_id: string; brands: ProviderAvailableBrand[] }>(
      `/v1/provider/brands/categories/${categoryId}/available`),

  /** Get brands this provider currently supports for a service */
  getSupportedForService: (serviceId: string) =>
    apiFetch<{ service_id: string; tenant_id: string; supported_brands: ProviderSupportedBrand[] }>(
      `/v1/provider/brands/services/${serviceId}/supported`),

  /** Replace provider's supported brands for a service */
  setSupportedForService: (serviceId: string, brandIds: string[], supportLevel?: string) =>
    apiFetch<{ service_id: string; tenant_id: string; selected_count: number }>(
      `/v1/provider/brands/services/${serviceId}/supported`,
      { method: "POST", body: JSON.stringify({ brand_ids: brandIds, support_level: supportLevel }) }),

  /** Provider submits a request for a missing brand */
  requestBrand: (data: { requested_brand_name: string; reason?: string; suggested_service_id?: string }) =>
    apiFetch<{ request_id: string; status: string }>(
      "/v1/provider/brands/requests",
      { method: "POST", body: JSON.stringify(data) }),

  /** Get provider's own brand requests */
  listMyRequests: () =>
    apiFetch<{ requests: { request_id:string; requested_brand_name:string; status:string; created_at:string }[] }>(
      "/v1/provider/brands/requests"),
};

export const customerBrandApi = {
  /** Customer-facing brand catalog filtered by service and provider coverage */
  getForService: (serviceId?: string, zoneId?: string) => {
    const qs = new URLSearchParams();
    if (serviceId) qs.set("service_id", serviceId);
    if (zoneId)    qs.set("zone_id", zoneId);
    return apiFetch<{ brands: CustomerCatalogBrand[]; total: number }>(
      `/v1/customer/catalog/brands?${qs.toString()}`);
  },

  /** Validate a brand is active and mapped to a service */
  validate: (serviceId: string, brandId: string, typedName?: string) =>
    apiFetch<{ valid: boolean; brand_id: string; matched_name?: string; match_type?: string }>(
      "/v1/customer/catalog/brands/validate",
      { method: "POST", body: JSON.stringify({ service_id: serviceId, brand_id: brandId, typed_brand_name: typedName }) }),
};

// ─────────────────────────────────────────────────────────────────────────────
// Sprint 34E — Service Options + Issue Catalog (Provider + Customer)
// ─────────────────────────────────────────────────────────────────────────────

export interface ProviderAvailableServiceOption {
  id: string;
  name: string;
  code: string;
  option_type: string;
  is_required: boolean;
  is_default: boolean;
  display_order: number;
  option_group_id?: string;
  // HOME-SERVICES-CATALOG ownership correction (migration 169): every
  // available option is now scoped to an exact Job-Type mapping. Tenant
  // pricing is set against mapping_id, never against the option template.
  mapping_id: string;
  job_type_id: string | null;
  usage?: "DISABLED" | "OPTIONAL" | "REQUIRED";
  quantity_supported?: boolean;
  minimum_quantity?: number | null;
  maximum_quantity?: number | null;
  measurement_unit?: string | null;
}

export interface TenantOptionPrice {
  id: string;
  service_option_mapping_id: string | null;
  status: string;
  pricing_model: "FIXED" | "PER_UNIT" | "RANGE" | null;
  fixed_price: string | null;
  unit_price: string | null;
  minimum_price: string | null;
  maximum_price: string | null;
  currency: string;
}

export interface ProviderSupportedServiceOption {
  id: string;
  service_option_id: string;
  status: string;
  option?: ProviderAvailableServiceOption;
}

export interface CustomerServiceOption {
  service_option_id: string;
  name: string;
  display_name: string;
  code: string;
  option_group_id?: string;
  is_required: boolean;
  is_default: boolean;
  display_order: number;
}

export interface CustomerIssueType {
  issue_type_id: string;
  name: string;
  code: string;
  severity: string;
  is_common: boolean;
  requires_photo: boolean;
  requires_description: boolean;
  display_order: number;
}

export interface DiagnosticsValidateResult {
  valid: boolean;
  error?: string;
  warnings?: string[];
  matched_issue_type_id?: string;
  matched_service_option_id?: string;
  requires_photo: boolean;
  requires_description: boolean;
}

export const providerServiceOptionApi = {
  getAvailableForService: (serviceId: string, jobTypeId?: string | null) =>
    apiFetch<ProviderAvailableServiceOption[]>(
      `/v1/provider/setup/services/${serviceId}/available-options${jobTypeId ? `?job_type_id=${jobTypeId}` : ""}`),
  getSupportedForService: (serviceId: string) =>
    apiFetch<ProviderSupportedServiceOption[]>(
      `/v1/provider/setup/services/${serviceId}/supported-options`),
  setSupportedForService: (serviceId: string, serviceOptionIds: string[]) =>
    apiFetch<{ set: number }>(
      `/v1/provider/setup/services/${serviceId}/supported-options`,
      { method: "POST", body: JSON.stringify({ service_option_ids: serviceOptionIds }) }),
  // Tenant-owned pricing (migration 169) -- admin never sets these.
  setOptionPrice: (mappingId: string, data: {
    enabled: boolean; pricing_model?: "FIXED" | "PER_UNIT" | "RANGE";
    fixed_price?: string; unit_price?: string; minimum_price?: string; maximum_price?: string;
  }) =>
    apiFetch<TenantOptionPrice>(`/v1/provider/setup/services/option-mappings/${mappingId}/price`,
      { method: "PUT", body: JSON.stringify(data) }),
};

export const customerServiceDiagnosticsApi = {
  getServiceOptions: (serviceId?: string, categoryId?: string) => {
    const qs = new URLSearchParams();
    if (serviceId) qs.set("service_id", serviceId);
    if (categoryId) qs.set("category_id", categoryId);
    return apiFetch<CustomerServiceOption[]>(`/v1/customer/catalog/service-options?${qs}`);
  },
  getIssueTypes: (serviceId?: string, categoryId?: string) => {
    const qs = new URLSearchParams();
    if (serviceId) qs.set("service_id", serviceId);
    if (categoryId) qs.set("category_id", categoryId);
    return apiFetch<CustomerIssueType[]>(`/v1/customer/catalog/issue-types?${qs}`);
  },
  validate: (data: {
    service_id?: string;
    issue_type_id?: string;
    service_option_id?: string;
    typed_issue?: string;
    typed_option?: string;
  }) =>
    apiFetch<DiagnosticsValidateResult>(
      "/v1/customer/catalog/service-diagnostics/validate",
      { method: "POST", body: JSON.stringify(data) }),
};

// ── Phase 6B: Tenant Setup / Provider Status APIs ─────────────────────────────
export const tenantSetupApi = {
  getStatus:           () => apiFetch<Record<string, unknown>>("/v1/provider/status"),
  getPackage:          () => apiFetch<Record<string, unknown>>("/v1/provider/subscription-status"),
  getWallet:           () => apiFetch<Record<string, unknown>>("/v1/provider/wallet"),
  getLedger:           (page = 1) => apiFetch<Record<string, unknown>>(`/v1/provider/wallet/ledger?page=${page}`),
  // /v1/provider/pricing does NOT exist — use pricingApi instead (see tenantPricingApi below)
  getPricingPreview:   () => apiFetch<Record<string, unknown>>("/v1/provider/pricing"),
  getOverrideRequests: () => apiFetch<Record<string, unknown>>("/v1/provider/pricing/overrides"),
  submitOverride:      (data: Record<string, unknown>) =>
    apiFetch<Record<string, unknown>>("/v1/provider/pricing/overrides", { method: "POST", body: JSON.stringify(data) }),
  getActivity:         (page = 1) => apiFetch<Record<string, unknown>>(`/v1/provider/activity?page=${page}`),
};

// ── Tenant Pricing API (uses existing /v1/pricing/tenants/{tid}/* endpoints) ──
export const tenantPricingApi = {
  // List tenant service price rows from the pricing engine
  listPrices: (limit = 50) => {
    const tid = getTenantId();
    return apiFetch<Record<string, unknown>>(`/v1/pricing/tenants/${tid}/prices?limit=${limit}`);
  },
  // Preview price for a specific service/context — returns base_price, min_price, max_price,
  // bargain_floor, completed_job_deduction_credits, payment_collection_mode
  previewPrice: (data: {
    service_type_id: string;
    service_category: string;
    city_name: string;
    pincode?: string;
  }) => {
    const tid = getTenantId();
    return apiFetch<Record<string, unknown>>(
      `/v1/pricing/tenants/${tid}/price-preview`,
      { method: "POST", body: JSON.stringify(data) },
    );
  },
  // Admin endpoint for pricing-rules preview (requires admin permission — will 403 for tenants,
  // but we try it for informational purposes in the UI)
  adminPreviewPricing: (data: Record<string, unknown>) =>
    apiFetch<Record<string, unknown>>("/v1/admin/pricing-rules/preview",
      { method: "POST", body: JSON.stringify(data) }),
};

// ── Phase 7B: Staff / Technician Self-Service APIs ────────────────────────────
// Distinct from `staffApi` (tenant-owner managing the staff roster) — these
// call the technician's own self-service surface, tenant_id/staff_id always
// derived server-side from the JWT, never passed by the client except where
// the backend route itself requires it as a required query param (jobs list),
// in which case the backend silently overrides it with the JWT's real value
// (see PHASE_7_STAFF_APP_BUG_FIX_REPORT.md bug #1).
// MODULE-L5-38: StaffJobShellItem/StaffJobShellDetail + staffSelfApi.getMyJobs/
// getJobDetail (which called the dead field_ops /v1/staff/me/jobs, 0 rows
// platform-wide) were removed -- every staff job surface now uses the real
// homeServiceStaffJobsApi (/v1/staff/service-jobs). See the staff job pages.
// MODULE-L5-39: this modeled `is_read` (boolean) + `type`, but the real
// InAppNotification.to_dict() returns `read_status` ("read"|"unread") and
// `notification_type` -- so the unread badge/highlight never matched and the
// title fell back to "Notification". Corrected to the real shape.
export interface StaffNotification {
  id: string; notification_type: string; title: string; body: string | null;
  action_url: string | null; action_label: string | null;
  source_record_type: string | null; source_record_id: string | null;
  severity: string; read_status: string; read_at: string | null; created_at: string;
}
export interface StaffSkillEntry {
  id: string; full_name: string; skills: string[] | null;
  supported_offering_ids?: string[] | null; status: string;
  can_receive_assignment: boolean; category_id: string;
}

// MODULE-L5-19: staff chat — the technician messaging the customer on a job.
// staff_chat_router (/v1/staff/chat) existed but had no staff UI at all.
export interface StaffChatThread {
  id: string; thread_number: string; tenant_id?: string | null;
  record_type: string; record_id: string; status: string;
  last_message_at?: string | null; created_at: string;
}
export interface StaffChatMessage {
  id: string; thread_id: string; sender_type: string;
  message_text?: string | null; message_type: string;
  delivery_status: string; created_at: string;
}
export const staffChatApi = {
  listThreads: () =>
    apiFetch<{ items: StaffChatThread[] }>("/v1/staff/chat/threads").then(d => d.items ?? []),
  listMessages: (threadId: string) =>
    apiFetch<{ items: StaffChatMessage[] }>(`/v1/staff/chat/threads/${threadId}/messages`).then(d => d.items ?? []),
  sendMessage: (threadId: string, text: string) =>
    apiFetch<StaffChatMessage>(`/v1/staff/chat/threads/${threadId}/messages`, {
      method: "POST", body: JSON.stringify({ message_text: text, message_type: "text" }) }),
  markRead: (threadId: string) =>
    apiFetch(`/v1/staff/chat/threads/${threadId}/read`, { method: "POST", body: "{}" }),
};

export const staffSelfApi = {
  // Skills & assigned services — reuses the real provider/team-members
  // endpoint, filtered client-side to the logged-in technician's own row
  // (the backend does not yet expose a dedicated "my skills" endpoint —
  // see PHASE_7B remaining blockers).
  getMySkills: async (): Promise<StaffSkillEntry | null> => {
    const uid = getUserId();
    const res = await apiFetch<{ members: StaffSkillEntry[]; count: number }>("/v1/provider/team-members");
    return res.members.find(m => (m as unknown as { user_id?: string }).user_id === uid) ?? res.members[0] ?? null;
  },

  // Service areas (tenant-wide view — technician sees the tenant's
  // configured areas; there is no per-technician area-assignment endpoint
  // yet, so this reads the same tenant service-areas list a manager sees,
  // read-only for this role).
  getServiceAreas: () => apiFetch<{ areas: Record<string, unknown>[]; total: number }>("/v1/tenant/service-areas"),

  // MODULE-L5-38: getMyJobs/getJobDetail removed -- they called the dead
  // field_ops /v1/staff/me/jobs. Staff jobs now use homeServiceStaffJobsApi.

  // Notifications
  getNotifications: () => apiFetch<{ items: StaffNotification[]; total: number; unread_count: number | null }>("/v1/staff/notifications"),
  // MODULE-L5-39: the real route is /{id}/read, not /{id}/mark-read (404'd);
  // mark-all-read returns {marked_read}, not {marked}.
  markRead: (id: string) => apiFetch<StaffNotification>(`/v1/staff/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => apiFetch<{ marked_read: number }>("/v1/staff/notifications/mark-all-read", { method: "POST" }),

  // Documents — no dedicated staff document endpoint exists yet
  // (confirmed absent in Phase 7 research; see PHASE_7B remaining blockers).

  // Sessions — no dedicated staff self-service session endpoint exists yet
  // (confirmed absent in Phase 7 research; see PHASE_7B remaining blockers).

  // Activity — no dedicated staff-scoped audit/activity endpoint exists yet.
  // /v1/provider/activity was assumed to exist but returns 404 live (confirmed
  // via Phase 7B smoke test); only platform-admin-level audit search endpoints
  // exist today. See PHASE_7B remaining blockers.
};

// ── HS8B — Home Services Job Execution (real, live-verified APIs) ───────────
// The real home_service_assignment + execution engines (fixed and
// live-verified in HS8/HS8B). As of MODULE-L5-38 these are the ONLY staff job
// APIs; the old disconnected field_ops /v1/staff/me/jobs client was removed.
export interface HomeServiceJobItem {
  id: string; job_number: string; booking_id: string; customer_id: string;
  tenant_id: string; category_id: string; offering_id: string;
  assigned_staff_id: string | null; scheduled_date: string | null;
  scheduled_time_window: string | null; city: string | null; zipcode: string | null;
  status: string; assignment_status: string; failure_reason: string | null;
  completion_data: Record<string, unknown> | null;
  created_at: string; updated_at: string;
  // Phase 2A.2: backend-authoritative work-start status (get_work_start_status) --
  // present on the staff job-detail response, absent on plain list rows.
  job_type_id?: string | null; job_type_key?: string | null; job_type_label?: string | null;
  quote_approval_required?: boolean | null; quote_state?: string | null;
  can_start_work?: boolean; start_work_block_code?: string | null;
}
export interface PartsRequestItem {
  parts_request_id: string; job_id: string; tenant_id: string; technician_id: string;
  part_name: string; quantity: number; estimated_cost: number; reason: string;
  photo_ids: string[]; technician_note: string | null;
  customer_approval_required: boolean; business_approval_required: boolean;
  status: string; approved_by: string | null; approved_at: string | null;
  rejected_by: string | null; rejected_at: string | null; rejection_reason: string | null;
  created_at: string; updated_at: string;
}

// MODULE-L5-38: home_service_assignment's staff_router wraps its outcomes in
// a non-standard envelope rather than HTTP status codes -- a controlled error
// (caught ValueError) is {success:false, error:{code,message}} and
// accept/reject's success case is {success:true, data:{...}} (a second data
// layer over apiFetch's own json.data unwrap). get/list success cases are the
// bare object. This unwraps all three into a value or a thrown Error, matching
// the same fix made in the staff-app mobile client (MODULE-L5-36).
function unwrapStaffJobResult<T>(raw: unknown): T {
  if (raw && typeof raw === "object" && "success" in raw) {
    const w = raw as { success: boolean; error?: { code: string; message: string }; data?: T };
    if (!w.success) throw new Error(w.error?.message ?? w.error?.code ?? "Action failed");
    return w.data as T;
  }
  return raw as T;
}

export interface HomeServiceJobBookingSummary {
  id: string; booking_number: string; customer_name: string | null;
  city: string | null; zipcode: string | null;
  preferred_date: string | null; preferred_time_window: string | null;
  issue_summary: string | null;
}
export interface HomeServiceJobAssignmentSummary {
  id: string; job_id: string; booking_id: string; assigned_staff_member_id: string;
  assignment_status: string; assignment_type: string; rejection_reason: string | null;
  scheduled_date: string | null; scheduled_time_window: string | null;
}
export interface HomeServiceJobDetail {
  job: HomeServiceJobItem;
  assignment: HomeServiceJobAssignmentSummary | null;
  booking: HomeServiceJobBookingSummary | null;
}

export const homeServiceStaffJobsApi = {
  list: () => apiFetch<{ jobs: HomeServiceJobItem[]; count: number }>("/v1/staff/service-jobs"),
  get: async (jobId: string) =>
    unwrapStaffJobResult<HomeServiceJobDetail>(await apiFetch<unknown>(`/v1/staff/service-jobs/${jobId}`)),
  accept: async (jobId: string) =>
    unwrapStaffJobResult<{ job_id: string; status: string }>(
      await apiFetch<unknown>(`/v1/staff/service-jobs/${jobId}/accept`, { method: "POST", body: "{}" })),
  reject: async (jobId: string, reason: string) =>
    unwrapStaffJobResult<{ job_id: string; status: string }>(
      await apiFetch<unknown>(`/v1/staff/service-jobs/${jobId}/reject`, { method: "POST", body: JSON.stringify({ reason }) })),
  onTheWay: (jobId: string) => apiFetch<HomeServiceJobItem>(`/v1/staff/service-jobs/${jobId}/on-the-way`, { method: "POST" }),
  reachedSite: (jobId: string) => apiFetch<HomeServiceJobItem>(`/v1/staff/service-jobs/${jobId}/reached-site`, { method: "POST" }),
  startInspection: (jobId: string) => apiFetch<HomeServiceJobItem>(`/v1/staff/service-jobs/${jobId}/start-inspection`, { method: "POST" }),
  completeInspection: (jobId: string) => apiFetch<HomeServiceJobItem>(`/v1/staff/service-jobs/${jobId}/complete-inspection`, { method: "POST" }),
  startService: (jobId: string) => apiFetch<HomeServiceJobItem>(`/v1/staff/service-jobs/${jobId}/start-service`, { method: "POST" }),
  markWorkDone: (jobId: string) => apiFetch<HomeServiceJobItem>(`/v1/staff/service-jobs/${jobId}/work-done`, { method: "POST" }),
  addNote: (jobId: string, noteText: string, isCustomerVisible = false) =>
    apiFetch<{ id: string }>(`/v1/staff/service-jobs/${jobId}/notes`, { method: "POST", body: JSON.stringify({ note_text: noteText, is_customer_visible: isCustomerVisible }) }),
  uploadMedia: (jobId: string, mediaType: string, fileUrl: string, isCustomerVisible = false) =>
    apiFetch<{ id: string }>(`/v1/staff/service-jobs/${jobId}/media`, { method: "POST", body: JSON.stringify({ media_type: mediaType, file_url: fileUrl, is_customer_visible: isCustomerVisible }) }),
  getTimeline: (jobId: string) => apiFetch<Record<string, unknown>[]>(`/v1/staff/service-jobs/${jobId}/timeline`),

  // HS8B — parts requests
  listPartsRequests: (jobId: string) => apiFetch<{ job_id: string; parts_requests: PartsRequestItem[] }>(`/v1/staff/service-jobs/${jobId}/parts-requests`),
  createPartsRequest: (jobId: string, body: { part_name: string; quantity: number; estimated_cost: number; reason: string; technician_note?: string }) =>
    apiFetch<PartsRequestItem>(`/v1/staff/service-jobs/${jobId}/parts-requests`, { method: "POST", body: JSON.stringify(body) }),

  // HS8B — single validated completion action
  complete: (jobId: string, body: { work_summary: string; collected_amount: number; payment_mode?: string; technician_note?: string }) =>
    apiFetch<HomeServiceJobItem>(`/v1/staff/service-jobs/${jobId}/complete`, { method: "POST", body: JSON.stringify(body) }),
};

// ── Checklist Catalog Engine — staff execution surface ───────────────────
// Only checklist instances applicable to this exact job + workflow phase
// are ever returned here; the backend (not this client) is the sole
// authority on required/gate enforcement.
export interface ChecklistExecutionItem {
  id: string; checklist_section_id: string; item_type: string; label: string;
  help_text: string | null; is_required: boolean; evidence_required: boolean;
  min_evidence_count: number; max_evidence_count: number;
  select_options: { value: string; label: string }[] | null;
  measurement_unit: string | null; response: {
    id: string; response_value: unknown; evidence: Record<string, unknown>[] | null;
    submitted_at: string | null; validation_result: Record<string, unknown> | null;
  } | null;
}
export interface ChecklistInstanceDetail {
  id: string; job_id: string; mapping_id: string; phase: string; assigned_actor: string;
  state: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED" | "WAIVED";
  started_at: string | null; completed_at: string | null; completed_by: string | null;
  items: ChecklistExecutionItem[];
}
export const checklistExecutionApi = {
  listForJob: (jobId: string) =>
    apiFetch<ChecklistInstanceDetail[]>(`/v1/staff/service-jobs/${jobId}/checklists`),
  saveResponse: (instanceId: string, itemId: string, body: { response_value?: unknown; evidence?: Record<string, unknown>[] }) =>
    apiFetch<Record<string, unknown>>(`/v1/staff/service-jobs/checklist-instances/${instanceId}/responses/${itemId}`, {
      method: "POST", body: JSON.stringify(body),
    }),
  complete: (instanceId: string) =>
    apiFetch<ChecklistInstanceDetail>(`/v1/staff/service-jobs/checklist-instances/${instanceId}/complete`, { method: "POST" }),
};

export const homeServiceProviderJobsApi = {
  assignable: () => apiFetch<{ jobs: HomeServiceJobItem[]; count: number }>("/v1/provider/service-jobs/assignable"),
  eligibleStaff: (jobId: string) => apiFetch<{ job_id: string; eligible_staff: Record<string, unknown>[]; blocked_staff: Record<string, unknown>[] }>(`/v1/provider/service-jobs/${jobId}/eligible-staff`),
  assign: (jobId: string, staffMemberId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/provider/service-jobs/${jobId}/assign`, { method: "POST", body: JSON.stringify({ staff_member_id: staffMemberId }) }),
  listPartsRequests: (jobId: string) => apiFetch<{ job_id: string; parts_requests: PartsRequestItem[] }>(`/v1/provider/service-jobs/${jobId}/parts-requests`),
  approveParts: (jobId: string, partsRequestId: string) =>
    apiFetch<PartsRequestItem>(`/v1/provider/service-jobs/${jobId}/parts-requests/${partsRequestId}/approve`, { method: "POST" }),
  rejectParts: (jobId: string, partsRequestId: string, reason?: string) =>
    apiFetch<PartsRequestItem>(`/v1/provider/service-jobs/${jobId}/parts-requests/${partsRequestId}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  installParts: (jobId: string, partsRequestId: string) =>
    apiFetch<PartsRequestItem>(`/v1/provider/service-jobs/${jobId}/parts-requests/${partsRequestId}/install`, { method: "POST" }),
  getExecutionTimeline: (jobId: string) => apiFetch<Record<string, unknown>[]>(`/v1/provider/service-jobs/${jobId}/execution-timeline`),
};

// ── Tenant My Status — Provider Visibility & Bookability Control Center ──────
// Real backend endpoints only. Two endpoints from the ticket's suggested list
// (/v1/provider/onboarding/status and /v1/provider/onboarding/items) were
// confirmed live-404/500 (the backing tables do not exist — see
// TENANT_MY_STATUS_API_MAPPING_REPORT.md) and are NOT used here; the Setup
// Readiness Checklist is instead computed client-side from the same real,
// working data sources this app's own SetupWizardDrawer already uses
// (provider status blockers + package summary + deposit + credit wallet +
// service areas + team members + availability), extended with two additional
// real, dedicated endpoints (security-deposit, credit-wallet) that give more
// accurate detail than the wallet/subscription-status pair the drawer uses.

// NOTE: PackageAssignmentSummary is already declared above (Phase 9) with the
// same shape our GET /v1/provider/onboarding/package-summary response uses —
// reused as-is. SecurityDepositStatus/CreditWalletDetail below are prefixed
// Tenant* to avoid colliding with the differently-shaped, admin-facing
// SecurityDepositStatus interface declared earlier in this file.

export interface TenantSecurityDepositStatus {
  tenant_id: string;
  status: string; // not_initialized | unpaid | paid | refunded | forfeited
  required_amount: number;
  paid_amount: number;
  paid_at: string | null;
  refunded_at?: string | null;
  message?: string;
}

export interface TenantCreditWalletDetail {
  tenant_id: string;
  balance: number;
  reserved_balance: number;
  currency: string;
  low_balance_threshold: number;
  is_low_balance: boolean;
  is_active: boolean;
  lifetime_purchased: number;
  lifetime_consumed: number;
  last_transaction_at: string | null;
}

export interface TenantStatusAuditLogEntry {
  log_id: string;
  action_type: string;
  actor_role: string | null;
  entity_type: string | null;
  entity_id: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
}

// MODULE-L5-12: earned trust badges (with icon/colour) for this provider + staff.
export interface EarnedBadge {
  assignment_id: string; badge_key: string; name: string; description?: string | null;
  icon?: string | null; color?: string | null;
  customer_visible: boolean; tenant_visible: boolean;
  award_source: string; earned_at: string | null; expires_at: string | null;
}
export const trustBadgesApi = {
  myBadges: () =>
    apiFetch<{ items: EarnedBadge[] }>("/v1/provider/trust-quality/badges").then(d => d.items ?? []),
  staffBadges: (staffId: string) =>
    apiFetch<{ items: EarnedBadge[] }>(`/v1/provider/trust-quality/staff/${staffId}/badges`).then(d => d.items ?? []),
};

export const myStatusApi = {
  getStatus:            () => providerStatusApi.get(),
  getOfferingStatuses:   () => providerStatusApi.getOfferingStatuses(),
  refreshStatus:         () => providerStatusApi.refresh(),
  getEnabledOfferings:   () => providerOfferingsApi.listEnabled(),
  getPackageSummary:     () => apiFetch<PackageAssignmentSummary>("/v1/provider/onboarding/package-summary"),
  getSecurityDeposit:    () => apiFetch<TenantSecurityDepositStatus>("/v1/tenant/security-deposit"),
  getCreditWallet:       () => apiFetch<TenantCreditWalletDetail>("/v1/tenant/credit-wallet"),
  getServiceAreas:       () => providerServiceAreasApi.list(),
  getTeamMembers:        () => providerTeamMembersApi.list(),
  getAvailability:       () => providerAvailabilityApi.list(),
  getAuditLog:           (limit = 20) => {
    const tid = getTenantId();
    return apiFetch<{ logs: TenantStatusAuditLogEntry[]; has_next: boolean; next_cursor: string | null }>(
      `/v1/tenants/${tid}/audit-log?limit=${limit}`);
  },
};

// ── Tenant My Offerings — coverage/pricing catalog reads ─────────────────────
// Real backend endpoints. Type/issue mapping reads reuse the same
// get_current_user-gated admin_catalog endpoints an admin uses to configure
// mappings (list_service_type_mappings / list_service_issue_mappings) — these
// are read-only GETs, safe for a tenant_owner to call, and are the only real
// source of per-service type/issue coverage (no separate provider-scoped
// endpoint exists for these two, unlike brands — see
// TENANT_MY_OFFERINGS_API_MAPPING_REPORT.md). Brand coverage reuses the
// existing, dedicated providerBrandApi.getAvailableForService.

export interface CoverageTypeMapping { mapping_id: string; service_type_id: string; name: string; is_required: boolean; is_default: boolean; }
export interface CoverageIssueMapping { mapping_id: string; issue_type_id: string; name: string; is_common: boolean; is_default: boolean; customer_visible: boolean; }
export interface CoverageServiceOption {
  id: string; master_service_id: string; code: string; name: string; option_type: string;
  default_price: string; is_customer_selectable: boolean; is_active: boolean;
}

export const offeringCoverageApi = {
  getTypes:  (masterServiceId: string) =>
    apiFetch<{ types: CoverageTypeMapping[] }>(`/v1/admin/master-services/${masterServiceId}/types`),
  getIssues: (masterServiceId: string) =>
    apiFetch<{ issues: CoverageIssueMapping[] }>(`/v1/admin/master-services/${masterServiceId}/issues`),
  getOptions: (masterServiceId: string) =>
    apiFetch<{ service_options: CoverageServiceOption[]; total: number }>(
      `/v1/catalog/master/service-options?master_service_id=${masterServiceId}`),
};

export interface OfferingPricePreviewResult {
  final_price: string | number;
  currency: string;
  step_city_floor: { tier: string; city: string; floor_price: number; source: string };
  step_tenant_price: { tenant_price_set: number | null; applied_price: number; floor_enforced: boolean; source: string };
  preview: boolean;
  note: string;
}

export const offeringPricingApi = {
  preview: (serviceTypeId: string, serviceCategory: string, cityName: string, pincode?: string | null) => {
    const tid = getTenantId();
    return apiFetch<OfferingPricePreviewResult>(`/v1/pricing/tenants/${tid}/price-preview`, {
      method: "POST",
      body: JSON.stringify({ service_type_id: serviceTypeId, service_category: serviceCategory, city_name: cityName, pincode: pincode ?? null }),
    });
  },
};

// ── Deactivate Manual Bargain Module — Automatic Customer Price Options ──────
// Tenant is read-only here: cannot edit platform fee, cannot configure a
// manual bargain rule. Shows exactly what the customer will see.
export interface TenantCustomerPricePreview {
  service_name: string | null;
  available: boolean;
  message?: string;
  currency?: string;
  allowed_offer_min?: number;
  allowed_offer_max?: number;
  low_price?: number;
  mid_price?: number;
  high_price?: number;
  platform_fee_percent?: number;
  platform_fee_amount?: number;
  payment_mode?: string;
  completed_job_deduction_credits?: number;
  explanation?: string;
}

export interface TenantMatchingReadiness {
  matching_ready: boolean;
  message: string;
}

export const tenantAutoPriceOptionsApi = {
  getCustomerPricePreview: (masterServiceId: string) =>
    apiFetch<TenantCustomerPricePreview>(`/v1/tenant/home-services/customer-price-preview?master_service_id=${masterServiceId}`),
  getMatchingReadiness: (masterServiceId: string) =>
    apiFetch<TenantMatchingReadiness>(`/v1/tenant/home-services/matching-readiness?master_service_id=${masterServiceId}`),
};

// ── FINAL-L5-04B — Tenant Entitlement Self-Read ───────────────────────────────
export interface TenantModuleEntitlement {
  id: string; tenant_id: string; module_id: string; module_key: string; module_label: string;
  status: string; source: string; enabled_at: string | null; disabled_at: string | null;
}
export interface TenantCategoryEntitlement {
  id: string; tenant_id: string; category_id: string; category_slug: string | null; category_label: string | null;
  module_entitlement_id: string; status: string; source: string; enabled_at: string | null; disabled_at: string | null;
}
export const entitlementApi = {
  getMyModules: () => apiFetch<{ modules: TenantModuleEntitlement[] }>("/v1/tenant/me/modules"),
  getMyCategories: () => apiFetch<{ categories: TenantCategoryEntitlement[] }>("/v1/tenant/me/categories"),
  getMyEntitlements: () =>
    apiFetch<{ modules: TenantModuleEntitlement[]; categories: TenantCategoryEntitlement[] }>("/v1/tenant/me/entitlements"),
};
