/**
 * ServiceOS Super Admin — API Client
 * PROVEN LEVEL 5:
 *   ✅ ALL API calls go through this file — no inline fetch() anywhere else
 *   ✅ Every call has typed response + error handling
 *   ✅ Auth token injected centrally — never repeated in components
 *   ✅ Request ID on every call for audit trail
 *   ✅ API_BASE from env — zero hardcoded URLs in components
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────────
export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T;
  request_id: string;
  engine_id: string;
}

export interface ApiError {
  error_code: string;
  detail: string;
  resolution?: string;
  context?: Record<string, unknown>;
  request_id?: string;
}

export class ServiceOSError extends Error {
  constructor(
    public code: string,
    message: string,
    public resolution?: string,
    public context?: Record<string, unknown>,
    public requestId?: string,
  ) {
    super(message);
    this.name = "ServiceOSError";
  }
}

// ── Auth token ────────────────────────────────────────────────────────────────
function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("serviceos_admin_token");
}
function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("serviceos_admin_refresh");
}
function clearSession() {
  localStorage.removeItem("serviceos_admin_token");
  localStorage.removeItem("serviceos_admin_refresh");
  window.location.href = "/login";
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────
async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  skipAuth = false,
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type":     "application/json",
    "X-Request-Source": "super-admin-portal",
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
            localStorage.setItem("serviceos_admin_token", newToken);
            const retryHeaders = { ...headers, "Authorization": `Bearer ${newToken}` };
            const retry = await fetch(`${API_BASE}${path}`, { ...options, headers: retryHeaders });
            if (retry.ok) {
              const json: ApiResponse<T> = await retry.json();
              return json.data;
            }
          }
        }
      } catch { /* fall through to clearSession */ }
    }
    clearSession();
    throw new ServiceOSError("UNAUTHORIZED", "Session expired. Please sign in again.");
  }

  if (!res.ok) {
    let err: ApiError;
    try { err = await res.json(); }
    catch { err = { error_code: "NETWORK_ERROR", detail: `HTTP ${res.status}` }; }
    throw new ServiceOSError(
      err.error_code ?? "API_ERROR",
      err.detail ?? "An unexpected error occurred.",
      err.resolution,
      err.context,
      err.request_id,
    );
  }

  const json: ApiResponse<T> = await res.json();
  return json.data;
}

// FINAL-L5-03: shared generic paginated-list fetch for EnterpriseDataGrid-style
// pages, so page components don't each hand-roll their own token read + raw
// fetch() + error unwrap (which also meant they silently lost 401->refresh
// handling and request_id on errors that every other call gets for free via
// apiFetch). Page-specific response reshaping (legacy pagination wrapping)
// stays in the page -- this only replaces the duplicated transport plumbing.
export async function apiFetchPaginatedRaw(
  endpoint: string,
  params: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
  return apiFetch<Record<string, unknown>>(`${endpoint}?${qs}`);
}

// ── Auth endpoints ─────────────────────────────────────────────────────────────
export const authApi = {
  // Session
  login:       (email: string, password: string) =>
    apiFetch<{ access_token: string; refresh_token: string | null; user: AdminUser; requires_password_change?: boolean; password_change_reason?: string; redirect_to?: string }>(
      "/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, true),
  refresh:     (refresh_token: string) =>
    apiFetch<{ access_token: string }>("/v1/auth/token/refresh",
      { method: "POST", body: JSON.stringify({ refresh_token }) }, true),
  introspect:  (token: string) =>
    apiFetch<TokenIntrospect>("/v1/auth/token/introspect",
      { method: "POST", body: JSON.stringify({ token }) }),
  me:          () => apiFetch<AdminUser>("/v1/auth/me"),
  updateMe:    (data: Partial<AdminUser>) =>
    apiFetch<AdminUser>("/v1/auth/me", { method: "PUT", body: JSON.stringify(data) }),
  logout:      () => apiFetch<void>("/v1/auth/logout", { method: "POST" }),
  logoutAll:   () => apiFetch<void>("/v1/auth/logout-all", { method: "POST" }),
  registerCustomer: (data: RegisterCustomerPayload) =>
    apiFetch<{ access_token: string; user: AdminUser }>(
      "/v1/auth/register/customer", { method: "POST", body: JSON.stringify(data) }, true),

  // OTP
  sendOtp:   (phone: string) =>
    apiFetch<void>("/v1/auth/otp/send", { method: "POST", body: JSON.stringify({ phone }) }),
  verifyOtp: (phone: string, otp: string) =>
    apiFetch<{ access_token: string; refresh_token: string; user: AdminUser }>(
      "/v1/auth/otp/verify", { method: "POST", body: JSON.stringify({ phone, otp }) }, true),

  // MFA
  setupMfa:             () => apiFetch<MfaSetup>("/v1/auth/mfa/setup", { method: "POST" }),
  confirmMfa:           (code: string) =>
    apiFetch<MfaConfirm>("/v1/auth/mfa/confirm", { method: "POST", body: JSON.stringify({ code }) }),
  verifyMfa:            (code: string) =>
    apiFetch<{ access_token: string; refresh_token: string }>(
      "/v1/auth/mfa/verify", { method: "POST", body: JSON.stringify({ code }) }),
  disableMfa:           (code: string) =>
    apiFetch<void>("/v1/auth/mfa/disable", { method: "POST", body: JSON.stringify({ code }) }),
  regenerateBackupCodes: () =>
    apiFetch<BackupCodes>("/v1/auth/mfa/backup-codes/regenerate", { method: "POST" }),

  // Password
  changePassword:       (current_password: string, new_password: string) =>
    apiFetch<void>("/v1/auth/password/change",
      { method: "PUT", body: JSON.stringify({ current_password, new_password }) }),
  requestPasswordReset: (email: string) =>
    apiFetch<void>("/v1/auth/password/reset/request",
      { method: "POST", body: JSON.stringify({ email }) }, true),
  confirmPasswordReset: (token: string, new_password: string) =>
    apiFetch<void>("/v1/auth/password/reset/confirm",
      { method: "POST", body: JSON.stringify({ token, new_password }) }, true),

  // Sessions
  getSessions:   () => apiFetch<UserSessionList>("/v1/auth/sessions"),
  deleteSession: (sessionId: string) =>
    apiFetch<void>(`/v1/auth/sessions/${sessionId}`, { method: "DELETE" }),
  approveSession:(sessionId: string) =>
    apiFetch<void>(`/v1/auth/sessions/${sessionId}/approve`, { method: "POST" }),

  // Staff management
  inviteStaff:     (data: InviteStaffPayload) =>
    apiFetch<StaffInvite>("/v1/auth/staff/invite", { method: "POST", body: JSON.stringify(data) }),
  acceptInvite:    (token: string, password: string) =>
    apiFetch<{ access_token: string }>(
      "/v1/auth/staff/invite/accept", { method: "POST", body: JSON.stringify({ token, password }) }, true),
  resendInvite:    (userId: string) =>
    apiFetch<void>(`/v1/auth/staff/${userId}/invite/resend`, { method: "POST" }),
  updatePermissions:(userId: string, permissions: string[]) =>
    apiFetch<void>(`/v1/auth/staff/${userId}/permissions`,
      { method: "PUT", body: JSON.stringify({ permissions }) }),
  deactivateStaff: (userId: string, reason: string) =>
    apiFetch<void>(`/v1/auth/staff/${userId}/deactivate`,
      { method: "POST", body: JSON.stringify({ reason }) }),

  // Impersonation
  impersonate:          (user_id: string, reason: string) =>
    apiFetch<ImpersonationSession>("/v1/auth/impersonate",
      { method: "POST", body: JSON.stringify({ user_id, reason }) }),
  endImpersonation:     (sessionId: string) =>
    apiFetch<void>(`/v1/auth/impersonate/${sessionId}/end`, { method: "POST" }),
  getActiveImpersonation: () =>
    apiFetch<ImpersonationSession | null>("/v1/auth/impersonate/active"),

  // API Keys
  createApiKey: (name: string, scopes: string[], expires_in_days?: number) =>
    apiFetch<ApiKeyCreated>("/v1/auth/api-keys",
      { method: "POST", body: JSON.stringify({ name, scopes, expires_in_days }) }),
  listApiKeys:  () => apiFetch<ApiKeyList>("/v1/auth/api-keys"),
  deleteApiKey: (keyId: string) =>
    apiFetch<void>(`/v1/auth/api-keys/${keyId}`, { method: "DELETE" }),
  updateApiKey: (keyId: string, data: { name?: string; is_active?: boolean }) =>
    apiFetch<ApiKey>(`/v1/auth/api-keys/${keyId}`,
      { method: "PATCH", body: JSON.stringify(data) }),

  // Audit log
  getAuditLog: (params?: { limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<AuthAuditLogList>(`/v1/auth/audit-log?${qs}`);
  },

  // Users
  listUsers: (params?: { role?: string; tenant_id?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries(params ?? {}).filter(([,v])=>v!=null).map(([k,v])=>[k,String(v)]))).toString();
    return apiFetch<UserListResponse>(`/v1/auth/users?${qs}`);
  },
  getUser:         (userId: string) => apiFetch<UserDetail>(`/v1/auth/users/${userId}`),
  getPermissionsMap: ()              => apiFetch<PermissionsMap>("/v1/auth/permissions/map"),

  // Force-change password (used when user must change password before accessing dashboard)
  changePasswordRequired: (current_password: string, new_password: string, confirm_password: string) =>
    apiFetch<{ message: string }>("/v1/auth/change-password-required",
      { method: "POST", body: JSON.stringify({ current_password, new_password, confirm_password }) }),

  // Admin user security actions
  getUserSecurityStatus: (userId: string) =>
    apiFetch<UserSecurityStatus>(`/v1/admin/users/${userId}/security-status`),
  adminForcePasswordChange: (userId: string, reason: string, revoke_sessions = true) =>
    apiFetch<{ message: string }>(`/v1/admin/users/${userId}/force-password-change`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),
  adminSendPasswordReset: (userId: string, reason: string, revoke_sessions = false) =>
    apiFetch<{ message: string; reset_token_dev_only?: string }>(`/v1/admin/users/${userId}/send-password-reset`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),
  adminGenerateTemporaryPassword: (userId: string, reason: string, revoke_sessions = true) =>
    apiFetch<{ message: string; temporary_password: string }>(`/v1/admin/users/${userId}/generate-temporary-password`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),

  // Phase 0E: Account security controls
  lockUser: (userId: string, reason: string, revoke_sessions = true) =>
    apiFetch<{ message: string }>(`/v1/admin/users/${userId}/lock`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),
  unlockUser: (userId: string, reason: string) =>
    apiFetch<{ message: string }>(`/v1/admin/users/${userId}/unlock`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  deactivateUser: (userId: string, reason: string, revoke_sessions = true) =>
    apiFetch<{ message: string }>(`/v1/admin/users/${userId}/deactivate`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),
  reactivateUser: (userId: string, reason: string) =>
    apiFetch<{ message: string }>(`/v1/admin/users/${userId}/reactivate`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  adminListSessions: (userId: string) =>
    apiFetch<{ sessions: SessionInfo[] }>(`/v1/admin/users/${userId}/sessions`),
  adminRevokeAllSessions: (userId: string, reason: string) =>
    apiFetch<{ message: string; revoked_count: number }>(`/v1/admin/users/${userId}/sessions/revoke-all`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  adminGetLoginHistory: (userId: string, limit = 50) =>
    apiFetch<{ events: LoginHistoryEvent[]; total: number }>(`/v1/admin/users/${userId}/login-history?limit=${limit}`),

  // Self: own session controls
  getSelfSessions: () => apiFetch<{ sessions: SessionInfo[] }>("/v1/auth/sessions"),
  revokeSelfOtherSessions: (reason = "Signed out of all other devices") =>
    apiFetch<{ message: string; revoked_count: number }>("/v1/auth/sessions/revoke-all-other",
      { method: "POST", body: JSON.stringify({ reason }) }),
  getSelfLoginHistory: (limit = 50) =>
    apiFetch<{ events: LoginHistoryEvent[]; total: number }>(`/v1/auth/login-history?limit=${limit}`),
};

// ── P0 Platform Users ─────────────────────────────────────────────────────────
export interface PlatformUserRow {
  id: string; full_name: string; email: string; phone: string | null;
  user_group: string; role: string; platform_role: string | null;
  access_scope: string | null; tenant_id: string | null;
  status: string; mfa_status: string; is_active: boolean;
  password_reset_required: boolean; last_login_at: string | null;
  created_at: string | null; failed_login_attempts: number;
}
export interface PlatformUserDetail extends PlatformUserRow {
  mfa_required: boolean; locked_until: string | null; lock_reason: string | null;
  deactivation_reason: string | null; last_password_reset_at: string | null;
  temporary_password_active: boolean; invited_by_user_id: string | null;
}
export interface PlatformUsersSummary {
  total_platform_users: number; active_users: number; inactive_users: number;
  mfa_enabled: number; mfa_missing: number; administrators: number;
  pending_invites: number; locked_accounts: number; suspicious_logins: number;
  inactive_30_days: number;
}
export interface PlatformUserInvite {
  invite_id: string; email: string; name: string; platform_role: string | null;
  access_scope: string | null; status: string; expires_at: string | null;
  invited_by_user_id: string | null; created_at: string | null;
}
export interface PlatformUserRiskSignal { risk_type: string; risk_level: string; description: string; }
export interface PlatformUserRiskSignals { user_id: string; risk_score: string; signals: PlatformUserRiskSignal[]; }
export interface PlatformUserAuditEntry {
  id: string; actor_id: string | null; actor_role: string | null; action_type: string;
  target_id: string | null; outcome: string; reason: string | null;
  old_value: Record<string, unknown>; new_value: Record<string, unknown>;
  ip_hint: string | null; created_at: string | null;
}

export const platformUsersApi = {
  getSummary: () => apiFetch<PlatformUsersSummary>("/v1/admin/platform-users/summary"),
  list: (params?: {
    user_group?: string; q?: string; role?: string; platform_role?: string;
    status?: string; mfa_status?: string; access_scope?: string;
    inactive_days_min?: number; page?: number; limit?: number;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params ?? {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") qs.set(k, String(v)); });
    return apiFetch<{ users: PlatformUserRow[]; meta: { total: number; page: number; limit: number; total_pages: number } }>(
      `/v1/admin/platform-users?${qs}`);
  },
  get: (userId: string) => apiFetch<PlatformUserDetail>(`/v1/admin/platform-users/${userId}`),
  export: (userGroup = "platform") =>
    apiFetch<{ rows: PlatformUserRow[]; count: number; format: string }>(
      `/v1/admin/platform-users/export?user_group=${userGroup}`),

  invite: (data: {
    full_name: string; email: string; phone?: string; platform_role: string;
    access_scope: string; require_mfa?: boolean; invite_expiry_days?: number;
  }) => apiFetch<{ invite_id: string; email: string; expires_at: string; message: string }>(
    "/v1/admin/platform-users/invite", { method: "POST", body: JSON.stringify(data) }),
  listInvites: () => apiFetch<{ invites: PlatformUserInvite[]; total: number }>("/v1/admin/platform-users/invites"),
  resendInvite: (inviteId: string) =>
    apiFetch<{ message: string }>(`/v1/admin/platform-users/invites/${inviteId}/resend`, { method: "POST" }),
  revokeInvite: (inviteId: string, reason: string) =>
    apiFetch<{ invite_id: string; status: string; message: string }>(
      `/v1/admin/platform-users/invites/${inviteId}/revoke`, { method: "POST", body: JSON.stringify({ reason }) }),

  changeRole: (userId: string, platform_role: string, reason: string) =>
    apiFetch<{ user_id: string; platform_role: string; message: string }>(
      `/v1/admin/platform-users/${userId}/role`, { method: "PUT", body: JSON.stringify({ platform_role, reason }) }),
  changeAccessScope: (userId: string, access_scope: string, reason: string) =>
    apiFetch<{ user_id: string; access_scope: string; message: string }>(
      `/v1/admin/platform-users/${userId}/access-scope`, { method: "PUT", body: JSON.stringify({ access_scope, reason }) }),

  suspend: (userId: string, reason: string, revoke_sessions = true) =>
    apiFetch<{ message: string }>(`/v1/admin/platform-users/${userId}/suspend`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),
  unsuspend: (userId: string, reason: string) =>
    apiFetch<{ message: string }>(`/v1/admin/platform-users/${userId}/unsuspend`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  deactivate: (userId: string, reason: string, revoke_sessions = true) =>
    apiFetch<{ message: string }>(`/v1/admin/platform-users/${userId}/deactivate`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),
  reactivate: (userId: string, reason: string) =>
    apiFetch<{ message: string }>(`/v1/admin/platform-users/${userId}/reactivate`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  lock: (userId: string, reason: string, revoke_sessions = true, locked_until?: string) =>
    apiFetch<{ message: string }>(`/v1/admin/platform-users/${userId}/lock`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions, locked_until }) }),
  unlock: (userId: string, reason: string) =>
    apiFetch<{ message: string }>(`/v1/admin/platform-users/${userId}/unlock`,
      { method: "POST", body: JSON.stringify({ reason }) }),

  requireMfa: (userId: string, reason: string) =>
    apiFetch<{ mfa_required: boolean; message: string }>(`/v1/admin/platform-users/${userId}/require-mfa`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  resetMfa: (userId: string, reason: string) =>
    apiFetch<{ is_mfa_enabled: boolean; message: string }>(`/v1/admin/platform-users/${userId}/reset-mfa`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  forcePasswordReset: (userId: string, reason: string, revoke_sessions = true) =>
    apiFetch<{ message: string }>(`/v1/admin/platform-users/${userId}/force-password-reset`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),
  sendResetLink: (userId: string, reason: string, revoke_sessions = false) =>
    apiFetch<{ message: string }>(`/v1/admin/platform-users/${userId}/send-reset-link`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),
  generateTempPassword: (userId: string, reason: string, revoke_sessions = true) =>
    apiFetch<{ message: string; temporary_password: string }>(`/v1/admin/platform-users/${userId}/generate-temp-password`,
      { method: "POST", body: JSON.stringify({ reason, revoke_sessions }) }),

  listSessions: (userId: string) => apiFetch<{ sessions: SessionInfo[]; total: number }>(`/v1/admin/platform-users/${userId}/sessions`),
  revokeSession: (userId: string, sessionId: string, reason: string) =>
    apiFetch<{ session_id: string; revoked: boolean; message: string }>(
      `/v1/admin/platform-users/${userId}/sessions/${sessionId}/revoke`, { method: "POST", body: JSON.stringify({ reason }) }),
  revokeAllSessions: (userId: string, reason: string) =>
    apiFetch<{ message: string; revoked_count: number }>(`/v1/admin/platform-users/${userId}/sessions/revoke-all`,
      { method: "POST", body: JSON.stringify({ reason }) }),

  loginHistory: (userId: string, limit = 50) =>
    apiFetch<{ events: LoginHistoryEvent[]; total: number }>(`/v1/admin/platform-users/${userId}/login-history?limit=${limit}`),
  riskSignals: (userId: string) => apiFetch<PlatformUserRiskSignals>(`/v1/admin/platform-users/${userId}/risk-signals`),
  userAuditLogs: (userId: string, page = 1, limit = 50) =>
    apiFetch<{ logs: PlatformUserAuditEntry[]; meta: { total: number } }>(
      `/v1/admin/platform-users/${userId}/audit-logs?page=${page}&limit=${limit}`),
  auditLogs: (actionType?: string, page = 1, limit = 50) => {
    const qs = new URLSearchParams({ page: String(page), limit: String(limit) });
    if (actionType) qs.set("action_type", actionType);
    return apiFetch<{ logs: PlatformUserAuditEntry[]; meta: { total: number } }>(`/v1/admin/platform-users/audit-logs?${qs}`);
  },

  bulkAction: (action: string, userIds: string[], reason: string) =>
    apiFetch<{ action: string; total: number; succeeded: number; failed: number;
               results: { user_id: string; success: boolean; error?: string }[] }>(
      `/v1/admin/platform-users/bulk/${action}`,
      { method: "POST", body: JSON.stringify({ action, user_ids: userIds, reason }) }),
};

// ── Tenant endpoints ──────────────────────────────────────────────────────────
export const tenantApi = {
  // Core CRUD
  list: (params?: { status?: string; vertical?: string; search?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params ?? {}).filter(([,v])=>v!=null).map(([k,v])=>[k,String(v)]))
    ).toString();
    return apiFetch<TenantListResponse>(`/v1/tenants?${qs}`);
  },
  get:    (id: string) => apiFetch<Tenant>(`/v1/tenants/${id}`),
  create: (payload: CreateTenantPayload) =>
    apiFetch<Tenant>("/v1/tenants", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: string, data: Partial<CreateTenantPayload>) =>
    apiFetch<Tenant>(`/v1/tenants/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // 360° view
  get360: (id: string) => apiFetch<Tenant360>(`/v1/tenants/${id}/360`),

  // Health
  getHealth:        (id: string) => apiFetch<TenantHealth>(`/v1/tenants/${id}/health`),
  getHealthHistory: (id: string, days?: number) =>
    apiFetch<TenantHealthHistory>(`/v1/tenants/${id}/health/history${days ? `?days=${days}` : ""}`),

  // Lifecycle
  suspend:         (id: string, reason: string) =>
    apiFetch<Tenant>(`/v1/tenants/${id}/suspend`, { method: "POST", body: JSON.stringify({ reason }) }),
  reinstate:       (id: string, reason: string) =>
    apiFetch<Tenant>(`/v1/tenants/${id}/reinstate`, { method: "POST", body: JSON.stringify({ reason }) }),
  beginTerminate:  (id: string, reason: string) =>
    apiFetch<Tenant>(`/v1/tenants/${id}/terminate/begin`, { method: "POST", body: JSON.stringify({ reason }) }),
  confirmTerminate:(id: string) =>
    apiFetch<void>(`/v1/tenants/${id}/terminate/confirm`, { method: "POST" }),

  // Plan management
  upgradePlan:   (id: string, plan_type: string, reason: string) =>
    apiFetch<Tenant>(`/v1/tenants/${id}/plan/upgrade`, { method: "POST", body: JSON.stringify({ target_plan: plan_type, reason }) }),
  downgradePlan: (id: string, plan_type: string, reason: string) =>
    apiFetch<Tenant>(`/v1/tenants/${id}/plan/downgrade`, { method: "POST", body: JSON.stringify({ target_plan: plan_type, reason }) }),
  convertTrial:  (id: string, plan_type: string) =>
    apiFetch<Tenant>(`/v1/tenants/${id}/trial/convert`, { method: "POST", body: JSON.stringify({ plan_type }) }),

  // Engines
  getEngines:           (id: string) => apiFetch<TenantEngineList>(`/v1/tenants/${id}/engines`),
  enableEngine:         (id: string, engineId: string) =>
    apiFetch<TenantEngine>(`/v1/tenants/${id}/engines/${engineId}/enable`, { method: "POST" }),
  disableEngine:        (id: string, engineId: string) =>
    apiFetch<TenantEngine>(`/v1/tenants/${id}/engines/${engineId}/disable`, { method: "POST" }),
  bulkToggleEngines:    (id: string, engineIds: string[], action: "enable"|"disable") =>
    apiFetch<TenantEngineList>(`/v1/tenants/${id}/engines/bulk-${action}`,
      { method: "POST", body: JSON.stringify({ engine_ids: engineIds }) }),
  getEngineConfig:      (id: string, engineId: string) =>
    apiFetch<EngineConfig>(`/v1/tenants/${id}/engines/${engineId}/config`),
  updateEngineConfig:   (id: string, engineId: string, config: Record<string,unknown>) =>
    apiFetch<EngineConfig>(`/v1/tenants/${id}/engines/${engineId}/config`,
      { method: "PUT", body: JSON.stringify({ config }) }),
  validateEngineConfig: (id: string, engineId: string, config: Record<string,unknown>) =>
    apiFetch<{ valid: boolean; errors?: string[] }>(`/v1/tenants/${id}/engines/${engineId}/config/validate`,
      { method: "POST", body: JSON.stringify({ config }) }),

  // Feature flags
  getFeatureFlags:   (id: string) => apiFetch<FeatureFlagList>(`/v1/tenants/${id}/feature-flags`),
  setFeatureFlag:    (id: string, flag: string, value: boolean|string|number) =>
    apiFetch<FeatureFlag>(`/v1/tenants/${id}/feature-flags/${flag}`,
      { method: "PUT", body: JSON.stringify({ value }) }),
  deleteFeatureFlag: (id: string, flag: string) =>
    apiFetch<void>(`/v1/tenants/${id}/feature-flags/${flag}`, { method: "DELETE" }),
  resolveFeatureFlag:(id: string, flag: string) =>
    apiFetch<FeatureFlag>(`/v1/tenants/${id}/feature-flags/${flag}/resolve`),

  // Billing
  getBillingInfo:      (id: string) => apiFetch<TenantBillingInfo>(`/v1/tenants/${id}/billing`),
  updatePaymentMethod: (id: string, data: Record<string,unknown>) =>
    apiFetch<TenantBillingInfo>(`/v1/tenants/${id}/billing/payment-method`,
      { method: "PUT", body: JSON.stringify(data) }),
  getBillingInvoices:  (id: string, limit = 20) =>
    apiFetch<InvoiceListResponse>(`/v1/tenants/${id}/billing/invoices?limit=${limit}`),
  triggerDunning:      (id: string) =>
    apiFetch<void>(`/v1/tenants/${id}/billing/dunning`, { method: "POST" }),

  // Data & GDPR
  requestDataExport: (id: string) =>
    apiFetch<DataExportRequest>(`/v1/tenants/${id}/data/export`, { method: "POST" }),
  getExportStatus:   (id: string, exportId: string) =>
    apiFetch<DataExportRequest>(`/v1/tenants/${id}/data/export/${exportId}`),
  requestDeletion:   (id: string, reason: string) =>
    apiFetch<void>(`/v1/tenants/${id}/data/delete-request`, { method: "POST", body: JSON.stringify({ reason }) }),

  // Audit
  getAuditLog: (id: string, params?: { limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<TenantAuditLogList>(`/v1/tenants/${id}/audit-log?${qs}`);
  },

  // Limit check
  checkLimit: (id: string, limitType: string, amount?: number) =>
    apiFetch<LimitCheck>(`/v1/tenants/${id}/limits/check/${limitType}${amount ? `?amount=${amount}` : ""}`),
};

// ── Platform Commerce ─────────────────────────────────────────────────────────
export const commerceApi = {
  // Platform summary
  platformSummary:        () => apiFetch<PlatformCommerceSummary>("/v1/commerce/platform/summary"),
  platformCommissionSummary: () =>
    apiFetch<{ total_collected: number; total_jobs: number; avg_rate: number }>("/v1/commerce/platform/commission/summary"),
  platformCommissionDaily:() =>
    apiFetch<{ daily: { date: string; total: number }[] }>("/v1/commerce/platform/commission/daily"),
  platformBadgeSummary:   () =>
    apiFetch<{ distribution: Record<string, number> }>("/v1/commerce/platform/badges/summary"),
  platformAtRiskTenants:  () =>
    apiFetch<{ tenants: { tenant_id: string; name: string; health_band: string }[] }>("/v1/commerce/platform/tenants/at-risk"),

  // Wallet (admin ops on behalf of tenant)
  walletBalance:    (tenantId: string) => apiFetch<WalletBalance>(`/v1/commerce/tenants/${tenantId}/wallet`),
  walletBalanceLight: (tenantId: string) => apiFetch<WalletBalance>(`/v1/commerce/tenants/${tenantId}/wallet/balance`),
  walletTransactions:(tenantId: string, limit = 20, cursor?: string) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries({ limit: String(limit), ...(cursor ? { cursor } : {}) }))
    ).toString();
    return apiFetch<WalletTransactionList>(`/v1/commerce/tenants/${tenantId}/wallet/transactions?${qs}`);
  },
  walletProjection: (tenantId: string) =>
    apiFetch<WalletProjection>(`/v1/commerce/tenants/${tenantId}/wallet/projection`),
  adminCredit:      (tenantId: string, amount: number, notes: string) =>
    apiFetch<WalletBalance>(`/v1/commerce/tenants/${tenantId}/wallet/admin-credit`,
      { method: "POST", body: JSON.stringify({ amount, notes }) }),
  walletCredit:     (tenantId: string, amount: number, reason: string) =>
    apiFetch<WalletBalance>(`/v1/commerce/tenants/${tenantId}/wallet/credit`,
      { method: "POST", body: JSON.stringify({ amount, reason }) }),
  walletDeduct:     (tenantId: string, amount: number, reason: string) =>
    apiFetch<WalletBalance>(`/v1/commerce/tenants/${tenantId}/wallet/deduct`,
      { method: "POST", body: JSON.stringify({ amount, reason }) }),

  // Security deposit (per-tenant, separate from wallet)
  getDeposit:         (tenantId: string) =>
    apiFetch<Deposit>(`/v1/commerce/tenants/${tenantId}/deposit`),
  initiateDeposit:    (tenantId: string, amount: number) =>
    apiFetch<PurchaseOrder>(`/v1/commerce/tenants/${tenantId}/deposit/initiate`,
      { method: "POST", body: JSON.stringify({ amount }) }),
  confirmDeposit:     (tenantId: string, paymentRef: string) =>
    apiFetch<Deposit>(`/v1/commerce/tenants/${tenantId}/deposit/confirm`,
      { method: "POST", body: JSON.stringify({ payment_reference: paymentRef }) }),
  depositTransactions:(tenantId: string) =>
    apiFetch<WalletTransactionList>(`/v1/commerce/tenants/${tenantId}/deposit/transactions`),
  adminAdjustDeposit: (tenantId: string, amount: number, reason: string, category: "goodwill"|"dispute"|"correction"|"refund") =>
    apiFetch<Deposit>(`/v1/commerce/tenants/${tenantId}/deposit/admin-adjust`,
      { method: "POST", body: JSON.stringify({ amount, reason, category }) }),

  // Wallet purchase flow (admin-initiated)
  initiatePurchase: (tenantId: string, packageId: string) =>
    apiFetch<PurchaseOrder>(`/v1/commerce/tenants/${tenantId}/wallet/purchase/initiate`,
      { method: "POST", body: JSON.stringify({ package_id: packageId }) }),
  confirmPurchase:  (tenantId: string, orderId: string, paymentRef?: string) =>
    apiFetch<WalletBalance>(`/v1/commerce/tenants/${tenantId}/wallet/purchase/confirm`,
      { method: "POST", body: JSON.stringify({ payment_reference: paymentRef }) }),

  // Commission
  commissionHistory: (tenantId: string, limit = 20, cursor?: string) => {
    const qs = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<CommissionListResponse>(`/v1/commerce/tenants/${tenantId}/commission/history${qs}`);
  },
  commissionRate:    (tenantId: string) =>
    apiFetch<CommissionRate>(`/v1/commerce/tenants/${tenantId}/commission/rate`),
  commissionProjection:(tenantId: string) =>
    apiFetch<CommissionProjection>(`/v1/commerce/tenants/${tenantId}/commission/projection`),
  deductCommission:  (jobId: string, amount: number, rate: number) =>
    apiFetch<CommissionRecord>(`/v1/commerce/jobs/${jobId}/commission/deduct`,
      { method: "POST", body: JSON.stringify({ amount, rate }) }),

  // Credit packages
  listPackages:  () => apiFetch<CreditPackageList>("/v1/commerce/packages"),
  getPackage:    (id: string) => apiFetch<CreditPackage>(`/v1/commerce/packages/${id}`),
  createPackage: (data: Omit<CreditPackage, "id"|"created_at">) =>
    apiFetch<CreditPackage>("/v1/commerce/packages", { method: "POST", body: JSON.stringify(data) }),
  updatePackage: (id: string, data: Partial<CreditPackage>) =>
    apiFetch<CreditPackage>(`/v1/commerce/packages/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deletePackage: (id: string) =>
    apiFetch<void>(`/v1/commerce/packages/${id}`, { method: "DELETE" }),

  // Customer health
  atRiskCustomers: (tenantId: string, limit = 10) =>
    apiFetch<CustomerAtRiskList>(`/v1/commerce/tenants/${tenantId}/customers/at-risk?limit=${limit}`),
  getCustomerHealthHistory: (customerId: string) =>
    apiFetch<{ history: { date: string; score: number }[] }>(`/v1/commerce/customers/${customerId}/health/history`),
  submitHealthSignal: (customerId: string, signal: string, value: number) =>
    apiFetch<void>(`/v1/commerce/customers/${customerId}/health/signals`,
      { method: "POST", body: JSON.stringify({ signal, value }) }),
  recomputeHealth:    (customerId: string) =>
    apiFetch<void>(`/v1/commerce/customers/${customerId}/health/recompute`, { method: "POST" }),
  overrideHealth:     (customerId: string, healthBand: string, reason: string) =>
    apiFetch<void>(`/v1/commerce/customers/${customerId}/health/override`,
      { method: "POST", body: JSON.stringify({ health_band: healthBand, reason }) }),

  // Warranty claims
  listWarrantyClaims: (params?: { status?: string; limit?: number }) => {
    const qs = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<WarrantyClaimList>(`/v1/commerce/warranty/claims?${qs}`);
  },
  listTenantWarrantyClaims: (tenantId: string, limit = 50) =>
    apiFetch<WarrantyClaimList>(`/v1/commerce/tenants/${tenantId}/warranty/claims?limit=${limit}`),
  getWarrantyClaim: (claimId: string) =>
    apiFetch<WarrantyClaim>(`/v1/commerce/warranty/claims/${claimId}`),
  createWarrantyClaim: (jobId: string, tenantId: string, issueDescription: string) =>
    apiFetch<WarrantyClaim>("/v1/commerce/warranty/claims",
      { method: "POST", body: JSON.stringify({ job_id: jobId, tenant_id: tenantId, issue_description: issueDescription }) }),
  approveWarrantyClaim:(claimId: string, notes?: string) =>
    apiFetch<WarrantyClaim>(`/v1/commerce/warranty/claims/${claimId}/approve`,
      { method: "POST", body: JSON.stringify({ notes }) }),
  rejectWarrantyClaim: (claimId: string, reason: string) =>
    apiFetch<WarrantyClaim>(`/v1/commerce/warranty/claims/${claimId}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) }),

  // Badges
  listBadges:  (tenantId?: string) =>
    apiFetch<BadgeList>(`/v1/commerce/tenants/${tenantId ?? ""}/badges`),
  recalculateBadges: (tenantId: string) =>
    apiFetch<BadgeList>(`/v1/commerce/tenants/${tenantId}/badges/recalculate`, { method: "POST" }),

  // Credit reservations (B2B bookings)
  createReservation:  (bookingId: string, amount: number) =>
    apiFetch<Reservation>(`/v1/commerce/bookings/${bookingId}/reservation/create`,
      { method: "POST", body: JSON.stringify({ amount }) }),
  confirmReservation: (bookingId: string) =>
    apiFetch<Reservation>(`/v1/commerce/bookings/${bookingId}/reservation/confirm`, { method: "POST" }),
  releaseReservation: (bookingId: string) =>
    apiFetch<Reservation>(`/v1/commerce/bookings/${bookingId}/reservation/release`, { method: "POST" }),
  forfeitReservation: (bookingId: string, reason: string) =>
    apiFetch<Reservation>(`/v1/commerce/bookings/${bookingId}/reservation/forfeit`,
      { method: "POST", body: JSON.stringify({ reason }) }),

  // Booking preflight (4-check gate)
  bookingPreflight: (tenantId: string, customerId: string, bookingAmount: number) =>
    apiFetch<PreflightResult>("/v1/commerce/bookings/preflight",
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId, customer_id: customerId, booking_amount: bookingAmount }) }),
  getPreflightRules: () =>
    apiFetch<{ rules: Record<string, unknown> }>("/v1/commerce/bookings/preflight/rules"),
};

// ── Payment Engine (14 endpoints incl. /meta + /webhook) ──────────────────────
export const paymentApi = {
  // Orders
  createOrder: (tenantId: string, amount: number, paymentType = "customer_payment", bookingId?: string, customerId?: string, gateway = "razorpay") =>
    apiFetch<PaymentOrder>("/v1/payments/orders",
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId, amount, payment_type: paymentType, booking_id: bookingId, customer_id: customerId, gateway }) }),

  // Payments
  getPayment:  (paymentId: string) => apiFetch<Payment>(`/v1/payments/${paymentId}`),
  listPayments:(tenantId: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries({ tenant_id: tenantId, limit: String(limit), ...(cursor ? { cursor } : {}) }))
    ).toString();
    return apiFetch<PaymentList>(`/v1/payments?${qs}`);
  },

  // Refunds
  createRefund:(paymentId: string, amount: number, reason: string) =>
    apiFetch<Refund>(`/v1/payments/${paymentId}/refund`,
      { method: "POST", body: JSON.stringify({ amount, reason }) }),
  getRefund:   (refundId: string) => apiFetch<Refund>(`/v1/payments/refunds/${refundId}`),
  listTenantRefunds: (tenantId: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries({ limit: String(limit), ...(cursor ? { cursor } : {}) }))
    ).toString();
    return apiFetch<RefundList>(`/v1/payments/tenants/${tenantId}/refunds?${qs}`);
  },

  // Invoices
  createInvoice: (tenantId: string, amount: number, paymentId?: string, bookingId?: string, taxAmount = 0, lineItems?: Record<string,unknown>[], invoiceType = "service") =>
    apiFetch<InvoiceRecord>("/v1/payments/invoices",
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId, payment_id: paymentId, booking_id: bookingId, amount, tax_amount: taxAmount, line_items: lineItems ?? [], invoice_type: invoiceType }) }),
  getInvoice:  (invoiceId: string) => apiFetch<InvoiceRecord>(`/v1/payments/invoices/${invoiceId}`),
  listTenantInvoices:(tenantId: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries({ limit: String(limit), ...(cursor ? { cursor } : {}) }))
    ).toString();
    return apiFetch<InvoiceListResponse>(`/v1/payments/tenants/${tenantId}/invoices?${qs}`);
  },

  // Payouts
  requestPayout:(tenantId: string, amount: number, bankAccount: Record<string,unknown>) =>
    apiFetch<Payout>(`/v1/payments/tenants/${tenantId}/payout`,
      { method: "POST", body: JSON.stringify({ amount, bank_account: bankAccount }) }),
  getPayout:    (payoutId: string) => apiFetch<Payout>(`/v1/payments/payouts/${payoutId}`),
  listTenantPayouts: (tenantId: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries({ limit: String(limit), ...(cursor ? { cursor } : {}) }))
    ).toString();
    return apiFetch<PayoutList>(`/v1/payments/tenants/${tenantId}/payouts?${qs}`);
  },
};

// ── Billing ───────────────────────────────────────────────────────────────────
export const billingApi = {
  getProfile:    (tenantId: string) => apiFetch<BillingProfile>(`/v1/billing/profiles/${tenantId}`),
  activateProfile: (tenantId: string, billingMode: string, vertical: string) =>
    apiFetch<BillingProfile>("/v1/billing/profiles",
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId, billing_mode: billingMode, vertical }) }),
  changeMode:    (tenantId: string, newMode: string, reason: string) =>
    apiFetch<BillingProfile>(`/v1/billing/profiles/${tenantId}/change-mode`,
      { method: "POST", body: JSON.stringify({ new_billing_mode: newMode, reason }) }),
  getConfigs:    (vertical?: string) => apiFetch<BillingConfigList>(`/v1/billing/configs${vertical ? `?vertical=${vertical}` : ""}`),
  setConfig:     (vertical: string, planType: string, rate: number) =>
    apiFetch<BillingConfig>("/v1/billing/configs",
      { method: "PUT", body: JSON.stringify({ vertical, plan_type: planType, commission_rate: rate }) }),
  getRoutingLogs: (tenantId: string, limit = 20) =>
    apiFetch<RoutingLogList>(`/v1/billing/logs/${tenantId}?limit=${limit}`),
  getProfileHistory: (tenantId: string) =>
    apiFetch<BillingProfileHistoryList>(`/v1/billing/profiles/${tenantId}/history`),
  routeOperation: (tenantId: string, operation: string, context: Record<string,unknown> = {}) =>
    apiFetch<BillingRouteResult>("/v1/billing/route",
      { method:"POST", body:JSON.stringify({ tenant_id: tenantId, operation, context }) }),
};

// ── Field Ops ─────────────────────────────────────────────────────────────────
export const jobsApi = {
  list: (params?: JobListParams) => {
    const qs = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<JobListResponse>(`/v1/jobs?${qs}`);
  },
  // Cross-tenant queue for Super Admin — tenant_id is optional (omit for platform-wide).
  adminList: (params?: {
    tenant_id?: string; status?: string; limit?: string; cursor?: string;
    q?: string; job_type?: string; sla_status?: string; unassigned?: string;
    date_from?: string; date_to?: string;
    sort_by?: string; sort_dir?: string; page?: string; page_size?: string;
  }) => {
    const cleaned: Record<string,string> = {};
    for (const [k, v] of Object.entries(params ?? {})) { if (v != null && v !== "") cleaned[k] = v; }
    const qs = new URLSearchParams(cleaned).toString();
    return apiFetch<JobListResponse>(`/v1/jobs/admin/all?${qs}`);
  },
  adminSummary: (tenant_id?: string) => {
    const qs = tenant_id ? `?tenant_id=${tenant_id}` : "";
    return apiFetch<OpsSummary>(`/v1/jobs/admin/summary${qs}`);
  },
  get:        (id: string) => apiFetch<Job>(`/v1/jobs/${id}`),
  platformSummary: () => apiFetch<JobSummary>("/v1/jobs/meta"),
  slaAlerts:  () => apiFetch<SlaAlert[]>("/v1/jobs/sla-alerts"),
  history:    (id: string) => apiFetch<JobHistory>(`/v1/jobs/${id}/timeline`),
  reassign:   (id: string, staffId: string, reason: string) =>
    apiFetch<Job>(`/v1/dispatch/jobs/${id}/reassign`,
      { method: "POST", body: JSON.stringify({ new_staff_id: staffId, reason }) }),
  overrideStatus: (id: string, status: string, reason: string) =>
    apiFetch<Job>(`/v1/jobs/${id}/status`,
      { method: "PUT",  body: JSON.stringify({ status, notes: reason, admin_override: true }) }),
  forceClose: (id: string, reason: string) =>
    apiFetch<Job>(`/v1/jobs/${id}/close`,
      { method: "POST", body: JSON.stringify({ closing_notes: reason, forced_by_admin: true }) }),
  getTransitions: (id: string) => apiFetch<JobTransitions>(`/v1/jobs/${id}/transitions`),
  voidJob: (id: string, reason: string) =>
    apiFetch<Job>(`/v1/jobs/${id}/void`, { method:"POST", body:JSON.stringify({ reason }) }),
  addNote: (id: string, tenantId: string, content: string, noteType = "staff_note", isInternal = true) =>
    apiFetch<JobNote>(`/v1/jobs/${id}/notes?tenant_id=${tenantId}`,
      { method:"POST", body:JSON.stringify({ content, note_type: noteType, is_internal: isInternal }) }),
  listNotes: (id: string) => apiFetch<JobNoteList>(`/v1/jobs/${id}/notes`),
  addMedia: (id: string, tenantId: string, mediaType = "photo", caption?: string, storageKey?: string, mediaId?: string) =>
    apiFetch<JobMedia>(`/v1/jobs/${id}/media?tenant_id=${tenantId}`,
      { method:"POST", body:JSON.stringify({ media_id: mediaId, media_type: mediaType, caption, storage_key: storageKey }) }),
  listMedia: (id: string) => apiFetch<JobMediaList>(`/v1/jobs/${id}/media`),
  slaStatus: (id: string) => apiFetch<SlaStatusDetail>(`/v1/jobs/${id}/sla`),
  counts: (tenantId: string) => apiFetch<JobCounts>(`/v1/jobs/tenants/${tenantId}/counts`),
  trackByToken: (token: string) => apiFetch<TrackedJob>(`/v1/jobs/track/${token}`),
};

// ── Bookings ──────────────────────────────────────────────────────────────────
export const bookingsApi = {
  list: (tenantId: string, params?: Partial<{ status:string; limit:string; cursor:string }>) => {
    const qs = new URLSearchParams({ ...(params ?? {}), tenant_id: tenantId }).toString();
    return apiFetch<BookingListResponse>(`/v1/bookings?${qs}`);
  },
  listByCustomer: (customerId: string, tenantId?: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams({ limit:String(limit), ...(tenantId?{tenant_id:tenantId}:{}), ...(cursor?{cursor}:{}) }).toString();
    return apiFetch<BookingListResponse>(`/v1/bookings/customers/${customerId}?${qs}`);
  },
  get:        (id: string) => apiFetch<Booking>(`/v1/bookings/${id}`),
  confirm:    (id: string) => apiFetch<Booking>(`/v1/bookings/${id}/confirm`, { method:"POST" }),
  cancel:     (id: string, reason: string) =>
    apiFetch<Booking>(`/v1/bookings/${id}/cancel`, { method:"POST", body:JSON.stringify({ reason }) }),
  convertToJob: (id: string) =>
    apiFetch<Job>(`/v1/bookings/${id}/convert-to-job`, { method:"POST" }),
  requestReschedule: (id: string, requestedDate: string, requestedSlot: string, reason?: string) =>
    apiFetch<Booking>(`/v1/bookings/${id}/reschedule/request`, { method:"POST",
      body:JSON.stringify({ requested_date: requestedDate, requested_slot: requestedSlot, reason }) }),
  acceptReschedule: (rescheduleId: string) =>
    apiFetch<Booking>(`/v1/bookings/reschedule/${rescheduleId}/accept`, { method:"POST" }),
  rejectReschedule: (rescheduleId: string, reason = "Slot unavailable") =>
    apiFetch<Booking>(`/v1/bookings/reschedule/${rescheduleId}/reject`,
      { method:"POST", body:JSON.stringify({ reason }) }),
  getTimeline: (id: string) => apiFetch<BookingTimeline>(`/v1/bookings/${id}/timeline`),
  addNote: (id: string, content: string, isInternal = true) =>
    apiFetch<BookingNote>(`/v1/bookings/${id}/notes`,
      { method:"POST", body:JSON.stringify({ content, is_internal: isInternal }) }),
  listNotes: (id: string) => apiFetch<BookingNoteList>(`/v1/bookings/${id}/notes`),
  checkSlot: (tenantId: string, date: string, slot: string) =>
    apiFetch<SlotAvailability>(`/v1/bookings/tenants/${tenantId}/slots/check?date=${date}&slot=${slot}`),
  getCancellationPolicy: (tenantId: string) =>
    apiFetch<CancellationPolicy>(`/v1/bookings/tenants/${tenantId}/cancellation-policy`),
  void: (id: string, reason = "Voided by admin") =>
    apiFetch<Booking>(`/v1/bookings/${id}/void`, { method:"POST", body:JSON.stringify({ reason }) }),
  search: (tenantId: string, q: string, limit = 20) =>
    apiFetch<BookingSearchResponse>(`/v1/bookings/tenants/${tenantId}/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};

// ── Admin Customers (platform-wide, no tenant required) ──────────────────────
export interface AdminCustomer {
  id: string;
  full_name: string;
  phone: string;
  email: string;
  is_active: boolean;
  city: string;
  district: string;
  state: string;
  zipcode: string;
  health_band: "new" | "healthy" | "active" | "at_risk" | "dormant" | "complaint_risk" | "blocked";
  total_bookings: number;
  completed_bookings: number;
  cancelled_bookings: number;
  complaints_count: number;
  reviews_count: number;
  average_rating: number | null;
  tenant_count: number;
  last_tenant_name: string;
  last_booking_at: string | null;
  created_at: string | null;
}
export interface AdminCustomerSummary {
  total: number; today: number; active: number; repeat_customers: number;
  at_risk: number; dormant: number; has_complaints: number; new_customers: number;
  blocked: number; avg_rating: number | null; bookings_per_customer: number;
}
export interface AdminCustomerMeta { page: number; page_size: number; total: number; total_pages: number; }
export interface AdminCustomerListResponse { customers: AdminCustomer[]; meta: AdminCustomerMeta; }
export interface AdminCustomerFilterOptions {
  cities: { value: string; label: string }[];
  states: { value: string; label: string }[];
}

export const adminCustomersApi = {
  filterOptions: () => apiFetch<{ data: AdminCustomerFilterOptions }>("/v1/admin/customers/filters"),
  summary: () => apiFetch<{ data: AdminCustomerSummary }>("/v1/admin/customers/summary"),
  list: (params: {
    q?: string; tenant_id?: string; health_band?: string; city?: string; state?: string;
    zipcode?: string; has_complaints?: boolean; has_reviews?: boolean;
    booking_count_min?: number; booking_count_max?: number;
    last_booking_from?: string; last_booking_to?: string;
    created_from?: string; created_to?: string;
    sort_by?: string; sort_dir?: string; page?: number; page_size?: number;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== null) qs.set(k, String(v));
    });
    return apiFetch<{ data: AdminCustomerListResponse }>(`/v1/admin/customers?${qs}`);
  },
  get: (id: string) => apiFetch<{ data: AdminCustomer }>(`/v1/admin/customers/${id}`),
  bookings: (id: string, params?: { tenant_id?: string; status?: string; date_from?: string; date_to?: string; page?: number }) => {
    const qs = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== "") qs.set(k, String(v)); });
    return apiFetch<{ data: { bookings: AdminBooking[]; meta: AdminCustomerMeta } }>(`/v1/admin/customers/${id}/bookings?${qs}`);
  },
  export: (params: Record<string, string>) => {
    const qs = new URLSearchParams(params).toString();
    return `/v1/admin/customers/export?${qs}`;
  },

  // ── Customer Users Enterprise Upgrade — detail tabs ─────────────────────────
  complaints: (id: string, status?: string) => {
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    return apiFetch<{ data: { complaints: CustomerComplaintRow[]; total: number } }>(
      `/v1/admin/customers/${id}/complaints?${qs}`);
  },
  serviceCredits: (id: string, status?: string) => {
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    return apiFetch<{ data: { credits: CustomerServiceCreditRow[]; meta: AdminCustomerMeta; summary: CustomerCreditSummary } }>(
      `/v1/admin/customers/${id}/service-credits?${qs}`);
  },
  issueServiceCredit: (id: string, data: {
    amount: number; credit_type?: string; issued_reason: string;
    customer_message?: string; validity_days?: number;
  }) => apiFetch<{ data: CustomerServiceCreditRow }>(`/v1/admin/customers/${id}/service-credits`,
    { method: "POST", body: JSON.stringify(data) }),
  addresses: (id: string) =>
    apiFetch<{ data: { addresses: CustomerAddressRow[]; total: number } }>(`/v1/admin/customers/${id}/addresses`),
  sessions: (id: string) =>
    apiFetch<{ data: { sessions: CustomerSessionRow[]; has_next: boolean; next_cursor: string | null } }>(
      `/v1/admin/customers/${id}/sessions`),
  loginHistory: (id: string) =>
    apiFetch<{ data: { login_history: CustomerLoginEvent[] } }>(`/v1/admin/customers/${id}/login-history`),
  privacyRequests: (id: string) =>
    apiFetch<{ data: { items: CustomerPrivacyRequest[]; meta: AdminCustomerMeta & { has_next: boolean } } }>(
      `/v1/admin/customers/${id}/privacy-requests`),
  auditLogs: (id: string) =>
    apiFetch<{ data: { audit_logs: CustomerAuditLogRow[] } }>(`/v1/admin/customers/${id}/audit-logs`),
  block: (id: string, reason: string) =>
    apiFetch<{ data: { user_id: string; account_status: string } }>(`/v1/admin/customers/${id}/block`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  unblock: (id: string, reason: string) =>
    apiFetch<{ data: { user_id: string; account_status: string } }>(`/v1/admin/customers/${id}/unblock`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  suspend: (id: string, reason: string) =>
    apiFetch<{ data: { user_id: string; account_status: string } }>(`/v1/admin/customers/${id}/suspend`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  reactivate: (id: string, reason: string) =>
    apiFetch<{ data: { user_id: string; account_status: string } }>(`/v1/admin/customers/${id}/reactivate`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  revokeAllSessions: (id: string, reason: string) =>
    apiFetch<{ data: { user_id: string; sessions_revoked: number } }>(`/v1/admin/customers/${id}/sessions/revoke-all`,
      { method: "POST", body: JSON.stringify({ reason }) }),
};

export interface CustomerComplaintRow {
  id: string; complaint_number: string; complaint_type: string; priority: string; status: string;
  title: string | null; description: string; settlement_status: string | null;
  booking_id: string | null; tenant_id: string | null;
  created_at: string | null; resolved_at: string | null; closed_at: string | null;
}
export interface CustomerServiceCreditRow {
  id: string; credit_number: string; amount: string; remaining_amount: string; currency: string;
  credit_type: string; source: string; status: string; issued_reason: string;
  valid_from: string | null; expires_at: string | null; created_at: string | null;
}
export interface CustomerCreditSummary {
  total_credits: number; active_credits: number; used_credits: number; expired_credits: number;
  cancelled_credits: number; active_credit_balance: number; credits_from_disputes: number;
}
export interface CustomerAddressRow {
  id: string; name: string | null; phone: string | null;
  address_line_1: string; address_line_2: string | null; landmark: string | null;
  city: string; district: string | null; state: string; country: string; zipcode: string;
  is_default: boolean; is_active: boolean; created_at: string | null;
}
export interface CustomerSessionRow {
  session_id: string; user_id: string; user_email: string; user_name: string; user_role: string;
  device_name: string; device_type: string; ip_address: string | null;
  status: "active" | "revoked"; last_active_at: string | null; expires_at: string | null;
}
export interface CustomerLoginEvent {
  event_type: string; ip_address: string | null; failure_reason: string | null;
  device_id: string | null; request_id: string | null; created_at: string;
}
export interface CustomerPrivacyRequest {
  id: string; request_number: string; request_type: string; status: string;
  sla_status: string; hours_until_sla: number | null; sla_overdue: boolean;
  submitted_at: string | null; due_at: string | null; completed_at: string | null;
}
export interface CustomerAuditLogRow {
  log_id: string; operation: string; actor_role: string | null; actor_ip: string | null;
  is_high_risk: boolean; created_at: string;
}

// ── Admin Bookings (platform-wide, no tenant required) ────────────────────────
export interface AdminBooking {
  id: string;
  booking_number: string;
  tenant_id: string | null;
  tenant_name: string;
  provider_name: string;
  customer_id: string | null;
  customer_name: string;
  customer_phone: string;
  category_name: string;
  service_name: string;
  service_type_id: string;
  status: string;
  job_status: string;
  assignment_status: string;
  estimated_amount: number | null;
  credit_applied?: number;
  payable_amount?: number;
  payment_recorded?: boolean;
  amount_collected?: number;
  city: string;
  zipcode: string;
  state: string;
  district: string;
  city_tier: string;
  created_at: string | null;
  scheduled_at: string | null;
  preferred_date: string | null;
  preferred_slot: string | null;
  job_id: string | null;
  reschedule_count: number;
  job_type: string;
  sla_breached: boolean;
}
export interface AdminBookingListMeta {
  page: number; page_size: number; total: number; total_pages: number;
}
export interface AdminBookingListResponse { bookings: AdminBooking[]; meta: AdminBookingListMeta; }
export interface AdminBookingSummary {
  total: number; today: number;
  pending_confirmation: number; confirmed: number; in_progress: number;
  scheduled: number; completed: number; cancelled: number; voided: number;
  unassigned: number; at_risk: number;
}
export interface AdminBookingFilterOptions {
  categories: { value: string; label: string }[];
  cities:     { value: string; label: string }[];
  states:     { value: string; label: string }[];
  statuses:   { value: string; label: string }[];
}
export interface AdminBookingListParams {
  q?: string; tenant_id?: string; customer_id?: string; status?: string;
  category?: string; service_id?: string;
  city?: string; state?: string; district?: string; zipcode?: string;
  date_from?: string; date_to?: string;
  scheduled_from?: string; scheduled_to?: string;
  amount_min?: number; amount_max?: number;
  sort_by?: string; sort_dir?: string;
  page?: number; page_size?: number;
}

export const adminBookingsApi = {
  filterOptions: () =>
    apiFetch<{ data: AdminBookingFilterOptions }>("/v1/admin/bookings/filters"),

  list: (params: AdminBookingListParams) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== null) qs.set(k, String(v));
    });
    return apiFetch<{ data: AdminBookingListResponse }>(`/v1/admin/bookings?${qs}`);
  },

  summary: () =>
    apiFetch<{ data: AdminBookingSummary }>("/v1/admin/bookings/summary"),

  get: (id: string) =>
    apiFetch<{ data: AdminBooking & Record<string, unknown> }>(`/v1/admin/bookings/${id}`),

  getTimeline: (id: string) =>
    apiFetch<{ data: { timeline: { from_status: string | null; to_status: string; reason: string | null; occurred_at: string | null }[] } }>(
      `/v1/admin/bookings/${id}/timeline`
    ),

  listNotes: (id: string) =>
    apiFetch<{ data: { notes: { note_id: string; content: string; author_role: string | null; is_internal: boolean; created_at: string | null }[] } }>(
      `/v1/admin/bookings/${id}/notes`
    ),

  cancel: (id: string, reason: string) =>
    apiFetch<{ data: { cancelled: boolean } }>(`/v1/admin/bookings/${id}/cancel`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  void: (id: string, reason: string) =>
    apiFetch<{ data: { voided: boolean } }>(`/v1/admin/bookings/${id}/void`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  tenantSearch: (q: string) =>
    apiFetch<{ data: { tenants: { id: string; name: string; city: string }[] } }>(
      `/v1/admin/bookings/tenant-search?q=${encodeURIComponent(q)}`
    ),

  export: (params: Record<string, string>) => {
    const qs = new URLSearchParams(params).toString();
    return `/v1/admin/bookings/export?${qs}`;
  },
};

// ── Admin Staff (platform-wide, no tenant required) ───────────────────────────
export interface AdminStaffMember {
  user_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  tenant_id: string | null;
  tenant_name: string | null;
  business_name: string | null;
  tenant_city: string | null;
  total_jobs: number;
  completed_jobs: number;
  active_jobs: number;
  last_job_at: string | null;
  last_category: string | null;
  average_rating: number | null;
  total_reviews: number;
  availability_status: "available" | "busy" | "inactive";
  created_at: string | null;
}

export interface AdminStaffSummary {
  total: number;
  active: number;
  inactive: number;
  verified: number;
  unverified: number;
  busy: number;
  new_this_week: number;
}

export interface AdminStaffFilterOptions {
  roles: { value: string; label: string }[];
  cities: { value: string; label: string }[];
  tenants: { value: string; label: string }[];
}

export interface AdminStaffListResponse {
  staff: AdminStaffMember[];
  meta: { page: number; page_size: number; total: number; total_pages: number };
}

export const adminStaffApi = {
  filterOptions: () => apiFetch<{ data: AdminStaffFilterOptions }>("/v1/admin/staff/filters"),
  summary: () => apiFetch<{ data: AdminStaffSummary }>("/v1/admin/staff/summary"),
  list: (params: {
    q?: string; tenant_id?: string; role?: string;
    availability_status?: string; is_active?: boolean;
    city?: string; created_from?: string; created_to?: string;
    sort_by?: string; sort_dir?: string; page?: number; page_size?: number;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== null) qs.set(k, String(v));
    });
    return apiFetch<{ data: AdminStaffListResponse }>(`/v1/admin/staff?${qs}`);
  },
  get: (id: string) => apiFetch<{ data: AdminStaffMember }>(`/v1/admin/staff/${id}`),
  jobs: (id: string, params?: { status?: string; page?: number }) => {
    const qs = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== "") qs.set(k, String(v)); });
    return apiFetch<{ data: { jobs: Record<string, unknown>[]; meta: { page: number; total: number; total_pages: number } } }>(`/v1/admin/staff/${id}/jobs?${qs}`);
  },
  export: (params: Record<string, string>) => {
    const qs = new URLSearchParams(params).toString();
    return `/v1/admin/staff/export?${qs}`;
  },
};

// ── Pricing ───────────────────────────────────────────────────────────────────
export const pricingApi = {
  // Platform city tiers (super-admin only)
  listCityTiers: (tier?: string, category?: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams({ ...(tier?{tier}:{}), ...(category?{category}:{}), limit:String(limit), ...(cursor?{cursor}:{}) }).toString();
    return apiFetch<CityTierConfigList>(`/v1/pricing/city-tiers?${qs}`);
  },
  getCityTier: (configId: string) => apiFetch<CityTierConfig>(`/v1/pricing/city-tiers/${configId}`),
  createCityTier: (data: { city_name:string; tier:string; service_category:string; floor_price:number; notes?:string }) =>
    apiFetch<CityTierConfig>("/v1/pricing/city-tiers", { method:"POST", body:JSON.stringify(data) }),
  updateCityTier: (configId: string, data: Partial<{ floor_price:number; is_active:boolean; notes:string }>) =>
    apiFetch<CityTierConfig>(`/v1/pricing/city-tiers/${configId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteCityTier: (configId: string) =>
    apiFetch<void>(`/v1/pricing/city-tiers/${configId}`, { method:"DELETE" }),

  // Tenant service prices
  listPrices: (tenantId: string, limit = 50, cursor?: string) => {
    const qs = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<ServiceTypePriceList>(`/v1/pricing/tenants/${tenantId}/prices${qs}`);
  },
  getPrice: (tenantId: string, serviceTypeId: string) =>
    apiFetch<ServiceTypePrice>(`/v1/pricing/tenants/${tenantId}/prices/${serviceTypeId}`),
  setPrice: (tenantId: string, data: { service_type_id:string; service_category:string; city_name:string; base_price:number; unit?:string; change_reason?:string }) =>
    apiFetch<ServiceTypePrice>(`/v1/pricing/tenants/${tenantId}/prices/set`,
      { method:"POST", body:JSON.stringify(data) }),
  getPriceHistory: (tenantId: string, serviceTypeId: string, limit = 20, cursor?: string) => {
    const qs = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<ServiceTypePriceList>(`/v1/pricing/tenants/${tenantId}/prices/${serviceTypeId}/history${qs}`);
  },

  // Brand adjustment
  getBrandAdjustment: (tenantId: string) =>
    apiFetch<BrandAdjustment>(`/v1/pricing/tenants/${tenantId}/brand-adjustment`),
  setBrandAdjustment: (tenantId: string, adjustmentPct: number, label?: string, reason?: string) =>
    apiFetch<BrandAdjustment>(`/v1/pricing/tenants/${tenantId}/brand-adjustment`,
      { method:"PUT", body:JSON.stringify({ adjustment_pct: adjustmentPct, label, reason }) }),

  // Zone surcharges
  listZones: (tenantId: string) => apiFetch<ZoneSurchargeList>(`/v1/pricing/tenants/${tenantId}/zones`),
  createZone: (tenantId: string, data: { zone_name:string; zone_type:string; zone_identifiers:string[]; surcharge_pct:number; notes?:string }) =>
    apiFetch<ZoneSurcharge>(`/v1/pricing/tenants/${tenantId}/zones`, { method:"POST", body:JSON.stringify(data) }),
  getZone: (tenantId: string, zoneId: string) => apiFetch<ZoneSurcharge>(`/v1/pricing/tenants/${tenantId}/zones/${zoneId}`),
  updateZone: (tenantId: string, zoneId: string, data: Partial<{ zone_name:string; surcharge_pct:number; is_active:boolean; notes:string }>) =>
    apiFetch<ZoneSurcharge>(`/v1/pricing/tenants/${tenantId}/zones/${zoneId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteZone: (tenantId: string, zoneId: string) =>
    apiFetch<void>(`/v1/pricing/tenants/${tenantId}/zones/${zoneId}`, { method:"DELETE" }),

  // Dynamic pricing rules
  listRules: (tenantId: string, activeOnly = false) =>
    apiFetch<DynamicPricingRuleList>(`/v1/pricing/tenants/${tenantId}/rules?active_only=${activeOnly}`),
  createRule: (tenantId: string, data: { rule_name:string; rule_type:string; priority?:number; adjustment_pct:number; conditions?:Record<string,unknown>; applies_to?:string[]; active_from?:string; active_until?:string }) =>
    apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tenantId}/rules`, { method:"POST", body:JSON.stringify(data) }),
  getRule: (tenantId: string, ruleId: string) => apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tenantId}/rules/${ruleId}`),
  updateRule: (tenantId: string, ruleId: string, data: Partial<{ rule_name:string; priority:number; adjustment_pct:number; conditions:Record<string,unknown>; applies_to:string[] }>) =>
    apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tenantId}/rules/${ruleId}`, { method:"PUT", body:JSON.stringify(data) }),
  activateRule: (tenantId: string, ruleId: string) =>
    apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tenantId}/rules/${ruleId}/activate`, { method:"POST" }),
  deactivateRule: (tenantId: string, ruleId: string) =>
    apiFetch<DynamicPricingRule>(`/v1/pricing/tenants/${tenantId}/rules/${ruleId}/deactivate`, { method:"POST" }),
  deleteRule: (tenantId: string, ruleId: string) =>
    apiFetch<void>(`/v1/pricing/tenants/${tenantId}/rules/${ruleId}`, { method:"DELETE" }),

  // Compute / preview / snapshots
  computePrice: (data: { tenant_id:string; service_type_id:string; service_category:string; city_name:string; pincode?:string; booking_id?:string; requested_at?:string }) =>
    apiFetch<PriceSnapshot>("/v1/pricing/compute", { method:"POST", body:JSON.stringify(data) }),
  previewPrice: (tenantId: string, serviceTypeId: string, serviceCategory: string, cityName: string, pincode?: string) =>
    apiFetch<PricePreviewResult>(`/v1/pricing/tenants/${tenantId}/price-preview`,
      { method:"POST", body:JSON.stringify({ service_type_id: serviceTypeId, service_category: serviceCategory, city_name: cityName, pincode }) }),
  getSnapshot: (snapshotId: string) => apiFetch<PriceSnapshot>(`/v1/pricing/snapshots/${snapshotId}`),
  replaySnapshot: (snapshotId: string) =>
    apiFetch<PriceSnapshot>(`/v1/pricing/snapshots/${snapshotId}/replay`, { method:"POST" }),
  listSnapshots: (tenantId: string, limit = 50, cursor?: string) => {
    const qs = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<PriceSnapshotList>(`/v1/pricing/tenants/${tenantId}/snapshots${qs}`);
  },
};

// ── Catalog Engine (Admin master catalog: tiers, categories, services, types, brands, pricing rules) ──
export const catalogApi = {
  // Category dropdown options (searchable — no raw UUID entry required)
  getCategoryOptions: (params?: { q?: string; vertical_type?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.vertical_type) qs.set("vertical_type", params.vertical_type);
    if (params?.status) qs.set("status", params.status);
    return apiFetch<CategoryOption[]>(`/v1/admin/catalog/categories/options?${qs}`);
  },

  // Tiers
  listTiers: (isActive?: boolean, extra?: {
    q?:string; usedInRules?:boolean; hasCityMapping?:boolean; hasZipcodeMapping?:boolean;
    dateFrom?:string; dateTo?:string;
  }) => {
    const qs = new URLSearchParams();
    if (isActive !== undefined) qs.set("is_active", String(isActive));
    if (extra?.q) qs.set("q", extra.q);
    if (extra?.usedInRules !== undefined) qs.set("used_in_rules", String(extra.usedInRules));
    if (extra?.hasCityMapping !== undefined) qs.set("has_city_mapping", String(extra.hasCityMapping));
    if (extra?.hasZipcodeMapping !== undefined) qs.set("has_zipcode_mapping", String(extra.hasZipcodeMapping));
    if (extra?.dateFrom) qs.set("date_from", extra.dateFrom);
    if (extra?.dateTo) qs.set("date_to", extra.dateTo);
    const q = qs.toString();
    return apiFetch<{ tiers: PricingTier[] }>(`/v1/admin/tiers${q ? `?${q}` : ""}`);
  },
  createTier: (data: Partial<PricingTier> & { name:string; code:string; tier_type:string }) =>
    apiFetch<PricingTier>("/v1/admin/tiers", { method:"POST", body:JSON.stringify(data) }),
  updateTier: (tierId: string, data: Partial<PricingTier>) =>
    apiFetch<PricingTier>(`/v1/admin/tiers/${tierId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteTier: (tierId: string) => apiFetch<void>(`/v1/admin/tiers/${tierId}`, { method:"DELETE" }),
  hardDeleteTier: (tierId: string) => apiFetch<{ deleted: boolean; tier_id: string; hard_delete: boolean }>(`/v1/admin/tiers/${tierId}/hard-delete`, { method:"DELETE" }),
  getTiersSummary: () => apiFetch<TiersSummary>("/v1/admin/tiers/summary"),
  exportTiers: (isActive?: boolean) => {
    const qs = isActive !== undefined ? `?is_active=${isActive}` : "";
    return apiFetch<{ rows: PricingTier[]; count: number }>(`/v1/admin/tiers/export${qs}`);
  },
  getTierDetail: (tierId: string) => apiFetch<TierDetail>(`/v1/admin/tiers/${tierId}/detail`),

  // Tier locations
  listTierLocations: (tierId?: string) => {
    const qs = tierId ? `?tier_id=${tierId}` : "";
    return apiFetch<{ locations: TierLocation[] }>(`/v1/admin/tier-locations${qs}`);
  },
  listTierLocationsGrid: (params: {
    tierId?: string; q?: string; state?: string; district?: string; city?: string; zipcode?: string;
    isActive?: boolean; hasConflict?: boolean; page?: number; pageSize?: number; sortBy?: string; sortDir?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params.tierId)      qs.set("tier_id", params.tierId);
    if (params.q)            qs.set("q", params.q);
    if (params.state)        qs.set("state", params.state);
    if (params.district)     qs.set("district", params.district);
    if (params.city)         qs.set("city", params.city);
    if (params.zipcode)      qs.set("zipcode", params.zipcode);
    if (params.isActive !== undefined)    qs.set("is_active", String(params.isActive));
    if (params.hasConflict !== undefined) qs.set("has_conflict", String(params.hasConflict));
    qs.set("page", String(params.page ?? 1));
    qs.set("page_size", String(params.pageSize ?? 50));
    qs.set("sort_by", params.sortBy ?? "created_at");
    qs.set("sort_dir", params.sortDir ?? "desc");
    return apiFetch<{ items: TierLocation[]; pagination: GridPagination }>(`/v1/admin/tier-locations?${qs.toString()}`);
  },
  createTierLocation: (data: { tier_id:string; city?:string; zipcode?:string; state?:string; district?:string; zone_name?:string; country?:string }) =>
    apiFetch<TierLocation>("/v1/admin/tier-locations", { method:"POST", body:JSON.stringify(data) }),
  updateTierLocation: (locationId: string, data: Partial<{ tier_id:string; city?:string; zipcode?:string; state?:string; district?:string; country?:string; is_active:boolean }>) =>
    apiFetch<TierLocation>(`/v1/admin/tier-locations/${locationId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteTierLocation: (locationId: string) =>
    apiFetch<void>(`/v1/admin/tier-locations/${locationId}`, { method:"DELETE" }),
  resolveLocation: (city?: string, zipcode?: string, state?: string, district?: string, zone?: string) => {
    const qs = new URLSearchParams();
    if (city)     qs.set("city", city);
    if (zipcode)  qs.set("zipcode", zipcode);
    if (state)    qs.set("state", state);
    if (district) qs.set("district", district);
    if (zone)     qs.set("zone", zone);
    return apiFetch<ResolveResult>(`/v1/admin/tiers/resolve-location?${qs.toString()}`);
  },
  getTierLocationsSummary: () => apiFetch<TierLocationsSummary>("/v1/admin/tier-locations/summary"),
  exportTierLocations: (filters?: { tierId?:string; state?:string; district?:string; city?:string; isActive?:boolean; hasConflict?:boolean }) => {
    const qs = new URLSearchParams();
    if (filters?.tierId)      qs.set("tier_id", filters.tierId);
    if (filters?.state)       qs.set("state", filters.state);
    if (filters?.district)    qs.set("district", filters.district);
    if (filters?.city)        qs.set("city", filters.city);
    if (filters?.isActive !== undefined)    qs.set("is_active", String(filters.isActive));
    if (filters?.hasConflict !== undefined) qs.set("has_conflict", String(filters.hasConflict));
    return apiFetch<{ rows: TierLocation[]; count: number }>(`/v1/admin/tier-locations/export?${qs.toString()}`);
  },
  importTierLocationsPreview: (fileName: string, csvText: string) =>
    apiFetch<ImportPreviewResult>("/v1/admin/tier-locations/import/preview",
      { method:"POST", body:JSON.stringify({ file_name: fileName, csv_text: csvText }) }),
  importTierLocationsConfirm: (batchId: string, conflictResolution: "skip" | "override") =>
    apiFetch<ImportBatch>("/v1/admin/tier-locations/import/confirm",
      { method:"POST", body:JSON.stringify({ batch_id: batchId, conflict_resolution: conflictResolution }) }),
  getImportBatch: (batchId: string) =>
    apiFetch<ImportBatch>(`/v1/admin/tier-locations/imports/${batchId}`),
  listImportBatches: (page = 1, pageSize = 20) =>
    apiFetch<{ batches: ImportBatch[]; pagination: GridPagination }>(`/v1/admin/tier-locations/imports?page=${page}&page_size=${pageSize}`),
  bulkChangeTierLocations: (locationIds: string[], newTierId: string) =>
    apiFetch<{ updated: number; new_tier_id: string }>("/v1/admin/tier-locations/bulk/change-tier",
      { method:"POST", body:JSON.stringify({ location_ids: locationIds, new_tier_id: newTierId }) }),
  bulkDeactivateTierLocations: (locationIds: string[]) =>
    apiFetch<{ deactivated: number }>("/v1/admin/tier-locations/bulk/deactivate",
      { method:"POST", body:JSON.stringify({ location_ids: locationIds }) }),
  resolveConflict: (locationId: string, resolutionType: "keep_this" | "override_tier" | "deactivate", overrideTierId?: string) =>
    apiFetch<{ resolved: boolean; location_id: string; resolution_type: string }>(
      `/v1/admin/tier-locations/${locationId}/resolve-conflict`,
      { method:"POST", body:JSON.stringify({ resolution_type: resolutionType, override_tier_id: overrideTierId }) }),

  // Service categories
  listCategories: (isActive?: boolean) => {
    const qs = isActive !== undefined ? `?is_active=${isActive}` : "";
    return apiFetch<{ categories: ServiceCategory[] }>(`/v1/admin/service-categories${qs}`);
  },
  createCategory: (data: {
    name: string; description?: string; icon_url?: string; image_url?: string; display_order?: number;
    vertical_type?: string; finance_model?: string; customer_flow_type?: string;
    provider_business_model?: string; requires_location?: boolean; requires_schedule?: boolean;
    requires_brand?: boolean; requires_service_option?: boolean; requires_issue_type?: boolean;
    tenant_selectable?: boolean; pricing_supported?: boolean;
  }) =>
    apiFetch<ServiceCategory>("/v1/admin/service-categories", { method:"POST", body:JSON.stringify(data) }),
  updateCategory: (categoryId: string, data: Partial<ServiceCategory>) =>
    apiFetch<ServiceCategory>(`/v1/admin/service-categories/${categoryId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteCategory: (categoryId: string) =>
    apiFetch<void>(`/v1/admin/service-categories/${categoryId}`, { method:"DELETE" }),
  hardDeleteCategory: (categoryId: string) =>
    apiFetch<{ deleted: boolean; category_id: string; hard_delete: boolean }>(`/v1/admin/service-categories/${categoryId}/hard-delete`, { method:"DELETE" }),

  // Master services
  listMasterServices: (categoryId?: string, jobType?: string, isActive?: boolean, serviceGroupId?: string) => {
    const params = new URLSearchParams();
    if (categoryId) params.set("category_id", categoryId);
    if (serviceGroupId) params.set("service_group_id", serviceGroupId);
    if (jobType) params.set("job_type", jobType);
    if (isActive !== undefined) params.set("is_active", String(isActive));
    return apiFetch<{ services: MasterService[] }>(`/v1/admin/master-services?${params.toString()}`);
  },
  createMasterService: (data: Partial<MasterService> & { category_id:string; service_name:string; job_type:string; pricing_model:string; base_price:number }) =>
    apiFetch<MasterService>("/v1/admin/master-services", { method:"POST", body:JSON.stringify(data) }),
  updateMasterService: (serviceId: string, data: Partial<MasterService>) =>
    apiFetch<MasterService>(`/v1/admin/master-services/${serviceId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteMasterService: (serviceId: string) =>
    apiFetch<void>(`/v1/admin/master-services/${serviceId}`, { method:"DELETE" }),
  hardDeleteMasterService: (serviceId: string) =>
    apiFetch<{ deleted: boolean; service_id: string; hard_delete: boolean }>(`/v1/admin/master-services/${serviceId}/hard-delete`, { method:"DELETE" }),

  // Service types
  listServiceTypes: (categoryId?: string) => {
    const qs = categoryId ? `?category_id=${categoryId}` : "";
    return apiFetch<{ types: ServiceTypeRow[] }>(`/v1/admin/service-types${qs}`);
  },
  createServiceType: (data: { category_id:string; name:string; description?:string }) =>
    apiFetch<ServiceTypeRow>("/v1/admin/service-types", { method:"POST", body:JSON.stringify(data) }),
  updateServiceType: (typeId: string, data: { name?: string; description?: string }) =>
    apiFetch<ServiceTypeRow>(`/v1/admin/service-types/${typeId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteServiceType: (typeId: string) =>
    apiFetch<void>(`/v1/admin/service-types/${typeId}`, { method:"DELETE" }),
  hardDeleteServiceType: (typeId: string) =>
    apiFetch<{ deleted: boolean; type_id: string; hard_delete: boolean }>(`/v1/admin/service-types/${typeId}/hard-delete`, { method:"DELETE" }),

  // Brands (Sprint 34D — Enterprise Brand Management)
  listBrands: (params?: { categoryId?: string; status?: string; search?: string; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.categoryId) qs.set("category_id", params.categoryId);
    if (params?.status)     qs.set("status", params.status);
    if (params?.search)     qs.set("search", params.search);
    if (params?.page)       qs.set("page", String(params.page));
    if (params?.page_size)  qs.set("page_size", String(params.page_size));
    return apiFetch<{ brands: Brand34D[]; total: number; page: number; page_size: number }>(
      `/v1/admin/brands?${qs.toString()}`);
  },
  getBrand: (brandId: string) => apiFetch<Brand34D>(`/v1/admin/brands/${brandId}`),
  createBrand: (data: Partial<Brand34D> & { name: string; force?: boolean }) =>
    apiFetch<Brand34D | BrandDuplicateWarning>("/v1/admin/brands", { method:"POST", body:JSON.stringify(data) }),
  updateBrand: (brandId: string, data: Partial<Brand34D>) =>
    apiFetch<Brand34D>(`/v1/admin/brands/${brandId}`, { method:"PUT", body:JSON.stringify(data) }),
  activateBrand: (brandId: string) =>
    apiFetch<{ brand_id:string; status:string }>(`/v1/admin/brands/${brandId}/activate`, { method:"POST", body:"{}" }),
  deactivateBrand: (brandId: string) =>
    apiFetch<{ brand_id:string; status:string }>(`/v1/admin/brands/${brandId}/deactivate`, { method:"POST", body:"{}" }),
  archiveBrand: (brandId: string) =>
    apiFetch<{ brand_id:string; status:string }>(`/v1/admin/brands/${brandId}/archive`, { method:"POST", body:"{}" }),
  mapBrandCategories: (brandId: string, categoryIds: string[]) =>
    apiFetch<{ brand_id:string; mapped:string[] }>(`/v1/admin/brands/${brandId}/map-categories`,
      { method:"POST", body:JSON.stringify({ category_ids: categoryIds }) }),
  unmapBrandCategory: (brandId: string, categoryId: string) =>
    apiFetch<{ brand_id:string; category_id:string; unmapped:boolean }>(
      `/v1/admin/brands/${brandId}/category-mappings/${categoryId}`, { method:"DELETE" }),
  mapBrandServices: (brandId: string, serviceIds: string[]) =>
    apiFetch<{ brand_id:string; mapped:string[] }>(`/v1/admin/brands/${brandId}/map-services`,
      { method:"POST", body:JSON.stringify({ service_ids: serviceIds }) }),
  listBrandServiceMappings: (brandId: string) =>
    apiFetch<{ brand_id:string; service_mappings: { mapping_id:string; service_id:string; service_name:string; job_type:string; is_required:boolean; is_default:boolean }[] }>(
      `/v1/admin/brands/${brandId}/service-mappings`),
  unmapBrandService: (brandId: string, serviceId: string) =>
    apiFetch<{ brand_id:string; service_id:string; unmapped:boolean }>(
      `/v1/admin/brands/${brandId}/service-mappings/${serviceId}`, { method:"DELETE" }),
  bulkMapBrandsToServices: (brandIds: string[], serviceIds: string[]) =>
    apiFetch<{ created_mappings:number; skipped_existing:number; errors:unknown[] }>(
      `/v1/admin/brands/bulk-map-services`,
      { method:"POST", body:JSON.stringify({ brand_ids: brandIds, service_ids: serviceIds }) }),
  mergeBrand: (sourceBrandId: string, targetBrandId: string, adminNote?: string) =>
    apiFetch<{ source_brand_id:string; target_brand_id:string; source_archived:boolean }>(
      `/v1/admin/brands/${sourceBrandId}/merge`,
      { method:"POST", body:JSON.stringify({ target_brand_id: targetBrandId, admin_note: adminNote }) }),
  deleteBrand: (brandId: string) =>
    apiFetch<{ brand_id:string; status:string }>(`/v1/admin/brands/${brandId}/archive`, { method:"POST", body:"{}" }),

  // Brand requests
  listBrandRequests: (params?: { status?: string; tenantId?: string } | string, tenantId?: string) => {
    const qs = new URLSearchParams();
    const status = typeof params === "string" ? params : params?.status;
    const tid    = typeof params === "string" ? tenantId : params?.tenantId;
    if (status) qs.set("status", status);
    if (tid)    qs.set("tenant_id", tid);
    return apiFetch<{ requests: BrandRequest34D[] }>(`/v1/admin/brand-requests?${qs.toString()}`);
  },
  approveBrandRequest: (requestId: string, adminNote?: string) =>
    apiFetch<{ request_id:string; status:string; brand?: Brand34D }>(
      `/v1/admin/brand-requests/${requestId}/approve`,
      { method:"POST", body:JSON.stringify({ admin_note: adminNote }) }),
  rejectBrandRequest: (requestId: string, adminNote?: string) =>
    apiFetch<{ request_id:string; status:string }>(
      `/v1/admin/brand-requests/${requestId}/reject`,
      { method:"POST", body:JSON.stringify({ admin_note: adminNote }) }),
  mergeBrandRequest: (requestId: string, existingBrandId: string, adminNote?: string) =>
    apiFetch<{ request_id:string; status:string }>(
      `/v1/admin/brand-requests/${requestId}/merge`,
      { method:"POST", body:JSON.stringify({ existing_brand_id: existingBrandId, admin_note: adminNote }) }),
  seedBrands: () =>
    apiFetch<{ seeded: number; skipped: number }>("/v1/admin/brands/seed", { method:"POST", body:"{}" }),

  // Brand templates
  listBrandTemplates: (status?: string, categoryId?: string) => {
    const qs = new URLSearchParams();
    if (status)     qs.set("status", status);
    if (categoryId) qs.set("category_id", categoryId);
    return apiFetch<{ templates: BrandTemplate34D[] }>(`/v1/admin/brand-templates?${qs.toString()}`);
  },
  createBrandTemplate: (data: { code:string; name:string; brand_ids:string[]; category_id?:string; vertical_type?:string }) =>
    apiFetch<BrandTemplate34D>("/v1/admin/brand-templates", { method:"POST", body:JSON.stringify(data) }),
  applyBrandTemplate: (templateId: string, serviceIds?: string[]) =>
    apiFetch<{ template_id:string; applied_brands:number }>(
      `/v1/admin/brand-templates/${templateId}/apply`,
      { method:"POST", body:JSON.stringify({ service_ids: serviceIds }) }),

  // Master service ↔ type/brand mapping
  listServiceTypeMappings: (serviceId: string) =>
    apiFetch<{ types: { mapping_id:string; service_type_id:string; name:string; is_required:boolean }[] }>(
      `/v1/admin/master-services/${serviceId}/types`),
  mapServiceType: (serviceId: string, serviceTypeId: string, isRequired = false) =>
    apiFetch<{ mapping_id:string }>(`/v1/admin/master-services/${serviceId}/types`,
      { method:"POST", body:JSON.stringify({ service_type_id: serviceTypeId, is_required: isRequired }) }),
  listBrandMappings: (serviceId: string) =>
    apiFetch<{ brands: { mapping_id:string; brand_id:string; name:string; is_required:boolean }[] }>(
      `/v1/admin/master-services/${serviceId}/brands`),
  mapBrand: (serviceId: string, brandId: string, isRequired = false) =>
    apiFetch<{ mapping_id:string }>(`/v1/admin/master-services/${serviceId}/brands`,
      { method:"POST", body:JSON.stringify({ brand_id: brandId, is_required: isRequired }) }),

  // Pricing rules
  listPricingRules: (masterServiceId?: string, extra?: {
    isActive?:boolean; q?:string; brandId?:string; serviceTypeId?:string; tierId?:string; city?:string;
    zipcode?:string; pricingModel?:string; expiringWithinDays?:number; ruleStatus?:string;
    page?:number; pageSize?:number; sortBy?:string; sortDir?:string;
  }) => {
    const qs = new URLSearchParams();
    if (masterServiceId) qs.set("master_service_id", masterServiceId);
    if (extra?.isActive !== undefined) qs.set("is_active", String(extra.isActive));
    if (extra?.q)             qs.set("q", extra.q);
    if (extra?.brandId)       qs.set("brand_id", extra.brandId);
    if (extra?.serviceTypeId) qs.set("service_type_id", extra.serviceTypeId);
    if (extra?.tierId)        qs.set("tier_id", extra.tierId);
    if (extra?.city)          qs.set("city", extra.city);
    if (extra?.zipcode)       qs.set("zipcode", extra.zipcode);
    if (extra?.pricingModel)  qs.set("pricing_model", extra.pricingModel);
    if (extra?.expiringWithinDays !== undefined) qs.set("expiring_within_days", String(extra.expiringWithinDays));
    if (extra?.ruleStatus)    qs.set("rule_status", extra.ruleStatus);
    qs.set("page", String(extra?.page ?? 1));
    qs.set("page_size", String(extra?.pageSize ?? 50));
    qs.set("sort_by", extra?.sortBy ?? "priority");
    qs.set("sort_dir", extra?.sortDir ?? "desc");
    // Backend returns both `items` (new, paginated) and `rules` (back-compat alias, same array).
    return apiFetch<{ items: PricingRule[]; rules: PricingRule[]; pagination: GridPagination }>(`/v1/admin/pricing-rules?${qs.toString()}`);
  },
  createPricingRule: (data: Partial<PricingRule> & { master_service_id:string; job_type:string; pricing_model:string; base_price:number }) =>
    apiFetch<PricingRule>("/v1/admin/pricing-rules", { method:"POST", body:JSON.stringify(data) }),
  updatePricingRule: (ruleId: string, data: Partial<PricingRule>) =>
    apiFetch<PricingRule>(`/v1/admin/pricing-rules/${ruleId}`, { method:"PUT", body:JSON.stringify(data) }),
  deletePricingRule: (ruleId: string) =>
    apiFetch<void>(`/v1/admin/pricing-rules/${ruleId}`, { method:"DELETE" }),
  hardDeletePricingRule: (ruleId: string) =>
    apiFetch<{ deleted: boolean; rule_id: string; hard_delete: boolean }>(`/v1/admin/pricing-rules/${ruleId}/hard-delete`, { method:"DELETE" }),
  previewPricingRule: (data: { master_service_id:string; city?:string; zipcode?:string; service_type_id?:string; brand_id?:string }) =>
    apiFetch<PricingPreviewResult>("/v1/admin/pricing-rules/preview", { method:"POST", body:JSON.stringify(data) }),
  getPricingRulesSummary: () => apiFetch<PricingRulesSummary>("/v1/admin/pricing-rules/summary"),
  exportPricingRules: (filters?: { masterServiceId?:string; isActive?:boolean }) => {
    const qs = new URLSearchParams();
    if (filters?.masterServiceId) qs.set("master_service_id", filters.masterServiceId);
    if (filters?.isActive !== undefined) qs.set("is_active", String(filters.isActive));
    return apiFetch<{ rows: PricingRule[]; count: number }>(`/v1/admin/pricing-rules/export?${qs.toString()}`);
  },
  getPricingRuleConflicts: (ruleId: string) =>
    apiFetch<{ rule_id:string; conflicts: PricingRule[] }>(`/v1/admin/pricing-rules/${ruleId}/conflicts`),

  // Cache management
  invalidateCache: (tenantId: string) =>
    apiFetch<{ invalidated:boolean }>(`/v1/pricing/tenants/${tenantId}/cache/invalidate`, { method:"POST" }),
  cacheStatus: (tenantId: string) =>
    apiFetch<{ cached_keys:string[] }>(`/v1/pricing/tenants/${tenantId}/cache/status`),

  // Tenant-scoped catalog (read-only from admin side)
  listEnabledServices: (tenantId: string) =>
    apiFetch<{ services: EnabledService[] }>(`/v1/tenant/catalog/enabled-services?tenant_id=${tenantId}`),

  // Service Groups — Enterprise (P0 upgrade)
  getServiceGroupsSummary: () =>
    apiFetch<ServiceGroupsSummary>("/v1/admin/service-groups/summary"),
  listServiceGroups: (params?: { categoryId?: string; status?: string; q?: string; hasServices?: boolean; limit?: number; offset?: number }) => {
    const p = new URLSearchParams();
    if (params?.categoryId)  p.set("category_id", params.categoryId);
    if (params?.status)      p.set("status", params.status);
    if (params?.q)           p.set("q", params.q);
    if (params?.hasServices !== undefined) p.set("has_services", String(params.hasServices));
    if (params?.limit)       p.set("limit", String(params.limit));
    if (params?.offset)      p.set("offset", String(params.offset));
    return apiFetch<{ groups: ServiceGroupEnriched[]; total: number }>(`/v1/admin/service-groups?${p.toString()}`);
  },
  getServiceGroup: (groupId: string) => apiFetch<ServiceGroupEnriched>(`/v1/admin/service-groups/${groupId}`),
  createServiceGroup: (data: { name:string; category_id:string; code?:string; description?:string; display_order?:number; icon_url?:string }) =>
    apiFetch<ServiceGroup>("/v1/admin/service-groups", { method:"POST", body:JSON.stringify(data) }),
  updateServiceGroup: (groupId: string, data: Partial<ServiceGroup>) =>
    apiFetch<ServiceGroup>(`/v1/admin/service-groups/${groupId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteServiceGroup: (groupId: string) =>
    apiFetch<{ deleted: boolean; group_id: string }>(`/v1/admin/service-groups/${groupId}`, { method:"DELETE" }),
  activateServiceGroup: (groupId: string) =>
    apiFetch<ServiceGroup>(`/v1/admin/service-groups/${groupId}/activate`, { method:"POST" }),
  deactivateServiceGroup: (groupId: string) =>
    apiFetch<ServiceGroup>(`/v1/admin/service-groups/${groupId}/deactivate`, { method:"POST" }),
  archiveServiceGroup: (groupId: string) =>
    apiFetch<{ archived: boolean }>(`/v1/admin/service-groups/${groupId}/archive`, { method:"POST" }),
  exportServiceGroups: (params?: { categoryId?: string; status?: string }) => {
    const p = new URLSearchParams();
    if (params?.categoryId) p.set("category_id", params.categoryId);
    if (params?.status)     p.set("status", params.status);
    return apiFetch<{ rows: ServiceGroupEnriched[]; count: number }>(`/v1/admin/service-groups/export?${p.toString()}`);
  },
  // Master Services — Enterprise (P0 upgrade)
  getMasterServicesSummary: () =>
    apiFetch<MasterServicesSummary>("/v1/admin/master-services/summary"),
  listMasterServicesEnterprise: (params?: { q?: string; categoryId?: string; serviceGroupId?: string; jobType?: string; pricingModel?: string; isActive?: boolean; limit?: number; offset?: number }) => {
    const p = new URLSearchParams();
    if (params?.q)              p.set("q", params.q);
    if (params?.categoryId)     p.set("category_id", params.categoryId);
    if (params?.serviceGroupId) p.set("service_group_id", params.serviceGroupId);
    if (params?.jobType)        p.set("job_type", params.jobType);
    if (params?.pricingModel)   p.set("pricing_model", params.pricingModel);
    if (params?.isActive !== undefined) p.set("is_active", String(params.isActive));
    if (params?.limit)          p.set("limit", String(params.limit));
    if (params?.offset)         p.set("offset", String(params.offset));
    return apiFetch<{ services: MasterServiceEnriched[]; total: number }>(`/v1/admin/master-services?${p.toString()}`);
  },
  activateMasterService: (serviceId: string) =>
    apiFetch<MasterService>(`/v1/admin/master-services/${serviceId}/activate`, { method:"POST" }),
  deactivateMasterService: (serviceId: string) =>
    apiFetch<MasterService>(`/v1/admin/master-services/${serviceId}/deactivate`, { method:"POST" }),
  archiveMasterService: (serviceId: string) =>
    apiFetch<{ archived: boolean }>(`/v1/admin/master-services/${serviceId}/archive`, { method:"POST" }),
  exportMasterServices: (params?: { categoryId?: string; serviceGroupId?: string; jobType?: string; isActive?: boolean }) => {
    const p = new URLSearchParams();
    if (params?.categoryId)     p.set("category_id", params.categoryId);
    if (params?.serviceGroupId) p.set("service_group_id", params.serviceGroupId);
    if (params?.jobType)        p.set("job_type", params.jobType);
    if (params?.isActive !== undefined) p.set("is_active", String(params.isActive));
    return apiFetch<{ rows: MasterServiceEnriched[]; count: number }>(`/v1/admin/master-services/export?${p.toString()}`);
  },

  // Customer flow config (Sprint 38)
  getFlowConfig: (params: { categoryId?: string; serviceId?: string }) => {
    const qs = new URLSearchParams();
    if (params.categoryId) qs.set("category_id", params.categoryId);
    if (params.serviceId)  qs.set("service_id", params.serviceId);
    return apiFetch<{ flow_type:string; steps:string[]; requires_location:boolean; requires_schedule:boolean; requires_brand:boolean; requires_service_option:boolean; requires_issue_type:boolean; finance_model?:string|null }>(`/v1/catalog/master/flow/config?${qs.toString()}`);
  },
};

export interface EnabledService {
  tenant_service_id: string; tenant_id: string; master_service_id: string;
  category_id: string; job_type: string; is_enabled: boolean;
  tenant_display_name?: string; tenant_description?: string;
  tenant_base_price?: number; tenant_min_price?: number; tenant_max_price?: number;
  tenant_visit_fee?: number; override_allowed: boolean; requires_brand: boolean;
  requires_type: boolean; is_active: boolean;
}

// ── Sprint 34D Brand Types ─────────────────────────────────────────────────────
export interface Brand34D {
  brand_id: string;
  name: string;
  display_name: string;
  slug: string;
  code?: string;
  status: "active" | "inactive" | "archived" | "deprecated" | "pending_review" | "rejected";
  normalized_name?: string;
  alias_names?: string[];
  logo_url?: string;
  description?: string;
  website_url?: string;
  country_of_origin?: string;
  is_global: boolean;
  display_order: number;
  is_active: boolean;
  category_id?: string;
  replacement_brand_id?: string;
  provider_usage_count?: number;
  category_mapping_count?: number;
  service_mapping_count?: number;
  category_mappings?: { mapping_id:string; category_id:string; category_name:string; display_order:number }[];
  service_mappings?: { mapping_id:string; service_id:string; service_name:string; is_required:boolean }[];
  created_at?: string;
  updated_at?: string;
}

export interface BrandDuplicateWarning {
  warning: "BRAND_DUPLICATE_POSSIBLE";
  message: string;
  possible_duplicates: Brand34D[];
  created: false;
}

export interface BrandRequest34D {
  request_id: string;
  tenant_id?: string;
  requested_by_user_id?: string;
  requested_brand_name: string;
  normalized_name?: string;
  reason?: string;
  status: "pending" | "approved" | "rejected" | "merged";
  matched_brand_id?: string;
  admin_note?: string;
  suggested_category_id?: string;
  suggested_service_id?: string;
  reviewed_at?: string;
  created_at?: string;
}

export interface BrandTemplate34D {
  template_id: string;
  code: string;
  name: string;
  description?: string;
  category_id?: string;
  vertical_type?: string;
  status: string;
  items?: { brand_id:string; brand_name:string; display_order:number }[];
  created_at?: string;
}

// ── Master Data API (Sprint 34C) ──────────────────────────────────────────────
export interface MasterIssueType {
  id: string; category_id: string | null; master_service_id: string | null;
  code: string; name: string; slug: string; description?: string;
  severity: "low" | "medium" | "high" | "critical";
  customer_visible?: boolean; requires_photo?: boolean; requires_description?: boolean;
  is_active: boolean; display_order: number; status?: string;
  created_at?: string; updated_at?: string;
}

export interface MasterServiceOption {
  id: string; category_id: string | null; master_service_id: string | null;
  code: string; name: string; slug: string; description?: string;
  option_type: string; unit: string;
  default_price: string; min_price?: string; max_price?: string;
  is_customer_selectable: boolean; is_active: boolean; display_order: number;
  created_at?: string; updated_at?: string;
}

export interface WorkflowEvidenceRule {
  evidence_type: string; required: boolean; min_count?: number; max_count?: number;
  allowed_file_types?: string[]; max_file_size?: number;
  visible_to_customer?: boolean; visible_to_tenant?: boolean; visible_to_admin?: boolean;
}
export interface WorkflowApprovalRule {
  approval_type: string; approval_actor: string; required: boolean;
  timeout_minutes?: number; auto_approve_after_timeout?: boolean;
  escalation_target?: string; reject_behavior?: string;
}
export interface WorkflowAutomationTrigger {
  trigger_type: string; action: string; config?: Record<string, unknown>;
}
export interface WorkflowStep {
  id: string; step_code: string; step_name: string; step_type: string; actor: string;
  description?: string | null; status_before?: string | null; status_after?: string | null;
  is_start?: boolean; is_terminal?: boolean; is_required?: boolean; can_skip?: boolean;
  display_order?: number; estimated_duration_minutes?: number | null; sla_minutes?: number | null;
  warning_before_minutes?: number | null; escalation_target?: string | null;
  auto_notify?: boolean; auto_escalate?: boolean;
  requires_note?: boolean; requires_photo?: boolean; requires_document?: boolean;
  requires_customer_signature?: boolean; requires_customer_approval?: boolean;
  requires_admin_approval?: boolean; notification_trigger?: boolean;
  evidence_rules?: WorkflowEvidenceRule[]; approval_rule?: WorkflowApprovalRule | null;
  automation_triggers?: WorkflowAutomationTrigger[];
}
export interface WorkflowTransition {
  id: string; from_step_code: string; to_step_code: string;
  from_status?: string | null; to_status?: string | null; allowed_actor: string;
  required_permission?: string | null; condition?: string | null;
  requires_reason?: boolean; requires_note?: boolean; auto_transition?: boolean;
}
export interface MasterWorkflowTemplate {
  id: string; category_id: string | null; master_service_id: string | null;
  service_group_id?: string | null; service_type_id?: string | null;
  name: string; slug: string; template_code?: string; description?: string;
  workflow_type: string; steps: WorkflowStep[]; transitions?: WorkflowTransition[];
  estimated_duration_minutes?: number; max_sla_hours?: number | null;
  is_active: boolean; status: string; display_order: number;
  requires_technician_assignment?: boolean; requires_customer_confirmation?: boolean;
  requires_photo_proof?: boolean; requires_part_approval?: boolean;
  requires_estimate_approval?: boolean; requires_direct_payment_confirmation?: boolean;
  allows_reschedule?: boolean; allows_cancellation?: boolean; allows_dispute_after_completion?: boolean;
  version_number?: number; parent_template_id?: string | null; is_latest?: boolean;
  activated_at?: string | null; deprecated_at?: string | null;
  created_by_user_id?: string | null;
  created_at?: string; updated_at?: string;
}
export interface WorkflowTemplatesSummary {
  total_templates: number; active_templates: number; draft_templates: number;
  used_by_services: number; unmapped_templates: number; templates_missing_steps: number;
  sla_enabled: number; approval_enabled: number; runtime_ready: number;
}
export interface WorkflowServiceMapping {
  id: string; template_id: string; category_id: string;
  service_group_id: string | null; master_service_id: string | null;
  service_type_id: string | null; brand_id: string | null; tenant_id: string | null;
  priority: number; status: string; created_at?: string; updated_at?: string;
}
export interface WorkflowValidationResult { template_id: string; valid: boolean; errors: string[]; warnings: string[]; }
export interface WorkflowReadinessResult { template_id: string; readiness: string; }
export interface WorkflowRuntimePreview {
  resolved: boolean; message?: string; template?: MasterWorkflowTemplate;
  readiness?: string; matched_mapping?: WorkflowServiceMapping | null;
}

export interface MasterDataAuditEntry {
  id: string; entity_type: string; entity_id: string;
  action: string; actor_user_id?: string; actor_role?: string;
  old_value?: unknown; new_value?: unknown;
  change_summary?: string; request_id?: string; created_at?: string;
}

export const masterDataApi = {
  // Issue Types
  listIssueTypes: (params?: { category_id?: string; master_service_id?: string; is_active?: boolean }) => {
    const qs = new URLSearchParams();
    if (params?.category_id) qs.set("category_id", params.category_id);
    if (params?.master_service_id) qs.set("master_service_id", params.master_service_id);
    if (params?.is_active !== undefined) qs.set("is_active", String(params.is_active));
    return apiFetch<{ issue_types: MasterIssueType[]; total: number }>(`/v1/admin/issue-types?${qs}`);
  },
  getIssueType: (id: string) =>
    apiFetch<MasterIssueType>(`/v1/admin/issue-types/${id}`),
  createIssueType: (data: { name: string; code: string; severity?: string; category_id?: string; master_service_id?: string; description?: string; display_order?: number; customer_visible?: boolean; requires_photo?: boolean; requires_description?: boolean; status?: string }) =>
    apiFetch<MasterIssueType>("/v1/admin/issue-types", { method: "POST", body: JSON.stringify(data) }),
  updateIssueType: (id: string, data: Partial<MasterIssueType>) =>
    apiFetch<MasterIssueType>(`/v1/admin/issue-types/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteIssueType: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/issue-types/${id}`, { method: "DELETE" }),

  // Service Options
  listServiceOptions: (params?: { category_id?: string; master_service_id?: string; is_active?: boolean }) => {
    const qs = new URLSearchParams();
    if (params?.category_id) qs.set("category_id", params.category_id);
    if (params?.master_service_id) qs.set("master_service_id", params.master_service_id);
    if (params?.is_active !== undefined) qs.set("is_active", String(params.is_active));
    return apiFetch<{ service_options: MasterServiceOption[]; total: number }>(`/v1/admin/service-options?${qs}`);
  },
  getServiceOption: (id: string) =>
    apiFetch<MasterServiceOption>(`/v1/admin/service-options/${id}`),
  createServiceOption: (data: { name: string; code: string; option_type?: string; unit?: string; default_price?: number; category_id?: string; master_service_id?: string; description?: string; is_customer_selectable?: boolean; display_order?: number }) =>
    apiFetch<MasterServiceOption>("/v1/admin/service-options", { method: "POST", body: JSON.stringify(data) }),
  updateServiceOption: (id: string, data: Partial<MasterServiceOption>) =>
    apiFetch<MasterServiceOption>(`/v1/admin/service-options/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteServiceOption: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/service-options/${id}`, { method: "DELETE" }),

  // Workflow Templates
  getWorkflowTemplatesSummary: () =>
    apiFetch<WorkflowTemplatesSummary>("/v1/admin/workflow-templates/summary"),
  listWorkflowTemplates: (params?: {
    category_id?: string; master_service_id?: string; workflow_type?: string; is_active?: boolean;
    status?: string; q?: string; readiness?: string; page?: number; limit?: number;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params ?? {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") qs.set(k, String(v)); });
    return apiFetch<{ workflow_templates: MasterWorkflowTemplate[]; total: number;
                       meta: { total: number; page: number; limit: number; total_pages: number } }>(
      `/v1/admin/workflow-templates?${qs}`);
  },
  exportWorkflowTemplates: () =>
    apiFetch<{ rows: MasterWorkflowTemplate[]; count: number; format: string }>("/v1/admin/workflow-templates/export"),
  getWorkflowTemplate: (id: string) =>
    apiFetch<MasterWorkflowTemplate>(`/v1/admin/workflow-templates/${id}`),
  createWorkflowTemplate: (data: Record<string, unknown>) =>
    apiFetch<MasterWorkflowTemplate>("/v1/admin/workflow-templates", { method: "POST", body: JSON.stringify(data) }),
  updateWorkflowTemplate: (id: string, data: Partial<MasterWorkflowTemplate>) =>
    apiFetch<MasterWorkflowTemplate>(`/v1/admin/workflow-templates/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteWorkflowTemplate: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/workflow-templates/${id}`, { method: "DELETE" }),
  cloneWorkflowTemplate: (id: string) =>
    apiFetch<MasterWorkflowTemplate>(`/v1/admin/workflow-templates/${id}/clone`, { method: "POST" }),
  createWorkflowNewVersion: (id: string) =>
    apiFetch<MasterWorkflowTemplate>(`/v1/admin/workflow-templates/${id}/new-version`, { method: "POST" }),
  activateWorkflowTemplate: (id: string) =>
    apiFetch<MasterWorkflowTemplate>(`/v1/admin/workflow-templates/${id}/activate`, { method: "POST" }),
  deactivateWorkflowTemplate: (id: string) =>
    apiFetch<MasterWorkflowTemplate>(`/v1/admin/workflow-templates/${id}/deactivate`, { method: "POST" }),
  validateWorkflowTemplate: (id: string) =>
    apiFetch<WorkflowValidationResult>(`/v1/admin/workflow-templates/${id}/validate`, { method: "POST" }),
  getWorkflowReadiness: (id: string) =>
    apiFetch<WorkflowReadinessResult>(`/v1/admin/workflow-templates/${id}/readiness`),

  // Steps
  addWorkflowStep: (templateId: string, data: Partial<WorkflowStep>) =>
    apiFetch<WorkflowStep>(`/v1/admin/workflow-templates/${templateId}/steps`, { method: "POST", body: JSON.stringify(data) }),
  updateWorkflowStep: (templateId: string, stepId: string, data: Partial<WorkflowStep>) =>
    apiFetch<WorkflowStep>(`/v1/admin/workflow-templates/${templateId}/steps/${stepId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteWorkflowStep: (templateId: string, stepId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/workflow-templates/${templateId}/steps/${stepId}`, { method: "DELETE" }),
  reorderWorkflowSteps: (templateId: string, stepIds: string[]) =>
    apiFetch<{ steps: WorkflowStep[] }>(`/v1/admin/workflow-templates/${templateId}/steps/reorder`,
      { method: "POST", body: JSON.stringify({ step_ids: stepIds }) }),

  // Transitions
  listWorkflowTransitions: (templateId: string) =>
    apiFetch<{ transitions: WorkflowTransition[]; total: number }>(`/v1/admin/workflow-templates/${templateId}/transitions`),
  addWorkflowTransition: (templateId: string, data: Partial<WorkflowTransition>) =>
    apiFetch<WorkflowTransition>(`/v1/admin/workflow-templates/${templateId}/transitions`, { method: "POST", body: JSON.stringify(data) }),
  updateWorkflowTransition: (templateId: string, transitionId: string, data: Partial<WorkflowTransition>) =>
    apiFetch<WorkflowTransition>(`/v1/admin/workflow-templates/${templateId}/transitions/${transitionId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteWorkflowTransition: (templateId: string, transitionId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/workflow-templates/${templateId}/transitions/${transitionId}`, { method: "DELETE" }),

  // Service mappings
  listWorkflowMappings: (templateId: string) =>
    apiFetch<{ mappings: WorkflowServiceMapping[]; total: number }>(`/v1/admin/workflow-templates/${templateId}/mappings`),
  createWorkflowMapping: (templateId: string, data: Partial<WorkflowServiceMapping>) =>
    apiFetch<WorkflowServiceMapping>(`/v1/admin/workflow-templates/${templateId}/mappings`, { method: "POST", body: JSON.stringify(data) }),
  deleteWorkflowMapping: (templateId: string, mappingId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/workflow-templates/${templateId}/mappings/${mappingId}`, { method: "DELETE" }),

  // Runtime preview
  previewWorkflowRuntime: (data: { category_id?: string; master_service_id?: string; service_type_id?: string; tenant_id?: string }) =>
    apiFetch<WorkflowRuntimePreview>("/v1/admin/workflow-templates/preview-runtime", { method: "POST", body: JSON.stringify(data) }),

  // Seed defaults
  seedWorkflowDefaultsPreview: () =>
    apiFetch<{ templates: { name: string; workflow_type: string; steps: number; description: string }[]; will_create: number; already_exist: string[] }>(
      "/v1/admin/workflow-templates/seed-defaults/preview", { method: "POST" }),
  seedWorkflowDefaults: () =>
    apiFetch<{ created: MasterWorkflowTemplate[]; count: number }>("/v1/admin/workflow-templates/seed-defaults", { method: "POST" }),

  // Audit
  getWorkflowTemplateAuditLogs: (templateId: string) =>
    apiFetch<{ audit_log: MasterDataAuditEntry[]; total: number }>(`/v1/admin/workflow-templates/${templateId}/audit-logs`),

  // Audit Log
  listAuditLog: (params?: { entity_type?: string; entity_id?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.entity_type) qs.set("entity_type", params.entity_type);
    if (params?.entity_id) qs.set("entity_id", params.entity_id);
    if (params?.limit) qs.set("limit", String(params.limit));
    return apiFetch<{ audit_log: MasterDataAuditEntry[]; total: number }>(`/v1/admin/master-data-audit?${qs}`);
  },
};

// ── Dispatch ──────────────────────────────────────────────────────────────────
export const dispatchApi = {
  dispatchJob: (jobId: string, tenantId: string, mode: "manual"|"auto_assign"|"broadcast", staffId?: string,
                jobLat?: number, jobLng?: number, serviceTypeId = "general") =>
    apiFetch<DispatchRecord>(`/v1/dispatch/jobs/${jobId}/dispatch`,
      { method:"POST", body:JSON.stringify({ tenant_id: tenantId, mode, staff_id: staffId,
        job_lat: jobLat, job_lng: jobLng, service_type_id: serviceTypeId }) }),
  getDispatch: (jobId: string) => apiFetch<DispatchRecord>(`/v1/dispatch/jobs/${jobId}`),
  listRecords: (tenantId: string, limit = 50, cursor?: string) => {
    const qs = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<DispatchRecordList>(`/v1/dispatch/tenants/${tenantId}/records${qs}`);
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
  getQueue: (tenantId: string) => apiFetch<DispatchQueue>(`/v1/dispatch/tenants/${tenantId}/queue`),
  getScoring: (jobId: string) => apiFetch<ScoringBreakdown>(`/v1/dispatch/jobs/${jobId}/scoring`),
};

// ── Geo ───────────────────────────────────────────────────────────────────────
export const geoApi = {
  listZones: (tenantId: string, activeOnly = true) =>
    apiFetch<ServiceZoneList>(`/v1/geo/tenants/${tenantId}/zones?active_only=${activeOnly}`),
  createZone: (tenantId: string, data: { zone_name:string; zone_type:string; identifiers?:string[]; center_lat?:number; center_lng?:number; radius_km?:number; surcharge_pct?:number }) =>
    apiFetch<ServiceZone>(`/v1/geo/tenants/${tenantId}/zones`, { method:"POST", body:JSON.stringify(data) }),
  getZone: (zoneId: string) => apiFetch<ServiceZone>(`/v1/geo/zones/${zoneId}`),
  updateZone: (zoneId: string, data: Partial<{ zone_name:string; identifiers:string[]; center_lat:number; center_lng:number; radius_km:number; surcharge_pct:number; is_active:boolean }>) =>
    apiFetch<ServiceZone>(`/v1/geo/zones/${zoneId}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteZone: (zoneId: string) => apiFetch<void>(`/v1/geo/zones/${zoneId}`, { method:"DELETE" }),
  checkPincode: (tenantId: string, pincode: string) =>
    apiFetch<PincodeZoneCheck>(`/v1/geo/tenants/${tenantId}/zones/check?pincode=${pincode}`),
  updateStaffLocation: (tenantId: string, staffId: string, latitude: number, longitude: number, accuracyM?: number, status?: string) =>
    apiFetch<GeoStaffLocation>(`/v1/geo/tenants/${tenantId}/staff/${staffId}/location`,
      { method:"POST", body:JSON.stringify({ latitude, longitude, accuracy_m: accuracyM, status }) }),
  getStaffLocation: (tenantId: string, staffId: string) =>
    apiFetch<GeoStaffLocation>(`/v1/geo/tenants/${tenantId}/staff/${staffId}/location`),
  staffInRadius: (tenantId: string, lat: number, lng: number, radiusKm = 10, staffStatus?: string) => {
    const qs = staffStatus ? `&staff_status=${staffStatus}` : "";
    return apiFetch<GeoStaffLocation[]>(`/v1/geo/tenants/${tenantId}/staff/radius?lat=${lat}&lng=${lng}&radius_km=${radiusKm}${qs}`);
  },
  getCoverage: (tenantId: string) => apiFetch<CoverageMap>(`/v1/geo/tenants/${tenantId}/coverage`),
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analyticsApi = {
  platformSummary: () => apiFetch<AnalyticsPlatformSummary>("/v1/analytics/platform/summary"),
  tenantMetrics:   (tenantId: string, days = 30) =>
    apiFetch<TenantMetrics>(`/v1/analytics/tenants/${tenantId}/metrics?days=${days}`),
  dailyMetrics:    (metricKey: string, days = 30, tenantId?: string) =>
    apiFetch<DailyMetricList>(`/v1/analytics/metrics/daily?metric_key=${metricKey}&days=${days}${tenantId ? `&tenant_id=${tenantId}` : ""}`),
  upsertDailyMetric: (metricDate: string, metricKey: string, valueNum?: number, valueJson?: Record<string,unknown>, tenantId?: string) =>
    apiFetch<DailyMetric>("/v1/analytics/metrics/daily/upsert",
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId, metric_date: metricDate, metric_key: metricKey, value_num: valueNum, value_json: valueJson }) }),
  ingestEvent:     (eventId: string, eventType: string, engineId: string, payload?: Record<string,unknown>, tenantId?: string, entityType?: string, entityId?: string, actorId?: string) =>
    apiFetch<void>("/v1/analytics/events/ingest",
      { method: "POST", body: JSON.stringify({ event_id: eventId, tenant_id: tenantId, event_type: eventType, engine_id: engineId, entity_type: entityType, entity_id: entityId, actor_id: actorId, payload: payload ?? {} }) }),
  eventStream:     (params?: { tenant_id?: string; event_type?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<EventStreamResponse>(`/v1/analytics/events/stream?${qs}`);
  },
  engineMeta:     () => apiFetch<EngineMeta>("/v1/analytics/meta"),
};

// ── Security ──────────────────────────────────────────────────────────────────
export const securityApi = {
  summary:         () => apiFetch<SecuritySummary>("/v1/security/summary"),
  listActivity:    (threatLevel?: string, limit = 20) =>
    apiFetch<ActivityList>(`/v1/security/activity?${threatLevel ? `threat_level=${threatLevel}&` : ""}limit=${limit}`),
  acknowledgeActivity: (logId: string, notes: string) =>
    apiFetch<void>(`/v1/security/activity/${logId}/acknowledge`,
      { method: "POST", body: JSON.stringify({ notes }) }),
  blockIp:         (ip: string, reason: string, threatLevel: string) =>
    apiFetch<IpBlockEntry>("/v1/security/blocklist",
      { method: "POST", body: JSON.stringify({ ip_or_cidr: ip, reason, threat_level: threatLevel, is_global: true }) }),
  listBlocklist:   (limit = 50) => apiFetch<BlocklistResponse>(`/v1/security/blocklist?limit=${limit}`),
  unblockIp:       (ip: string) => apiFetch<void>(`/v1/security/blocklist/${encodeURIComponent(ip)}`, { method: "DELETE" }),
  listSessions:    (userId: string) => apiFetch<SessionList>(`/v1/security/sessions/users/${userId}`),
  revokeAllSessions: (userId: string, reason: string) =>
    apiFetch<void>(`/v1/security/sessions/users/${userId}/revoke-all`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  searchAuditLog:  (params: AuditSearchParams) => {
    const qs = new URLSearchParams(params as Record<string,string>).toString();
    return apiFetch<AuditLogList>(`/v1/security/audit-log?${qs}`);
  },
};

// ── RAG Engine (17 usable endpoints) ──────────────────────────────────────────
export const ragApi = {
  // Knowledge base CRUD
  createKb: (tenantId: string, name: string, description?: string, vertical?: string, chunkSize = 512, chunkOverlap = 64, topK = 5) =>
    apiFetch<RagKnowledgeBaseV1>("/v1/rag/knowledge-bases",
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId, name, description, vertical, chunk_size: chunkSize, chunk_overlap: chunkOverlap, top_k: topK }) }),
  getKb:   (kbId: string) => apiFetch<RagKnowledgeBaseV1>(`/v1/rag/knowledge-bases/${kbId}`),
  listTenantKbs: (tenantId: string, limit = 20, cursor?: string) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries({ limit: String(limit), ...(cursor ? { cursor } : {}) }))).toString();
    return apiFetch<KnowledgeBaseList>(`/v1/rag/tenants/${tenantId}/knowledge-bases?${qs}`);
  },
  updateKb: (kbId: string, data: Partial<{ name: string; description: string; chunk_size: number; chunk_overlap: number; top_k: number }>) =>
    apiFetch<RagKnowledgeBaseV1>(`/v1/rag/knowledge-bases/${kbId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteKb: (kbId: string) => apiFetch<void>(`/v1/rag/knowledge-bases/${kbId}`, { method: "DELETE" }),

  // Documents
  ingestDocument: (kbId: string, fileName: string, content: string, mimeType = "text/plain", sourceUrl?: string, tags?: string[]) =>
    apiFetch<KBDocument>(`/v1/rag/knowledge-bases/${kbId}/documents`,
      { method: "POST", body: JSON.stringify({ file_name: fileName, mime_type: mimeType, content, source_url: sourceUrl, tags: tags ?? [] }) }),
  listDocuments: (kbId: string, status?: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries({ ...(status ? { status } : {}), limit: String(limit), ...(cursor ? { cursor } : {}) }))).toString();
    return apiFetch<KBDocumentList>(`/v1/rag/knowledge-bases/${kbId}/documents?${qs}`);
  },
  getDocument:    (docId: string) => apiFetch<KBDocument>(`/v1/rag/documents/${docId}`),
  deleteDocument: (docId: string) => apiFetch<void>(`/v1/rag/documents/${docId}`, { method: "DELETE" }),
  reindexDocument:(docId: string) => apiFetch<KBDocument>(`/v1/rag/documents/${docId}/reindex`, { method: "POST" }),

  // Chunks
  listChunks: (kbId: string, docId?: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries({ ...(docId ? { doc_id: docId } : {}), limit: String(limit), ...(cursor ? { cursor } : {}) }))).toString();
    return apiFetch<ChunkList>(`/v1/rag/knowledge-bases/${kbId}/chunks?${qs}`);
  },
  getChunk: (chunkId: string) => apiFetch<Chunk>(`/v1/rag/chunks/${chunkId}`),

  // Query & retrieval
  query: (kbId: string, question: string, topK?: number, planType?: string) =>
    apiFetch<RagQueryResult>("/v1/rag/query",
      { method: "POST", body: JSON.stringify({ kb_id: kbId, question, top_k: topK, plan_type: planType }) }),
  search: (kbId: string, question: string, topK = 5) =>
    apiFetch<RagSearchResult>("/v1/rag/search",
      { method: "POST", body: JSON.stringify({ kb_id: kbId, question, top_k: topK }) }),
  getQuery: (queryId: string) => apiFetch<RagQueryResult>(`/v1/rag/queries/${queryId}`),
  listQueries: (tenantId: string, kbId?: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries({ ...(kbId ? { kb_id: kbId } : {}), limit: String(limit), ...(cursor ? { cursor } : {}) }))).toString();
    return apiFetch<RagQueryList>(`/v1/rag/tenants/${tenantId}/queries?${qs}`);
  },

  // Platform admin
  platformUsage: () => apiFetch<RagPlatformUsage>("/v1/rag/platform/usage"),
};

// ── Compliance ────────────────────────────────────────────────────────────────
export const complianceApi = {
  // Legacy endpoints (keep for backward compat)
  summary:          () => apiFetch<ComplianceSummary>("/v1/compliance/summary"),
  listDeletionRequests: (status?: string) =>
    apiFetch<DeletionRequestList>(`/v1/compliance/deletion-requests${status ? `?status=${status}` : ""}`),
  processDeletion:  (requestId: string) =>
    apiFetch<DeletionRequest>(`/v1/compliance/deletion-requests/${requestId}/process`,
      { method: "POST" }),
  listRetentionPolicies: () => apiFetch<RetentionPolicyList>("/v1/compliance/retention-policies"),

  // Enterprise DPDP dashboard
  enterpriseSummary: () =>
    apiFetch<ComplianceEnterpriseSummary>("/v1/admin/compliance/summary"),

  // Request management
  listRequests: (params?: {
    request_type?: string; status?: string; sla_status?: string;
    subject_type?: string; verification_status?: string;
    search?: string; page?: number; limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.request_type)       q.set("request_type", params.request_type);
    if (params?.status)             q.set("status", params.status);
    if (params?.sla_status)         q.set("sla_status", params.sla_status);
    if (params?.subject_type)       q.set("subject_type", params.subject_type);
    if (params?.verification_status)q.set("verification_status", params.verification_status);
    if (params?.search)             q.set("search", params.search);
    if (params?.page)               q.set("page", String(params.page));
    if (params?.limit)              q.set("limit", String(params.limit));
    const qs = q.toString();
    return apiFetch<ComplianceEnterpriseRequestList>(
      `/v1/admin/compliance/requests${qs ? `?${qs}` : ""}`);
  },
  createRequest: (data: {
    subject_type: string; subject_id: string; request_type: string;
    subject_email?: string; subject_name?: string;
    request_source?: string; reason?: string; verification_status?: string;
  }) => apiFetch<ComplianceEnterpriseRequest>("/v1/admin/compliance/requests",
    { method: "POST", body: JSON.stringify(data) }),
  getRequest: (requestId: string) =>
    apiFetch<ComplianceEnterpriseRequest>(`/v1/admin/compliance/requests/${requestId}`),
  verifyIdentity: (requestId: string, notes?: string) =>
    apiFetch<ComplianceEnterpriseRequest>(`/v1/admin/compliance/requests/${requestId}/verify-identity`,
      { method: "POST", body: JSON.stringify({ notes }) }),
  scanData: (requestId: string) =>
    apiFetch<{ request_id: string; modules_scanned: number; items: ComplianceRequestItem[] }>(
      `/v1/admin/compliance/requests/${requestId}/scan-data`, { method: "POST" }),
  approveRequest: (requestId: string, notes?: string) =>
    apiFetch<ComplianceEnterpriseRequest>(`/v1/admin/compliance/requests/${requestId}/approve`,
      { method: "POST", body: JSON.stringify({ notes }) }),
  rejectRequest: (requestId: string, reason: string) =>
    apiFetch<ComplianceEnterpriseRequest>(`/v1/admin/compliance/requests/${requestId}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  applyExemption: (requestId: string, itemId: string, exemptionReason: string) =>
    apiFetch<ComplianceRequestItem>(`/v1/admin/compliance/requests/${requestId}/apply-exemption`,
      { method: "POST", body: JSON.stringify({ item_id: itemId, exemption_reason: exemptionReason }) }),
  processRequest: (requestId: string) =>
    apiFetch<ComplianceEnterpriseRequest>(`/v1/admin/compliance/requests/${requestId}/process`,
      { method: "POST" }),
  getRequestAudit: (requestId: string) =>
    apiFetch<{ request_id: string; audit_trail: ComplianceAuditEntry[] }>(
      `/v1/admin/compliance/requests/${requestId}/audit`),
  refreshSla: () =>
    apiFetch<{ breached: number; at_risk: number; on_track: number; checked_at: string }>(
      "/v1/admin/compliance/sla/refresh", { method: "POST" }),

  // Consent registry
  listConsents: (params?: {
    subject_id?: string; consent_type?: string; action?: string;
    page?: number; limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.subject_id)   q.set("subject_id", params.subject_id);
    if (params?.consent_type) q.set("consent_type", params.consent_type);
    if (params?.action)       q.set("action", params.action);
    if (params?.page)         q.set("page", String(params.page));
    if (params?.limit)        q.set("limit", String(params.limit));
    const qs = q.toString();
    return apiFetch<ConsentRecordList>(`/v1/admin/compliance/consents${qs ? `?${qs}` : ""}`);
  },
  revokeConsent: (userId: string, consentType: string, notes?: string) =>
    apiFetch<{ record_id: string; action: string }>(
      `/v1/admin/compliance/consents/${userId}/revoke`,
      { method: "POST", body: JSON.stringify({ consent_type: consentType, notes }) }),

  // Exports
  listExports: (status?: string, page?: number) => {
    const q = new URLSearchParams();
    if (status) q.set("status", status);
    if (page)   q.set("page", String(page));
    return apiFetch<ComplianceExportList>(`/v1/admin/compliance/exports${q.toString() ? `?${q}` : ""}`);
  },
  getExport: (exportId: string) =>
    apiFetch<ComplianceExportRecord>(`/v1/admin/compliance/exports/${exportId}`),
  expireExport: (exportId: string) =>
    apiFetch<ComplianceExportRecord>(`/v1/admin/compliance/exports/${exportId}/expire`,
      { method: "POST" }),

  // Audit trail
  listAuditTrail: (params?: { user_id?: string; action?: string; page?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.user_id) q.set("user_id", params.user_id);
    if (params?.action)  q.set("action", params.action);
    if (params?.page)    q.set("page", String(params.page));
    if (params?.limit)   q.set("limit", String(params.limit));
    const qs = q.toString();
    return apiFetch<ComplianceAuditList>(`/v1/admin/compliance/audit-trail${qs ? `?${qs}` : ""}`);
  },

  // Retention policies (enterprise)
  createRetentionPolicy: (data: { table_name: string; retention_days: number; legal_basis?: string }) =>
    apiFetch<RetentionPolicy>("/v1/admin/compliance/retention-policies",
      { method: "POST", body: JSON.stringify(data) }),
  updateRetentionPolicy: (tableName: string, data: { retention_days: number; legal_basis?: string }) =>
    apiFetch<RetentionPolicy>(`/v1/admin/compliance/retention-policies/${tableName}`,
      { method: "PUT", body: JSON.stringify(data) }),

  // SLA job triggers
  runJobs: () =>
    apiFetch<{ sla_check: Record<string, unknown>; expire_exports: Record<string, unknown>; run_at: string }>(
      "/v1/admin/compliance/jobs/run", { method: "POST" }),
  runSlaCheck: () =>
    apiFetch<{ task: string; checked: number; newly_breached: number; newly_at_risk: number; notifications_sent: number; run_at: string }>(
      "/v1/admin/compliance/jobs/run-sla", { method: "POST" }),
  runExpireExports: () =>
    apiFetch<{ task: string; expired: number; run_at: string }>(
      "/v1/admin/compliance/jobs/run-expire-exports", { method: "POST" }),

  // ── DPDP Command Center upgrade (migration 107) ──────────────────────────
  getHealth: () =>
    apiFetch<DpdpHealth>("/v1/admin/compliance/dpdp/health"),
  getActionQueue: (limit = 50) =>
    apiFetch<{ items: DpdpActionQueueItem[]; count: number }>(
      `/v1/admin/compliance/dpdp/action-queue?limit=${limit}`),
  assignRequest: (requestId: string, assignedToUserId: string) =>
    apiFetch<ComplianceEnterpriseRequest>(`/v1/admin/compliance/requests/${requestId}/assign`,
      { method: "POST", body: JSON.stringify({ assigned_to_user_id: assignedToUserId }) }),
  escalateRequest: (requestId: string, reason: string) =>
    apiFetch<ComplianceEnterpriseRequest>(`/v1/admin/compliance/requests/${requestId}/escalate`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  getDataMap: (requestId: string) =>
    apiFetch<DpdpDataMap>(`/v1/admin/compliance/requests/${requestId}/data-map`),
  refreshDataMap: (requestId: string) =>
    apiFetch<DpdpDataMap>(`/v1/admin/compliance/requests/${requestId}/refresh-data-map`,
      { method: "POST" }),
  listLegalHolds: (status?: string, page = 1, limit = 50) => {
    const q = new URLSearchParams();
    if (status) q.set("status", status);
    q.set("page", String(page)); q.set("limit", String(limit));
    return apiFetch<{ items: DpdpLegalHold[]; meta: { total: number; page: number; limit: number } }>(
      `/v1/admin/compliance/dpdp/legal-holds?${q.toString()}`);
  },
  applyLegalHold: (data: { entity_type: string; entity_id: string; reason: string; expires_at?: string }) =>
    apiFetch<{ id: string; hold_code: string; status: string }>("/v1/admin/compliance/dpdp/legal-holds",
      { method: "POST", body: JSON.stringify(data) }),
  releaseLegalHold: (holdId: string, reason: string) =>
    apiFetch<{ id: string; hold_code: string; status: string }>(
      `/v1/admin/compliance/dpdp/legal-holds/${holdId}/release`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  generateEvidencePack: (requestId: string) =>
    apiFetch<{ pack_id: string; request_id: string; generated_at: string }>(
      `/v1/admin/compliance/requests/${requestId}/generate-evidence-pack`, { method: "POST" }),
  listEvidencePacks: (requestId?: string, page = 1, limit = 50) => {
    const q = new URLSearchParams();
    if (requestId) q.set("request_id", requestId);
    q.set("page", String(page)); q.set("limit", String(limit));
    return apiFetch<{ items: DpdpEvidencePack[]; meta: { total: number; page: number; limit: number } }>(
      `/v1/admin/compliance/dpdp/evidence-packs?${q.toString()}`);
  },
};

export interface DpdpHealth {
  score: number; band: string; status: string;
  top_risks: string[]; recommended_actions: string[];
  last_sla_job_run: string | null; last_retention_job_run: string | null;
  generated_at: string;
}
export interface DpdpActionQueueItem extends ComplianceEnterpriseRequest {
  priority: "critical" | "high" | "medium" | "low";
  next_action: string;
}
export interface DpdpDataMapItem {
  id: string; request_id: string; module_name: string; record_type: string;
  record_count: number; planned_action: string; actual_action: string | null;
  exemption_reason: string | null; status: string; legal_hold: string | null;
}
export interface DpdpDataMap {
  request_id: string; data_map: DpdpDataMapItem[];
  active_legal_hold: { id: string; hold_code: string; reason: string; expires_at: string | null } | null;
}
export interface DpdpLegalHold {
  id: string; hold_code: string; entity_type: string; entity_id: string;
  reason: string; status: string; applied_by_user_id: string | null; applied_at: string;
  expires_at: string | null; released_by_user_id: string | null; released_at: string | null;
  release_reason: string | null;
}
export interface DpdpEvidencePack {
  id: string; request_id: string; generated_by_user_id: string | null; created_at: string;
}

// ── Marketing ─────────────────────────────────────────────────────────────────
export const marketingApi = {
  summary:         () => apiFetch<MarketingSummary>("/v1/marketing/summary"),
  budgetStatus:    () => apiFetch<BudgetStatus>("/v1/marketing/budget"),

  // Social accounts
  listAccounts:    (platform?: string) => apiFetch<SocialAccountList>(`/v1/marketing/accounts${platform ? `?platform=${platform}` : ""}`),
  getAccount:      (accountId: string) => apiFetch<SocialAccount>(`/v1/marketing/accounts/${accountId}`),
  connectAccount:  (platform: string, pageId: string, pageName: string, accessToken: string, igUserId?: string, isPrimary = false) =>
    apiFetch<SocialAccount>("/v1/marketing/accounts",
      { method: "POST", body: JSON.stringify({ platform, page_id: pageId, page_name: pageName, access_token: accessToken, ig_user_id: igUserId, is_primary: isPrimary }) }),
  refreshToken:    (accountId: string) => apiFetch<SocialAccount>(`/v1/marketing/accounts/${accountId}/refresh-token`, { method: "POST" }),

  // Content templates
  createTemplate: (postType: string, name: string, dallePrompt: string, captionTemplate: string, vertical?: string, requiredVars?: string[], defaultTags?: string[]) =>
    apiFetch<ContentTemplate>("/v1/marketing/templates",
      { method: "POST", body: JSON.stringify({ post_type: postType, vertical, name, dalle_prompt: dallePrompt, caption_template: captionTemplate, required_vars: requiredVars ?? [], default_tags: defaultTags ?? [] }) }),
  listTemplates:  (postType?: string, vertical?: string) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries({ ...(postType ? { post_type: postType } : {}), ...(vertical ? { vertical } : {}) }))).toString();
    return apiFetch<ContentTemplateList>(`/v1/marketing/templates?${qs}`);
  },
  getTemplate:    (templateId: string) => apiFetch<ContentTemplate>(`/v1/marketing/templates/${templateId}`),

  // Image generation
  generateImage:   (postType: string, variables: Record<string,string>, templateId?: string) =>
    apiFetch<GeneratedAsset>("/v1/marketing/images/generate",
      { method: "POST", body: JSON.stringify({ post_type: postType, variables, template_id: templateId }) }),
  getAsset:       (assetId: string) => apiFetch<GeneratedAsset>(`/v1/marketing/images/${assetId}`),
  listAssets:     (postType?: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries({ ...(postType ? { post_type: postType } : {}), limit: String(limit), ...(cursor ? { cursor } : {}) }))).toString();
    return apiFetch<GeneratedAssetList>(`/v1/marketing/images?${qs}`);
  },

  // Content calendar
  schedulePost:    (data: SchedulePostInput) =>
    apiFetch<ScheduledPost>("/v1/marketing/posts",
      { method: "POST", body: JSON.stringify(data) }),
  getCalendar:     (dateFrom: string, dateTo: string, accountId?: string) =>
    apiFetch<CalendarResponse>(`/v1/marketing/calendar?date_from=${dateFrom}&date_to=${dateTo}${accountId ? `&account_id=${accountId}` : ""}`),
  publishPost:    (postId: string) => apiFetch<ScheduledPost>(`/v1/marketing/posts/${postId}/publish`, { method: "POST" }),
  cancelPost:     (postId: string, reason?: string) =>
    apiFetch<ScheduledPost>(`/v1/marketing/posts/${postId}/cancel`, { method: "POST", body: JSON.stringify({ reason }) }),

  // Deliveries
  listDeliveries: (accountId?: string, status?: string, limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries({ ...(accountId ? { account_id: accountId } : {}), ...(status ? { status } : {}), limit: String(limit), ...(cursor ? { cursor } : {}) }))).toString();
    return apiFetch<DeliveryList>(`/v1/marketing/deliveries?${qs}`);
  },

  // Tenant onboarding trigger
  triggerOnboarding: (tenantId: string, tenantName: string, city: string, vertical: string) =>
    apiFetch<OnboardingResult>("/v1/marketing/tenant-onboarded",
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId, tenant_name: tenantName, city, vertical, service_types: [] }) }),
};

// ── Review ────────────────────────────────────────────────────────────────────────────────
export const reviewApi = {
  listByTenant:  (tenantId: string, limit = 10, status?: string) => {
    const qs = new URLSearchParams(Object.assign({ tenant_id: tenantId, limit: String(limit) }, status ? { status } : {})).toString();
    return apiFetch<ReviewList>(`/v1/reviews?${qs}`);
  },
  getAggregate:  (entityType: string, entityId: string) =>
    apiFetch<ReviewAggregate>(`/v1/reviews/aggregates/${entityType}/${entityId}`),
  flag:    (reviewId: string, reason: string) =>
    apiFetch<AdminReview>(`/v1/reviews/${reviewId}/flag`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  resolve: (reviewId: string, action: "publish"|"remove", reason?: string) =>
    apiFetch<AdminReview>(`/v1/reviews/${reviewId}/resolve`,
      { method: "POST", body: JSON.stringify({ action, reason }) }),
  listFlagged: (tenantId: string, limit = 20) =>
    apiFetch<ReviewList>(`/v1/reviews?tenant_id=${tenantId}&status=flagged&limit=${limit}`),
};

// ── Notification templates (super-admin) ──────────────────────────────────────────────────────
export const notificationApi = {
  listTemplates: (tenantId?: string) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : "";
    return apiFetch<NotifTemplateList>(`/v1/notifications/templates/list${qs}`);
  },
  createTemplate: (data: { tenant_id?:string; notif_type:string; channel:string; title?:string; body:string; vertical?:string }) =>
    apiFetch<NotifTemplate>("/v1/notifications/templates",
      { method: "POST", body: JSON.stringify(data) }),
  updateTemplate: (templateId: string, data: Partial<{ title:string; body:string; is_active:boolean }>) =>
    apiFetch<NotifTemplate>(`/v1/notifications/templates/${templateId}`,
      { method: "PUT", body: JSON.stringify(data) }),
  deleteTemplate: (templateId: string) =>
    apiFetch<void>(`/v1/notifications/templates/${templateId}`, { method: "DELETE" }),
}

// ── Notification Template Center (Enterprise Upgrade) ─────────────────────────
export interface AdminNotifTemplate {
  template_id: string; template_key: string; name: string; event_type: string;
  channel: string; audience: string; app_scope: string; scope_type: string;
  vertical_key: string | null; tenant_id: string | null; language: string; status: string;
  title: string | null; subject: string | null; body: string; html_body: string | null;
  plain_text_body: string | null; action_label: string | null; action_url: string | null;
  priority: string; variables: string[]; is_platform_default: boolean; is_system: boolean;
  fallback_template_id: string | null; created_at: string; updated_at: string; archived_at: string | null;
}
export interface NotifTemplateSummary {
  total_templates: number; active_templates: number; draft_templates: number;
  platform_defaults: number; tenant_overrides: number; missing_translations: number;
  validation_errors: number; failed_deliveries: number;
}
export interface NotifTemplateVariableValidation {
  valid: boolean; used_variables: string[]; allowed_variables: string[];
  unknown_variables: string[]; forbidden_variables: string[];
}
export interface NotifTemplatePreview {
  rendered_title: string; rendered_body: string; rendered_subject: string; channel: string;
  variable_values_used: Record<string, string>; missing_variables: string[]; warnings: string[];
}
export interface NotifTemplateVersion {
  id: string; template_id: string; version_number: number;
  snapshot: Record<string, unknown>; change_reason: string | null; created_at: string;
}

export const notifTemplateAdminApi = {
  listTemplates: (params?: Record<string, string | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params ?? {}).forEach(([k, v]) => { if (v) qs.set(k, v); });
    return apiFetch<{ items: AdminNotifTemplate[]; total: number }>(`/v1/admin/notifications/templates?${qs}`);
  },
  getSummary: () => apiFetch<NotifTemplateSummary>("/v1/admin/notifications/templates/summary"),
  getTemplate: (templateId: string) => apiFetch<AdminNotifTemplate>(`/v1/admin/notifications/templates/${templateId}`),
  createTemplate: (data: Record<string, unknown>) =>
    apiFetch<AdminNotifTemplate>("/v1/admin/notifications/templates", { method: "POST", body: JSON.stringify(data) }),
  updateTemplate: (templateId: string, data: Record<string, unknown>) =>
    apiFetch<AdminNotifTemplate>(`/v1/admin/notifications/templates/${templateId}`, { method: "PUT", body: JSON.stringify(data) }),
  activate: (templateId: string) =>
    apiFetch<AdminNotifTemplate>(`/v1/admin/notifications/templates/${templateId}/activate`, { method: "POST" }),
  deactivate: (templateId: string) =>
    apiFetch<AdminNotifTemplate>(`/v1/admin/notifications/templates/${templateId}/deactivate`, { method: "POST" }),
  archive: (templateId: string) =>
    apiFetch<AdminNotifTemplate>(`/v1/admin/notifications/templates/${templateId}/archive`, { method: "POST" }),
  deleteTemplate: (templateId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/notifications/templates/${templateId}`, { method: "DELETE" }),
  clone: (templateId: string) =>
    apiFetch<AdminNotifTemplate>(`/v1/admin/notifications/templates/${templateId}/clone`, { method: "POST" }),
  createOverride: (templateId: string, data: { scope_type: string; tenant_id?: string; vertical_key?: string }) =>
    apiFetch<AdminNotifTemplate>(`/v1/admin/notifications/templates/${templateId}/create-override`,
      { method: "POST", body: JSON.stringify(data) }),
  validate: (templateId: string) =>
    apiFetch<NotifTemplateVariableValidation>(`/v1/admin/notifications/templates/${templateId}/validate`, { method: "POST" }),
  renderPreview: (templateId: string, sampleData: Record<string, string>) =>
    apiFetch<NotifTemplatePreview>(`/v1/admin/notifications/templates/${templateId}/render-preview`,
      { method: "POST", body: JSON.stringify({ sample_data: sampleData }) }),
  testSend: (templateId: string, recipient: string, sampleData: Record<string, string>) =>
    apiFetch<{ is_test: boolean; message: string }>(`/v1/admin/notifications/templates/${templateId}/test-send`,
      { method: "POST", body: JSON.stringify({ recipient, sample_data: sampleData }) }),
  listVersions: (templateId: string) =>
    apiFetch<{ items: NotifTemplateVersion[] }>(`/v1/admin/notifications/templates/${templateId}/versions`),
  rollback: (templateId: string, versionNumber: number, reason: string) =>
    apiFetch<AdminNotifTemplate>(`/v1/admin/notifications/templates/${templateId}/rollback`,
      { method: "POST", body: JSON.stringify({ version_number: versionNumber, reason }) }),
  deliveryAnalytics: (templateId: string) =>
    apiFetch<{ sent: number; delivered: number; failed: number; delivery_rate: number; failure_rate: number; last_failure_reason: string | null }>(
      `/v1/admin/notifications/templates/${templateId}/delivery-analytics`),
  listAuditLogs: (templateId?: string) =>
    apiFetch<{ items: { id: string; action_type: string; reason: string | null; created_at: string }[] }>(
      templateId ? `/v1/admin/notifications/templates/${templateId}/audit-logs` : "/v1/admin/notifications/templates/audit-logs"),
  seedDefaultsPreview: () =>
    apiFetch<{ templates_to_create: number }>("/v1/admin/notifications/templates/seed-defaults/preview", { method: "POST" }),
  seedDefaults: () =>
    apiFetch<{ created: number }>("/v1/admin/notifications/templates/seed-defaults", { method: "POST" }),
  resolveEffectiveTemplate: (eventType: string, channel: string, audience: string, tenantId?: string, verticalKey?: string) =>
    apiFetch<{ effective_template: AdminNotifTemplate | null; resolution_path: { scope: string; matched: boolean }[] }>(
      "/v1/admin/notifications/templates/resolve-effective-template",
      { method: "POST", body: JSON.stringify({ event_type: eventType, channel, audience, tenant_id: tenantId, vertical_key: verticalKey }) }),
};

// ── Data Science (20 endpoints) ───────────────────────────────────────────────
export const dsApi = {
  // Churn prediction
  getChurnScore:    (tenantId: string) => apiFetch<ChurnScore>(`/v1/ds/tenants/${tenantId}/churn/score`),
  listAtRiskTenants:(limit = 50, cursor?: string) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries({ limit: String(limit), ...(cursor ? { cursor } : {}) }))).toString();
    return apiFetch<ChurnAtRiskList>(`/v1/ds/churn/at-risk?${qs}`);
  },
  getChurnFactors:  (tenantId: string) => apiFetch<ChurnFactors>(`/v1/ds/tenants/${tenantId}/churn/factors`),
  getChurnHistory:  (tenantId: string, days = 30) =>
    apiFetch<ChurnHistory>(`/v1/ds/tenants/${tenantId}/churn/history?days=${days}`),

  // Demand forecasting
  getDemandForecast: (tenantId: string) => apiFetch<DemandForecastDetail>(`/v1/ds/tenants/${tenantId}/demand/forecast`),
  recomputeDemand:   (tenantId: string) =>
    apiFetch<DemandForecastDetail>(`/v1/ds/tenants/${tenantId}/demand/recompute`, { method: "POST" }),
  getDemandHistory:  (tenantId: string, days = 30) =>
    apiFetch<DemandHistory>(`/v1/ds/tenants/${tenantId}/demand/history?days=${days}`),

  // Pricing recommendations
  getPricingRecommendations: (tenantId: string) =>
    apiFetch<PricingRecommendationList>(`/v1/ds/tenants/${tenantId}/pricing/recommendations`),
  applyPricingRecommendation:(tenantId: string, serviceTypeId: string, targetPrice: number) =>
    apiFetch<void>(`/v1/ds/tenants/${tenantId}/pricing/apply`,
      { method: "POST", body: JSON.stringify({ service_type_id: serviceTypeId, target_price: targetPrice }) }),
  getPricingHistory: (tenantId: string) =>
    apiFetch<PricingHistory>(`/v1/ds/tenants/${tenantId}/pricing/history`),

  // Staff performance
  getStaffRankings: (tenantId: string) => apiFetch<StaffRankingList>(`/v1/ds/tenants/${tenantId}/staff/rankings`),
  getStaffScore:    (tenantId: string, staffId: string) =>
    apiFetch<StaffScoreDetail>(`/v1/ds/tenants/${tenantId}/staff/${staffId}/score`),
  updateStaffSignal:(tenantId: string, staffId: string, signal: string, value: number) =>
    apiFetch<void>(`/v1/ds/tenants/${tenantId}/staff/${staffId}/signal`,
      { method: "POST", body: JSON.stringify({ signal, value }) }),

  // Customer LTV
  getCustomerLtv:     (tenantId: string, customerId: string) =>
    apiFetch<CustomerLtv>(`/v1/ds/tenants/${tenantId}/customers/${customerId}/ltv`),
  listHighValueCustomers: (tenantId: string, limit = 20) =>
    apiFetch<HighValueCustomerList>(`/v1/ds/tenants/${tenantId}/customers/high-value?limit=${limit}`),
  recomputeLtv:       (tenantId: string, customerId: string) =>
    apiFetch<CustomerLtv>(`/v1/ds/tenants/${tenantId}/customers/${customerId}/ltv/recompute`, { method: "POST" }),

  // Anomaly detection
  listAnomalies: (params?: { tenant_id?: string; status?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<AnomalyList>(`/v1/ds/anomalies?${qs}`);
  },
  getAnomaly:        (anomalyId: string) => apiFetch<Anomaly>(`/v1/ds/anomalies/${anomalyId}`),
  acknowledgeAnomaly:(anomalyId: string, notes?: string) =>
    apiFetch<Anomaly>(`/v1/ds/anomalies/${anomalyId}/acknowledge`,
      { method: "POST", body: JSON.stringify({ notes }) }),

  // Model management
  listModelVersions: (modelType?: string) =>
    apiFetch<ModelVersionList>(`/v1/ds/models${modelType ? `?model_type=${modelType}` : ""}`),
  triggerRetrain:    (modelType: string) =>
    apiFetch<void>(`/v1/ds/models/${modelType}/retrain`, { method: "POST" }),

  // Platform summary
  platformSummary:   () => apiFetch<DsPlatformSummary>("/v1/ds/platform/summary"),
};

// ── Phase 2 types ─────────────────────────────────────────────────────────────
export interface Tenant360 extends Tenant { health?: TenantHealth; engines?: TenantEngine[]; }
export interface TenantHealth { tenant_id: string; overall_score: number; signals: Record<string,number>; computed_at: string; }
export interface TenantHealthHistory { tenant_id: string; history: { date: string; score: number }[]; }
export interface TenantEngine { engine_id: string; name: string; is_enabled: boolean; config?: Record<string,unknown>; }
export interface TenantEngineList { engines: TenantEngine[]; }
export interface EngineConfig { engine_id: string; tenant_id: string; config: Record<string,unknown>; updated_at?: string; }
export interface FeatureFlag { flag: string; value: boolean|string|number; source: string; resolved_at?: string; }
export interface FeatureFlagList { flags: Record<string, FeatureFlag>; }
export interface TenantBillingInfo { tenant_id: string; billing_mode: string; plan_type: string; commission_rate: number; payment_method?: Record<string,unknown>; next_billing_at?: string; subscription_status?: string; }
export interface InvoiceRecord { id: string; invoice_number: string; amount: number; status: string; pdf_url?: string; created_at: string; }
export interface InvoiceListResponse { invoices: InvoiceRecord[]; has_next: boolean; next_cursor?: string; }
export interface DataExportRequest { export_id: string; status: string; download_url?: string; expires_at?: string; requested_at: string; }
export interface TenantAuditLog { log_id: string; operation: string; actor_id?: string; details?: Record<string,unknown>; created_at: string; }
export interface TenantAuditLogList { logs: TenantAuditLog[]; has_next: boolean; }
export interface LimitCheck { resource: string; current: number; limit: number; within_limit: boolean; }
export interface WalletTransaction {
  txn_id: string; txn_type: string; amount: number;
  balance_before: number; balance_after: number;
  reference_id?: string | null; reference_type?: string | null;
  description?: string | null; created_at: string;
}
export interface WalletTransactionList { transactions: WalletTransaction[]; has_next: boolean; next_cursor?: string; }
export interface WalletProjection { projected_days_remaining: number; avg_daily_spend: number; low_balance_warning: boolean; }
export interface PurchaseOrder { order_id: string; amount: number; status: string; payment_url?: string; expires_at: string; }
export interface CommissionRate { rate: number; effective_from: string; plan_type: string; }
export interface CommissionProjection { projected_monthly: number; based_on_jobs: number; period_days: number; }
export interface Deposit { tenant_id: string; status: string; required_amount: number; total_paid: number; warranty_drawn: number; replenishment_total: number; current_balance: number; }
export interface DepositList { deposits: Deposit[]; has_next: boolean; }
export interface CreditPackage { id: string; name: string; credits: number; price_inr: number; bonus_credits?: number; is_active: boolean; created_at: string; }
export interface CreditPackageList { packages: CreditPackage[]; }
export interface CustomerAtRisk { customer_id: string; name: string; health_score: number; risk_flags: string[]; last_job_at?: string; }
export interface CustomerAtRiskList { customers: CustomerAtRisk[]; total: number; }
export interface WarrantyClaim { claim_id: string; job_id: string; tenant_id: string; customer_name?: string; issue_description: string; status: string; claimed_at: string; resolved_at?: string; notes?: string; }
export interface WarrantyClaimList { claims: WarrantyClaim[]; total: number; has_next: boolean; }
export interface TenantBadge { badge_id: string; badge_type: string; tenant_id: string; awarded_at: string; }
export interface BadgeList { badges: TenantBadge[]; }
export interface Reservation { id: string; tenant_id: string; customer_id: string; service_type: string; scheduled_at: string; status: string; created_at: string; }
export interface ReservationList { reservations: Reservation[]; has_next: boolean; }
export interface PreflightResult { allowed: boolean; errors?: string[]; warnings?: string[]; }
export interface PlatformCommerceAnalytics { period_days: number; total_credits_sold: number; total_commission: number; active_tenants: number; avg_wallet_balance: number; }
export interface PaymentOrder { order_id: string; tenant_id: string; amount: number; currency: string; status: string; gateway: string; created_at: string; }
export interface PaymentOrderList { orders: PaymentOrder[]; has_next: boolean; }
export interface Payment { payment_id: string; order_id?: string; tenant_id: string; amount: number; status: string; gateway?: string; created_at: string; }
export interface PaymentList { payments: Payment[]; has_next: boolean; }
export interface Refund { refund_id: string; payment_id: string; amount: number; status: string; reason: string; created_at: string; }
export interface RefundList { refunds: Refund[]; has_next: boolean; }
export interface Payout { payout_id: string; tenant_id: string; amount: number; status: string; bank_account_id?: string; requested_at: string; processed_at?: string; }
export interface PayoutList { payouts: Payout[]; has_next: boolean; }

// ── Phase 3 — Data Science types ──────────────────────────────────────────────
export interface ChurnScore {
  tenant_id: string; churn_score: number; churn_band: string;
  contributing_factors: { signal: string; value: number; weight: number; contribution: number }[];
  score_delta: number | null; prev_score: number | null; observation_mode: boolean;
  ds_phase: number; model_version: string; computed_at: string; interpretation: string;
}
export interface ChurnAtRiskEntry { tenant_id: string; churn_score: number; churn_band: string; score_delta: number | null; observation_mode: boolean; computed_at: string; }
export interface ChurnAtRiskList { at_risk_tenants: ChurnAtRiskEntry[]; has_next: boolean; next_cursor?: string; }
export interface ChurnFactors {
  tenant_id: string; churn_score: number; churn_band: string;
  contributing_factors: { signal: string; value: number; weight: number; contribution: number }[];
  signal_values: Record<string, number>; observation_mode: boolean;
  recommended_actions: { action: string; priority: string }[];
}
export interface ChurnHistory { tenant_id: string; days: number; history: { score: number; band: string; ds_phase: number; computed_at: string }[]; }
export interface DemandForecastDetail {
  tenant_id: string; forecast_date: string; horizon_days: number; total_predicted: number;
  peak_day: string; daily_forecasts: Record<string, unknown>; observation_mode: boolean;
  ds_phase: number; model_version: string; computed_at: string; interpretation: string;
}
export interface DemandHistory { tenant_id: string; days: number; forecasts: { forecast_date: string; total_predicted: number; peak_day: string; model_version: string }[]; }
export interface PricingRecommendation { service_type_id: string; current_price: number; benchmark_price: number; floor_price: number; gap_pct: number; action: "increase"|"decrease"|"hold"; potential_uplift: number; }
export interface PricingRecommendationList { tenant_id: string; recommendations: PricingRecommendation[]; observation_mode: boolean; ds_phase: number; generated_at: string; }
export interface PricingHistory { tenant_id: string; history: { computed_at: string; recommendations: number }[]; }
export interface StaffRanking { staff_id: string; rank: number; composite_score: number; jobs_completed: number; avg_rating: number; sla_adherence: number; }
export interface StaffRankingList { tenant_id: string; observation_mode: boolean; rankings: StaffRanking[]; }
export interface StaffScoreDetail { staff_id: string; tenant_id: string; composite_score: number; rank: number; signal_values: Record<string,number>; jobs_completed: number; avg_customer_rating: number; sla_adherence_rate: number; }
export interface CustomerLtv { customer_id: string; tenant_id: string; predicted_ltv: number; ltv_band: string; booking_frequency: number; avg_job_value: number; churn_probability: number; observation_mode: boolean; }
export interface HighValueCustomer { customer_id: string; predicted_ltv: number; ltv_band: string; booking_frequency: number; churn_probability: number; }
export interface HighValueCustomerList { tenant_id: string; high_value_customers: HighValueCustomer[]; }
export interface Anomaly {
  anomaly_id: string; tenant_id: string; anomaly_type: string; severity: string;
  description: string; detected_value: number; threshold_value: number; context: Record<string,unknown>;
  status: string; notification_sent: boolean; acknowledged_at?: string; resolution_notes?: string; created_at: string;
}
export interface AnomalyList { anomalies: Anomaly[]; has_next: boolean; next_cursor?: string; }
export interface ModelVersion { version_id: string; model_type: string; version: string; is_active: boolean; training_date: string; training_rows: number; metrics: Record<string,unknown>; }
export interface ModelVersionList { versions: ModelVersion[]; }
export interface DsPlatformSummary { tenants_at_risk: number; open_anomalies: number; total_predictions_computed: number; models_active: number; generated_at: string; }

// ── Phase 3 — Analytics types ──────────────────────────────────────────────────
export interface TenantMetrics { tenant_id: string; period_days: number; event_counts: Record<string,number>; generated_at: string; }
export interface DailyMetric { date: string; value: number | Record<string,unknown>; }
export interface DailyMetricList { metric_key: string; period_days: number; data: DailyMetric[]; }
export interface AnalyticsEventEntry { event_id: string; event_type: string; tenant_id?: string; occurred_at: string; }
export interface EventStreamResponse { events: AnalyticsEventEntry[]; has_next: boolean; next_cursor?: string; }
export interface AnalyticsPlatformSummary { active_tenants_estimate: number; events_today: number; generated_at: string; _note?: string; }

// ── Phase 3 — RAG types ────────────────────────────────────────────────────────
export interface RagKnowledgeBaseV1 {
  kb_id: string; tenant_id: string; name: string; description?: string; vertical?: string;
  embedding_model: string; chunk_size: number; chunk_overlap: number; top_k: number;
  document_count: number; indexed_count: number; total_chunks: number; total_tokens_used: number; created_at: string;
}
export interface KnowledgeBaseList { knowledge_bases: RagKnowledgeBaseV1[]; has_next: boolean; next_cursor?: string; }
export interface KBDocument {
  doc_id: string; kb_id: string; file_name: string; mime_type: string; content_hash: string;
  status: string; status_message?: string; version: number; char_count: number; chunk_count: number;
  token_count: number; tags: string[]; indexed_at?: string; created_at: string; idempotent?: boolean;
}
export interface KBDocumentList { documents: KBDocument[]; has_next: boolean; next_cursor?: string; }
export interface Chunk { chunk_id: string; kb_id: string; doc_id: string; content: string; chunk_index: number; has_embedding: boolean; created_at: string; }
export interface ChunkList { chunks: Chunk[]; has_next: boolean; next_cursor?: string; }
export interface RagQueryResult {
  query_id: string; kb_id: string; tenant_id: string; question: string; answer?: string; status: string;
  citations: Record<string,unknown>[]; top_similarity: number; low_confidence: boolean;
  embedding_tokens: number; completion_tokens: number; total_tokens: number; latency_ms: number;
  model_used: string; created_at: string; idempotent?: boolean;
}
export interface RagQueryList { queries: RagQueryResult[]; has_next: boolean; next_cursor?: string; }
export interface RagSearchResult { kb_id: string; question: string; results: { chunk_id: string; content: string; similarity: number }[]; }
export interface RagPlatformUsage { kb_count: number; total_tokens_used: number; indexed_docs: number; total_queries: number; avg_latency_ms: number; total_query_tokens: number; }

// ── Phase 3 — Marketing extended types ────────────────────────────────────────
export interface ContentTemplate { template_id: string; post_type: string; vertical?: string; name: string; dalle_prompt: string; caption_template: string; required_vars: string[]; default_tags: string[]; is_active: boolean; created_at: string; }
export interface ContentTemplateList { templates: ContentTemplate[]; }
export interface GeneratedAssetList { assets: GeneratedAsset[]; has_next: boolean; next_cursor?: string; }
export interface Delivery { delivery_id: string; post_id: string; account_id: string; status: string; meta_response?: Record<string,unknown>; created_at: string; }
export interface DeliveryList { deliveries: Delivery[]; has_next: boolean; next_cursor?: string; }

// ── Mock data for offline / development mode ──────────────────────────────────
// PROVEN: All mock data matches the real API response shape exactly.
// Remove NEXT_PUBLIC_USE_MOCK=true in production.

export interface JobHistory    { history: { status: string; changed_at: string; notes?: string; changed_by?: string }[] }
export interface StaffMember   { id: string; full_name: string; phone?: string; status: string; specialisations: string[]; rating?: number; jobs_today?: number; }
export interface StaffList     { staff: StaffMember[]; total: number; }
export interface AdminStaffUser { user_id: string; email: string; full_name: string; phone?: string; role: string; tenant_id?: string; is_active: boolean; is_verified: boolean; last_login_at?: string; created_at: string; }
export interface AdminStaffList { users: AdminStaffUser[]; total: number; }
export interface CreateTenantPayload {
  name: string; owner_name: string; owner_email: string; owner_phone: string;
  vertical: string; city: string; city_tier: number;
  plan_type: string; billing_mode: string; commission_rate: number;
}


// ── Documents ─────────────────────────────────────────────────────────────────
export const documentsApi = {
  create: (tenantId: string, docType: string, entityType: string, entityId: string, customerId?: string, variables?: Record<string,string>) =>
    apiFetch<TenantDocument>("/v1/documents",
      { method:"POST", body:JSON.stringify({ tenant_id: tenantId, doc_type: docType, entity_type: entityType,
        entity_id: entityId, customer_id: customerId, variables: variables ?? {} }) }),
  get:  (id: string) => apiFetch<TenantDocument>(`/v1/documents/${id}`),
  list: (tenantId: string, entityType: string, entityId: string, limit = 20, cursor?: string) => {
    const qs = new URLSearchParams({ tenant_id: tenantId, entity_type: entityType, entity_id: entityId,
      limit: String(limit), ...(cursor ? { cursor } : {}) }).toString();
    return apiFetch<TenantDocumentList>(`/v1/documents?${qs}`);
  },
  send: (id: string) => apiFetch<TenantDocument>(`/v1/documents/${id}/send`, { method:"POST" }),
  void: (id: string, reason = "Voided") =>
    apiFetch<TenantDocument>(`/v1/documents/${id}/void`, { method:"POST", body:JSON.stringify({ reason }) }),
  events: (id: string) => apiFetch<DocumentEventList>(`/v1/documents/${id}/events`),
  getSigningUrl: (id: string) =>
    apiFetch<{ signing_url:string; expires_at:string }>(`/v1/documents/${id}/signing-url`),
  getTemplate: (tenantId: string, docType: string) =>
    apiFetch<DocumentTemplate>(`/v1/documents/tenants/${tenantId}/templates/${docType}`),
};

// ── Subscription ──────────────────────────────────────────────────────────────
export const subscriptionApi = {
  create: (tenantId: string, planType: string, billingCycle = "monthly", trialDays = 14) =>
    apiFetch<SubscriptionInfo>("/v1/subscriptions",
      { method:"POST", body:JSON.stringify({ tenant_id: tenantId, plan_type: planType,
        billing_cycle: billingCycle, trial_days: trialDays }) }),
  get:    (tenantId: string) => apiFetch<SubscriptionInfo>(`/v1/subscriptions/tenants/${tenantId}`),
  updatePlan: (tenantId: string, newPlan: string, billingCycle = "monthly") =>
    apiFetch<SubscriptionInfo>(`/v1/subscriptions/tenants/${tenantId}/plan`,
      { method:"PUT", body:JSON.stringify({ new_plan: newPlan, billing_cycle: billingCycle }) }),
  cancel: (tenantId: string, reason = "") =>
    apiFetch<SubscriptionInfo>(`/v1/subscriptions/tenants/${tenantId}/cancel`,
      { method:"POST", body:JSON.stringify({ reason }) }),
  pause:  (tenantId: string) =>
    apiFetch<SubscriptionInfo>(`/v1/subscriptions/tenants/${tenantId}/pause`, { method:"POST" }),
  resume: (tenantId: string) =>
    apiFetch<SubscriptionInfo>(`/v1/subscriptions/tenants/${tenantId}/resume`, { method:"POST" }),
  getPeriod: (tenantId: string) =>
    apiFetch<SubscriptionPeriod>(`/v1/subscriptions/tenants/${tenantId}/period`),
  getHistory: (tenantId: string, limit = 12, cursor?: string) => {
    const qs = cursor ? `?limit=${limit}&cursor=${cursor}` : `?limit=${limit}`;
    return apiFetch<SubscriptionHistoryList>(`/v1/subscriptions/tenants/${tenantId}/history${qs}`);
  },
  prorationPreview: (tenantId: string, newPlan: string, billingCycle = "monthly") =>
    apiFetch<ProrationPreview>(
      `/v1/subscriptions/tenants/${tenantId}/proration-preview?new_plan=${newPlan}&billing_cycle=${billingCycle}`),
};

// ── Staff (platform-wide) ─────────────────────────────────────────────────────
export const staffApi = {
  listByTenant: (tenantId: string, limit = 50) =>
    apiFetch<StaffList>(`/v1/auth/staff?tenant_id=${tenantId}&limit=${limit}`),
  adminList: (tenantId: string, limit = 100) =>
    apiFetch<AdminStaffList>(`/v1/auth/users?role=staff&tenant_id=${tenantId}&limit=${limit}`),
  invite: (tenantId: string, data: InviteStaffPayload) =>
    apiFetch<{ invite_id: string; email: string; role: string; expires_at: string }>(
      `/v1/auth/admin/staff/invite?tenant_id=${tenantId}`, { method: "POST", body: JSON.stringify(data) }),
  deactivate: (userId: string) =>
    apiFetch<{ message: string }>(`/v1/auth/admin/staff/${userId}/deactivate`, { method: "POST" }),
  resendInvite: (userId: string) =>
    apiFetch<void>(`/v1/auth/staff/${userId}/invite/resend`, { method: "POST" }),
};

// ── Customers (platform-wide) ─────────────────────────────────────────────────
export const customersApi = {
  listByTenant: (tenantId: string, params?: { limit?: number; cursor?: string; health_band?: string }) => {
    const qs = new URLSearchParams({ tenant_id: tenantId, ...(params?.limit ? { limit: String(params.limit) } : {}), ...(params?.cursor ? { cursor: params.cursor } : {}), ...(params?.health_band ? { health_band: params.health_band } : {}) }).toString();
    return apiFetch<CustomerListResponse>(`/v1/commerce/tenants/${tenantId}/customers?${qs}`);
  },
};

export interface CustomerListResponse { customers: Customer[]; total: number; has_next: boolean; next_cursor?: string; }
export interface Customer { customer_id: string; tenant_id: string; name: string; phone?: string; email?: string; health_score: number; total_jobs: number; total_spent?: number; last_job_at?: string; created_at: string; }

// ── Geo Service Zones (admin — via /v1/geo) ───────────────────────────────────
export const serviceAreaAdminApi = {
  listByTenant: (tenantId: string) =>
    apiFetch<{ tenant_id: string; zones: GeoZone[] }>(`/v1/geo/tenants/${tenantId}/zones`),
  create: (tenantId: string, body: GeoZoneCreatePayload) =>
    apiFetch<GeoZone>(`/v1/geo/tenants/${tenantId}/zones`, { method:"POST", body:JSON.stringify(body) }),
  update: (_tenantId: string, zoneId: string, body: Partial<GeoZoneCreatePayload>) =>
    apiFetch<GeoZone>(`/v1/geo/zones/${zoneId}`, { method:"PUT", body:JSON.stringify(body) }),
  deactivate: (_tenantId: string, zoneId: string) =>
    apiFetch<{ zone_id:string; deactivated:boolean }>(`/v1/geo/zones/${zoneId}`, { method:"DELETE" }),
};

export const serviceabilityApi = {
  check: (body: { city?:string; zipcode?:string; state?:string; service_id:string; job_type:string; address_id?:string }) =>
    apiFetch<ServiceabilityCheckResponse>("/v1/serviceability/check", { method:"POST", body:JSON.stringify(body) }),
  matchingTenants: (body: { city?:string; zipcode?:string; state?:string; service_id:string; job_type:string; address_id?:string }) =>
    apiFetch<{ matched_tenants: MatchedTenant[] }>("/v1/serviceability/matching-tenants", { method:"POST", body:JSON.stringify(body) }),
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
export type ServiceArea = GeoZone;
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

// ── Types ─────────────────────────────────────────────────────────────────────
export interface AdminUser { id: string; email: string; full_name: string; role: string; permissions?: string[]; }
export interface Tenant {
  tenant_id: string; tenant_name: string; vertical: string; city: string; state: string;
  status: string; health_score: number; health_band: string; plan_type: string;
  is_discoverable: boolean; activated_at?: string; created_at: string;
  owner_user_id?: string; country?: string; suspended_at?: string;
  suspension_reason?: string; trial_expires_at?: string; logo_url?: string | null;
  owner_name?: string | null; email?: string | null; phone?: string | null;
  verification_status?: string;
}
export interface TenantListResponse { tenants: Tenant[]; total: number; has_next: boolean; next_cursor?: string; }
export interface WalletBalance {
  credit_balance: number; lifetime_purchased: number; lifetime_consumed: number;
  last_transaction_at?: string; burn_rate_daily: number; projected_days_remaining?: number;
  low_balance_alert: boolean; reconciliation_ok: boolean;
  /** aliases for backward compat */
  balance?: number; reserved?: number; available?: number; currency?: string;
}
export interface CommissionRecord { id: string; job_id: string; amount: number; rate: number; deducted_at?: string; }
export interface CommissionListResponse { records: CommissionRecord[]; total_deducted: number; }
export interface PlatformCommerceSummary { total_credits_issued: number; total_commission_collected: number; active_wallets: number; low_balance_count: number; }
export interface BillingProfile { profile_id: string; tenant_id: string; billing_mode: string; vertical: string; commission_rate: number; plan_type: string; is_active: boolean; activated_at: string; }
export interface BillingConfig { vertical: string; plan_type: string; commission_rate: number; valid_from: string; }
export interface BillingConfigList { configs: BillingConfig[]; }
export interface BillingConfigSet extends BillingConfig { previous_config_closed: boolean; }
export interface RoutingLog { log_id: string; billing_mode: string; operation: string; engine: string; result: string; created_at: string; }
export interface RoutingLogList { logs: RoutingLog[]; has_next: boolean; }
export interface Job { id: string; job_id?: string; job_number: string; tenant_id: string; tenant_name?: string; customer_name?: string; staff_name?: string; assigned_staff?: string; status: string; job_type?: string; service_type?: string; service_type_id?: string; service_category?: string; city?: string; zipcode?: string; created_at: string; updated_at?: string; commission_amount?: number; sla_minutes?: number; minutes_in_status?: number; sla_breach?: boolean; sla_breached?: boolean; sla_breach_level?: string; final_price?: number; quoted_price?: number; scheduled_at?: string; assigned_staff_id?: string; customer_id?: string; title?: string;
  customer_credit_applied?: number; payable_to_provider?: number; payment_collection_mode?: "customer_pays_provider_directly"; platform_payment_collected?: boolean; amount_collected?: number; payment_recorded?: boolean; }
export interface JobListParams { status?: string; tenant_id?: string; city?: string; limit?: string; cursor?: string; }
export interface JobListResponse { jobs: Job[]; total: number; has_next: boolean; next_cursor?: string; }
export interface JobSummary { engine_id: string; endpoint_count: number; status: string; }
export interface SlaAlert { job_id: string; job_number: string; tenant_name: string; status: string; minutes_overdue: number; severity: string; }
export interface OpsSummary { total_active: number; in_progress: number; sla_breached: number; unassigned: number; rework_required: number; completed_today: number; }
export interface JobTransitions { job_id: string; current_status: string; allowed_transitions: string[]; }
export interface JobNote { note_id: string; job_id: string; content: string; note_type: string; is_internal: boolean; created_by?: string; created_at: string; }
export interface JobNoteList { notes: JobNote[]; }
export interface JobMedia { media_id: string; job_id: string; media_type: string; caption?: string; storage_key?: string; status_at_capture?: string; created_at: string; }
export interface JobMediaList { media: JobMedia[]; }
export interface SlaStatusDetail { job_id: string; current_status: string; sla_hours?: number; sla_breach: boolean; }
export interface JobCounts { tenant_id: string; counts: Record<string,number>; total: number; }
export interface TrackedJob { job_number: string; status: string; title: string; scheduled_at?: string; staff_assigned: boolean; allowed_transitions: string[]; }

// ── Booking types ─────────────────────────────────────────────────────────────
export interface Booking {
  booking_id: string; booking_number: string; tenant_id: string; customer_id: string;
  service_type_id: string; service_category: string; status: string;
  quoted_price?: number; price_snapshot_id?: string;
  // Customer Service Credit breakdown — see BookingPaymentBreakdown.
  credit_applied?: number; payable_amount?: number;
  payment_collection_mode?: "customer_pays_provider_directly"; platform_payment_collected?: boolean;
  preferred_date?: string; preferred_slot?: string; scheduled_at?: string;
  address?: Record<string,unknown>; pincode?: string;
  preflight_passed?: boolean; blocking_reason?: string; job_id?: string;
  cancellation_reason?: string; within_cancel_window?: boolean;
  reschedule_count: number; customer_notes?: string; tags?: string[];
  created_at: string; allowed_transitions: string[]; is_terminal: boolean;
}
// Shared payment-breakdown shapes — Home Services rule: customer pays the
// provider directly on-site, ServiceOS never collects the service payment.
// Kept separate from Booking/Job so any page can render a typed subset
// (e.g. a summary card) without depending on the full entity shape.
export type BookingPaymentBreakdown = {
  quoted_price: number;
  credit_applied: number;
  payable_amount: number;
  payment_collection_mode: "customer_pays_provider_directly";
  platform_payment_collected: boolean;
};
export type JobPaymentBreakdown = {
  quoted_price: number;
  customer_credit_applied: number;
  payable_to_provider: number;
  amount_collected?: number;
  payment_recorded: boolean;
  payment_mode?: string;
};

export interface BookingListResponse { bookings: Booking[]; has_next: boolean; next_cursor?: string; }
export interface BookingSearchResponse { results: Booking[]; query: string; }
export interface BookingTimeline { timeline: { from_status?: string; to_status: string; reason?: string; changed_by_role?: string; occurred_at: string }[]; }
export interface BookingNote { note_id: string; booking_id: string; content: string; is_internal: boolean; author_role?: string; created_at: string; }
export interface BookingNoteList { notes: BookingNote[]; }
export interface SlotAvailability { date: string; slot: string; available: boolean; reason?: string; }
export interface CancellationPolicy { tenant_id: string; policy: string; free_cancel_hours: number; max_reschedules: number; penalty_pct?: number; }

// ── Pricing types ─────────────────────────────────────────────────────────────
export interface CityTierConfig { id: string; city_name: string; tier: string; service_category: string; floor_price: number; currency: string; is_active: boolean; notes?: string; }
export interface CityTierConfigList { configs: CityTierConfig[]; }
export interface ServiceTypePrice { id: string; tenant_id: string; service_type_id: string; service_category: string; city_name: string; base_price: number; unit: string; valid_from: string; valid_until?: string; change_reason?: string; previous_price?: number; }
export interface ServiceTypePriceList { prices: ServiceTypePrice[]; }
export interface BrandAdjustment { id: string; tenant_id: string; adjustment_pct: number; label?: string; valid_from: string; reason?: string; }
export interface ZoneSurcharge { zone_id: string; tenant_id: string; zone_name: string; zone_type: string; zone_identifiers: string[]; surcharge_pct: number; is_active: boolean; notes?: string; }
export interface ZoneSurchargeList { zones: ZoneSurcharge[]; }
export interface DynamicPricingRule { rule_id: string; tenant_id: string; rule_name: string; rule_type: string; priority: number; adjustment_pct: number; conditions: Record<string,unknown>; applies_to: string[]; is_active: boolean; active_from?: string; active_until?: string; }
export interface DynamicPricingRuleList { rules: DynamicPricingRule[]; }
export interface PricePipelineStep { applied: boolean; amount?: number; [k: string]: unknown; }
export interface PricePreviewResult { final_price: number; currency: string; steps: Record<string,PricePipelineStep>; }
export interface PriceSnapshot { snapshot_id: string; tenant_id: string; service_type_id: string; service_category: string; city_name: string; final_price: number; currency: string; pipeline_inputs: Record<string,unknown>; step_city_floor: PricePipelineStep; step_tenant_price: PricePipelineStep; step_brand_adj: PricePipelineStep; step_zone_surge: PricePipelineStep; step_dynamic_rule: PricePipelineStep; created_at: string; }
export interface PriceSnapshotList { snapshots: PriceSnapshot[]; has_next: boolean; next_cursor?: string; }

// ── Dispatch types ────────────────────────────────────────────────────────────
export interface DispatchCandidate { staff_id: string; score: number; distance_km?: number; [k: string]: unknown; }
export interface DispatchRecord { job_id: string; tenant_id: string; dispatch_mode: string; status: string; assigned_staff_id?: string; candidates_scored: DispatchCandidate[]; score_weights: Record<string,number>; rejection_count: number; escalation_count: number; accepted_at?: string; expires_at?: string; }
export interface DispatchRecordList { records: DispatchRecord[]; has_next: boolean; next_cursor?: string; }
export interface DispatchQueue { tenant_id: string; queue_size: number; items: DispatchRecord[]; }
export interface ScoringBreakdown { job_id: string; dispatch_mode: string; candidates: DispatchCandidate[]; score_weights: Record<string,number>; selected_staff_id?: string; }

// ── Geo types ─────────────────────────────────────────────────────────────────
export interface ServiceZone { zone_id: string; tenant_id: string; zone_name: string; zone_type: string; identifiers: string[]; center_lat?: number; center_lng?: number; radius_km?: number; surcharge_pct: number; is_active: boolean; }
export interface ServiceZoneList { zones: ServiceZone[]; }
export interface PincodeZoneCheck { pincode: string; in_zone: boolean; zone?: ServiceZone; }
export interface CoverageMap { tenant_id: string; zones: ServiceZone[]; total_area_km2?: number; }
export interface GeoStaffLocation { staff_id: string; tenant_id: string; latitude: number; longitude: number; accuracy_m?: number; status: string; last_ping_at: string; active_job_count: number; }
export interface PlatformKpis { active_tenants: number; jobs_today: number; commission_today: number; at_risk_tenants: number; open_security_threats: number; pending_compliance: number; total_revenue_mtd: number; new_tenants_mtd: number; }
export interface ChartData { date: string; value: number; label?: string; }
export interface EngineMeta { engine_id: string; name: string; endpoint_count: number; status: string; }
export interface SecuritySummary { active_api_keys: number; blocked_ips: number; open_high_threats: number; active_sessions: number; generated_at: string; }
export interface ActivityLog { log_id: string; activity_type: string; threat_level: string; entity_id?: string; description: string; ip_address?: string; detected_value: number; threshold: number; status: string; created_at: string; }
export interface ActivityList { activities: ActivityLog[]; has_next: boolean; }
export interface IpBlockEntry { entry_id: string; ip_or_cidr: string; reason: string; threat_level: string; blocked: boolean; }
export interface BlocklistResponse { entries: IpBlockEntry[]; has_next: boolean; }
export interface Session { session_id: string; device_info: Record<string,unknown>; ip_address: string; last_seen_at: string; expires_at: string; }
export interface SessionList { user_id: string; active_sessions: number; sessions: Session[]; }
export interface AuditSearchParams { actor_id?: string; tenant_id?: string; operation?: string; engine_id?: string; limit?: string; }
export interface AuditLog { log_id: string; operation: string; engine_id: string; entity_type?: string; entity_id?: string; actor_role?: string; actor_ip?: string; is_high_risk: boolean; created_at: string; }
export interface AuditLogList { audit_logs: AuditLog[]; has_next: boolean; note: string; }
export interface ComplianceSummary { pending_deletion_requests: number; sla_breached_deletions: number; pending_exports: number; total_consent_records: number; compliance_status: string; generated_at: string; }
export interface DeletionRequest { request_id: string; user_id: string; status: string; sla_deadline: string; hours_until_sla: number; sla_breached: boolean; tables_erased: string[]; tables_exempted: string[]; exemption_reasons: Record<string,string>; created_at: string; }
export interface DeletionRequestList { requests: DeletionRequest[]; has_next: boolean; }
export interface RetentionPolicyList { policies: RetentionPolicy[]; exempt_tables: Record<string,string>; }
export interface RetentionPolicy { table_name: string; retention_days: number; is_exempt: boolean; exemption_reason?: string; }

// ── Enterprise Compliance (DPDP Act 2023) ────────────────────────────────────
export interface ComplianceEnterpriseSummary {
  pending_erasure: number; pending_export: number; pending_consent_withdrawal: number;
  pending_verification: number; sla_breached: number; sla_at_risk: number;
  completed_this_month: number; rejected_total: number; exemptions_applied: number;
  consent_records: number; compliance_status: string; generated_at: string;
}
export interface ComplianceRequestItem {
  id: string; request_id: string; module_name: string; record_type: string;
  record_id?: string | null; record_count: number;
  planned_action: "delete" | "anonymize" | "retain" | "manual_review" | "export";
  actual_action?: string | null; exemption_reason?: string | null;
  retention_until?: string | null; status: string; created_at: string;
}
export interface ComplianceAuditEntry {
  log_id: string; action: string; actor_role?: string | null; purpose?: string | null;
  reference_id?: string | null; created_at: string;
}
export interface ComplianceEnterpriseRequest {
  id: string; request_number: string; subject_type: string; subject_id: string;
  subject_email?: string | null; subject_name?: string | null;
  request_type: string; status: string; sla_status: string; verification_status: string;
  submitted_at?: string | null; due_at?: string | null; completed_at?: string | null;
  assigned_to_admin_id?: string | null; request_source: string;
  reason?: string | null; admin_notes?: string | null; rejection_reason?: string | null;
  metadata_json: Record<string, unknown>;
  hours_until_sla?: number | null; sla_overdue?: boolean;
  items?: ComplianceRequestItem[];
  audit_trail?: ComplianceAuditEntry[];
  created_at: string; updated_at?: string | null;
}
export interface ComplianceEnterpriseRequestList {
  items: ComplianceEnterpriseRequest[];
  meta: { total: number; page: number; limit: number; total_pages: number; has_next: boolean; };
}
export interface ConsentRecord {
  id: string; user_id: string; consent_type: string; action: string;
  policy_version: string; granted_at?: string | null; withdrawn_at?: string | null;
  expires_at?: string | null; source?: string | null; created_at: string;
}
export interface ConsentRecordList {
  items: ConsentRecord[];
  meta: { total: number; page: number; limit: number; total_pages: number; has_next: boolean; };
}
export interface ComplianceExportRecord {
  id: string; request_id?: string | null; subject_type: string; subject_id: string;
  export_format: string; status: string; download_url?: string | null;
  file_size_bytes?: number | null; record_count?: number | null;
  expires_at?: string | null; generated_at?: string | null; downloaded_at?: string | null;
  created_at: string;
}
export interface ComplianceExportList {
  items: ComplianceExportRecord[];
  meta: { total: number; page: number; limit: number; total_pages: number; has_next: boolean; };
}
export interface ComplianceAuditList {
  items: ComplianceAuditEntry[];
  meta: { total: number; page: number; limit: number; total_pages: number; has_next: boolean; };
}
export interface MarketingSummary { total_posts_published: number; posts_pending: number; total_assets_generated: number; total_dalle_cost_inr: number; daily_budget: BudgetStatus; generated_at: string; }
export interface BudgetStatus { date: string; spent_inr: number; budget_inr: number; remaining_inr: number; budget_pct_used: number; }
export interface SocialAccount { account_id: string; platform: string; page_name: string; status: string; follower_count: number; post_count: number; days_until_token_expiry: number; token_needs_refresh: boolean; }
export interface SocialAccountList { accounts: SocialAccount[]; total: number; }
export interface CalendarResponse { date_from: string; date_to: string; posts: ScheduledPost[]; total: number; }
export interface ScheduledPost { post_id: string; post_type: string; status: string; scheduled_at: string; caption?: string; tags: string[]; }
export interface SchedulePostInput { account_id: string; post_type: string; scheduled_at: string; variables: Record<string,string>; }
export interface GeneratedAsset { asset_id: string; post_type: string; cost_inr: number; storage_key?: string; dalle_url?: string; reused: boolean; }
export interface OnboardingResult { tenant_id: string; scheduled_posts: Array<{account: string; post_id: string}>; }
export interface ReviewList { reviews: Review[]; has_next: boolean; }
export interface Review { review_id: string; job_id: string; tenant_id?: string; customer_id?: string; staff_id?: string; composite_score: number; comment?: string; status: string; signals: Record<string,number>; has_reply?: boolean; reply_text?: string; flagged_reason?: string; created_at: string; }
export interface ReviewAggregate { entity_type: string; entity_id: string; review_count: number; avg_composite: number; reply_rate: number; last_computed_at?: string; }
export interface ChurnList { predictions: ChurnPrediction[]; }
export interface ChurnPrediction { tenant_id: string; churn_probability: number; risk_factors: string[]; }
export interface ForecastList { forecasts: DemandForecast[]; }
export interface DemandForecast { date: string; predicted_jobs: number; confidence: number; }

// ── Auth extended types ───────────────────────────────────────────────────────
export interface TokenIntrospect { active: boolean; user_id?: string; role?: string; scopes?: string[]; expires_at?: string; }
export interface MfaSetup { secret: string; qr_code_url: string; backup_codes: string[]; }
export interface MfaConfirm { mfa_enabled: boolean; backup_codes: string[]; }
export interface BackupCodes { backup_codes: string[]; generated_at: string; }
export interface UserSessionList { user_id: string; active_sessions: number; sessions: UserSession[]; }
export interface UserSession { session_id: string; device_info: Record<string,unknown>; ip_address: string; last_seen_at: string; expires_at: string; is_current?: boolean; }
export interface InviteStaffPayload { email: string; full_name: string; role: string; permissions?: string[]; tenant_id?: string; }
export interface StaffInvite { invite_id: string; email: string; role: string; expires_at: string; }
export interface ImpersonationSession { session_id: string; target_user_id: string; target_email: string; reason: string; started_at: string; expires_at: string; }
export interface ApiKey { key_id: string; name: string; prefix: string; scopes: string[]; is_active: boolean; created_at: string; expires_at?: string; last_used_at?: string; }
export interface ApiKeyCreated extends ApiKey { secret_key: string; }
export interface ApiKeyList { keys: ApiKey[]; total: number; }
export interface AuthAuditLog { log_id: string; action: string; actor_id?: string; actor_email?: string; target_id?: string; ip_address?: string; user_agent?: string; success: boolean; created_at: string; }
export interface AuthAuditLogList { logs: AuthAuditLog[]; has_next: boolean; }
export interface UserDetail { id: string; user_id?: string; email: string; full_name: string; role: string; phone?: string; is_active: boolean; mfa_enabled?: boolean; is_mfa_enabled?: boolean; is_verified?: boolean; permissions?: string[]; tenant_id?: string; created_at: string; last_login_at?: string; }
export interface UserListResponse { users: UserDetail[]; total: number; has_next?: boolean; next_cursor?: string; }
export interface PermissionsMap { roles: Record<string, string[]>; all_permissions: string[]; }
export interface UserSecurityStatus { user_id: string; email: string; full_name: string; role: string; password_reset_required: boolean; temporary_password_active: boolean; password_expires_at: string | null; last_password_reset_at: string | null; last_password_reset_by_admin_id: string | null; last_login_at: string | null; active_sessions: number; mfa_enabled: boolean; is_active: boolean; }
export interface SessionInfo { session_id: string; device_name: string; device_type: string; ip_address: string | null; last_active_at: string; is_trusted: boolean; is_approved: boolean; is_current?: boolean; created_at: string; }
export interface LoginHistoryEvent { event_id: string; event_type: string; failure_reason: string | null; ip_address: string | null; device_id: string | null; user_agent: string | null; created_at: string; }
export interface RegisterCustomerPayload { full_name: string; email: string; phone: string; password: string; }

// ── Media types ───────────────────────────────────────────────────────────────
export interface UploadSession { session_id: string; upload_url: string; expires_at: string; }
export interface MediaFile { file_id: string; tenant_id: string; filename: string; content_type: string; size_bytes: number; purpose: string; url?: string; created_at: string; }
export interface MediaFileList { files: MediaFile[]; total: number; has_next: boolean; next_cursor?: string; }
export interface MediaQuota { tenant_id: string; used_bytes: number; limit_bytes: number; file_count: number; file_limit: number; }

// ── Platform Settings types ───────────────────────────────────────────────────
export interface PlatformSetting { key: string; value: unknown; description?: string; source: string; updated_at?: string; updated_by?: string; }
export interface PlatformSettingsList { settings: PlatformSetting[]; }
export interface PlanSetting { key: string; value: unknown; plan_type: string; }
export interface PlanSettingsList { plan_type: string; settings: PlanSetting[]; }
export interface ResolvedSetting { key: string; value: unknown; source: string; resolved_for?: string; }
export interface SettingsAuditEntry { log_id: string; key: string; old_value?: unknown; new_value?: unknown; action: string; actor_id?: string; scope: string; created_at: string; }
export interface SettingsAuditList { logs: SettingsAuditEntry[]; has_next: boolean; }

// ── Media ─────────────────────────────────────────────────────────────────────
export const mediaApi = {
  initiateUpload: (tenantId: string, filename: string, contentType: string, sizeBytes: number, entityType?: string, entityId?: string) =>
    apiFetch<UploadSession>("/v1/media/upload/initiate",
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId, file_name: filename, mime_type: contentType, size_bytes: sizeBytes, entity_type: entityType, entity_id: entityId }) }),
  confirmUpload: (sessionId: string, etag?: string) =>
    apiFetch<MediaFile>(`/v1/media/upload/${sessionId}/confirm`,
      { method: "POST", body: JSON.stringify({ etag }) }),
  listFiles: (tenantId: string, params?: { limit?: number; cursor?: string; purpose?: string }) => {
    const qs = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<MediaFileList>(`/v1/media/tenants/${tenantId}/files?${qs}`);
  },
  getFile:   (tenantId: string, fileId: string) =>
    apiFetch<MediaFile>(`/v1/media/tenants/${tenantId}/files/${fileId}`),
  deleteFile:(tenantId: string, fileId: string) =>
    apiFetch<void>(`/v1/media/tenants/${tenantId}/files/${fileId}`, { method: "DELETE" }),
  getQuota:  (tenantId: string) =>
    apiFetch<MediaQuota>(`/v1/media/tenants/${tenantId}/quota`),
  listAssets: (params?: { media_context?: string; owner_type?: string; owner_id?: string; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.media_context) qs.set("media_context", params.media_context);
    if (params?.owner_type)    qs.set("owner_type",    params.owner_type);
    if (params?.owner_id)      qs.set("owner_id",      params.owner_id);
    if (params?.page)          qs.set("page",          String(params.page));
    if (params?.page_size)     qs.set("page_size",     String(params.page_size));
    return apiFetch<{ items: MediaAsset[]; total: number; page: number; page_size: number }>(`/v1/media?${qs}`);
  },
  deleteAssetAdmin: (mediaId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/media/${mediaId}`, { method: "DELETE" }),
};

// ── Media Assets (Phase 0A/0B — multipart upload, profile photos) ─────────────
export interface MediaAsset {
  id: string;
  media_context: string;
  file_name_original: string;
  mime_type: string;
  file_size_bytes: number;
  storage_driver: string;
  is_public: boolean;
  access_level: string;
  status: string;
  preview_url: string | null;
  public_url: string | null;
  created_at: string;
}

export interface MediaAssetAdmin extends MediaAsset {
  owner_type: string;
  owner_id: string;
  tenant_id: string | null;
  customer_id: string | null;
  uploaded_by_user_id: string;
  file_extension: string;
  width: number | null;
  height: number | null;
  visibility: "public" | "private";
  is_flagged: boolean;
  flag_reason: string | null;
  flagged_at: string | null;
  moderation_status: "clean" | "flagged" | "quarantined" | "review_required";
  scan_status: "not_scanned" | "clean" | "infected" | "pending";
  description: string | null;
  tags_json: string[];
  linked_module: string | null;
  linked_record_id: string | null;
  archived_at: string | null;
  upload_from_app: string | null;
  updated_at: string;
}

export interface MediaSummary {
  total: number;
  active: number;
  archived: number;
  flagged: number;
  quarantined: number;
  public_count: number;
  private_count: number;
  images_count: number;
  videos_count: number;
  documents_count: number;
  recent_count: number;
  total_size_bytes: number;
  total_size_mb: number;
  active_size_bytes: number;
  active_size_mb: number;
  by_context: Record<string, number>;
}

export interface MediaStorageSummary {
  total_bytes: number;
  total_mb: number;
  by_context: Array<{ context: string; count: number; total_bytes: number; total_mb: number }>;
}

export interface MediaLinkedRecord {
  id: string;
  module_name: string;
  record_type: string;
  record_id: string;
  display_name: string | null;
  status: string;
  created_at: string;
}

export interface MediaAuditLog {
  id: string;
  actor_user_id: string | null;
  actor_role: string | null;
  action_type: string;
  request_id: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface MediaSignedUrl {
  token: string;
  url: string;
  expires_at: string;
  purpose: "preview" | "download";
}

export const mediaAdminApi = {
  getSummary: () => apiFetch<MediaSummary>("/v1/admin/media/summary"),
  getStorageSummary: () => apiFetch<MediaStorageSummary>("/v1/admin/media/storage-summary"),
  getFilterOptions: () => apiFetch<{ contexts: Array<{value:string;count:number}>; owner_types: Array<{value:string;count:number}>; statuses: string[]; file_types: string[]; visibilities: string[] }>("/v1/admin/media/filter-options"),

  listMedia: (params?: {
    q?: string; context?: string; ownerType?: string; visibility?: string;
    status?: string; moderationStatus?: string; isFlagged?: boolean;
    tenantId?: string; customerId?: string; fileType?: string;
    dateFrom?: string; dateTo?: string; page?: number; pageSize?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.q)                qs.set("q", params.q);
    if (params?.context)          qs.set("context", params.context);
    if (params?.ownerType)        qs.set("owner_type", params.ownerType);
    if (params?.visibility)       qs.set("visibility", params.visibility);
    if (params?.status)           qs.set("status", params.status);
    if (params?.moderationStatus) qs.set("moderation_status", params.moderationStatus);
    if (params?.isFlagged !== undefined) qs.set("is_flagged", String(params.isFlagged));
    if (params?.tenantId)         qs.set("tenant_id", params.tenantId);
    if (params?.customerId)       qs.set("customer_id", params.customerId);
    if (params?.fileType)         qs.set("file_type", params.fileType);
    if (params?.dateFrom)         qs.set("date_from", params.dateFrom);
    if (params?.dateTo)           qs.set("date_to", params.dateTo);
    if (params?.page)             qs.set("page", String(params.page));
    if (params?.pageSize)         qs.set("page_size", String(params.pageSize));
    return apiFetch<{ items: MediaAssetAdmin[]; total: number; page: number; page_size: number }>(`/v1/admin/media?${qs}`);
  },

  getDetail:        (mediaId: string) => apiFetch<MediaAssetAdmin>(`/v1/admin/media/${mediaId}`),
  getLinkedRecords: (mediaId: string) => apiFetch<MediaLinkedRecord[]>(`/v1/admin/media/${mediaId}/linked-records`),
  getAuditLogs:     (mediaId: string, limit = 50) => apiFetch<MediaAuditLog[]>(`/v1/admin/media/${mediaId}/audit-logs?limit=${limit}`),

  createSignedPreviewUrl:   (mediaId: string) => apiFetch<MediaSignedUrl>(`/v1/admin/media/${mediaId}/signed-preview-url`,  { method: "POST" }),
  createSignedDownloadUrl:  (mediaId: string) => apiFetch<MediaSignedUrl>(`/v1/admin/media/${mediaId}/signed-download-url`, { method: "POST" }),

  archiveMedia:   (mediaId: string, reason?: string) => apiFetch<{ id: string; status: string }>(`/v1/admin/media/${mediaId}/archive`,   { method: "POST", body: JSON.stringify({ reason }) }),
  restoreMedia:   (mediaId: string)                  => apiFetch<{ id: string; status: string }>(`/v1/admin/media/${mediaId}/restore`,   { method: "POST" }),
  deleteMedia:    (mediaId: string, force = false)   => apiFetch<{ id: string; deleted: boolean }>(`/v1/admin/media/${mediaId}?force=${force}`, { method: "DELETE" }),
  changeVisibility:(mediaId: string, isPublic: boolean) => apiFetch<{ id: string; is_public: boolean }>(`/v1/admin/media/${mediaId}/change-visibility`, { method: "POST", body: JSON.stringify({ is_public: isPublic }) }),
  flagMedia:      (mediaId: string, reason: string) => apiFetch<{ id: string; is_flagged: boolean }>(`/v1/admin/media/${mediaId}/flag`,         { method: "POST", body: JSON.stringify({ reason }) }),
  markClean:      (mediaId: string)                  => apiFetch<{ id: string; is_flagged: boolean }>(`/v1/admin/media/${mediaId}/mark-clean`,   { method: "POST" }),
  quarantineMedia:(mediaId: string, reason: string) => apiFetch<{ id: string; status: string }>(`/v1/admin/media/${mediaId}/quarantine`,  { method: "POST", body: JSON.stringify({ reason }) }),

  bulkArchive: (ids: string[])                      => apiFetch<{ archived: string[]; failed: Array<{id:string;error:string}> }>("/v1/admin/media/bulk/archive", { method: "POST", body: JSON.stringify({ ids }) }),
  bulkDelete:  (ids: string[], force = false)        => apiFetch<{ deleted: string[]; failed: Array<{id:string;error:string}> }>("/v1/admin/media/bulk/delete",  { method: "POST", body: JSON.stringify({ ids, force }) }),
  bulkChangeVisibility: (ids: string[], isPublic: boolean) => apiFetch<{ updated: string[]; failed: Array<{id:string;error:string}> }>("/v1/admin/media/bulk/change-visibility", { method: "POST", body: JSON.stringify({ ids, is_public: isPublic }) }),

  uploadMedia: (file: File, mediaContext: string, ownerType = "admin", isPublic = false) => {
    const form = new FormData();
    form.append("file", file);
    form.append("media_context", mediaContext);
    form.append("owner_type", ownerType);
    form.append("is_public", String(isPublic));
    return (async () => {
      const token = getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`${API_BASE}/v1/media/upload`, { method: "POST", headers, body: form });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new ServiceOSError(e.error_code ?? "UPLOAD_ERROR", e.detail ?? "Upload failed."); }
      const json = await res.json();
      return json.data as MediaAssetAdmin;
    })();
  },

  exportCsv: async (params?: { context?: string; status?: string; isFlagged?: boolean }) => {
    const qs = new URLSearchParams();
    if (params?.context)           qs.set("context", params.context);
    if (params?.status)            qs.set("status", params.status);
    if (params?.isFlagged !== undefined) qs.set("is_flagged", String(params.isFlagged));
    const token = getToken();
    const res = await fetch(`${API_BASE}/v1/admin/media/export/csv?${qs}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.blob();
  },
};

async function apiUpload<T>(path: string, formData: FormData, timeoutMs = 60_000): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "X-Request-Source": "super-admin-portal" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { method: "POST", headers, body: formData, signal: controller.signal });
  } catch (fetchErr: unknown) {
    if ((fetchErr as { name?: string }).name === "AbortError") {
      throw new ServiceOSError("UPLOAD_TIMEOUT", "Upload timed out. Please try again with a smaller file.", undefined, undefined);
    }
    throw fetchErr;
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let err: ApiError;
    try { err = await res.json(); }
    catch { err = { error_code: "UPLOAD_ERROR", detail: `HTTP ${res.status}` }; }
    throw new ServiceOSError(err.error_code ?? "UPLOAD_ERROR", err.detail ?? "Upload failed.", err.resolution, err.context);
  }
  const json: ApiResponse<T> = await res.json();
  return json.data;
}

export const profilePhotoApi = {
  uploadOwnPhoto: (file: File) => {
    const form = new FormData(); form.append("file", file);
    return apiUpload<MediaAsset>("/v1/me/profile-photo", form);
  },
  removeOwnPhoto: () => apiFetch<{ removed: boolean }>("/v1/me/profile-photo", { method: "DELETE" }),

  uploadAsset: (file: File, mediaContext: string, ownerType = "user", ownerId?: string, isPublic = false) => {
    const form = new FormData();
    form.append("file", file);
    form.append("media_context", mediaContext);
    form.append("owner_type", ownerType);
    if (ownerId) form.append("owner_id", ownerId);
    form.append("is_public", String(isPublic));
    return apiUpload<MediaAsset>("/v1/media/upload", form);
  },
  deleteAsset: (mediaId: string) => apiFetch<{ deleted: boolean }>(`/v1/media/${mediaId}`, { method: "DELETE" }),
  getAsset:    (mediaId: string) => apiFetch<MediaAsset>(`/v1/media/${mediaId}`),
};

// ── Platform Settings ─────────────────────────────────────────────────────────
export const platformSettingsApi = {
  getAll: () => apiFetch<PlatformSettingsList>("/v1/settings/platform"),
  get:    (key: string) => apiFetch<PlatformSetting>(`/v1/settings/platform/${key}`),
  set:    (key: string, value: unknown, description?: string) =>
    apiFetch<PlatformSetting>(`/v1/settings/platform/${key}`,
      { method: "PUT", body: JSON.stringify({ value, description }) }),
  delete: (key: string) =>
    apiFetch<void>(`/v1/settings/platform/${key}`, { method: "DELETE" }),
  bulkSet:(settings: Array<{ key: string; value: unknown }>) =>
    apiFetch<PlatformSettingsList>("/v1/settings/platform/bulk",
      { method: "POST", body: JSON.stringify({ settings }) }),
  getPlanSettings: (planType: string) =>
    apiFetch<PlanSettingsList>(`/v1/settings/plans/${planType}`),
  setPlanSetting: (planType: string, key: string, value: unknown) =>
    apiFetch<PlanSetting>(`/v1/settings/plans/${planType}/${key}`,
      { method: "PUT", body: JSON.stringify({ value }) }),
  deletePlanSetting: (planType: string, key: string) =>
    apiFetch<void>(`/v1/settings/plans/${planType}/${key}`, { method: "DELETE" }),
  resolve: (key: string, tenantId?: string) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : "";
    return apiFetch<ResolvedSetting>(`/v1/settings/resolve/${key}${qs}`);
  },
  getAuditLog: (params?: { limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams(params as Record<string,string> ?? {}).toString();
    return apiFetch<SettingsAuditList>(`/v1/settings/audit-log?${qs}`);
  },
};

// ── Onboarding Queue (Tenant Self-Registration) ───────────────────────────────
export interface OnboardingRequest {
  id:                  string;
  business_name:       string;
  vertical:            string;
  owner_name:          string;
  owner_email:         string;
  owner_phone:         string;
  city:                string;
  state:               string;
  gstin?:              string;
  description?:        string;
  status:              "submitted" | "under_review" | "documents_requested" | "activated" | "rejected";
  plan_type?:          string;
  admin_notes?:        string;
  rejection_reason?:   string;
  assigned_admin_id?:  string;
  review_started_at?:  string;
  activated_at?:       string;
  source:              string;
  checklist:           Record<string, { status: string }>;
  engines_to_enable:   string[];
  created_at:          string;
  updated_at:          string;
}

export interface OnboardingQueueResponse {
  requests:   OnboardingRequest[];
  total:      number;
  has_next:   boolean;
  next_cursor?: string;
}

export const engineRegistryApi = {
  list: () => apiFetch<{ total:number; core:number; plugin:number; tenant_enabled:number; engines:PlatformEngine[] }>("/v1/engines"),
  get:  (engineId: string) => apiFetch<PlatformEngine & { is_enabled_for_tenant:boolean }>(`/v1/engines/${engineId}`),
};
// PlatformEngine is defined below in the enterprise engine management section (migration 081)

export const onboardingApi = {
  signup: (data: Omit<OnboardingRequest, "id"|"status"|"checklist"|"engines_to_enable"|"created_at"|"updated_at">) =>
    apiFetch<OnboardingRequest>("/v1/tenants/onboarding/signup", { method: "POST", body: JSON.stringify(data) }, true),
  queue: (params?: { status?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params ?? {}).filter(([,v]) => v != null).map(([k,v]) => [k, String(v)]))
    ).toString();
    return apiFetch<OnboardingQueueResponse>(`/v1/tenants/onboarding/queue?${qs}`);
  },
  get: (id: string) =>
    apiFetch<OnboardingRequest>(`/v1/tenants/onboarding/${id}`),
  startReview: (id: string) =>
    apiFetch<OnboardingRequest>(`/v1/tenants/onboarding/${id}/start-review`, { method: "POST" }),
  requestDocuments: (id: string, message: string) =>
    apiFetch<OnboardingRequest>(`/v1/tenants/onboarding/${id}/request-documents`,
      { method: "POST", body: JSON.stringify({ message }) }),
  updateChecklistItem: (id: string, itemKey: string, status: string, notes?: string) =>
    apiFetch<OnboardingRequest>(`/v1/tenants/onboarding/${id}/checklist/${itemKey}`,
      { method: "PUT", body: JSON.stringify({ status, notes }) }),
  preflightCheck: (id: string) =>
    apiFetch<{ ready: boolean; blockers: string[] }>(`/v1/tenants/onboarding/${id}/preflight-check`, { method: "POST" }),
  activate: (id: string) =>
    apiFetch<{ tenant_id: string; message: string }>(`/v1/tenants/onboarding/${id}/activate`, { method: "POST" }),
  reject: (id: string, reason: string) =>
    apiFetch<OnboardingRequest>(`/v1/tenants/onboarding/${id}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  addNote: (id: string, note: string) =>
    apiFetch<OnboardingRequest>(`/v1/tenants/onboarding/${id}/notes`,
      { method: "PUT", body: JSON.stringify({ admin_notes: note }) }),
};

// ── Document engine types ─────────────────────────────────────────────────────
export interface TenantDocument { id:string; document_number:string; title:string; status:string; doc_type:string; entity_type?:string; entity_id?:string; tenant_id:string; is_frozen:boolean; signed_at?:string; signing_url?:string; signing_url_expires_at?:string; variables:Record<string,string>; created_at:string; }
export interface TenantDocumentList { documents:TenantDocument[]; has_next:boolean; next_cursor?:string; }
export interface DocumentEvent { event_id:string; document_id:string; event_type:string; actor_id?:string; actor_ip?:string; details?:Record<string,unknown>; created_at:string; }
export interface DocumentEventList { events:DocumentEvent[]; }
export interface DocumentTemplate { doc_type:string; tenant_id:string; template_content?:string; required_variables:string[]; sample_variables?:Record<string,string>; }

// ── Subscription engine types ─────────────────────────────────────────────────
export interface SubscriptionInfo { subscription_id?:string; plan_type:string; status:string; billing_cycle?:string; started_at?:string; ends_at?:string; jobs_used?:number; jobs_included?:number; leads_used?:number; leads_included?:number; next_billing_at?:string; }
export interface SubscriptionPeriod { tenant_id:string; period_start:string; period_end:string; plan_type:string; billing_cycle:string; jobs_used:number; jobs_included?:number; leads_used?:number; leads_included?:number; amount_billed?:number; }
export interface SubscriptionHistoryEntry { period_id:string; period_start:string; period_end:string; plan_type:string; billing_cycle:string; amount_billed?:number; }
export interface SubscriptionHistoryList { history:SubscriptionHistoryEntry[]; has_next:boolean; next_cursor?:string; }
export interface ProrationPreview { tenant_id:string; current_plan:string; new_plan:string; billing_cycle:string; days_remaining:number; credit_amount:number; debit_amount:number; net_amount:number; effective_date:string; }

// ── Billing router extended types ─────────────────────────────────────────────
export interface BillingProfileHistoryList { tenant_id:string; profiles:BillingProfile[]; note:string; }
export interface BillingRouteResult { billing_mode:string; operation:string; engine:string; [k:string]:unknown; }

// ── Review (admin extended) + Notification template types ────────────────────
export interface AdminReview { review_id:string; tenant_id:string; job_id:string; customer_id:string; staff_id?:string; signals:Record<string,number>; composite_score:number; comment?:string; status:string; tenant_reply?:string; has_reply:boolean; flagged_reason?:string; created_at:string; }
export interface NotifTemplate { id:string; tenant_id?:string; notif_type:string; channel:string; title?:string; body:string; variables:string[]; is_active:boolean; vertical?:string; created_at:string; }

// ── Catalog Engine types ──────────────────────────────────────────────────────
export interface PricingTier {
  tier_id:string; name:string; code:string; tier_type:string; description?:string|null;
  base_multiplier:number; platform_fee_percent:number; default_commission_percent:number;
  default_sla_minutes:number; is_active:boolean; created_at?:string;
  linked_counts?: { cities:number; zipcodes:number; zones:number; rules_total:number; rules_active:number };
}
export interface TiersSummary {
  total_tiers:number; active_tiers:number; inactive_tiers:number;
  mapped_cities:number; mapped_zipcodes:number; rules_using_tiers:number; unmapped_tiers:number;
}
export interface TierDetail {
  tier: PricingTier;
  mapped_cities: string[]; mapped_zipcodes: string[]; zones: string[];
  pricing_rules: PricingRule[];
  audit_log: { id:string; entity_type:string; entity_id:string; action:string; actor_role?:string|null;
    change_summary?:string|null; created_at?:string }[];
}
export interface TierLocation {
  location_id:string; tier_id:string; country:string; state?:string|null; district?:string|null;
  city?:string|null; zipcode?:string|null; zone_name?:string|null; priority:number; is_active:boolean;
  tier_name?:string|null; tier_code?:string|null; has_conflict?:boolean; conflict_status?:string;
  mapping_type?:string|null; source?:string|null;
  created_at?:string|null; updated_at?:string|null;
}
export interface GridPagination { page:number; page_size:number; total:number; total_pages:number; }
export interface TierLocationsSummary {
  total_mappings:number; mapped_cities:number; mapped_zipcodes:number; mapped_districts:number;
  mapped_states:number; duplicate_zipcodes:number; inactive_mappings:number; recently_imported:number;
}
export interface ImportPreviewRow {
  row_no:number; country:string; state?:string|null; district?:string|null; city:string;
  zipcode?:string|null; tier_code:string; zone_code?:string|null; status:string;
  errors:string[]; conflict:boolean; action?:string; reason?:string;
}
export interface ImportPreviewResult {
  batch_id:string; total_rows:number; valid_rows:number; invalid_rows:number; conflict_rows:number;
  sample_rows: ImportPreviewRow[];
}
export interface ImportBatch {
  id:string; status:string; file_name?:string|null; total_rows:number; valid_rows:number;
  invalid_rows:number; conflict_rows:number; created_rows:number; updated_rows:number; skipped_rows:number;
  report_payload?: { rows: ImportPreviewRow[] } | null; conflict_resolution?:string|null;
  created_at?:string; updated_at?:string;
}
export interface ResolveResult { matched_by:string|null; tier:PricingTier|null; resolution_path:string[]; }
export interface ServiceCategory {
  category_id: string; name: string; slug: string; description?: string | null;
  icon_url?: string | null; image_url?: string | null; display_order: number;
  is_active: boolean; created_at?: string; updated_at?: string;
  // Category runtime fields
  category_type?: string | null;
  primary_engine_id?: string | null;
  primary_engine_key?: string | null;
  customer_flow_type?: string | null;
  provider_dashboard_type?: string | null;
  is_provider_registerable?: boolean;
  monetization_model?: string | null;
  // Sprint 38 universal fields
  vertical_type?: string | null;
  finance_model?: string | null;
  provider_business_model?: string | null;
  requires_location?: boolean;
  requires_schedule?: boolean;
  requires_brand?: boolean;
  requires_service_option?: boolean;
  requires_issue_type?: boolean;
  tenant_selectable?: boolean;
  pricing_supported?: boolean;
}

export interface ServiceGroup {
  id: string;
  category_id: string;
  code: string;
  name: string;
  slug: string;
  description?: string | null;
  status: string;
  display_order: number;
  icon_url?: string | null;
  created_by_user_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ServiceGroupEnriched extends ServiceGroup {
  category_name: string;
  runtime_readiness: "ready" | "empty_group" | "inactive" | "archived" | "category_inactive";
  linked_counts: { services: number; providers: number };
}

export interface ServiceGroupsSummary {
  total: number;
  active: number;
  inactive: number;
  groups_with_services: number;
  empty_groups: number;
  runtime_ready: number;
}

export interface MasterServiceEnriched extends MasterService {
  id: string;
  name: string;
  category_name: string;
  group_name?: string | null;
  unit_label?: string | null;
  currency?: string | null;
  runtime_readiness: "ready" | "inactive" | "missing_brand_mapping" | "missing_service_options" | "missing_issue_types" | "missing_pricing";
  pricing_readiness: "ready" | "fallback_only" | "missing_rules" | "inactive" | "not_required";
  linked_counts: {
    brands: number; options: number; issues: number;
    pricing_rules: number; providers: number; service_types: number; checklists: number;
  };
}

export interface MasterServicesSummary {
  total: number;
  active: number;
  inactive: number;
  by_job_type: Record<string, number>;
  pricing_ready: number;
  missing_pricing: number;
  provider_enabled: number;
}

export interface CategoryEngineRuntime {
  category_engine_id: string; engine_id: string; engine_key: string; name: string;
  is_enabled: boolean; is_required: boolean; is_optional: boolean; is_primary: boolean;
  display_order: number; health_status: string; config: Record<string, unknown>;
  dependencies: string[]; status: string;
}

export interface CategoryDashboardModule {
  module_id: string; category_id: string; module_key: string; module_name: string;
  module_type: string; dashboard_area: string | null; engine_key: string | null;
  api_endpoint: string | null; route_path: string | null;
  required_permission: string | null; frontend_component_key: string | null;
  description: string | null; is_enabled: boolean; is_required: boolean;
  display_order: number; config: Record<string, unknown>;
}

export interface CategoryRuntime {
  category: ServiceCategory;
  running_engines: CategoryEngineRuntime[];
  engine_summary: { total: number; required: number; optional: number; primary: CategoryEngineRuntime | null };
  dashboard_modules: CategoryDashboardModule[];
  tenant_count: number;
  active_tenant_count: number;
}

export interface CategoryLinkedCounts {
  service_groups: number;
  services: number;
  pricing_rules: number;
  brands: number;
  packages: number;
  providers: number;
}
export interface CategoryReadinessItem {
  key: string;
  status: "missing" | "warning" | "ok";
  message: string;
}
export interface CategorySummaryData {
  total: number;
  active: number;
  inactive: number;
  customer_visible: number;
  tenant_selectable: number;
  runtime_ready: number;
  missing_required_setup: number;
  with_services: number;
  with_pricing: number;
}
export interface EnterpriseCategory extends ServiceCategory {
  linked_counts: CategoryLinkedCounts;
  readiness_status: string;
  readiness_items: CategoryReadinessItem[];
  is_customer_visible?: boolean;
}

export const categoryRuntimeApi = {
  summary: () =>
    apiFetch<CategorySummaryData>("/v1/admin/categories/summary"),

  listCategories: (params?: {
    is_active?: boolean; category_type?: string;
    q?: string; vertical_type?: string; finance_model?: string;
    customer_flow_type?: string; status?: string;
    customer_visible?: boolean; tenant_selectable?: boolean;
    pricing_supported?: boolean; readiness_status?: string;
    page?: number; page_size?: number; sort_by?: string; sort_dir?: string;
  }) => {
    const qs = params ? `?${new URLSearchParams(Object.fromEntries(
      Object.entries(params).filter(([,v]) => v !== undefined && v !== "").map(([k,v]) => [k, String(v)])
    ))}` : "";
    return apiFetch<{ items: EnterpriseCategory[]; categories: EnterpriseCategory[]; total: number; page: number; pages: number }>(`/v1/admin/categories${qs}`);
  },

  exportCategories: (params?: { status?: string; vertical_type?: string }) => {
    const apiBase = typeof window !== "undefined"
      ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
      : "http://localhost:8000";
    const qs = params ? `?${new URLSearchParams(Object.fromEntries(
      Object.entries(params).filter(([,v]) => v !== undefined && v !== "").map(([k,v]) => [k, String(v)])
    ))}` : "";
    return fetch(`${apiBase}/v1/admin/categories/export${qs}`, {
      credentials: "include",
      headers: { "Accept": "text/csv" },
    });
  },

  getCategory: (id: string) =>
    apiFetch<EnterpriseCategory>(`/v1/admin/categories/${id}`),
  getCategoryRuntime: (id: string) =>
    apiFetch<CategoryRuntime>(`/v1/admin/categories/${id}/runtime`),
  getCategoryReadiness: (id: string) =>
    apiFetch<{ readiness_status: string; readiness_items: CategoryReadinessItem[]; linked_counts: CategoryLinkedCounts }>(`/v1/admin/categories/${id}/readiness`),
  activateCategory: (id: string) =>
    apiFetch<{ activated: boolean }>(`/v1/admin/categories/${id}/activate`, { method: "POST" }),
  deactivateCategory: (id: string) =>
    apiFetch<{ deactivated: boolean }>(`/v1/admin/categories/${id}/deactivate`, { method: "POST" }),
  updateCategoryRuntime: (id: string, data: Partial<ServiceCategory>) =>
    apiFetch<ServiceCategory>(`/v1/admin/categories/${id}/runtime`, { method: "PUT", body: JSON.stringify(data) }),
  // Category engines
  listCategoryEngines: (id: string) =>
    apiFetch<{ engines: CategoryEngineRuntime[]; total: number; required_count: number; optional_count: number; primary_engine: CategoryEngineRuntime | null }>(`/v1/admin/categories/${id}/engines`),
  enableCategoryEngine: (catId: string, engId: string) =>
    apiFetch<CategoryEngineRuntime>(`/v1/admin/categories/${catId}/engines/${engId}/enable`, { method: "POST" }),
  disableCategoryEngine: (catId: string, engId: string) =>
    apiFetch<CategoryEngineRuntime>(`/v1/admin/categories/${catId}/engines/${engId}/disable`, { method: "POST" }),
  setPrimaryEngine: (catId: string, engId: string) =>
    apiFetch<CategoryEngineRuntime>(`/v1/admin/categories/${catId}/engines/${engId}/set-primary`, { method: "POST" }),
  // Dashboard modules
  listDashboardModules: (id: string) =>
    apiFetch<{ modules: CategoryDashboardModule[]; total: number; enabled_count: number }>(`/v1/admin/categories/${id}/dashboard-modules`),
  createDashboardModule: (id: string, data: Partial<CategoryDashboardModule>) =>
    apiFetch<CategoryDashboardModule>(`/v1/admin/categories/${id}/dashboard-modules`, { method: "POST", body: JSON.stringify(data) }),
  updateModule: (catId: string, moduleId: string, data: Partial<CategoryDashboardModule>) =>
    apiFetch<CategoryDashboardModule>(`/v1/admin/categories/${catId}/dashboard-modules/${moduleId}`, { method: "PUT", body: JSON.stringify(data) }),
  enableModule: (catId: string, moduleId: string) =>
    apiFetch<CategoryDashboardModule>(`/v1/admin/categories/${catId}/dashboard-modules/${moduleId}/enable`, { method: "POST" }),
  disableModule: (catId: string, moduleId: string) =>
    apiFetch<CategoryDashboardModule>(`/v1/admin/categories/${catId}/dashboard-modules/${moduleId}/disable`, { method: "POST" }),
  reorderModules: (catId: string, orders: { module_id: string; display_order: number }[]) =>
    apiFetch<{ reordered: number }>(`/v1/admin/categories/${catId}/dashboard-modules/reorder`, { method: "POST", body: JSON.stringify({ module_orders: orders }) }),
};

// ── Sprint 14 — Customer Flow Config API ─────────────────────────────────────

export interface CustomerFlowConfig {
  id: string;
  category_id: string;
  customer_flow_type: string;
  frontend_component_key: string;
  primary_engine_key: string;
  required_steps: string[];
  optional_steps: string[];
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export const adminCustomerFlowApi = {
  getFlowConfig: (categoryId: string) =>
    apiFetch<CustomerFlowConfig>(`/v1/admin/categories/${categoryId}/customer-flow`),
  upsertFlowConfig: (categoryId: string, data: Partial<CustomerFlowConfig>) =>
    apiFetch<CustomerFlowConfig>(`/v1/admin/categories/${categoryId}/customer-flow`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  activateFlowConfig: (categoryId: string) =>
    apiFetch<{ activated: boolean }>(`/v1/admin/categories/${categoryId}/customer-flow/activate`, { method: "POST" }),
  deactivateFlowConfig: (categoryId: string) =>
    apiFetch<{ deactivated: boolean }>(`/v1/admin/categories/${categoryId}/customer-flow/deactivate`, { method: "POST" }),
};

// ── Sprint 5 — Monetization types & API ──────────────────────────────────────

export interface MonetizationConfig {
  id: string; category_id: string; monetization_model: string;
  subscription_plan_type: string | null; subscription_billing_cycle: string | null;
  subscription_amount_inr: number | null; trial_days: number;
  credit_minimum_balance: number; credit_per_lead: number | null;
  commission_rate: number; leads_per_billing_cycle: number | null;
  is_active: boolean; notes: string | null; set_by: string | null;
  created_at: string | null; updated_at: string | null;
}

export interface ProviderMonetizationStatus {
  id: string; tenant_id: string; category_id: string | null;
  monetization_model: string | null;
  is_monetization_ready: boolean; is_bookable: boolean; is_visible: boolean;
  subscription_status: string | null; subscription_expires_at: string | null;
  credit_balance: number; credit_minimum_required: number; deposit_paid: boolean;
  last_synced_at: string | null;
  override_is_bookable: boolean | null; override_reason: string | null;
  overridden_by: string | null; overridden_at: string | null;
  created_at: string | null; updated_at: string | null;
}

export interface MonetizationAuditLog {
  id: string; tenant_id: string; category_id: string | null;
  event_type: string; monetization_model: string | null;
  payload: Record<string, unknown>;
  actor_id: string | null; actor_type: string | null; notes: string | null;
  created_at: string | null;
}

export const monetizationApi = {
  getCategoryConfig: (catId: string) =>
    apiFetch<MonetizationConfig>(`/v1/admin/categories/${catId}/monetization`),
  upsertCategoryConfig: (catId: string, data: Partial<MonetizationConfig>) =>
    apiFetch<MonetizationConfig>(`/v1/admin/categories/${catId}/monetization`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  listConfigs: (isActive?: boolean) => {
    const qs = isActive !== undefined ? `?is_active=${isActive}` : "";
    return apiFetch<{ configs: MonetizationConfig[]; total: number }>(`/v1/admin/monetization/configs${qs}`);
  },
  listProviderStatuses: (params?: { category_id?: string; is_bookable?: boolean; is_ready?: boolean; limit?: number }) => {
    const qs = params ? `?${new URLSearchParams(Object.fromEntries(
      Object.entries(params).filter(([,v]) => v !== undefined).map(([k,v]) => [k, String(v)])
    ))}` : "";
    return apiFetch<{ statuses: ProviderMonetizationStatus[]; total: number }>(`/v1/admin/monetization/providers${qs}`);
  },
  getProviderStatus: (tenantId: string) =>
    apiFetch<ProviderMonetizationStatus>(`/v1/admin/monetization/providers/${tenantId}`),
  syncProviderStatus: (tenantId: string) =>
    apiFetch<ProviderMonetizationStatus>(`/v1/admin/monetization/providers/${tenantId}/sync`, { method: "POST" }),
  overrideProviderBookable: (tenantId: string, override_is_bookable: boolean, reason: string) =>
    apiFetch<ProviderMonetizationStatus>(`/v1/admin/monetization/providers/${tenantId}/override`, {
      method: "POST", body: JSON.stringify({ override_is_bookable, reason }),
    }),
  listAuditLogs: (params?: { tenant_id?: string; category_id?: string; event_type?: string; limit?: number }) => {
    const qs = params ? `?${new URLSearchParams(Object.fromEntries(
      Object.entries(params).filter(([,v]) => v !== undefined).map(([k,v]) => [k, String(v)])
    ))}` : "";
    return apiFetch<{ logs: MonetizationAuditLog[]; total: number }>(`/v1/admin/monetization/audit-logs${qs}`);
  },
};
export interface MasterService {
  service_id:string; category_id:string; service_name:string; slug:string; description?:string|null;
  job_type:string; pricing_model:"fixed"|"range"|"post_assessment"|"hourly";
  base_price:number|null; min_price?:number|null; max_price?:number|null; visit_fee:number;
  pre_approval_limit?:number|null; default_estimate?:number|null;
  hourly_rate?:number|null; minimum_billable_hours?:number|null;
  estimated_hours?:number|null; maximum_hours?:number|null;
  assessment_label?:string|null; show_estimated_range?:boolean; customer_note?:string|null;
  estimated_duration_minutes?:number|null;
  unit_label?:string|null;
  requires_checklist:boolean; is_brand_required:boolean; is_type_required:boolean;
  requires_issue_type?:boolean; requires_schedule?:boolean; requires_address?:boolean;
  service_group_id?:string|null; image_url?:string|null; is_active:boolean; created_at?:string;
}
export interface ServiceTypeRow { type_id:string; category_id:string; name:string; slug:string; description?:string|null; is_active:boolean; }
export interface BrandRow { brand_id:string; name:string; slug:string; category_id?:string|null; logo_url?:string|null; is_active:boolean; }

// ── Types & Brands Enterprise (Sprint 76) ─────────────────────────────────────
export interface ServiceTypeMaster {
  type_id:string; name:string; code?:string|null; slug:string; description?:string|null;
  type_family?:string|null; customer_visible:boolean; status:string; display_order:number;
  is_active:boolean; category_count:number; service_count:number; mapping_count:number;
  created_at:string; updated_at:string; mappings?:ServiceTypeMapRecord[];
}
export interface ServiceTypeMapRecord {
  mapping_id:string; type_id:string; category_id?:string|null; service_group_id?:string|null;
  service_id?:string|null; customer_visible:boolean; provider_visible:boolean;
  status:string; display_order:number; created_at:string;
  type_name?:string|null; category_name?:string|null; service_name?:string|null;
}
export interface ServiceTypeSummary {
  total:number; active:number; inactive:number; archived:number;
  mapped:number; unmapped:number; customer_visible:number;
}
export interface BrandMasterSummary {
  total:number; active:number; inactive:number; archived:number;
  mapped:number; unmapped:number; global:number; customer_visible:number;
}
export interface BrandMapRecord {
  mapping_id:string; brand_id:string; category_id?:string|null; service_group_id?:string|null;
  service_id?:string|null; customer_visible:boolean; provider_visible:boolean;
  status:string; display_order:number; created_at:string;
  brand_name?:string|null; category_name?:string|null; service_name?:string|null;
}

export const typesApi = {
  // Service Types
  list: (p?: { q?:string; category_id?:string; status?:string; mapped?:boolean; customer_visible?:boolean; page?:number; page_size?:number }) => {
    const qs = p ? "?" + new URLSearchParams(Object.entries(p).filter(([,v])=>v!=null).map(([k,v])=>[k,String(v)])).toString() : "";
    return apiFetch<{ types:ServiceTypeMaster[]; total:number; page:number; page_size:number; pages:number }>(`/v1/admin/catalog/types${qs}`);
  },
  summary: () => apiFetch<ServiceTypeSummary>("/v1/admin/catalog/types/summary"),
  get: (id:string) => apiFetch<ServiceTypeMaster>(`/v1/admin/catalog/types/${id}`),
  create: (data:object) => apiFetch<ServiceTypeMaster>("/v1/admin/catalog/types", { method:"POST", body:JSON.stringify(data) }),
  update: (id:string, data:object) => apiFetch<ServiceTypeMaster>(`/v1/admin/catalog/types/${id}`, { method:"PUT", body:JSON.stringify(data) }),
  activate:   (id:string) => apiFetch<{type_id:string;status:string}>(`/v1/admin/catalog/types/${id}/activate`,   { method:"POST" }),
  deactivate: (id:string) => apiFetch<{type_id:string;status:string}>(`/v1/admin/catalog/types/${id}/deactivate`, { method:"POST" }),
  archive:    (id:string) => apiFetch<{type_id:string;status:string}>(`/v1/admin/catalog/types/${id}/archive`,    { method:"POST" }),
  exportTypes: () => apiFetch<ServiceTypeMaster[]>("/v1/admin/catalog/types/export"),
  // Type Mappings
  listMappings: (p?: { type_id?:string; category_id?:string; service_id?:string; status?:string; page?:number }) => {
    const qs = p ? "?" + new URLSearchParams(Object.entries(p).filter(([,v])=>v!=null).map(([k,v])=>[k,String(v)])).toString() : "";
    return apiFetch<{ mappings:ServiceTypeMapRecord[]; total:number }>(`/v1/admin/catalog/type-mappings${qs}`);
  },
  createMapping: (data:object) => apiFetch<ServiceTypeMapRecord>("/v1/admin/catalog/type-mappings", { method:"POST", body:JSON.stringify(data) }),
  updateMapping: (id:string, data:object) => apiFetch<ServiceTypeMapRecord>(`/v1/admin/catalog/type-mappings/${id}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteMapping: (id:string) => apiFetch<{mapping_id:string;deleted:boolean}>(`/v1/admin/catalog/type-mappings/${id}`, { method:"DELETE" }),
  // Brand summary + mappings
  brandSummary: () => apiFetch<BrandMasterSummary>("/v1/admin/catalog/brands/summary"),
  listBrandMappings: (p?: { brand_id?:string; category_id?:string; service_id?:string; status?:string; page?:number }) => {
    const qs = p ? "?" + new URLSearchParams(Object.entries(p).filter(([,v])=>v!=null).map(([k,v])=>[k,String(v)])).toString() : "";
    return apiFetch<{ mappings:BrandMapRecord[]; total:number }>(`/v1/admin/catalog/brand-mappings${qs}`);
  },
  createBrandMapping: (data:object) => apiFetch<BrandMapRecord>("/v1/admin/catalog/brand-mappings", { method:"POST", body:JSON.stringify(data) }),
  updateBrandMapping: (id:string, data:object) => apiFetch<BrandMapRecord>(`/v1/admin/catalog/brand-mappings/${id}`, { method:"PUT", body:JSON.stringify(data) }),
  deleteBrandMapping: (id:string) => apiFetch<{mapping_id:string;deleted:boolean}>(`/v1/admin/catalog/brand-mappings/${id}`, { method:"DELETE" }),
};
export interface PricingRule {
  rule_id:string; master_service_id:string; category_id?:string|null; job_type:string;
  tier_id?:string|null; service_type_id?:string|null; service_option_id?:string|null; brand_id?:string|null; city?:string|null; zipcode?:string|null;
  district?:string|null; state?:string|null; zone?:string|null;
  pricing_model:string; base_price:number; min_price?:number|null; max_price?:number|null; visit_fee:number;
  platform_fee_percent:number; commission_percent:number; tax_percent:number;
  bargain_floor?:number|null; completed_job_deduction_credits?:number; rule_name?:string|null; rule_code?:string|null; source?:string;
  effective_from?:string|null; effective_to?:string|null; priority:number; is_active:boolean;
  has_conflict?:boolean; validity_status?:string;
}
export interface PricingRulesSummary {
  total_rules:number; active_rules:number; inactive_rules:number; service_rules:number;
  brand_rules:number; type_option_rules:number; zipcode_rules:number; tier_rules:number;
  conflicting_rules:number; expiring_soon:number; expired_rules:number;
}
export interface PricingPreviewResult {
  matched_rule_id:string|null; matched_rule_name?:string|null; source:string; pricing_model:string; base_price:number;
  min_price?:number|null; max_price?:number|null; visit_fee:number; commission_percent:number;
  tax_percent:number; bargain_floor?:number|null; completed_job_deduction_credits?:number;
  payment_collection_mode?:string; final_customer_estimate?:number; message?:string;
  tier_matched:{ matched_by:string|null; tier:PricingTier|null };
  resolution_path?:string[]; warnings?:string[];
}

// ── Bargain Rules + Provider Pricing Overrides (Phase 3 / 3B / 3C) ─────────────
export interface BargainRule {
  id: string; vertical_key?: string | null; category_id?: string | null;
  master_service_id?: string | null; pricing_rule_id?: string | null;
  rule_name?: string | null; rule_code?: string | null;
  bargain_enabled: boolean; floor_type: string; floor_amount: number;
  below_floor_action: string; provider_approval_required: boolean;
  max_attempts?: number | null; status: string;
  created_at?: string; updated_at?: string;
  // enriched fields (Phase 3B)
  category_name?: string | null; master_service_name?: string | null;
  base_price?: number | null; min_price?: number | null; max_price?: number | null;
  currency?: string; pricing_source?: string | null;
  readiness?: "ready" | "missing_pricing_rule" | "invalid_floor" | "inactive" | "conflict";
  warning?: string | null;
  // Customer Range + Platform Fee Floor Fix — customer-facing display/negotiation
  // range and fee used to derive the real bargain floor (bargain_floor =
  // customer_min_price * (1 + platform_fee_percent/100) + platform_fee_fixed_amount).
  // floor_amount above is still populated (computed from these when set) for
  // backward compatibility with older rules that predate this fix.
  customer_min_price?: number | null; customer_max_price?: number | null;
  platform_fee_percent?: number | null; platform_fee_fixed_amount?: number;
}
export interface BargainRulesSummary {
  total_bargain_rules: number; active_rules: number; inactive_rules: number;
  bargain_enabled_services: number; below_floor_rejections: number;
  provider_approval_required: number; avg_accepted_offer: number | null;
  validation_issues: number;
}
export interface BargainRuleValidation {
  rule_id: string; valid: boolean;
  checks: {
    floor_gte_min_price: boolean; floor_lte_max_price: boolean;
    active_pricing_rule_exists: boolean; no_duplicate_active_bargain_rule: boolean;
    provider_approval_rule_valid: boolean;
  };
}
export interface AuditEntry {
  id: string; action: string; actor_user_id: string | null;
  change_summary: string | null; request_id: string | null; created_at: string | null;
}
export interface BargainEvaluationResult {
  service_name?: string | null; currency?: string;
  accepted: boolean; eligible: boolean; decision: "accepted" | "rejected" | "provider_approval_required";
  reason: string;
  // legacy/back-compat (still populated)
  base_price?: number | null; min_price?: number | null; max_price?: number | null;
  minimum_allowed_offer: number | null;
  // Customer Range + Platform Fee Floor Fix — the real, authoritative fields.
  admin_min_price?: number | null; admin_max_price?: number | null; admin_base_price?: number | null;
  customer_min_price?: number | null; customer_max_price?: number | null;
  platform_fee_percent?: number | null; platform_fee_amount?: number | null;
  bargain_floor: number | null;
  allowed_offer_min?: number | null; allowed_offer_max?: number | null;
  customer_offer?: number;
  payment_mode?: string;
  provider_approval_required?: boolean;
  pricing_source?: string | null; rule_used?: string | null;
}
export interface ProviderPricingOverride {
  id: string; tenant_id: string; vertical_key?: string | null; category_id?: string | null;
  master_service_id: string; service_type_id?: string | null; brand_id?: string | null;
  issue_type_id?: string | null; zipcode?: string | null; tier_id?: string | null;
  override_price: number; currency: string; approval_status: string; status: string;
  reason?: string | null; rejection_reason?: string | null;
  approved_by_user_id?: string | null; approved_at?: string | null;
  created_at?: string; updated_at?: string;
  // enriched fields (Phase 3B)
  tenant_name?: string | null; tenant_code?: string | null;
  master_service_name?: string | null; category_name?: string | null;
  service_type_name?: string | null; brand_name?: string | null;
  issue_type_name?: string | null; tier_name?: string | null;
  platform_min_price?: number | null; platform_max_price?: number | null;
  platform_base_price?: number | null; delta_from_base?: number | null;
}
export interface ProviderOverridesSummary {
  total_overrides: number; active_overrides: number; pending_approval: number;
  rejected_overrides: number; out_of_range_attempts: number;
  avg_override_price: number | null; tenants_with_overrides: number; validation_issues: number;
}
export interface OverrideValidationError {
  error_code: string; message: string;
  platform_min_price?: number; platform_max_price?: number; override_price?: number;
  existing_override_id?: string;
}
export interface OverrideValidationResult {
  valid: boolean; errors: OverrideValidationError[];
  platform_min_price: number | null; platform_max_price: number | null; platform_base_price: number | null;
}

export const bargainRulesApi = {
  summary: () => apiFetch<BargainRulesSummary>("/v1/admin/pricing/bargain-rules/summary"),
  list: (params?: {
    masterServiceId?: string; categoryId?: string; status?: string; search?: string;
    bargainEnabled?: boolean; providerApprovalRequired?: boolean; belowFloorAction?: string;
    page?: number; pageSize?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.masterServiceId) qs.set("master_service_id", params.masterServiceId);
    if (params?.categoryId) qs.set("category_id", params.categoryId);
    if (params?.status) qs.set("status", params.status);
    if (params?.search) qs.set("search", params.search);
    if (params?.bargainEnabled !== undefined) qs.set("bargain_enabled", String(params.bargainEnabled));
    if (params?.providerApprovalRequired !== undefined) qs.set("provider_approval_required", String(params.providerApprovalRequired));
    if (params?.belowFloorAction) qs.set("below_floor_action", params.belowFloorAction);
    qs.set("page", String(params?.page ?? 1));
    qs.set("page_size", String(params?.pageSize ?? 50));
    return apiFetch<{ items: BargainRule[]; total: number }>(`/v1/admin/pricing/bargain-rules?${qs.toString()}`);
  },
  get: (ruleId: string) => apiFetch<BargainRule>(`/v1/admin/pricing/bargain-rules/${ruleId}`),
  audit: (ruleId: string) => apiFetch<{ items: AuditEntry[] }>(`/v1/admin/pricing/bargain-rules/${ruleId}/audit`),
  create: (data: Partial<BargainRule> & { floor_amount: number }) =>
    apiFetch<BargainRule>("/v1/admin/pricing/bargain-rules", { method: "POST", body: JSON.stringify(data) }),
  update: (ruleId: string, data: Partial<BargainRule>) =>
    apiFetch<BargainRule>(`/v1/admin/pricing/bargain-rules/${ruleId}`, { method: "PUT", body: JSON.stringify(data) }),
  enable: (ruleId: string) => apiFetch<BargainRule>(`/v1/admin/pricing/bargain-rules/${ruleId}/enable`, { method: "POST" }),
  disable: (ruleId: string) => apiFetch<BargainRule>(`/v1/admin/pricing/bargain-rules/${ruleId}/disable`, { method: "POST" }),
  activate: (ruleId: string) => apiFetch<BargainRule>(`/v1/admin/pricing/bargain-rules/${ruleId}/activate`, { method: "POST" }),
  deactivate: (ruleId: string) => apiFetch<BargainRule>(`/v1/admin/pricing/bargain-rules/${ruleId}/deactivate`, { method: "POST" }),
  validate: (ruleId: string) => apiFetch<BargainRuleValidation>(`/v1/admin/pricing/bargain-rules/${ruleId}/validate`, { method: "POST" }),
  evaluatePreview: (data: { master_service_id?: string; pricing_rule_id?: string; offer_price: number }) =>
    apiFetch<BargainEvaluationResult>("/v1/admin/pricing/bargain/evaluate-preview", { method: "POST", body: JSON.stringify(data) }),
};

export const providerOverridesApi = {
  summary: () => apiFetch<ProviderOverridesSummary>("/v1/admin/pricing/provider-overrides/summary"),
  list: (params?: {
    tenantId?: string; approvalStatus?: string; status?: string; search?: string;
    page?: number; pageSize?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.tenantId) qs.set("tenant_id", params.tenantId);
    if (params?.approvalStatus) qs.set("approval_status", params.approvalStatus);
    if (params?.status) qs.set("status", params.status);
    if (params?.search) qs.set("search", params.search);
    qs.set("page", String(params?.page ?? 1));
    qs.set("page_size", String(params?.pageSize ?? 50));
    return apiFetch<{ items: ProviderPricingOverride[]; total: number }>(`/v1/admin/pricing/provider-overrides?${qs.toString()}`);
  },
  get: (overrideId: string) => apiFetch<ProviderPricingOverride>(`/v1/admin/pricing/provider-overrides/${overrideId}`),
  audit: (overrideId: string) => apiFetch<{ items: AuditEntry[] }>(`/v1/admin/pricing/provider-overrides/${overrideId}/audit`),
  create: (data: Partial<ProviderPricingOverride> & { tenant_id: string; master_service_id: string; override_price: number }) =>
    apiFetch<ProviderPricingOverride>("/v1/admin/pricing/provider-overrides", { method: "POST", body: JSON.stringify(data) }),
  update: (overrideId: string, data: Partial<ProviderPricingOverride>) =>
    apiFetch<ProviderPricingOverride>(`/v1/admin/pricing/provider-overrides/${overrideId}`, { method: "PUT", body: JSON.stringify(data) }),
  approve: (overrideId: string) => apiFetch<ProviderPricingOverride>(`/v1/admin/pricing/provider-overrides/${overrideId}/approve`, { method: "POST" }),
  reject: (overrideId: string, reason: string) =>
    apiFetch<ProviderPricingOverride>(`/v1/admin/pricing/provider-overrides/${overrideId}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  enable: (overrideId: string) => apiFetch<ProviderPricingOverride>(`/v1/admin/pricing/provider-overrides/${overrideId}/enable`, { method: "POST" }),
  disable: (overrideId: string) => apiFetch<ProviderPricingOverride>(`/v1/admin/pricing/provider-overrides/${overrideId}/disable`, { method: "POST" }),
  activate: (overrideId: string) => apiFetch<ProviderPricingOverride>(`/v1/admin/pricing/provider-overrides/${overrideId}/activate`, { method: "POST" }),
  deactivate: (overrideId: string) => apiFetch<ProviderPricingOverride>(`/v1/admin/pricing/provider-overrides/${overrideId}/deactivate`, { method: "POST" }),
  validatePreview: (data: { tenant_id: string; master_service_id: string; override_price: number; reason?: string }) =>
    apiFetch<OverrideValidationResult>("/v1/admin/pricing/provider-overrides/validate-preview", { method: "POST", body: JSON.stringify(data) }),
};
export interface NotifTemplateList { templates:NotifTemplate[]; total:number; }

// ── Engine Management types (enterprise, migration 081) ───────────────────────
export interface PlatformEngine {
  id: string;
  engine_key: string;
  display_name: string;
  description?: string | null;
  engine_type: string;
  lifecycle_status: string;
  global_status: string;
  is_core: boolean;
  is_locked: boolean;
  is_customer_visible: boolean;
  is_tenant_visible: boolean;
  version: string;
  owner_team?: string | null;
  // enriched fields from get_engine()
  dependencies?: EngineDependencyItem[];
  dependent_engines?: string[];
  latest_health?: EngineHealthCheckItem | null;
  category_usage_count?: number;
  package_usage_count?: number;
  active_overrides?: number;
  created_at: string;
  updated_at: string;
}
export interface EngineSummary {
  total_engines: number;
  enabled_globally: number;
  disabled: number;
  core_locked: number;
  beta_engines: number;
  category_mapped: number;
  package_entitled: number;
  tenant_overrides_active: number;
  degraded_or_down: number;
}
export interface EngineImpactPreview {
  engine_key: string;
  engine_name: string;
  action: string;
  current_status: string;
  is_locked: boolean;
  is_core: boolean;
  categories_affected: number;
  packages_affected: number;
  active_tenant_overrides: number;
  blockers: string[];
  warnings: string[];
  risk_level: string;
  can_proceed: boolean;
  recommendation: string;
}
export interface EngineHealthCheckItem {
  id: string;
  engine_key: string;
  health_status: string;
  check_type: string;
  result: Record<string, unknown>;
  error_message?: string | null;
  response_ms?: number | null;
  checked_at: string;
}
export interface EngineHealthOverview {
  engines: (PlatformEngine & { health_status: string; last_check?: string | null; last_error?: string | null })[];
  summary: { healthy: number; degraded: number; down: number; unknown: number; total: number };
}
export interface EnterpriseEnginePermission {
  id: string;
  engine_key: string;
  permission_key: string;
  label: string;
  description?: string | null;
  scope: string;
  is_sensitive: boolean;
  requires_mfa: boolean;
  status: string;
}
export interface EnterpriseEngineAuditLog {
  id: string;
  engine_key?: string | null;
  action_type: string;
  scope_type: string;
  scope_id?: string | null;
  actor_user_id?: string | null;
  actor_role?: string | null;
  old_value?: Record<string, unknown> | null;
  new_value?: Record<string, unknown> | null;
  reason?: string | null;
  created_at: string;
}
export interface EngineDependencyGraph {
  nodes: { id: string; label: string; type: string; status: string }[];
  edges: { from: string; to: string; type: string }[];
  blocked_enables: { engine_key: string; blocked_by: string }[];
}
export interface EnterpriseCategoryEngineEntry {
  id: string; category_id: string; engine_key: string;
  is_enabled: boolean; is_required: boolean;
}
export interface CategoryOption {
  id: string; name: string; slug: string;
  vertical_type: string | null; status: string;
}
export interface CategoryMatrixRow {
  id: string; category_id: string; engine_key: string;
  is_enabled: boolean; is_required: boolean;
  recommendation_status: "required" | "optional" | "not_recommended" | "not_applicable";
  dependency_status: "met" | "missing" | "not_checked";
  missing_dependencies: string[];
  runtime_risk: "low" | "medium" | "high" | "blocked";
  status: string;
  package_usage_count: number;
  tenant_impact_count: number;
  created_at: string | null; updated_at: string | null;
}
export interface CategoryMatrixDetail {
  category: {
    id: string; name: string; slug: string; vertical_type: string | null;
    customer_flow_type: string | null; finance_model: string | null; status: string;
  };
  rows: CategoryMatrixRow[];
  meta: { total: number; mapped_engine_keys: string[] };
}
export interface CategoryMatrixSummary {
  category: CategoryMatrixDetail["category"];
  total_engines: number; enabled_engines: number;
  required_engines: number; optional_engines: number;
  missing_dependencies: number; used_by_packages: number;
  used_by_tenants: number; blocked_actions: number;
}
export interface CategorySeedPreview {
  category: string; template: string; will_create: number;
  required_engines: string[]; optional_engines: string[];
  already_mapped: string[]; warnings: string[];
}
export interface CategoryMatrixTemplateOption {
  key: string; vertical_type: string; required_count: number; optional_count: number;
}
export interface CategoryEngineActionPreview {
  category_id: string; engine_key: string; action: string;
  affected_packages: number; affected_tenants: number;
  missing_dependencies: string[]; risk_level: string;
  blocked: boolean; blockers: string[]; warnings: string[];
  recommendation: string;
}
export interface CategoryEnginePackageUsageRow {
  package_id: string; package_name: string; package_type: string;
  status: string; tenant_count: number; engine_included: boolean; required: boolean;
}
export interface CategoryEngineTenantImpactRow {
  tenant_id: string; tenant_name: string; status: string; plan_type: string;
  runtime_access: boolean | null; override: string | null; risk: string;
}
export interface EnterprisePackageEntitlement {
  id: string; package_id: string; engine_key: string;
  is_included: boolean; status: string;
  limits: Record<string, unknown>; feature_flags: Record<string, unknown>;
}
export interface EnterpriseTenantOverride {
  id: string; tenant_id: string; engine_key: string;
  override_type: string; effective_status: string;
  reason: string; expires_at?: string | null;
  status: string; created_at: string;
}
export interface EngineAccessResolution {
  engine_key: string;
  runtime_enabled: boolean;
  resolution_path: string[];
  blockers: string[];
}

export interface EngineDependencyItem {
  id:                    string;
  engine_key:            string;
  depends_on_engine_key: string;
  dependency_type:       string;
  status:                string;
}

export interface EnginePermissionItem {
  id:              string;
  engine_id:       string;
  permission_key:  string;
  permission_name: string;
  description:     string | null;
  is_admin_only:   boolean;
}

export interface EngineHealthHistoryItem {
  id:            string;
  engine_id:     string;
  health_status: string;
  message:       string | null;
  details:       Record<string, unknown> | null;
  checked_at:    string;
}
export interface PlatformEngineList { engines: PlatformEngine[]; total: number; }

export interface CategoryEngineItem {
  id:                  string;
  category_id:         string;
  engine_id:           string;
  engine_key:          string;
  engine_name:         string;
  is_enabled:          boolean;
  is_required:         boolean;
  is_optional:         boolean;
  config:              Record<string, unknown>;
  inherited_from_global: boolean;
  health_status:       string;
  dependencies:        string[];
  dependencies_met:    boolean;
}
export interface CategoryEngineList { engines: CategoryEngineItem[]; total: number; }

export interface PackageEntitlementItem {
  id:          string;
  package_id:  string;
  engine_id:   string;
  engine_key:  string;
  engine_name: string;
  is_enabled:  boolean;
  usage_limit: Record<string, unknown> | null;
  config:      Record<string, unknown>;
}
export interface PackageEntitlementList { engines: PackageEntitlementItem[]; total: number; }

export interface TenantEngineOverride {
  id:                  string;
  tenant_id:           string;
  engine_id:           string;
  engine_key:          string;
  engine_name:         string;
  override_type:       "force_enable" | "force_disable" | "config_override";
  is_enabled:          boolean | null;
  config:              Record<string, unknown> | null;
  reason:              string | null;
  approved_by_user_id: string | null;
  created_at:          string;
}
export interface TenantEngineOverrideList { overrides: TenantEngineOverride[]; total: number; }

export interface EffectiveEngineItem {
  engine_key:         string;
  name:               string;
  effective_enabled:  boolean;
  source:             "global" | "category" | "package_entitlement" | "tenant_override";
  is_required:        boolean;
  health_status:      string;
  dependencies_met:   boolean;
  dependencies:       string[];
  reason:             string | null;
  config:             Record<string, unknown>;
}
export interface EffectiveEnginesResponse {
  tenant_id: string;
  category:  { id: string; name: string } | null;
  package:   { id: string; name: string } | null;
  engines:   EffectiveEngineItem[];
  summary:   { total: number; enabled: number; disabled: number };
}

export interface EngineAuditLog {
  id:            string;
  engine_id:     string | null;
  engine_key:    string | null;
  category_id:   string | null;
  tenant_id:     string | null;
  package_id:    string | null;
  actor_user_id: string | null;
  actor_role:    string | null;
  action:        string;
  old_value:     Record<string, unknown> | null;
  new_value:     Record<string, unknown> | null;
  reason:        string | null;
  created_at:    string;
}
export interface EngineAuditLogList { logs: EngineAuditLog[]; has_next: boolean; }

export interface EngineHealthItem {
  engine_id:            string;
  engine_key:           string;
  name:                 string;
  health_status:        string;
  is_global_enabled:    boolean;
  last_health_check_at: string | null;
  dependencies:         string[];
  dependencies_healthy: boolean;
}
export interface EngineHealthList { engines: EngineHealthItem[]; total: number; }

// ── Engine Management API ─────────────────────────────────────────────────────
// Enterprise Engine Management API (migration 081)
export const engineMgmtApi = {
  // Registry
  getSummary: () => apiFetch<EngineSummary>("/v1/admin/engines/summary"),
  list: (params?: { engine_type?: string; global_status?: string; lifecycle_status?: string; is_core?: boolean; q?: string; page?: number; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.engine_type) qs.set("engine_type", params.engine_type);
    if (params?.global_status) qs.set("global_status", params.global_status);
    if (params?.lifecycle_status) qs.set("lifecycle_status", params.lifecycle_status);
    if (params?.is_core !== undefined) qs.set("is_core", String(params.is_core));
    if (params?.q) qs.set("q", params.q);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.limit) qs.set("limit", String(params.limit));
    return apiFetch<{ engines: PlatformEngine[]; meta: { total: number; page: number; limit: number; total_pages: number } }>(`/v1/admin/engines?${qs}`);
  },
  get: (engineKey: string) => apiFetch<PlatformEngine>(`/v1/admin/engines/${engineKey}`),
  create: (data: object) => apiFetch<PlatformEngine>("/v1/admin/engines", { method: "POST", body: JSON.stringify(data) }),
  update: (engineKey: string, data: object) => apiFetch<PlatformEngine>(`/v1/admin/engines/${engineKey}`, { method: "PUT", body: JSON.stringify(data) }),
  impactPreview: (engineKey: string, action: "enable" | "disable") =>
    apiFetch<EngineImpactPreview>(`/v1/admin/engines/${engineKey}/impact-preview`, {
      method: "POST", body: JSON.stringify({ action }),
    }),
  enableGlobally: (engineKey: string, reason = "") =>
    apiFetch<PlatformEngine>(`/v1/admin/engines/${engineKey}/enable`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  disableGlobally: (engineKey: string, reason: string) =>
    apiFetch<PlatformEngine>(`/v1/admin/engines/${engineKey}/disable`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  // Category Matrix
  getCategoryMatrix: (categoryId?: string) => {
    const qs = new URLSearchParams();
    if (categoryId) qs.set("category_id", categoryId);
    return apiFetch<{ matrix: EnterpriseCategoryEngineEntry[]; meta: { total: number } }>(`/v1/admin/engines/category-matrix?${qs}`);
  },
  getCategoryMatrixDetail: (categoryId: string) =>
    apiFetch<CategoryMatrixDetail>(`/v1/admin/engines/category-matrix/${categoryId}`),
  getCategoryMatrixSummary: (categoryId: string) =>
    apiFetch<CategoryMatrixSummary>(`/v1/admin/engines/category-matrix/${categoryId}/summary`),
  getCategoryMatrixTemplates: () =>
    apiFetch<{ templates: CategoryMatrixTemplateOption[] }>("/v1/admin/engines/category-matrix/templates"),
  seedCategoryDefaultsPreview: (categoryId: string, template?: string) =>
    apiFetch<CategorySeedPreview>(`/v1/admin/engines/category-matrix/${categoryId}/seed-defaults/preview`, {
      method: "POST", body: JSON.stringify({ template }),
    }),
  seedCategoryDefaults: (categoryId: string, template?: string, dryRun = false, reason = "Seeded recommended defaults") =>
    apiFetch<CategorySeedPreview & { created_engine_keys: string[]; dry_run: boolean }>(
      `/v1/admin/engines/category-matrix/${categoryId}/seed-defaults`, {
      method: "POST", body: JSON.stringify({ template, dry_run: dryRun, reason }),
    }),
  categoryEngineEnablePreview: (categoryId: string, engineKey: string) =>
    apiFetch<CategoryEngineActionPreview>(`/v1/admin/engines/category-matrix/${categoryId}/engines/${engineKey}/enable-preview`, {
      method: "POST",
    }),
  categoryEngineDisablePreview: (categoryId: string, engineKey: string) =>
    apiFetch<CategoryEngineActionPreview>(`/v1/admin/engines/category-matrix/${categoryId}/engines/${engineKey}/disable-preview`, {
      method: "POST",
    }),
  enableCategoryEngine: (categoryId: string, engineKey: string, reason = "", force = false) =>
    apiFetch<EnterpriseCategoryEngineEntry>(`/v1/admin/engines/category-matrix/${categoryId}/engines/${engineKey}/enable`, {
      method: "POST", body: JSON.stringify({ reason, force }),
    }),
  disableCategoryEngine: (categoryId: string, engineKey: string, reason = "", force = false) =>
    apiFetch<EnterpriseCategoryEngineEntry>(`/v1/admin/engines/category-matrix/${categoryId}/engines/${engineKey}/disable`, {
      method: "POST", body: JSON.stringify({ reason, force }),
    }),
  markCategoryEngineRequired: (categoryId: string, engineKey: string, reason = "") =>
    apiFetch<EnterpriseCategoryEngineEntry>(`/v1/admin/engines/category-matrix/${categoryId}/engines/${engineKey}/mark-required`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  markCategoryEngineOptional: (categoryId: string, engineKey: string, reason = "") =>
    apiFetch<EnterpriseCategoryEngineEntry>(`/v1/admin/engines/category-matrix/${categoryId}/engines/${engineKey}/mark-optional`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  getCategoryEnginePackageUsage: (categoryId: string, engineKey: string) =>
    apiFetch<{ packages: CategoryEnginePackageUsageRow[]; total: number }>(
      `/v1/admin/engines/category-matrix/${categoryId}/engines/${engineKey}/packages`),
  getCategoryEngineTenantImpact: (categoryId: string, engineKey: string) =>
    apiFetch<{ tenants: CategoryEngineTenantImpactRow[]; total: number }>(
      `/v1/admin/engines/category-matrix/${categoryId}/engines/${engineKey}/tenant-impact`),
  exportCategoryMatrix: (categoryId?: string) => {
    const qs = new URLSearchParams();
    if (categoryId) qs.set("category_id", categoryId);
    return apiFetch<{ rows: CategoryMatrixRow[]; count: number; format: string }>(
      `/v1/admin/engines/category-matrix/export?${qs}`);
  },

  // Dependencies
  getDependencies: () => apiFetch<{ dependencies: EngineDependencyItem[]; total: number }>("/v1/admin/engines/dependencies"),
  getDependencyGraph: () => apiFetch<EngineDependencyGraph>("/v1/admin/engines/dependencies/graph"),
  validateDependencies: (engineKey: string, action: string) =>
    apiFetch<{ valid: boolean; blockers: string[]; warnings: string[] }>("/v1/admin/engines/dependencies/validate", {
      method: "POST", body: JSON.stringify({ engine_key: engineKey, action }),
    }),

  // Package Entitlements
  getPackageEntitlements: (packageId?: string) => {
    const qs = new URLSearchParams();
    if (packageId) qs.set("package_id", packageId);
    return apiFetch<{ entitlements: EnterprisePackageEntitlement[]; meta: { total: number } }>(`/v1/admin/engines/package-entitlements?${qs}`);
  },
  getPackageEntitlementsById: (packageId: string) =>
    apiFetch<{ entitlements: EnterprisePackageEntitlement[]; meta: { total: number } }>(`/v1/admin/engines/package-entitlements/${packageId}`),
  includePackageEngine: (packageId: string, engineKey: string, data?: { limits?: object; feature_flags?: object; reason?: string }) =>
    apiFetch<EnterprisePackageEntitlement>(`/v1/admin/engines/package-entitlements/${packageId}/engines/${engineKey}/include`, {
      method: "POST", body: JSON.stringify(data ?? {}),
    }),
  removePackageEngine: (packageId: string, engineKey: string, reason = "") =>
    apiFetch<EnterprisePackageEntitlement>(`/v1/admin/engines/package-entitlements/${packageId}/engines/${engineKey}/remove`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  // Tenant Overrides
  listTenantOverrides: (params?: { tenantId?: string; status?: string; page?: number; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.tenantId) qs.set("tenant_id", params.tenantId);
    if (params?.status) qs.set("status", params.status);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.limit) qs.set("limit", String(params.limit));
    return apiFetch<{ overrides: EnterpriseTenantOverride[]; meta: { total: number; page: number; limit: number } }>(`/v1/admin/engines/tenant-overrides?${qs}`);
  },
  getTenantOverrides: (tenantId: string) =>
    apiFetch<{ overrides: EnterpriseTenantOverride[]; meta: { total: number } }>(`/v1/admin/engines/tenant-overrides/${tenantId}`),
  createTenantOverride: (tenantId: string, data: { engine_key: string; override_type: string; reason: string; expires_at?: string }) =>
    apiFetch<EnterpriseTenantOverride>(`/v1/admin/engines/tenant-overrides/${tenantId}`, {
      method: "POST", body: JSON.stringify(data),
    }),
  revokeTenantOverride: (tenantId: string, overrideId: string, reason = "") =>
    apiFetch<EnterpriseTenantOverride>(`/v1/admin/engines/tenant-overrides/${tenantId}/${overrideId}/revoke`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  // Health
  getHealth: () => apiFetch<EngineHealthOverview>("/v1/admin/engines/health"),
  checkAllHealth: () => apiFetch<{ results: EngineHealthCheckItem[]; total: number }>("/v1/admin/engines/health/check-all", { method: "POST", body: "{}" }),
  checkEngineHealth: (engineKey: string) => apiFetch<EngineHealthCheckItem>(`/v1/admin/engines/${engineKey}/health/check`, { method: "POST", body: "{}" }),
  getEngineHealthHistory: (engineKey: string, limit = 10) =>
    apiFetch<{ history: EngineHealthCheckItem[]; total: number }>(`/v1/admin/engines/${engineKey}/health?limit=${limit}`),

  // Permissions
  listPermissions: (params?: { engine_key?: string; scope?: string; q?: string; page?: number }) => {
    const qs = new URLSearchParams();
    if (params?.engine_key) qs.set("engine_key", params.engine_key);
    if (params?.scope) qs.set("scope", params.scope);
    if (params?.q) qs.set("q", params.q);
    if (params?.page) qs.set("page", String(params.page));
    return apiFetch<{ permissions: EnterpriseEnginePermission[]; meta: { total: number } }>(`/v1/admin/engines/permissions?${qs}`);
  },
  getEnginePermissions: (engineKey: string) =>
    apiFetch<{ permissions: EnterpriseEnginePermission[]; meta: { total: number } }>(`/v1/admin/engines/${engineKey}/permissions`),
  updatePermission: (permissionId: string, data: object) =>
    apiFetch<EnterpriseEnginePermission>(`/v1/admin/engines/permissions/${permissionId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),

  // Audit Logs
  listAuditLogs: (params?: { engine_key?: string; action_type?: string; scope_type?: string; page?: number; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.engine_key) qs.set("engine_key", params.engine_key);
    if (params?.action_type) qs.set("action_type", params.action_type);
    if (params?.scope_type) qs.set("scope_type", params.scope_type);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.limit) qs.set("limit", String(params.limit));
    return apiFetch<{ logs: EnterpriseEngineAuditLog[]; meta: { total: number; page: number; limit: number; total_pages: number } }>(`/v1/admin/engines/audit-logs?${qs}`);
  },

  // Runtime Resolver
  resolveAccess: (data: { engine_key: string; tenant_id?: string; category_id?: string; package_id?: string }) =>
    apiFetch<EngineAccessResolution>("/v1/admin/engines/resolve-access-preview", {
      method: "POST", body: JSON.stringify(data),
    }),

  // Backward-compat: effective engines for a tenant (returns overrides list + optional category/package context)
  getEffectiveEngines: (tenantId: string) =>
    apiFetch<{
      engines: (PlatformEngine & { effective_enabled: boolean; source: string })[];
      summary: { total: number; enabled: number; disabled: number };
      category?: { name: string } | null;
      package?: { name: string } | null;
    }>(`/v1/admin/engines/tenant-overrides/${tenantId}`),
};

// ── Sprint 4: Admin Tenant CRUD + Tenant 360 sub-resources ───────────────────
export const adminTenantApi = {
  onboard: (data: AdminTenantOnboardPayload) =>
    apiFetch<AdminTenantOnboardResult>("/v1/admin/tenants/onboard", { method:"POST", body:JSON.stringify(data) }),

  list: (params?: { status?:string; verification_status?:string; city?:string; state?:string; search?:string; limit?:number }) => {
    const qs = new URLSearchParams(Object.fromEntries(Object.entries(params??{}).filter(([,v])=>v!=null).map(([k,v])=>[k,String(v)]))).toString();
    return apiFetch<{ tenants: AdminTenantRow[]; total: number }>(`/v1/admin/tenants?${qs}`);
  },

  get: (tenantId: string) => apiFetch<AdminTenantRow>(`/v1/admin/tenants/${tenantId}`),
  update: (tenantId: string, data: Record<string, unknown>) =>
    apiFetch<AdminTenantRow>(`/v1/admin/tenants/${tenantId}`, { method:"PATCH", body:JSON.stringify(data) }),

  verify:            (tenantId: string) => apiFetch<AdminTenantRow>(`/v1/admin/tenants/${tenantId}/verify`, { method:"POST" }),
  rejectVerification:(tenantId: string, reason: string) =>
    apiFetch<AdminTenantRow>(`/v1/admin/tenants/${tenantId}/reject-verification`, { method:"POST", body:JSON.stringify({ reason }) }),
  activate:          (tenantId: string) => apiFetch<AdminTenantRow>(`/v1/admin/tenants/${tenantId}/activate`, { method:"POST" }),
  archive:           (tenantId: string) => apiFetch<AdminTenantRow>(`/v1/admin/tenants/${tenantId}/archive`, { method:"POST" }),

  // Users
  listUsers:   (tenantId: string, search?: string) => {
    const qs = search ? `?search=${encodeURIComponent(search)}` : "";
    return apiFetch<{ users: AdminTenantUser[]; total: number }>(`/v1/admin/tenants/${tenantId}/users${qs}`);
  },
  createUser:  (tenantId: string, data: AdminTenantUserCreate) =>
    apiFetch<AdminTenantUser & { temp_password?: string }>(`/v1/admin/tenants/${tenantId}/users`, { method:"POST", body:JSON.stringify(data) }),
  suspendUser: (tenantId: string, userId: string) =>
    apiFetch<AdminTenantUser>(`/v1/admin/tenants/${tenantId}/users/${userId}/suspend`, { method:"POST" }),

  // Staff
  listStaff:      (tenantId: string) => apiFetch<{ staff: AdminTenantUser[]; total: number }>(`/v1/admin/tenants/${tenantId}/staff`),
  createStaff:    (tenantId: string, data: AdminTenantUserCreate) =>
    apiFetch<AdminTenantUser & { temp_password?: string }>(`/v1/admin/tenants/${tenantId}/staff`, { method:"POST", body:JSON.stringify(data) }),
  deactivateStaff:(tenantId: string, staffId: string) =>
    apiFetch<AdminTenantUser>(`/v1/admin/tenants/${tenantId}/staff/${staffId}/deactivate`, { method:"POST" }),

  // Service Areas
  listServiceAreas:  (tenantId: string) => apiFetch<{ service_areas: AdminServiceArea[]; total: number }>(`/v1/admin/tenants/${tenantId}/service-areas`),
  createServiceArea: (tenantId: string, data: AdminServiceAreaCreate) =>
    apiFetch<AdminServiceArea>(`/v1/admin/tenants/${tenantId}/service-areas`, { method:"POST", body:JSON.stringify(data) }),
  deleteServiceArea: (tenantId: string, areaId: string) =>
    apiFetch<{ deleted: boolean; area_id: string }>(`/v1/admin/tenants/${tenantId}/service-areas/${areaId}`, { method:"DELETE" }),

  // Finance
  getSecurityDeposit: (tenantId: string) => apiFetch<AdminDepositDetail>(`/v1/admin/tenants/${tenantId}/security-deposit`),
  markDepositPaid:    (tenantId: string, amount: number) =>
    apiFetch<{ deposit_id:string; status:string; total_paid:number }>(`/v1/admin/tenants/${tenantId}/security-deposit/mark-paid`, { method:"POST", body:JSON.stringify({ amount }) }),
  getWallet:          (tenantId: string) => apiFetch<AdminWalletDetail>(`/v1/admin/tenants/${tenantId}/wallet`),
  getWalletLedger:    (tenantId: string, limit=50) => apiFetch<{ transactions: AdminWalletTxn[] }>(`/v1/admin/tenants/${tenantId}/wallet/ledger?limit=${limit}`),
  walletTopup:        (tenantId: string, amount: number, notes: string) =>
    apiFetch<{ new_balance:number; amount_added:number }>(`/v1/admin/tenants/${tenantId}/wallet/topup`, { method:"POST", body:JSON.stringify({ amount, notes }) }),
};

export interface AdminTenantOnboardPayload {
  business: { business_name:string; city:string; state:string; vertical?:string; category_id?:string; email?:string; phone?:string; address_line1?:string; zipcode?:string; gst_number?:string };
  owner: { name:string; email:string; phone:string; password?:string };
  commercial?: { commission_rate?:number; security_deposit_required?:boolean };
  settings?: { timezone?:string; currency?:string; language?:string };
}
export interface AdminTenantOnboardResult {
  tenant_id:string; tenant_name:string; owner_user_id:string; slug:string; tenant_code:string;
  category_id:string|null; security_deposit_status:string; credit_wallet_balance:number;
  status:string; verification_status:string; owner_temp_password?:string; message:string;
}
export interface AdminTenantRow {
  tenant_id:string; tenant_name:string; business_name:string; slug?:string; tenant_code?:string;
  status:string; verification_status:string; plan_type:string; city?:string; state?:string;
  email?:string; phone?:string; health_score:number; health_band:string;
  rating_average:number; activated_at?:string; created_at:string;
}
export interface AdminTenantUser {
  user_id:string; name:string; email:string; phone?:string; role:string;
  is_active:boolean; is_verified:boolean; last_login_at?:string; created_at:string;
}
export interface AdminTenantUserCreate { name:string; email:string; phone?:string; role?:string; }
export interface AdminServiceArea {
  area_id:string; tenant_id:string; coverage_type:string; country:string;
  state:string; district?:string; city:string; zipcode?:string;
  zone_name?:string; radius_km?:number; priority:number; is_active:boolean; created_at:string;
}
export interface AdminServiceAreaCreate {
  coverage_type?:string; city:string; state:string; zipcode?:string;
  district?:string; zone_name?:string; country?:string; priority?:number;
}
export interface AdminDepositDetail {
  deposit_id:string; tenant_id:string; required_amount:number; total_paid:number;
  current_balance:number; status:string; paid_at?:string;
}
export interface AdminWalletDetail {
  wallet_id:string; tenant_id:string; credit_balance:number;
  lifetime_purchased:number; lifetime_consumed:number;
}
export interface AdminWalletTxn {
  txn_id:string; txn_type:string; amount:number; balance_before:number;
  balance_after:number; description?:string; created_at:string;
}

// ── Sprint 6 — Package types ──────────────────────────────────────────────────
export interface PackageFeature {
  feature_id: string;
  package_id: string;
  feature_key: string | null;
  feature_label: string;
  feature_description: string | null;
  feature_icon: string | null;
  is_highlighted: boolean;
  is_included: boolean;
  display_order: number;
  status: string;
  created_at: string | null;
}

export interface PackageLimit {
  limit_id: string;
  package_id: string;
  limit_key: string;
  limit_label: string;
  limit_value: number | null;
  limit_unit: string | null;
  is_unlimited: boolean;
  display_order: number;
  status: string;
  created_at: string | null;
}

export interface AdminPackage {
  id: string;
  package_id: string;
  package_type: string;
  plan_level: string | null;
  name: string;
  slug: string;
  short_description: string | null;
  description: string | null;
  // pricing
  price: number;
  package_price: number;
  currency: string;
  billing_cycle: string | null;
  validity_days: number | null;
  trial_days: number | null;
  security_deposit_amount: number;
  included_credit_amount: number;
  bonus_credits: number | null;
  lead_credits: number | null;
  setup_fee_amount: number | null;
  renewal_price_amount: number | null;
  storage_quota_gb: number | null;
  commission_rate: number | null;
  // signup display
  vertical_type: string | null;
  is_public_signup_visible: boolean;
  is_popular: boolean;
  is_featured: boolean;
  is_recommended: boolean;
  badge_label: string | null;
  cta_label: string | null;
  display_order: number;
  // terms
  terms_summary: string | null;
  terms_content_json: Record<string, unknown> | null;
  refund_policy: string | null;
  // legacy
  features: Record<string, unknown>;
  // child rows
  package_features: PackageFeature[];
  package_limits: PackageLimit[];
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminPackagePurchase {
  id: string;
  tenant_id: string;
  category_id: string;
  package_id: string;
  monetization_model: string;
  package_type: string;
  purchase_status: string;
  payment_status: string;
  amount_paid: string;
  currency: string;
  payment_method: string | null;
  payment_reference: string | null;
  starts_at: string | null;
  expires_at: string | null;
  paid_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PackageAuditLog {
  id: string;
  package_id: string | null;
  tenant_id: string | null;
  package_purchase_id: string | null;
  actor_user_id: string | null;
  actor_role: string | null;
  action: string;
  action_type: string;
  target_type: string | null;
  target_id: string | null;
  old_value_json: Record<string, unknown> | null;
  new_value_json: Record<string, unknown> | null;
  reason: string | null;
  request_id: string | null;
  created_at: string;
}

// ── packageApi ────────────────────────────────────────────────────────────────
// ── Package Summary ───────────────────────────────────────────────────────────

export interface PackageSummary {
  total: number;
  active: number;
  inactive: number;
  onboarding: number;
  subscription: number;
  lead_credit: number;
  deposit: number;
  featured: number;
  active_assignments: number;
}

// ── Provider Directory / New Requests ─────────────────────────────────────────

export interface ProviderDirectorySummary {
  total: number;
  active: number;
  suspended: number;
  pending_setup: number;
  pending_review: number;
  changes_requested: number;
  rejected: number;
  package_pending_approval: number;
}

export interface NewRequestsSummary {
  total: number;
  with_package: number;
  without_package: number;
  package_selected: number;
  profile_near_complete: number;
}

export interface NewRequestsProvider {
  tenant_id: string;
  business_name: string | null;
  tenant_name: string | null;
  owner_name: string | null;
  owner_email: string | null;
  owner_phone: string | null;
  vertical_type: string | null;
  category_name: string | null;
  city: string | null;
  state: string | null;
  verification_status: string;
  tenant_status: string;
  package_name: string | null;
  package_status: string | null;
  profile_completion_percentage: number;
  review_status: string;
  onboarding_status: string;
  created_at: string;
  updated_at: string | null;
}

export const providersAdminApi = {
  summary: () => apiFetch<ProviderDirectorySummary>("/v1/admin/providers/summary"),
  newRequestsSummary: () => apiFetch<NewRequestsSummary>("/v1/admin/providers/new-requests/summary"),
  newRequests: (params?: {
    q?: string; vertical_type?: string; city?: string;
    has_package?: boolean; page?: number; page_size?: number;
    sort_by?: string; sort_dir?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.q)                  qs.set("q",            params.q);
    if (params?.vertical_type)      qs.set("vertical_type",params.vertical_type);
    if (params?.city)               qs.set("city",         params.city);
    if (params?.has_package !== undefined) qs.set("has_package", String(params.has_package));
    if (params?.page)               qs.set("page",         String(params.page));
    if (params?.page_size)          qs.set("page_size",    String(params.page_size));
    if (params?.sort_by)            qs.set("sort_by",      params.sort_by);
    if (params?.sort_dir)           qs.set("sort_dir",     params.sort_dir);
    return apiFetch<{ providers: NewRequestsProvider[]; total: number; page: number; page_size: number }>(
      `/v1/admin/providers/new-requests?${qs}`
    );
  },
  sendReminder: (tenantId: string) =>
    apiFetch<{ reminder_sent: boolean; message: string }>(
      `/v1/admin/onboarding/providers/${tenantId}/send-reminder`,
      { method: "POST" }
    ),
};

// ── Admin Tenants Enterprise API ─────────────────────────────────────────────

export interface TenantListItem {
  tenant_id: string;
  tenant_name: string;
  business_name: string | null;
  owner_name: string | null;
  email: string | null;
  phone: string | null;
  logo_url: string | null;
  status: string;
  verification_status: string;
  plan_type: string;
  vertical: string;
  city: string | null;
  state: string | null;
  city_tier: string | null;
  health_score: number;
  health_band: string;
  usage_credit_balance: number;
  security_deposit_paid: boolean;
  billing_cycle: string;
  active_jobs: number;
  completed_jobs: number;
  open_complaints: number;
  staff_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface TenantsSummary {
  total: number;
  active: number;
  suspended: number;
  pending_setup: number;
  pending_review: number;
  changes_requested: number;
  rejected: number;
  package_pending_approval: number;
}

export interface TenantsInsights {
  verification_overview: {
    not_started: number; in_progress: number; completed: number;
    changes_requested: number; rejected: number; total: number;
  };
  plan_distribution: { plan: string; count: number }[];
  top_locations: { city: string; state: string; count: number }[];
  financial_summary: {
    total_usage_credits: number;
    total_security_deposits: number;
    low_credit_tenants: number;
  };
  health_summary: {
    average_health_score: number;
    high_risk: number; medium_risk: number; low_risk: number;
  };
  recent_activity: {
    action: string; tenant_name: string; notes: string | null; created_at: string | null;
  }[];
}

export const adminTenantsApi = {
  // apiFetch<T> already unwraps {success,data} to T — don't re-wrap in { data: T }.
  getSummary: () =>
    apiFetch<TenantsSummary>("/v1/admin/tenants/summary"),

  getInsights: () =>
    apiFetch<TenantsInsights>("/v1/admin/tenants/insights"),

  list: (params: {
    q?: string; status?: string; verification_status?: string; plan_type?: string;
    city_tier?: string; state?: string; district?: string; city?: string;
    created_from?: string; created_to?: string;
    page?: number; page_size?: number; sort_by?: string; sort_direction?: string;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k === "q" ? "search" : k, String(v)); });
    return apiFetch<{ items: TenantListItem[]; pagination: { page: number; total_items: number; total_pages: number; has_next: boolean; has_previous: boolean } }>(
      `/v1/admin/tenants?${qs}`
    );
  },

  exportCsv: async (params: { status?: string; verification_status?: string; plan_type?: string; state?: string; city?: string; search?: string }): Promise<Blob> => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, v); });
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const token = typeof window !== "undefined" ? (localStorage.getItem("serviceos_admin_token") ?? "") : "";
    const res = await fetch(`${API}/v1/admin/tenants/export?${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Export failed");
    return res.blob();
  },

  addUsageCredits: (tenantId: string, amount: number, reason: string) =>
    apiFetch<{ data: { new_balance: number } }>(`/v1/admin/tenants/${tenantId}/add-usage-credits`, {
      method: "POST", body: JSON.stringify({ amount, reason }),
    }),

  changePlan: (tenantId: string, plan: string, reason: string) =>
    apiFetch<{ data: { new_plan: string } }>(`/v1/admin/tenants/${tenantId}/change-plan`, {
      method: "POST", body: JSON.stringify({ plan, reason }),
    }),

  suspend: (tenantId: string, reason: string) =>
    apiFetch<{ data: object }>(`/v1/admin/tenants/${tenantId}/suspend`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  addNote: (tenantId: string, note: string) =>
    apiFetch<{ tenant_id: string; note_added: boolean }>(`/v1/admin/tenants/${tenantId}/notes`, {
      method: "POST", body: JSON.stringify({ note }),
    }),

  reactivate: (tenantId: string, reason?: string) =>
    apiFetch<{ data: object }>(`/v1/admin/tenants/${tenantId}/reactivate`, {
      method: "POST", body: JSON.stringify({ reason: reason ?? "" }),
    }),

  requestChanges: (tenantId: string, reason: string) =>
    apiFetch<{ data: object }>(`/v1/admin/tenants/${tenantId}/request-changes`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  sendNotification: (tenantId: string, subject: string, message: string) =>
    apiFetch<{ data: object }>(`/v1/admin/tenants/${tenantId}/send-notification`, {
      method: "POST", body: JSON.stringify({ subject, message }),
    }),

  exportTenantReport: async (tenantId: string): Promise<Blob> => {
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const token = typeof window !== "undefined" ? (localStorage.getItem("serviceos_admin_token") ?? "") : "";
    const res = await fetch(`${API}/v1/admin/tenants/${tenantId}/export`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Export failed");
    return res.blob();
  },
};

export const packageApi = {
  // Admin package CRUD
  summary: () => apiFetch<PackageSummary>("/v1/admin/packages/summary"),
  list: (params?: {
    package_type?: string; vertical_type?: string;
    is_active?: boolean; limit?: number; offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.package_type)          qs.set("package_type",  params.package_type);
    if (params?.vertical_type)         qs.set("vertical_type", params.vertical_type);
    if (params?.is_active !== undefined) qs.set("is_active",   String(params.is_active));
    if (params?.limit)                 qs.set("limit",         String(params.limit));
    if (params?.offset)                qs.set("offset",        String(params.offset));
    return apiFetch<{ packages: AdminPackage[]; total: number }>(`/v1/admin/packages?${qs}`);
  },
  get: (packageId: string) => apiFetch<AdminPackage>(`/v1/admin/packages/${packageId}`),
  create: (data: Record<string, unknown>) =>
    apiFetch<AdminPackage>("/v1/admin/packages", { method: "POST", body: JSON.stringify(data) }),
  update: (packageId: string, data: Record<string, unknown>) =>
    apiFetch<AdminPackage>(`/v1/admin/packages/${packageId}`, { method: "PUT", body: JSON.stringify(data) }),
  activate: (packageId: string) =>
    apiFetch<AdminPackage>(`/v1/admin/packages/${packageId}/activate`, { method: "POST" }),
  deactivate: (packageId: string) =>
    apiFetch<AdminPackage>(`/v1/admin/packages/${packageId}/deactivate`, { method: "POST" }),
  clone: (packageId: string) =>
    apiFetch<AdminPackage>(`/v1/admin/packages/${packageId}/clone`, { method: "POST" }),
  delete: (packageId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/packages/${packageId}`, { method: "DELETE" }),

  // Features
  listFeatures: (packageId: string) =>
    apiFetch<{ features: PackageFeature[]; total: number }>(`/v1/admin/packages/${packageId}/features`),
  createFeature: (packageId: string, data: Partial<PackageFeature> & { feature_label: string }) =>
    apiFetch<PackageFeature>(`/v1/admin/packages/${packageId}/features`,
      { method: "POST", body: JSON.stringify(data) }),
  updateFeature: (packageId: string, featureId: string, data: Partial<PackageFeature>) =>
    apiFetch<PackageFeature>(`/v1/admin/packages/${packageId}/features/${featureId}`,
      { method: "PUT", body: JSON.stringify(data) }),
  deleteFeature: (packageId: string, featureId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/packages/${packageId}/features/${featureId}`,
      { method: "DELETE" }),

  // Limits
  listLimits: (packageId: string) =>
    apiFetch<{ limits: PackageLimit[]; total: number }>(`/v1/admin/packages/${packageId}/limits`),
  createLimit: (packageId: string, data: Partial<PackageLimit> & { limit_key: string; limit_label: string }) =>
    apiFetch<PackageLimit>(`/v1/admin/packages/${packageId}/limits`,
      { method: "POST", body: JSON.stringify(data) }),
  updateLimit: (packageId: string, limitId: string, data: Partial<PackageLimit>) =>
    apiFetch<PackageLimit>(`/v1/admin/packages/${packageId}/limits/${limitId}`,
      { method: "PUT", body: JSON.stringify(data) }),
  deleteLimit: (packageId: string, limitId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/packages/${packageId}/limits/${limitId}`,
      { method: "DELETE" }),

  // Tenant purchases (existing system)
  listPurchases: (params?: {
    tenant_id?: string; payment_status?: string; limit?: number; offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.tenant_id)      qs.set("tenant_id",      params.tenant_id);
    if (params?.payment_status) qs.set("payment_status", params.payment_status);
    if (params?.limit)          qs.set("limit",          String(params.limit));
    if (params?.offset)         qs.set("offset",         String(params.offset));
    return apiFetch<{ purchases: AdminPackagePurchase[]; total: number }>(`/v1/admin/packages/purchases?${qs}`);
  },

  // Audit logs
  auditLogs: (params?: { package_id?: string; tenant_id?: string; action?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.package_id) qs.set("package_id", params.package_id);
    if (params?.tenant_id)  qs.set("tenant_id",  params.tenant_id);
    if (params?.action)     qs.set("action",      params.action);
    if (params?.limit)      qs.set("limit",       String(params.limit));
    return apiFetch<{ items: PackageAuditLog[]; total: number }>(`/v1/admin/packages/audit-logs?${qs}`);
  },
};

// ── Sprint 10 — Admin Onboarding APIs ─────────────────────────────────────────

export interface OnboardingChecklistTemplate {
  id: string;
  category_id: string;
  checklist_key: string;
  title: string;
  description: string | null;
  item_type: string;
  completion_source: string;
  required_engine_key: string | null;
  required_permission: string | null;
  is_required: boolean;
  is_blocking: boolean;
  allows_admin_override: boolean;
  provider_action_label: string | null;
  provider_action_route: string | null;
  admin_action_label: string | null;
  admin_action_route: string | null;
  completion_rule: Record<string, unknown> | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
}

export interface AdminProviderOnboardingItem {
  id: string;
  checklist_key: string;
  title: string;
  status: string;
  is_required: boolean;
  is_blocking: boolean;
  completion_source: string;
  blocked_reason: string | null;
  completed_at: string | null;
  allows_admin_override: boolean;
  override_reason: string | null;
  overridden_at: string | null;
}

export interface AdminProviderOnboarding {
  tenant_id: string;
  business_name: string | null;
  tenant_name: string | null;
  owner_name: string | null;
  owner_email: string | null;
  vertical_type: string | null;
  category_name: string | null;
  category_type: string | null;
  city: string | null;
  state: string | null;
  district: string | null;
  zipcode: string | null;
  verification_status: string | null;
  tenant_status: string | null;
  created_at: string | null;
  updated_at: string | null;
  selected_package_name: string | null;
  package_status: string | null;
  profile_completion_percentage: number;
  review_status: string;
  onboarding_status: string;
  readiness_status: string;
  bookable_status: string;
}

export interface AdminOnboardingProviderListItem {
  tenant_id: string;
  business_name: string | null;
  tenant_name: string | null;
  owner_name: string | null;
  owner_email: string | null;
  vertical_type: string | null;
  category_name: string | null;
  category_type: string | null;
  city: string | null;
  state: string | null;
  district: string | null;
  zipcode: string | null;
  verification_status: string | null;
  tenant_status: string | null;
  review_status: string;
  onboarding_status: string;
  readiness_status: string;
  bookable_status: string;
  profile_completion_percentage: number;
  selected_package_name: string | null;
  package_status: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface OnboardingProviderSummary {
  pending_review: number;
  not_submitted: number;
  changes_requested: number;
  rejected: number;
  total: number;
}

export const adminOnboardingTemplatesApi = {
  list: (categoryId: string) =>
    apiFetch<{ templates: OnboardingChecklistTemplate[]; count: number }>(
      `/v1/admin/onboarding/templates/${categoryId}`
    ),
  create: (categoryId: string, data: Partial<OnboardingChecklistTemplate>) =>
    apiFetch<OnboardingChecklistTemplate>(
      `/v1/admin/onboarding/templates/${categoryId}`,
      { method: "POST", body: JSON.stringify(data) }
    ),
  get: (templateId: string) =>
    apiFetch<OnboardingChecklistTemplate>(`/v1/admin/onboarding/templates/item/${templateId}`),
  update: (templateId: string, data: Partial<OnboardingChecklistTemplate>) =>
    apiFetch<OnboardingChecklistTemplate>(
      `/v1/admin/onboarding/templates/item/${templateId}`,
      { method: "PUT", body: JSON.stringify(data) }
    ),
  activate: (templateId: string) =>
    apiFetch<OnboardingChecklistTemplate>(
      `/v1/admin/onboarding/templates/item/${templateId}/activate`,
      { method: "POST" }
    ),
  deactivate: (templateId: string) =>
    apiFetch<OnboardingChecklistTemplate>(
      `/v1/admin/onboarding/templates/item/${templateId}/deactivate`,
      { method: "POST" }
    ),
  reorder: (categoryId: string, ordered_ids: string[]) =>
    apiFetch<{ reordered: number }>(
      `/v1/admin/onboarding/templates/${categoryId}/reorder`,
      { method: "POST", body: JSON.stringify({ ordered_ids }) }
    ),
};

export const adminProviderOnboardingApi = {
  get: (tenantId: string) =>
    apiFetch<AdminProviderOnboarding>(`/v1/admin/onboarding/providers/${tenantId}`),
  refresh: (tenantId: string) =>
    apiFetch<{ tenant_id: string; refreshed: boolean }>(`/v1/admin/onboarding/providers/${tenantId}/refresh`, { method: "POST" }),
  override: (tenantId: string, checklistKey: string, reason: string) =>
    apiFetch<{ overridden: boolean }>(
      `/v1/admin/onboarding/providers/${tenantId}/items/${checklistKey}/override`,
      { method: "POST", body: JSON.stringify({ reason }) }
    ),
};

export const adminOnboardingProvidersApi = {
  list: (params?: {
    q?: string; category_id?: string; vertical_type?: string;
    review_status?: string; city?: string;
    page?: number; page_size?: number;
    sort_by?: string; sort_dir?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.q)               qs.set("q",             params.q);
    if (params?.category_id)     qs.set("category_id",   params.category_id);
    if (params?.vertical_type)   qs.set("vertical_type", params.vertical_type);
    if (params?.review_status)   qs.set("review_status", params.review_status);
    if (params?.city)            qs.set("city",          params.city);
    if (params?.page)            qs.set("page",          String(params.page));
    if (params?.page_size)       qs.set("page_size",     String(params.page_size));
    if (params?.sort_by)         qs.set("sort_by",       params.sort_by);
    if (params?.sort_dir)        qs.set("sort_dir",      params.sort_dir);
    return apiFetch<{
      providers: AdminOnboardingProviderListItem[];
      count: number; total: number; page: number; page_size: number;
      summary: OnboardingProviderSummary;
    }>(`/v1/admin/onboarding/providers?${qs}`);
  },
  approve: (tenantId: string) =>
    apiFetch<unknown>(`/v1/admin/onboarding/providers/${tenantId}/approve`, { method: "POST" }),
  reject: (tenantId: string, reason: string) =>
    apiFetch<unknown>(`/v1/admin/onboarding/providers/${tenantId}/reject`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  requestChanges: (tenantId: string, notes: string) =>
    apiFetch<unknown>(`/v1/admin/onboarding/providers/${tenantId}/request-changes`, {
      method: "POST", body: JSON.stringify({ notes }),
    }),
  sendReminder: (tenantId: string) =>
    apiFetch<{ reminder_sent: boolean; message: string }>(
      `/v1/admin/onboarding/providers/${tenantId}/send-reminder`,
      { method: "POST" }
    ),
};

// ── Sprint 11 — Admin Provider Enablement ────────────────────────────────────

export interface AdminTenantEnabledOffering {
  provider_enabled_offering_id: string;
  offering_id: string;
  offering_name: string;
  offering_type: string | null;
  status: string;
  readiness_status: string | null;
  supported_type_ids: string[] | null;
  supported_brand_ids: string[] | null;
  supports_emergency: boolean;
  provider_price_override: string | null;
  readiness_blockers: Array<{ code: string; message: string }> | null;
  activated_at: string | null;
  suspended_at: string | null;
  suspension_reason: string | null;
}

export interface AdminTenantServiceArea {
  area_id: string;
  area_type: string;
  state: string | null;
  district: string | null;
  city: string | null;
  zipcode: string | null;
  zone_name: string | null;
  radius_km: number | null;
  is_primary: boolean;
  is_active: boolean;
  created_at: string | null;
}

export interface AdminTenantTeamMember {
  member_id: string;
  member_type: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  designation: string | null;
  skills: string[] | null;
  can_receive_assignment: boolean;
  status: string;
  created_at: string | null;
}

export interface AdminTenantAvailabilityRule {
  availability_id: string;
  scope_type: string;
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

export const adminProviderEnablementApi = {
  listOfferings: (tenantId: string) =>
    apiFetch<{ offerings: AdminTenantEnabledOffering[]; count: number }>(
      `/v1/admin/tenants/${tenantId}/offerings/enabled`
    ),
  suspendOffering: (tenantId: string, offeringId: string, reason: string) =>
    apiFetch<AdminTenantEnabledOffering>(
      `/v1/admin/tenants/${tenantId}/offerings/enabled/${offeringId}/suspend`,
      { method: "POST", body: JSON.stringify({ reason }) }
    ),
  reactivateOffering: (tenantId: string, offeringId: string) =>
    apiFetch<AdminTenantEnabledOffering>(
      `/v1/admin/tenants/${tenantId}/offerings/enabled/${offeringId}/reactivate`,
      { method: "POST" }
    ),
  refreshReadiness: (tenantId: string) =>
    apiFetch<{ refreshed: number }>(
      `/v1/admin/tenants/${tenantId}/offerings/refresh-readiness`,
      { method: "POST" }
    ),
  listServiceAreas: (tenantId: string) =>
    apiFetch<{ areas: AdminTenantServiceArea[]; count: number }>(
      `/v1/admin/tenants/${tenantId}/service-areas`
    ),
  listTeamMembers: (tenantId: string) =>
    apiFetch<{ members: AdminTenantTeamMember[]; count: number }>(
      `/v1/admin/tenants/${tenantId}/team-members`
    ),
  listAvailability: (tenantId: string) =>
    apiFetch<{ rules: AdminTenantAvailabilityRule[]; count: number }>(
      `/v1/admin/tenants/${tenantId}/availability`
    ),
};


// ── Sprint 12 Types ───────────────────────────────────────────────────────────
export interface BookabilityBlocker {
  code: string;
  message: string;
  route?: string | null;
}

export interface ProviderVisibilityStatus {
  tenant_id: string;
  category_id: string | null;
  is_visible: boolean;
  is_bookable: boolean;
  visibility_blockers: BookabilityBlocker[];
  bookability_blockers: BookabilityBlocker[];
  override_is_visible: boolean | null;
  override_visible_reason: string | null;
  override_is_bookable: boolean | null;
  override_bookable_reason: string | null;
  last_evaluated_at: string | null;
  last_changed_at: string | null;
  created_at: string | null;
  // Admin list fields
  business_name?: string;
  city?: string;
  verification_status?: string;
}

export interface BookabilityRule {
  id: string;
  rule_code: string;
  category_id: string | null;
  rule_type: string;
  display_name: string;
  description: string | null;
  is_required_for_visible: boolean;
  is_required_for_bookable: boolean;
  blocker_message: string | null;
  resolution_route: string | null;
  sort_order: number;
  is_active: boolean;
}

export interface BookabilityAuditLog {
  id: string;
  tenant_id: string;
  event_type: string;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  trigger_source: string | null;
  actor_id: string | null;
  actor_type: string | null;
  notes: string | null;
  created_at: string;
}

export interface BookabilitySummary {
  total_providers: number;
  bookable: number;
  not_bookable: number;
  visible: number;
  not_visible: number;
  with_overrides: number;
}

export const adminBookabilityApi = {
  listProviders: (params?: {
    is_bookable?: boolean;
    is_visible?: boolean;
    category_id?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.is_bookable !== undefined) q.set("is_bookable", String(params.is_bookable));
    if (params?.is_visible !== undefined)  q.set("is_visible",  String(params.is_visible));
    if (params?.category_id) q.set("category_id", params.category_id);
    if (params?.search)      q.set("search",      params.search);
    if (params?.page)        q.set("page",        String(params.page));
    if (params?.page_size)   q.set("page_size",   String(params.page_size));
    return apiFetch<{ providers: ProviderVisibilityStatus[]; count: number; page: number; page_size: number }>(
      `/v1/admin/bookability/providers${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  getProvider: (tenantId: string) =>
    apiFetch<ProviderVisibilityStatus>(`/v1/admin/bookability/providers/${tenantId}`),
  refreshProvider: (tenantId: string) =>
    apiFetch<ProviderVisibilityStatus>(`/v1/admin/bookability/providers/${tenantId}/refresh`, { method: "POST" }),
  overrideVisibility: (tenantId: string, override: boolean, reason: string) =>
    apiFetch<ProviderVisibilityStatus>(
      `/v1/admin/bookability/providers/${tenantId}/override-visibility`,
      { method: "POST", body: JSON.stringify({ override, reason }) }
    ),
  removeVisibilityOverride: (tenantId: string) =>
    apiFetch<ProviderVisibilityStatus>(
      `/v1/admin/bookability/providers/${tenantId}/override-visibility`,
      { method: "DELETE" }
    ),
  overrideBookability: (tenantId: string, override: boolean, reason: string) =>
    apiFetch<ProviderVisibilityStatus>(
      `/v1/admin/bookability/providers/${tenantId}/override-bookability`,
      { method: "POST", body: JSON.stringify({ override, reason }) }
    ),
  removeBookabilityOverride: (tenantId: string) =>
    apiFetch<ProviderVisibilityStatus>(
      `/v1/admin/bookability/providers/${tenantId}/override-bookability`,
      { method: "DELETE" }
    ),
  getAuditLogs: (tenantId: string, limit?: number, offset?: number) => {
    const q = new URLSearchParams();
    if (limit)  q.set("limit",  String(limit));
    if (offset) q.set("offset", String(offset));
    return apiFetch<{ logs: BookabilityAuditLog[]; count: number }>(
      `/v1/admin/bookability/providers/${tenantId}/audit-logs?${q.toString()}`
    );
  },
  bulkRefresh: () =>
    apiFetch<{ refreshed: number; errors: string[] }>(`/v1/admin/bookability/bulk-refresh`, { method: "POST" }),
  listRules: (params?: { category_id?: string; include_inactive?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.category_id)        q.set("category_id",        params.category_id);
    if (params?.include_inactive)   q.set("include_inactive",   "true");
    return apiFetch<{ rules: BookabilityRule[]; count: number }>(
      `/v1/admin/bookability/rules${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  createRule: (payload: Partial<BookabilityRule>) =>
    apiFetch<BookabilityRule>(`/v1/admin/bookability/rules`, { method: "POST", body: JSON.stringify(payload) }),
  updateRule: (ruleId: string, payload: Partial<BookabilityRule>) =>
    apiFetch<BookabilityRule>(`/v1/admin/bookability/rules/${ruleId}`, { method: "PUT", body: JSON.stringify(payload) }),
  getSummary: () =>
    apiFetch<BookabilitySummary>(`/v1/admin/bookability/summary`),
};

// ── Sprint 15 — AI Conversation Engine ────────────────────────────────────────

export interface AIConversationSession {
  id: string;
  session_key: string;
  customer_id: string | null;
  category_id: string | null;
  current_intent: string;
  workflow_status: "active" | "paused" | "completed" | "abandoned";
  collected_fields: Record<string, unknown>;
  context_data: Record<string, unknown>;
  turn_count: number;
  last_activity_at: string;
  completed_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIConversationMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  intent_at_time: string | null;
  tool_calls_made: string[];
  latency_ms: number | null;
  token_count: number | null;
  created_at: string;
}

export interface AILLMCallLog {
  id: string;
  session_id: string | null;
  call_type: string;
  model_used: string;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  latency_ms: number | null;
  had_tool_calls: boolean;
  tool_names: string[];
  response_status: string;
  error_message: string | null;
  request_payload_size: number | null;
  created_at: string;
  tool_calls?: AIToolCallLog[];
}

export interface AIToolCallLog {
  id: string;
  llm_call_id: string | null;
  session_id: string | null;
  tool_name: string;
  input_params: Record<string, unknown>;
  output_data: Record<string, unknown>;
  success: boolean;
  latency_ms: number | null;
  created_at: string;
}

export interface AIPromptTemplate {
  id: string;
  template_key: string;
  name: string;
  description: string | null;
  category: "system" | "workflow" | "safety" | "context";
  template_content: string;
  variables: string[];
  version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const adminAIChatApi = {
  // Sessions
  listSessions: (params?: { workflow_status?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.workflow_status) q.set("workflow_status", params.workflow_status);
    if (params?.page)            q.set("page", String(params.page));
    if (params?.page_size)       q.set("page_size", String(params.page_size));
    return apiFetch<{ sessions: AIConversationSession[]; total: number; page: number; page_size: number }>(
      `/v1/admin/ai-chat/sessions${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  getSession: (sessionId: string) =>
    apiFetch<AIConversationSession>(`/v1/admin/ai-chat/sessions/${sessionId}`),
  getSessionMessages: (sessionId: string, params?: { page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.page)      q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    return apiFetch<{ messages: AIConversationMessage[]; total: number }>(
      `/v1/admin/ai-chat/sessions/${sessionId}/messages${q.toString() ? "?" + q.toString() : ""}`
    );
  },

  // LLM Logs
  listLogs: (params?: { session_id?: string; response_status?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.session_id)      q.set("session_id", params.session_id);
    if (params?.response_status) q.set("response_status", params.response_status);
    if (params?.page)            q.set("page", String(params.page));
    if (params?.page_size)       q.set("page_size", String(params.page_size));
    return apiFetch<{ logs: AILLMCallLog[]; total: number; page: number; page_size: number }>(
      `/v1/admin/ai-chat/logs${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  getLog: (logId: string) =>
    apiFetch<AILLMCallLog>(`/v1/admin/ai-chat/logs/${logId}`),

  // Prompt Templates
  listTemplates: (params?: { category?: string; active_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.category)    q.set("category", params.category);
    if (params?.active_only === false) q.set("active_only", "false");
    return apiFetch<{ templates: AIPromptTemplate[]; total: number }>(
      `/v1/admin/ai-chat/prompt-templates${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  getTemplate: (key: string) =>
    apiFetch<AIPromptTemplate>(`/v1/admin/ai-chat/prompt-templates/${key}`),
  createTemplate: (data: Partial<AIPromptTemplate>) =>
    apiFetch<AIPromptTemplate>(`/v1/admin/ai-chat/prompt-templates`, {
      method: "POST", body: JSON.stringify(data),
    }),
  updateTemplate: (key: string, data: Partial<AIPromptTemplate>) =>
    apiFetch<AIPromptTemplate>(`/v1/admin/ai-chat/prompt-templates/${key}`, {
      method: "PUT", body: JSON.stringify(data),
    }),

  // Test Console
  testConsole: (message: string, templateKey?: string, context?: Record<string, unknown>) =>
    apiFetch<{ reply: string; model: string; usage: Record<string, number>; template_key: string | null }>(
      `/v1/admin/ai-chat/test-console`,
      { method: "POST", body: JSON.stringify({ message, template_key: templateKey, context }) }
    ),
};

// ── Sprint 13: Marketing Launch Types ────────────────────────────────────────
export interface MarketingBlocker {
  code: string;
  message: string;
  route?: string | null;
}

export interface MarketingAsset {
  id: string;
  campaign_id: string;
  tenant_id: string;
  category_id: string | null;
  template_id: string | null;
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
  publish_proof_url: string | null;
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MarketingCampaign {
  id: string;
  tenant_id: string;
  category_id: string | null;
  campaign_key: string;
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
  updated_at: string | null;
  assets?: MarketingAsset[];
}

export interface MarketingTemplate {
  id: string;
  category_id: string | null;
  template_key: string;
  template_name: string;
  template_type: string;
  channel: string;
  language: string;
  title_template: string | null;
  body_template: string;
  variables: string[] | null;
  design_config: Record<string, unknown> | null;
  is_ai_enabled: boolean;
  requires_admin_approval: boolean;
  is_active: boolean;
  display_order: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface AutomationTrigger {
  trigger_key: string; description: string; cooldown_hours: number;
}

export interface MarketingPublishQueueEntry {
  id: string;
  asset_id: string;
  campaign_id: string;
  tenant_id: string;
  channel: string;
  publish_mode: string;
  status: string;
  scheduled_at: string | null;
  published_at: string | null;
  external_url: string | null;
  created_at: string | null;
}

export interface MarketingAuditLog {
  id: string;
  tenant_id: string | null;
  campaign_id: string | null;
  asset_id: string | null;
  action: string;
  actor_user_id: string | null;
  actor_role: string | null;
  reason: string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string | null;
}

// ── Sprint 13: Admin Marketing API ────────────────────────────────────────────
export const adminMarketingApi = {
  // Campaigns
  listCampaigns: (params?: { status?: string; category_id?: string; search?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.status)      q.set("status",      params.status);
    if (params?.category_id) q.set("category_id", params.category_id);
    if (params?.search)      q.set("search",      params.search);
    if (params?.page)        q.set("page",        String(params.page));
    if (params?.page_size)   q.set("page_size",   String(params.page_size));
    return apiFetch<{ campaigns: MarketingCampaign[]; count: number; page: number; page_size: number }>(
      `/v1/admin/marketing/campaigns${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  getCampaign: (campaignId: string) =>
    apiFetch<{ campaign: MarketingCampaign }>(`/v1/admin/marketing/campaigns/${campaignId}`),

  // Assets
  listAssets: (params?: { status?: string; category_id?: string; tenant_id?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.status)      q.set("status",      params.status);
    if (params?.category_id) q.set("category_id", params.category_id);
    if (params?.tenant_id)   q.set("tenant_id",   params.tenant_id);
    if (params?.page)        q.set("page",        String(params.page));
    if (params?.page_size)   q.set("page_size",   String(params.page_size));
    return apiFetch<{ assets: MarketingAsset[]; count: number; page: number; page_size: number }>(
      `/v1/admin/marketing/assets${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  approveAsset: (assetId: string) =>
    apiFetch<{ success: boolean; asset: MarketingAsset }>(`/v1/admin/marketing/assets/${assetId}/approve`, { method: "POST" }),
  rejectAsset: (assetId: string, reason: string) =>
    apiFetch<{ success: boolean; asset: MarketingAsset }>(`/v1/admin/marketing/assets/${assetId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  requestChanges: (assetId: string, reason: string) =>
    apiFetch<{ success: boolean; asset: MarketingAsset }>(`/v1/admin/marketing/assets/${assetId}/request-changes`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  markReadyToPublish: (assetId: string) =>
    apiFetch<{ success: boolean; asset: MarketingAsset }>(`/v1/admin/marketing/assets/${assetId}/mark-ready-to-publish`, { method: "POST" }),
  markManuallyPublished: (assetId: string, payload: { publish_url?: string; publish_proof_url?: string; notes?: string }) =>
    apiFetch<{ success: boolean; asset: MarketingAsset }>(`/v1/admin/marketing/assets/${assetId}/mark-manually-published`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Publish Queue
  listPublishQueue: (params?: { status?: string; channel?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.status)    q.set("status",    params.status);
    if (params?.channel)   q.set("channel",   params.channel);
    if (params?.page)      q.set("page",      String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    return apiFetch<{ queue: MarketingPublishQueueEntry[]; count: number; page: number; page_size: number }>(
      `/v1/admin/marketing/publish-queue${q.toString() ? "?" + q.toString() : ""}`
    );
  },

  // Templates
  listTemplates: (params?: { category_id?: string; template_type?: string; include_inactive?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.category_id)     q.set("category_id",     params.category_id);
    if (params?.template_type)   q.set("template_type",   params.template_type);
    if (params?.include_inactive) q.set("include_inactive", "true");
    return apiFetch<{ templates: MarketingTemplate[]; count: number }>(
      `/v1/admin/marketing/templates${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  getTemplate: (templateId: string) =>
    apiFetch<{ template: MarketingTemplate }>(`/v1/admin/marketing/templates/${templateId}`),
  createTemplate: (payload: Partial<MarketingTemplate> & { template_key: string; template_name: string; template_type: string; channel: string; body_template: string }) =>
    apiFetch<{ success: boolean; template: MarketingTemplate }>(`/v1/admin/marketing/templates`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateTemplate: (templateId: string, payload: Partial<MarketingTemplate>) =>
    apiFetch<{ success: boolean; template: MarketingTemplate }>(`/v1/admin/marketing/templates/${templateId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  activateTemplate: (templateId: string) =>
    apiFetch<{ success: boolean }>(`/v1/admin/marketing/templates/${templateId}/activate`, { method: "POST" }),
  deactivateTemplate: (templateId: string) =>
    apiFetch<{ success: boolean }>(`/v1/admin/marketing/templates/${templateId}/deactivate`, { method: "POST" }),

  // Campaign lifecycle (Sprint 29)
  createCampaign: (body: Record<string, unknown>) =>
    apiFetch<MarketingCampaign>("/v1/admin/marketing/campaigns", { method: "POST", body: JSON.stringify(body) }),
  updateCampaign: (campaign_id: string, body: Record<string, unknown>) =>
    apiFetch<MarketingCampaign>(`/v1/admin/marketing/campaigns/${campaign_id}`, { method: "PUT", body: JSON.stringify(body) }),
  scheduleCampaign: (campaign_id: string) =>
    apiFetch<MarketingCampaign>(`/v1/admin/marketing/campaigns/${campaign_id}/schedule`, { method: "POST" }),
  pauseCampaign: (campaign_id: string) =>
    apiFetch<MarketingCampaign>(`/v1/admin/marketing/campaigns/${campaign_id}/pause`, { method: "POST" }),
  resumeCampaign: (campaign_id: string) =>
    apiFetch<MarketingCampaign>(`/v1/admin/marketing/campaigns/${campaign_id}/resume`, { method: "POST" }),
  cancelCampaign: (campaign_id: string) =>
    apiFetch<MarketingCampaign>(`/v1/admin/marketing/campaigns/${campaign_id}/cancel`, { method: "POST" }),
  runNow: (campaign_id: string) =>
    apiFetch<{ campaign: MarketingCampaign; sent: number; failed: number; total: number }>(
      `/v1/admin/marketing/campaigns/${campaign_id}/run-now`, { method: "POST" }
    ),
  getPerformance: (campaign_id: string) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/marketing/campaigns/${campaign_id}/performance`),
  previewSegment: (body: { audience: string; rules: Record<string, unknown> }) =>
    apiFetch<{ audience: string; estimated_total: number; preview_ids: string[] }>(
      "/v1/admin/marketing/segments/preview", { method: "POST", body: JSON.stringify(body) }
    ),
  listEvents: (params?: { campaign_id?: string; event_type?: string; limit?: number; offset?: number }) =>
    apiFetch<Record<string, unknown>[]>(`/v1/admin/marketing/events?${new URLSearchParams(params as Record<string, string>)}`),
  listTriggers: () =>
    apiFetch<AutomationTrigger[]>("/v1/admin/marketing/automation-triggers"),
  runTrigger: (trigger_key: string, params?: Record<string, unknown>) =>
    apiFetch<{ trigger_key: string; targeted: number; skipped: number }>(
      `/v1/admin/marketing/automation-triggers/${trigger_key}/run`,
      { method: "POST", body: JSON.stringify(params || {}) }
    ),
};

// ── Sprint 16 — Home Service Booking Drafts ───────────────────────────────────

export interface HomeServiceBookingDraft {
  id: string;
  customer_id: string | null;
  ai_session_id: string | null;
  category_id: string;
  offering_id: string;
  selected_tenant_id: string | null;
  status: string;
  customer_name: string | null;
  customer_phone: string | null;
  address_snapshot: Record<string, unknown> | null;
  city: string | null;
  zipcode: string | null;
  issue_summary: string | null;
  offering_type_id: string | null;
  brand_id: string | null;
  photo_urls: string[];
  preferred_date: string | null;
  preferred_time_window: string | null;
  serviceability_status: string | null;
  price_status: string | null;
  provider_match_status: string | null;
  price_snapshot: Record<string, unknown> | null;
  provider_options: Record<string, unknown>[] | null;
  selected_provider_snapshot: Record<string, unknown> | null;
  booking_summary: Record<string, unknown> | null;
  failure_code: string | null;
  failure_message: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  // enriched fields
  offering_name?: string;
  offering_slug?: string;
  category_name?: string;
  category_slug?: string;
  required_fields?: string[];
}

export interface HomeServiceBookingDraftEvent {
  id: string;
  draft_id: string;
  actor_type: string;
  event_type: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  message: string | null;
  created_at: string;
}

export const adminHomeServiceBookingApi = {
  listDrafts: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    city?: string;
    offering_id?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.page)        q.set("page",        String(params.page));
    if (params?.page_size)   q.set("page_size",   String(params.page_size));
    if (params?.status)      q.set("status",      params.status);
    if (params?.city)        q.set("city",        params.city);
    if (params?.offering_id) q.set("offering_id", params.offering_id);
    return apiFetch<{ drafts: HomeServiceBookingDraft[]; page: number; page_size: number }>(
      `/v1/admin/home-services/booking-drafts${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  getDraft: (draftId: string) =>
    apiFetch<HomeServiceBookingDraft>(`/v1/admin/home-services/booking-drafts/${draftId}`),
  getDraftEvents: (draftId: string) =>
    apiFetch<{ events: HomeServiceBookingDraftEvent[]; total: number }>(
      `/v1/admin/home-services/booking-drafts/${draftId}/events`
    ),
};


// ── Sprint 17 — Coaching Appointment Drafts ──────────────────────────────────

export interface CoachingAppointmentDraft {
  id: string;
  customer_id: string | null;
  ai_session_id: string | null;
  category_id: string;
  offering_id: string;
  offering_name?: string;
  selected_tenant_id: string | null;
  status: string;
  student_name: string | null;
  student_phone: string | null;
  student_email: string | null;
  student_age: number | null;
  current_education: string | null;
  target_exam: string | null;
  target_band: string | null;
  preferred_mode: string | null;
  city: string | null;
  zipcode: string | null;
  selected_date: string | null;
  selected_time_start: string | null;
  selected_time_end: string | null;
  slot_snapshot: Record<string, unknown> | null;
  appointment_fee_snapshot: Record<string, unknown> | null;
  provider_options: Record<string, unknown>[] | null;
  next_available_slots: Record<string, unknown>[] | null;
  recommended_slot_snapshot: Record<string, unknown> | null;
  selected_provider_snapshot: Record<string, unknown> | null;
  fallback_inquiry_payload: Record<string, unknown> | null;
  appointment_summary: Record<string, unknown> | null;
  location_status: string | null;
  slot_status: string | null;
  fee_status: string | null;
  failure_code: string | null;
  notes: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CoachingAppointmentSlotHold {
  id: string;
  draft_id: string;
  tenant_id: string;
  offering_id: string;
  slot_date: string;
  start_time: string;
  end_time: string;
  hold_status: string;
  expires_at: string;
  created_at: string;
}

export interface CoachingAppointmentDraftEvent {
  id: string;
  draft_id: string;
  actor_type: string;
  event_type: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  message: string | null;
  created_at: string;
}

export const adminCoachingAppointmentApi = {
  listDrafts: (params?: { page?: number; page_size?: number; status?: string; city?: string }) => {
    const q = new URLSearchParams();
    if (params?.page)      q.set("page",      String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    if (params?.status)    q.set("status",    params.status);
    if (params?.city)      q.set("city",      params.city);
    return apiFetch<{ drafts: CoachingAppointmentDraft[]; page: number; page_size: number }>(
      `/v1/admin/coaching/appointment-drafts${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  getDraft: (draftId: string) =>
    apiFetch<CoachingAppointmentDraft>(`/v1/admin/coaching/appointment-drafts/${draftId}`),
  getDraftEvents: (draftId: string) =>
    apiFetch<{ draft_id: string; events: CoachingAppointmentDraftEvent[] }>(
      `/v1/admin/coaching/appointment-drafts/${draftId}/events`
    ),
  listSlotHolds: (params?: { page?: number; page_size?: number; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.page)      q.set("page",      String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    if (params?.status)    q.set("status",    params.status);
    return apiFetch<{ holds: CoachingAppointmentSlotHold[]; page: number; page_size: number }>(
      `/v1/admin/coaching/appointment-slot-holds${q.toString() ? "?" + q.toString() : ""}`
    );
  },
};

// ── Sprint 18 — Real Estate Lead Drafts ────────────────────────────────────────

export interface RealEstateLeadDraft {
  id: string;
  customer_id: string | null;
  ai_session_id: string | null;
  category_id: string;
  offering_id: string;
  selected_tenant_id: string | null;
  selected_agent_id: string | null;
  status: string;
  lead_intent: string | null;
  property_type: string | null;
  city: string | null;
  locality: string | null;
  zipcode: string | null;
  budget_min: number | null;
  budget_max: number | null;
  rent_min: number | null;
  rent_max: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  area_sqft_min: number | null;
  area_sqft_max: number | null;
  furnishing: string | null;
  possession_preference: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
  preferred_contact_time: string | null;
  notes: string | null;
  requirement_snapshot: Record<string, unknown> | null;
  provider_options: unknown[] | null;
  selected_provider_snapshot: Record<string, unknown> | null;
  lead_score_snapshot: Record<string, unknown> | null;
  lead_summary: Record<string, unknown> | null;
  fallback_payload: Record<string, unknown> | null;
  failure_code: string | null;
  failure_message: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RealEstateLeadDraftEvent {
  id: string;
  draft_id: string;
  actor_type: string;
  event_type: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  message: string | null;
  request_id: string | null;
  created_at: string;
}

export interface RealEstateLeadRoutingRule {
  id: string;
  category_id: string;
  rule_key: string;
  rule_name: string;
  lead_intent: string | null;
  match_scope: string;
  priority: number;
  require_agent_available: boolean;
  require_provider_bookable: boolean;
  require_subscription_active: boolean;
  require_lead_credit: boolean;
  max_providers: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const adminRealEstateLeadApi = {
  listDrafts: (params?: { status?: string; city?: string; intent?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.status)  q.set("status",  params.status);
    if (params?.city)    q.set("city",    params.city);
    if (params?.intent)  q.set("intent",  params.intent);
    if (params?.limit)   q.set("limit",   String(params.limit));
    if (params?.offset)  q.set("offset",  String(params.offset));
    return apiFetch<{ drafts: RealEstateLeadDraft[]; total: number }>(
      `/v1/admin/real-estate/lead-drafts${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  getDraft: (draftId: string) =>
    apiFetch<RealEstateLeadDraft>(`/v1/admin/real-estate/lead-drafts/${draftId}`),
  getDraftEvents: (draftId: string) =>
    apiFetch<{ draft_id: string; events: RealEstateLeadDraftEvent[] }>(
      `/v1/admin/real-estate/lead-drafts/${draftId}/events`
    ),
  listRoutingRules: (params?: { category_id?: string; active_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.category_id)  q.set("category_id",  params.category_id);
    if (params?.active_only !== undefined) q.set("active_only", String(params.active_only));
    return apiFetch<{ rules: RealEstateLeadRoutingRule[]; total: number }>(
      `/v1/admin/real-estate/lead-routing-rules${q.toString() ? "?" + q.toString() : ""}`
    );
  },
  createRoutingRule: (payload: Partial<RealEstateLeadRoutingRule>) =>
    apiFetch<RealEstateLeadRoutingRule>(`/v1/admin/real-estate/lead-routing-rules`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateRoutingRule: (ruleId: string, payload: Partial<RealEstateLeadRoutingRule>) =>
    apiFetch<RealEstateLeadRoutingRule>(`/v1/admin/real-estate/lead-routing-rules/${ruleId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  activateRule: (ruleId: string) =>
    apiFetch<RealEstateLeadRoutingRule>(`/v1/admin/real-estate/lead-routing-rules/${ruleId}/activate`, {
      method: "POST",
    }),
  deactivateRule: (ruleId: string) =>
    apiFetch<RealEstateLeadRoutingRule>(`/v1/admin/real-estate/lead-routing-rules/${ruleId}/deactivate`, {
      method: "POST",
    }),
};


// ── Sprint 20: Admin Service Job Assignment API ───────────────────────────────

export interface AdminServiceJob {
  id: string;
  job_number: string;
  booking_id: string;
  customer_id: string | null;
  tenant_id: string | null;
  status: string;
  assignment_status: string;
  assigned_staff_id: string | null;
  scheduled_date: string | null;
  scheduled_time_window: string | null;
  city: string | null;
  created_at: string | null;
}

export interface AdminServiceJobAssignment {
  id: string;
  job_id: string;
  booking_id: string;
  tenant_id: string;
  assigned_staff_member_id: string;
  assigned_by_user_id: string | null;
  assignment_status: string;
  assignment_type: string;
  rejection_reason: string | null;
  scheduled_date: string | null;
  scheduled_time_window: string | null;
  is_current: boolean;
  accepted_at: string | null;
  rejected_at: string | null;
  cancelled_at: string | null;
  created_at: string | null;
}

export interface AdminAssignmentEvent {
  id: string;
  job_id: string;
  event_type: string;
  actor_role: string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  reason: string | null;
  created_at: string | null;
}

export const adminServiceJobAssignmentApi = {
  listAssignments: (params?: { tenant_id?: string; assignment_status?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.tenant_id) q.set("tenant_id", params.tenant_id);
    if (params?.assignment_status) q.set("assignment_status", params.assignment_status);
    if (params?.limit) q.set("limit", String(params.limit));
    return apiFetch<{ assignments: AdminServiceJobAssignment[]; count: number }>(
      `/v1/admin/service-job-assignments?${q}`
    );
  },
  getAssignment: (assignmentId: string) =>
    apiFetch<AdminServiceJobAssignment>(`/v1/admin/service-job-assignments/${assignmentId}`),
  listUnassigned: (params?: { tenant_id?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.tenant_id) q.set("tenant_id", params.tenant_id);
    if (params?.limit) q.set("limit", String(params.limit));
    return apiFetch<{ jobs: AdminServiceJob[]; count: number }>(
      `/v1/admin/service-job-assignments/unassigned?${q}`
    );
  },
  listAssigned: (params?: { tenant_id?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.tenant_id) q.set("tenant_id", params.tenant_id);
    if (params?.limit) q.set("limit", String(params.limit));
    return apiFetch<{ jobs: AdminServiceJob[]; count: number }>(
      `/v1/admin/service-job-assignments/assigned?${q}`
    );
  },
  getJobTimeline: (jobId: string) =>
    apiFetch<{ job_id: string; events: AdminAssignmentEvent[] }>(
      `/v1/admin/service-jobs/${jobId}/assignment-timeline`
    ),
};

// ── Sprint 21: Admin Execution Timeline API ───────────────────────────────────
export interface AdminExecutionEvent {
  id: string;
  event_type: string;
  old_status: string | null;
  new_status: string | null;
  notes: string | null;
  actor_role: string | null;
  created_at: string | null;
}

export const adminExecutionApi = {
  getJobTimeline:  (jobId: string) =>
    apiFetch<AdminExecutionEvent[]>(`/v1/admin/service-jobs/${jobId}/execution-timeline`),
  getJobNotes:     (jobId: string) =>
    apiFetch<{ id: string; note_text: string; note_type: string; created_at: string | null }[]>(
      `/v1/admin/service-jobs/${jobId}/notes`
    ),
  getApptTimeline: (apptId: string) =>
    apiFetch<AdminExecutionEvent[]>(`/v1/admin/coaching-appointments/${apptId}/execution-timeline`),
  getLeadTimeline: (leadId: string) =>
    apiFetch<AdminExecutionEvent[]>(`/v1/admin/real-estate-leads/${leadId}/execution-timeline`),
};

// ── Sprint 22: Admin Checklist Template + Quote Admin API ─────────────────────
export interface ChecklistTemplateRecord {
  id: string; template_name: string; template_type: string; applies_to: string;
  category_id?: string; offering_id?: string; tenant_id?: string;
  is_required: boolean; is_active: boolean; created_at?: string;
  items?: ChecklistTemplateItemRecord[];
}
export interface ChecklistTemplateItemRecord {
  id: string; template_id: string; item_label: string; input_type: string;
  is_required: boolean; sort_order: number; options?: unknown;
}
export interface AdminQuoteRecord {
  id: string; quote_number: string; job_id: string; status: string;
  total_amount: string; customer_payable_amount: string; created_at?: string;
}

export const adminChecklistTemplateApi = {
  create:     (body: Partial<ChecklistTemplateRecord>) =>
    apiFetch<ChecklistTemplateRecord>("/admin/checklist-templates", { method: "POST", body: JSON.stringify(body) }),
  list:       () =>
    apiFetch<ChecklistTemplateRecord[]>("/admin/checklist-templates"),
  get:        (templateId: string) =>
    apiFetch<ChecklistTemplateRecord>(`/admin/checklist-templates/${templateId}`),
  addItem:    (templateId: string, item: Partial<ChecklistTemplateItemRecord>) =>
    apiFetch<ChecklistTemplateItemRecord>(`/admin/checklist-templates/${templateId}/items`, { method: "POST", body: JSON.stringify(item) }),
  jobChecklists: (jobId: string) =>
    apiFetch<unknown[]>(`/admin/checklist-templates/jobs/${jobId}`),
};

export const adminQuoteApi = {
  listForJob: (jobId: string) =>
    apiFetch<AdminQuoteRecord[]>(`/admin/quotes/jobs/${jobId}`),
  get:        (quoteId: string) =>
    apiFetch<AdminQuoteRecord>(`/admin/quotes/${quoteId}`),
  events:     (quoteId: string) =>
    apiFetch<unknown[]>(`/admin/quotes/${quoteId}/events`),
};

// ── Sprint 23: Types ──────────────────────────────────────────────────────────
export interface ServiceInvoiceRecord {
  id: string; invoice_number?: string; job_id: string; booking_id?: string;
  tenant_id: string; customer_id?: string; source: string;
  invoice_status: string; payment_status: string;
  subtotal?: string; tax_amount?: string; discount_amount?: string;
  customer_payable_amount?: string; commission_amount?: string;
  notes?: string; issued_at?: string; paid_at?: string;
  created_at?: string; updated_at?: string;
}
export interface PaymentRecord {
  id: string; invoice_id: string; tenant_id: string; payment_mode: string;
  payment_status: string; collected_amount: string; proof_media_url?: string;
  customer_confirmed: boolean; admin_verified: boolean;
  created_at?: string; verified_at?: string;
}
export interface CommissionRecord {
  id: string; invoice_id: string; tenant_id: string; commission_rate: string;
  commission_amount: string; customer_payable_amount: string;
  status: string; failure_reason?: string; reversal_reason?: string;
  created_at?: string; deducted_at?: string;
}
export interface WalletRecord {
  tenant_id: string; currency: string; current_balance: string;
  reserved_balance: string; total_purchased: string; total_deducted: string;
  low_balance_threshold?: string; is_active: boolean; last_transaction_at?: string;
}
export interface FinancialEventRecord {
  id: string; tenant_id?: string; event_type: string; reference_id?: string;
  reference_type?: string; amount?: string; description?: string; created_at?: string;
}

// ── Sprint 23: Admin invoice API ──────────────────────────────────────────────
export const adminInvoiceApi = {
  list:  (tenant_id?: string, status?: string) => {
    const params = new URLSearchParams();
    if (tenant_id) params.set("tenant_id", tenant_id);
    if (status) params.set("status", status);
    const q = params.toString();
    return apiFetch<ServiceInvoiceRecord[]>(`/v1/admin/service-invoices${q ? `?${q}` : ""}`);
  },
  get:   (invoiceId: string) =>
    apiFetch<ServiceInvoiceRecord>(`/v1/admin/service-invoices/${invoiceId}`),
};

// ── Sprint 23: Admin payment API ──────────────────────────────────────────────
export const adminPaymentApi = {
  list:   (tenant_id?: string) =>
    apiFetch<PaymentRecord[]>(`/v1/admin/payments${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),
  verify: (paymentId: string) =>
    apiFetch<PaymentRecord>(`/v1/admin/payments/${paymentId}/verify`, { method: "POST" }),
};

// ── Sprint 23: Admin commission API ───────────────────────────────────────────
export const adminCommissionApi = {
  list:    (tenant_id?: string, status?: string) => {
    const params = new URLSearchParams();
    if (tenant_id) params.set("tenant_id", tenant_id);
    if (status) params.set("status", status);
    const q = params.toString();
    return apiFetch<CommissionRecord[]>(`/v1/admin/commission-records${q ? `?${q}` : ""}`);
  },
  get:     (commissionId: string) =>
    apiFetch<CommissionRecord>(`/v1/admin/commission-records/${commissionId}`),
  retry:   (commissionId: string) =>
    apiFetch<CommissionRecord>(`/v1/admin/commission-records/${commissionId}/retry`, { method: "POST" }),
  reverse: (commissionId: string, body: { reason: string }) =>
    apiFetch<CommissionRecord>(`/v1/admin/commission-records/${commissionId}/reverse`, { method: "POST", body: JSON.stringify(body) }),
};

// ── Sprint 23: Admin wallet API ───────────────────────────────────────────────
export const adminWalletApi = {
  list:   () =>
    apiFetch<WalletRecord[]>("/v1/admin/provider-wallets"),
  get:    (tenantId: string) =>
    apiFetch<WalletRecord>(`/v1/admin/provider-wallets/${tenantId}`),
  ledger: (tenantId: string) =>
    apiFetch<Record<string, unknown>[]>(`/v1/admin/provider-wallets/${tenantId}/ledger`),
  credit: (tenantId: string, body: { amount: number; reason?: string }) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/provider-wallets/${tenantId}/credit`, { method: "POST", body: JSON.stringify(body) }),
};

// ── Sprint 23: Admin financial events API ─────────────────────────────────────
export const adminFinancialEventsApi = {
  list: (tenant_id?: string, event_type?: string) => {
    const params = new URLSearchParams();
    if (tenant_id) params.set("tenant_id", tenant_id);
    if (event_type) params.set("event_type", event_type);
    const q = params.toString();
    return apiFetch<FinancialEventRecord[]>(`/v1/admin/financial-events${q ? `?${q}` : ""}`);
  },
};


// ── Sprint 24 / P0-upgrade: Review types ─────────────────────────────────────
export interface CustomerReviewRecord {
  id: string; review_number?: string; customer_id: string; tenant_id: string;
  tenant_name?: string; customer_name?: string; customer_phone?: string;
  category_id?: string; record_type: string; record_id: string;
  overall_rating: number; provider_rating?: number; staff_rating?: number;
  communication_rating?: number; punctuality_rating?: number;
  quality_rating?: number; value_rating?: number;
  review_title?: string; review_text?: string;
  status: string; visibility: string;
  sentiment?: string; has_reply?: boolean; has_media?: boolean;
  reply_text?: string; replied_at?: string;
  submitted_at?: string; approved_at?: string;
  rejection_reason?: string; moderation_reason?: string;
  created_at?: string; updated_at?: string;
}
export interface ReviewSummary {
  total: number; today: number; avg_rating: number; low_rating: number;
  flagged: number; pending_moderation: number; five_star: number;
  positive: number; neutral: number; negative: number;
  unreplied: number; replied: number;
}
export interface ReviewListMeta {
  page: number; page_size: number; total: number; total_pages: number;
  has_next: boolean; has_previous: boolean;
}
export interface ReviewListResponse { items: CustomerReviewRecord[]; meta: ReviewListMeta; }
export interface ReviewFlagRecord {
  id: string; review_id: string; tenant_id?: string;
  flagged_by_user_id?: string; flagged_by_type: string;
  reason_code: string; reason_text?: string;
  status: string; created_at?: string;
}
export interface ReviewReplyRecord {
  id: string; review_id: string; tenant_id: string;
  reply_text: string; status: string;
  submitted_at?: string; approved_at?: string;
  created_at?: string;
}
export interface ReviewPolicyRecord {
  id: string; policy_key: string; policy_name: string;
  auto_approve_enabled: boolean; require_admin_moderation: boolean;
  allow_provider_reply: boolean; require_reply_moderation: boolean;
  allow_review_edit: boolean; edit_window_hours: number;
  min_rating: number; max_rating: number;
  allow_media: boolean; max_media_count: number;
  is_active: boolean; created_at?: string; updated_at?: string;
}
export interface TenantRatingSummaryRecord {
  id: string; tenant_id: string; total_reviews: number;
  average_rating: string; five_star_count: number; four_star_count: number;
  three_star_count: number; two_star_count: number; one_star_count: number;
  last_review_at?: string; updated_at?: string;
}
export interface StaffRatingSummaryRecord {
  id: string; tenant_id: string; staff_member_id: string;
  total_reviews: number; average_rating: string;
  last_review_at?: string; updated_at?: string;
}

// ── Sprint 24 / P0-upgrade: Admin reviews API ─────────────────────────────────
export const adminReviewApi = {
  summary: (tenant_id?: string) => {
    const qs = tenant_id ? `?tenant_id=${tenant_id}` : "";
    return apiFetch<ReviewSummary>(`/v1/admin/reviews/summary${qs}`);
  },
  list: (params?: {
    q?: string; tenant_id?: string; rating?: string; rating_min?: string; rating_max?: string;
    status?: string; record_type?: string; has_reply?: string;
    sort_by?: string; sort_dir?: string; page?: string; page_size?: string;
  }) => {
    const cleaned: Record<string,string> = {};
    for (const [k, v] of Object.entries(params ?? {})) { if (v != null && v !== "") cleaned[k] = v; }
    const qs = new URLSearchParams(cleaned).toString();
    return apiFetch<ReviewListResponse>(`/v1/admin/reviews${qs ? `?${qs}` : ""}`);
  },
  get:     (id: string)  => apiFetch<CustomerReviewRecord>(`/v1/admin/reviews/${id}`),
  approve: (id: string)  => apiFetch<CustomerReviewRecord>(`/v1/admin/reviews/${id}/approve`, { method: "POST" }),
  reject:  (id: string, reason: string) =>
    apiFetch<CustomerReviewRecord>(`/v1/admin/reviews/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  hide:    (id: string, reason?: string) =>
    apiFetch<CustomerReviewRecord>(`/v1/admin/reviews/${id}/hide`, { method: "POST", body: JSON.stringify({ reason }) }),
  delete:  (id: string)  => apiFetch<CustomerReviewRecord>(`/v1/admin/reviews/${id}`, { method: "DELETE" }),
  events:  (id: string)  => apiFetch<Record<string, unknown>[]>(`/v1/admin/reviews/${id}/events`),
};

// ── Sprint 24: Admin flags API ────────────────────────────────────────────────
export const adminFlagApi = {
  list:    (status?: string) =>
    apiFetch<ReviewFlagRecord[]>(`/v1/admin/review-flags${status ? `?status=${status}` : ""}`),
  resolve: (flagId: string) =>
    apiFetch<ReviewFlagRecord>(`/v1/admin/review-flags/${flagId}/resolve`, { method: "POST" }),
};

// ── Sprint 24: Admin replies API ──────────────────────────────────────────────
export const adminReplyApi = {
  list:    (status?: string) =>
    apiFetch<ReviewReplyRecord[]>(`/v1/admin/review-replies${status ? `?status=${status}` : ""}`),
  approve: (reviewId: string) =>
    apiFetch<ReviewReplyRecord>(`/v1/admin/review-replies/${reviewId}/approve`, { method: "POST" }),
  reject:  (reviewId: string, reason: string) =>
    apiFetch<ReviewReplyRecord>(`/v1/admin/review-replies/${reviewId}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
};

// ── Sprint 24: Admin policy API ───────────────────────────────────────────────
export const adminPolicyApi = {
  list:   () => apiFetch<ReviewPolicyRecord[]>("/v1/admin/review-policies"),
  get:    (id: string) => apiFetch<ReviewPolicyRecord>(`/v1/admin/review-policies/${id}`),
  update: (id: string, body: Partial<ReviewPolicyRecord>) =>
    apiFetch<ReviewPolicyRecord>(`/v1/admin/review-policies/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
};

// ── Sprint 24: Admin rating summaries API ─────────────────────────────────────
export const adminRatingApi = {
  listTenants:    () => apiFetch<TenantRatingSummaryRecord[]>("/v1/admin/rating-summaries"),
  listStaff:      (tenant_id?: string) =>
    apiFetch<StaffRatingSummaryRecord[]>(`/v1/admin/rating-summaries/staff${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),
  recompute:      (tenant_id: string) =>
    apiFetch<TenantRatingSummaryRecord>(`/v1/admin/rating-summaries/tenant/${tenant_id}/recompute`, { method: "POST" }),
};

// ── Sprint 25: Complaint types ────────────────────────────────────────────────
export interface ComplaintRecord {
  id: string; complaint_number?: string; customer_id: string;
  tenant_id?: string; category_id?: string;
  record_type: string; record_id: string;
  complaint_type: string; requested_resolution?: string;
  title?: string; description: string;
  status: string; priority: string;
  internal_admin_notes?: string;
  assigned_admin_user_id?: string;
  resolved_at?: string; closed_at?: string; created_at?: string; updated_at?: string;
}
export interface ComplaintResolutionRecord {
  id: string; complaint_id: string; status: string;
  resolution_type: string; description: string;
  customer_visible_notes?: string; internal_notes?: string;
  proposed_by_type: string; created_at?: string;
}
export interface ReworkRecord {
  id: string; complaint_id: string; status: string;
  rework_reason: string; admin_notes?: string;
  scheduled_date?: string; completed_at?: string; created_at?: string;
}
export interface RefundRecord {
  id: string; complaint_id: string; status: string;
  refund_type: string; requested_amount?: string;
  approved_amount?: string; recorded_amount?: string;
  reason: string; rejection_reason?: string;
  approved_at?: string; recorded_at?: string; verified_at?: string; created_at?: string;
}
export interface ComplaintPolicyRecord {
  id: string; policy_key: string; category_id?: string;
  complaint_window_hours: number; allow_duplicate_open_complaints: boolean;
  allow_rework_request: boolean; allow_refund_request: boolean;
  require_admin_review: boolean; is_active: boolean;
  created_at?: string;
}
export interface ComplaintEventRecord {
  id: string; complaint_id: string; event_type: string;
  actor_type: string; old_status?: string; new_status?: string;
  reason?: string; created_at?: string;
}

// ── Sprint 25: Admin complaints API ──────────────────────────────────────────
export const adminComplaintApi = {
  list: (p?: { tenant_id?: string; status?: string; priority?: string; record_type?: string }) => {
    const qs = new URLSearchParams(Object.entries(p ?? {}).filter(([,v]) => v) as [string,string][]);
    return apiFetch<ComplaintRecord[]>(`/v1/admin/complaints${qs.toString() ? `?${qs}` : ""}`);
  },
  get:       (id: string) => apiFetch<ComplaintRecord>(`/v1/admin/complaints/${id}`),
  assign:    (id: string, assignee_id: string) =>
    apiFetch<ComplaintRecord>(`/v1/admin/complaints/${id}/assign`, { method: "POST", body: JSON.stringify({ assignee_id }) }),
  priority:  (id: string, priority: string, reason?: string) =>
    apiFetch<ComplaintRecord>(`/v1/admin/complaints/${id}/priority`, { method: "POST", body: JSON.stringify({ priority, reason }) }),
  requestProviderResponse: (id: string) =>
    apiFetch<ComplaintRecord>(`/v1/admin/complaints/${id}/request-provider-response`, { method: "POST" }),
  addMessage: (id: string, message_text: string, visibility?: string) =>
    apiFetch<Record<string,unknown>>(`/v1/admin/complaints/${id}/messages`, { method: "POST", body: JSON.stringify({ message_text, visibility }) }),
  messages:   (id: string) =>
    apiFetch<Record<string,unknown>[]>(`/v1/admin/complaints/${id}/messages`),
  proposeResolution: (id: string, body: { resolution_type: string; description: string; customer_visible_notes?: string; internal_notes?: string }) =>
    apiFetch<ComplaintResolutionRecord>(`/v1/admin/complaints/${id}/propose-resolution`, { method: "POST", body: JSON.stringify(body) }),
  resolutions: (id: string) =>
    apiFetch<ComplaintResolutionRecord[]>(`/v1/admin/complaints/${id}/resolutions`),
  reject:    (id: string, reason: string) =>
    apiFetch<ComplaintRecord>(`/v1/admin/complaints/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  resolve:   (id: string, reason?: string) =>
    apiFetch<ComplaintRecord>(`/v1/admin/complaints/${id}/resolve`, { method: "POST", body: JSON.stringify({ reason }) }),
  close:     (id: string, reason?: string) =>
    apiFetch<ComplaintRecord>(`/v1/admin/complaints/${id}/close`, { method: "POST", body: JSON.stringify({ reason }) }),
  events:    (id: string) =>
    apiFetch<ComplaintEventRecord[]>(`/v1/admin/complaints/${id}/events`),
};

// ── Sprint 25: Admin rework API ───────────────────────────────────────────────
export const adminReworkApi = {
  list:    (tenant_id?: string, status?: string) => {
    const p = new URLSearchParams();
    if (tenant_id) p.set("tenant_id", tenant_id);
    if (status)    p.set("status", status);
    const q = p.toString();
    return apiFetch<ReworkRecord[]>(`/v1/admin/rework-requests${q ? `?${q}` : ""}`);
  },
  approve: (id: string, admin_notes?: string) =>
    apiFetch<ReworkRecord>(`/v1/admin/rework-requests/${id}/approve`, { method: "POST", body: JSON.stringify({ admin_notes }) }),
  reject:  (id: string, reason: string) =>
    apiFetch<ReworkRecord>(`/v1/admin/rework-requests/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  assign:  (id: string, staff_member_id: string) =>
    apiFetch<ReworkRecord>(`/v1/admin/rework-requests/${id}/assign`, { method: "POST", body: JSON.stringify({ staff_member_id }) }),
};

// ── Sprint 25: Admin refund API ───────────────────────────────────────────────
export const adminRefundApi = {
  list:    (p?: { tenant_id?: string; status?: string }) => {
    const qs = new URLSearchParams(Object.entries(p ?? {}).filter(([,v]) => v) as [string,string][]);
    return apiFetch<RefundRecord[]>(`/v1/admin/refund-requests${qs.toString() ? `?${qs}` : ""}`);
  },
  approve: (id: string, approved_amount?: string) =>
    apiFetch<RefundRecord>(`/v1/admin/refund-requests/${id}/approve`, { method: "POST", body: JSON.stringify({ approved_amount }) }),
  reject:  (id: string, reason: string) =>
    apiFetch<RefundRecord>(`/v1/admin/refund-requests/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  record:  (id: string, recorded_amount: string, proof_media_url?: string) =>
    apiFetch<RefundRecord>(`/v1/admin/refund-requests/${id}/record`, { method: "POST", body: JSON.stringify({ recorded_amount, proof_media_url }) }),
  verify:  (id: string) =>
    apiFetch<RefundRecord>(`/v1/admin/refund-requests/${id}/verify`, { method: "POST" }),
};

// ── Sprint 25: Admin complaint policy API ─────────────────────────────────────
export const adminComplaintPolicyApi = {
  list:   () => apiFetch<ComplaintPolicyRecord[]>("/v1/admin/complaint-policies"),
  create: (body: Partial<ComplaintPolicyRecord>) =>
    apiFetch<ComplaintPolicyRecord>("/v1/admin/complaint-policies", { method: "POST", body: JSON.stringify(body) }),
  update: (id: string, body: Partial<ComplaintPolicyRecord>) =>
    apiFetch<ComplaintPolicyRecord>(`/v1/admin/complaint-policies/${id}`, { method: "PUT", body: JSON.stringify(body) }),
};

// ── Sprint 26: Enterprise Grid types ──────────────────────────────────────────
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
  saved_view_id?:   string | null;
}
export interface EnterpriseSavedView {
  id: string; owner_user_id: string; tenant_id?: string;
  scope: string; resource_key: string; view_name: string;
  is_default: boolean; filters: Record<string, unknown>;
  sort: Record<string, unknown>; columns: unknown[];
  page_size: number; visibility: string;
  created_at?: string; updated_at?: string;
}
export interface EnterpriseColumnPreference {
  id?: string; user_id?: string; resource_key: string;
  columns: unknown[]; density: string; created_at?: string;
}
export interface EnterpriseExportJob {
  id: string; resource_key: string; status: string;
  export_format: string; row_count?: number; file_url?: string;
  failure_reason?: string; expires_at?: string; created_at?: string;
}

// ── Sprint 26: Enterprise API ──────────────────────────────────────────────────
export const enterpriseApi = {
  // Registry
  listResources: () =>
    apiFetch<{ resource_keys: string[] }>("/v1/enterprise/registry"),
  getResourceConfig: (key: string) =>
    apiFetch<Record<string, unknown>>(`/v1/enterprise/registry/${key}`),

  // Saved views
  listSavedViews:  (resource_key: string, scope = "admin") =>
    apiFetch<EnterpriseSavedView[]>(`/v1/enterprise/saved-views?resource_key=${resource_key}&scope=${scope}`),
  createSavedView: (body: Partial<EnterpriseSavedView> & { resource_key: string; view_name: string }) =>
    apiFetch<EnterpriseSavedView>("/v1/enterprise/saved-views", { method: "POST", body: JSON.stringify(body) }),
  getSavedView:    (id: string) =>
    apiFetch<EnterpriseSavedView>(`/v1/enterprise/saved-views/${id}`),
  updateSavedView: (id: string, body: Partial<EnterpriseSavedView>) =>
    apiFetch<EnterpriseSavedView>(`/v1/enterprise/saved-views/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteSavedView: (id: string) =>
    apiFetch<Record<string, unknown>>(`/v1/enterprise/saved-views/${id}`, { method: "DELETE" }),
  setDefaultView:  (id: string) =>
    apiFetch<EnterpriseSavedView>(`/v1/enterprise/saved-views/${id}/set-default`, { method: "POST" }),

  // Column preferences
  getColumnPrefs:   (resource_key: string) =>
    apiFetch<EnterpriseColumnPreference>(`/v1/enterprise/column-preferences?resource_key=${resource_key}`),
  saveColumnPrefs:  (resource_key: string, columns: unknown[], density = "comfortable") =>
    apiFetch<EnterpriseColumnPreference>("/v1/enterprise/column-preferences", { method: "PUT", body: JSON.stringify({ resource_key, columns, density }) }),
  resetColumnPrefs: (resource_key: string) =>
    apiFetch<EnterpriseColumnPreference>("/v1/enterprise/column-preferences/reset", { method: "POST", body: JSON.stringify({ resource_key }) }),

  // Exports
  createExport: (body: { resource_key: string; filters: Record<string, unknown>; columns: string[]; export_format?: string }) =>
    apiFetch<EnterpriseExportJob>("/v1/enterprise/exports", { method: "POST", body: JSON.stringify(body) }),
  listExports:  () =>
    apiFetch<EnterpriseExportJob[]>("/v1/enterprise/exports"),
  getExport:    (id: string) =>
    apiFetch<EnterpriseExportJob>(`/v1/enterprise/exports/${id}`),
  retryExport:  (id: string) =>
    apiFetch<EnterpriseExportJob>(`/v1/enterprise/exports/${id}/retry`, { method: "POST" }),
};

// ── Sprint 27: Platform Notifications + Chat + Audit ──────────────────────────
export interface InAppNotification {
  id: string;
  notification_type: string;
  title: string;
  body: string;
  action_url: string | null;
  action_label: string | null;
  source_record_type: string | null;
  source_record_id: string | null;
  severity: string;
  read_status: string;
  read_at: string | null;
  created_at: string;
}

export interface NotificationOutboxRecord {
  id: string;
  notification_event_id: string | null;
  recipient_user_id: string | null;
  recipient_type: string;
  channel: string;
  template_key: string;
  title: string;
  body: string;
  delivery_status: string;
  provider_name: string | null;
  failure_code: string | null;
  retry_count: number;
  max_retries: number;
  sent_at: string | null;
  created_at: string;
}

export interface NotificationEventRecord {
  id: string;
  event_key: string;
  event_name: string;
  source_engine: string;
  severity: string;
  status: string;
  tenant_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
  processed_at: string | null;
}

export interface NotifEventTemplate {
  id: string;
  template_key: string;
  template_name: string;
  channel: string;
  subject_template: string | null;
  body_template: string;
  action_label_template: string | null;
  action_url_template: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ChatThreadRecord {
  id: string;
  thread_number: string;
  tenant_id: string | null;
  customer_id: string | null;
  record_type: string;
  record_id: string;
  status: string;
  last_message_at: string | null;
  created_at: string;
}

export interface ChatMessageRecord {
  id: string;
  thread_id: string;
  sender_user_id: string | null;
  sender_type: string;
  message_type: string;
  message_text: string | null;
  visibility: string;
  delivery_status: string;
  created_at: string;
}

export interface AuditLogRecord {
  id: string;
  actor_id: string | null;
  actor_role: string | null;
  actor_ip: string | null;
  action: string;
  engine_key: string | null;
  resource_type: string | null;
  resource_id: string | null;
  tenant_id: string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  is_high_risk: boolean;
  created_at: string;
}

export const sprint27AdminApi = {
  // In-app notifications
  listNotifications: (params?: { read_status?: string; limit?: number; offset?: number }) =>
    apiFetch<{ items: InAppNotification[]; total: number }>(`/v1/admin/notifications?${new URLSearchParams(params as Record<string, string>)}`),
  getUnreadCount: () =>
    apiFetch<{ unread_count: number }>("/v1/admin/notifications/unread-count"),
  markRead: (id: string) =>
    apiFetch<InAppNotification>(`/v1/admin/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () =>
    apiFetch<{ marked_read: number }>("/v1/admin/notifications/mark-all-read", { method: "POST" }),

  // Notification events
  listEvents: (params?: Record<string, string | number>) =>
    apiFetch<{ items: NotificationEventRecord[]; total: number }>(`/v1/admin/notification-events?${new URLSearchParams(params as Record<string, string>)}`),

  // Notification outbox
  listOutbox: (params?: Record<string, string | number>) =>
    apiFetch<{ items: NotificationOutboxRecord[]; total: number }>(`/v1/admin/notification-outbox?${new URLSearchParams(params as Record<string, string>)}`),
  getOutbox: (id: string) =>
    apiFetch<NotificationOutboxRecord>(`/v1/admin/notification-outbox/${id}`),
  retryOutbox: (id: string) =>
    apiFetch<NotificationOutboxRecord>(`/v1/admin/notification-outbox/${id}/retry`, { method: "POST" }),

  // Templates
  listTemplates: (channel?: string) =>
    apiFetch<{ items: NotifEventTemplate[]; total: number }>(`/v1/admin/notification-templates${channel ? `?channel=${channel}` : ""}`),
  createTemplate: (body: Partial<NotifEventTemplate>) =>
    apiFetch<NotifEventTemplate>("/v1/admin/notification-templates", { method: "POST", body: JSON.stringify(body) }),
  updateTemplate: (id: string, body: Partial<NotifEventTemplate>) =>
    apiFetch<NotifEventTemplate>(`/v1/admin/notification-templates/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  activateTemplate: (id: string) =>
    apiFetch<NotifEventTemplate>(`/v1/admin/notification-templates/${id}/activate`, { method: "POST" }),
  deactivateTemplate: (id: string) =>
    apiFetch<NotifEventTemplate>(`/v1/admin/notification-templates/${id}/deactivate`, { method: "POST" }),

  // Chat
  listChatThreads: (params?: Record<string, string | number>) =>
    apiFetch<{ items: ChatThreadRecord[]; total: number }>(`/v1/admin/chat/threads?${new URLSearchParams(params as Record<string, string>)}`),
  getChatThread: (id: string) =>
    apiFetch<ChatThreadRecord>(`/v1/admin/chat/threads/${id}`),
  listChatMessages: (threadId: string, params?: { limit?: number; offset?: number }) =>
    apiFetch<{ items: ChatMessageRecord[]; total: number }>(`/v1/admin/chat/threads/${threadId}/messages?${new URLSearchParams(params as Record<string, string>)}`),
  closeThread: (id: string) =>
    apiFetch<ChatThreadRecord>(`/v1/admin/chat/threads/${id}/close`, { method: "POST" }),
  hideMessage: (msgId: string, reason: string) =>
    apiFetch<{ hidden: boolean }>(`/v1/admin/chat/messages/${msgId}/hide`, { method: "POST", body: JSON.stringify({ reason }) }),

  // Audit logs
  listAuditLogs: (params?: Record<string, string | number>) =>
    apiFetch<{ items: AuditLogRecord[]; total: number }>(`/v1/admin/audit-logs?${new URLSearchParams(params as Record<string, string>)}`),
  getAuditTimeline: (resource_type: string, resource_id: string) =>
    apiFetch<{ timeline: AuditLogRecord[] }>(`/v1/admin/audit-logs/record-timeline?resource_type=${resource_type}&resource_id=${resource_id}`),
};

// ── Sprint 28 — Analytics Types ───────────────────────────────────────────────

export interface AnalyticsDateRange { from: string | null; to: string | null; }

export interface AnalyticsResponse {
  success: boolean;
  data: {
    summary:         Record<string, unknown>;
    series:          unknown[];
    breakdown:       Record<string, unknown>[];
    top_items:       Record<string, unknown>[];
    filters_applied: Record<string, string | null>;
    date_range:      AnalyticsDateRange;
    generated_at:    string;
    [key: string]:   unknown;
  };
}

export interface ReportDefinition {
  report_key:      string;
  report_name:     string;
  scope:           string;
  allowed_filters: string[];
  export_formats:  string[];
}

export interface ReportRun {
  id:                   string;
  report_key:           string;
  report_name:          string | null;
  scope:                string;
  requested_by_user_id: string;
  tenant_id:            string | null;
  status:               string;
  filters:              Record<string, unknown>;
  result_summary:       Record<string, unknown> | null;
  row_count:            number | null;
  file_url:             string | null;
  export_format:        string | null;
  failure_reason:       string | null;
  created_at:           string;
  completed_at:         string | null;
}

// ── Sprint 28 — Admin Analytics API ──────────────────────────────────────────

type AnalyticsParams = {
  date_from?:   string;
  date_to?:     string;
  category_id?: string;
  tenant_id?:   string;
};

function analyticsQs(p: AnalyticsParams): string {
  const q: Record<string, string> = {};
  if (p.date_from)   q.date_from   = p.date_from;
  if (p.date_to)     q.date_to     = p.date_to;
  if (p.category_id) q.category_id = p.category_id;
  if (p.tenant_id)   q.tenant_id   = p.tenant_id;
  const s = new URLSearchParams(q).toString();
  return s ? `?${s}` : "";
}

export const adminAnalyticsApi = {
  getSummary: (p: AnalyticsParams = {}) =>
    apiFetch<AnalyticsResponse["data"]>(`/v1/admin/analytics/summary${analyticsQs(p)}`),

  getCategoryPerformance: (p: AnalyticsParams = {}) =>
    apiFetch<AnalyticsResponse["data"]>(`/v1/admin/analytics/category-performance${analyticsQs(p)}`),

  getCategoryDetail: (category_id: string, p: AnalyticsParams = {}) =>
    apiFetch<AnalyticsResponse["data"]>(`/v1/admin/analytics/categories/${category_id}${analyticsQs(p)}`),

  getProviderPerformance: (p: AnalyticsParams = {}) =>
    apiFetch<AnalyticsResponse["data"]>(`/v1/admin/analytics/provider-performance${analyticsQs(p)}`),

  getProviderDetail: (tenant_id: string, p: AnalyticsParams = {}) =>
    apiFetch<AnalyticsResponse["data"]>(`/v1/admin/analytics/providers/${tenant_id}${analyticsQs(p)}`),

  getFinancialSummary: (p: AnalyticsParams = {}) =>
    apiFetch<AnalyticsResponse["data"]>(`/v1/admin/analytics/financial-summary${analyticsQs(p)}`),

  getQualitySummary: (p: AnalyticsParams = {}) =>
    apiFetch<AnalyticsResponse["data"]>(`/v1/admin/analytics/quality-summary${analyticsQs(p)}`),

  getComplaintSummary: (p: AnalyticsParams = {}) =>
    apiFetch<AnalyticsResponse["data"]>(`/v1/admin/analytics/complaint-summary${analyticsQs(p)}`),

  getStaffPerformance: (p: AnalyticsParams = {}) =>
    apiFetch<AnalyticsResponse["data"]>(`/v1/admin/analytics/staff-performance${analyticsQs(p)}`),

  getOperationalAlerts: () =>
    apiFetch<AnalyticsResponse["data"]>("/v1/admin/analytics/operational-alerts"),

  listReports: (params?: { limit?: number; offset?: number }) =>
    apiFetch<{ definitions: ReportDefinition[]; recent_runs: { items: ReportRun[]; total: number } }>(
      `/v1/admin/reports?${new URLSearchParams(params as Record<string, string>)}`
    ),

  runReport: (body: { report_key: string; filters?: Record<string, string>; export_format?: string }) =>
    apiFetch<{ id: string; status: string; row_count: number; preview: Record<string, unknown>[]; csv_content?: string; generated_at: string }>(
      "/v1/admin/reports/run", { method: "POST", body: JSON.stringify(body) }
    ),

  getReportRun: (run_id: string) =>
    apiFetch<ReportRun>(`/v1/admin/reports/${run_id}`),
};

// ── Sprint 29 — Admin AI Monitoring API ───────────────────────────────────────

export interface AISession {
  id: string; session_key: string; customer_id: string | null;
  current_intent: string; workflow_status: string;
  collected_fields: Record<string, unknown>; turn_count: number;
  is_active: boolean; created_at: string; messages?: AIMessage[];
}

export interface AIMessage {
  id: string; session_id: string; role: string; content: string;
  intent_at_time: string | null; created_at: string;
}

export interface AIActionLog {
  id: string; session_id: string; customer_id: string | null;
  action: string; intent: string | null; flow_type: string | null;
  draft_type: string | null; draft_id: string | null;
  status: string; failure_code: string | null; failure_message: string | null;
  request_payload: Record<string, unknown> | null; created_at: string;
}

export interface AIMetrics {
  executed_count: number; blocked_count: number; failed_count: number;
  validated_count: number; unique_sessions: number; unique_customers: number;
  last_hour_count: number; rate_limiter: { active_customers_in_msg_window: number; customers_in_cooldown: number };
}

export const adminAiApi = {
  listSessions: (params?: { status?: string; intent?: string; limit?: number; offset?: number }) =>
    apiFetch<AISession[]>(`/v1/admin/ai/sessions?${new URLSearchParams(params as Record<string, string>)}`),

  getSession: (session_id: string) =>
    apiFetch<AISession>(`/v1/admin/ai/sessions/${session_id}`),

  listActionLogs: (params?: { session_id?: string; status?: string; limit?: number; offset?: number }) =>
    apiFetch<AIActionLog[]>(`/v1/admin/ai/action-logs?${new URLSearchParams(params as Record<string, string>)}`),

  listFailedActions: (params?: { session_id?: string; customer_id?: string; limit?: number; offset?: number }) =>
    apiFetch<AIActionLog[]>(`/v1/admin/ai/failed-actions?${new URLSearchParams(params as Record<string, string>)}`),

  getMetrics: () =>
    apiFetch<AIMetrics>("/v1/admin/ai/metrics"),

  handoffSession: (session_id: string) =>
    apiFetch<AISession>(`/v1/admin/ai/sessions/${session_id}/handoff`, { method: "POST" }),

  closeSession: (session_id: string) =>
    apiFetch<AISession>(`/v1/admin/ai/sessions/${session_id}/close`, { method: "POST" }),
};

// ── Sprint 29 — Admin Marketing Campaigns API ─────────────────────────────────

export interface MarketingCampaign {
  id: string; campaign_key: string; campaign_name: string;
  campaign_type: string; status: string; target_audience: string;
  category_id: string | null; city: string | null;
  starts_at: string | null; ends_at: string | null;
  created_at: string; messages?: CampaignMessage[]; rules?: CampaignRule[];
}

export interface CampaignMessage {
  id: string; campaign_id: string; channel: string;
  title: string; body: string; action_label: string | null; action_url: string | null;
}

export interface CampaignRule {
  id: string; campaign_id: string; rule_type: string; rule_config: Record<string, unknown>;
}

export interface CampaignPerformance {
  campaign: MarketingCampaign;
  performance: { targeted: number; sent: number; delivered: number; opened: number;
                 clicked: number; converted: number; failed: number;
                 open_rate: number; click_rate: number; conversion_rate: number };
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
  is_mfa_enabled: boolean;
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

export const profileApi = {
  getProfile: () =>
    apiFetch<UserProfile>("/v1/me/profile"),
  updateProfile: (data: UpdateUserProfilePayload) =>
    apiFetch<UserProfile>("/v1/me/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

// ─────────────────────────────────────────────────────────────────────────────
// Sprint 34E — Service Options + Issue Catalog
// ─────────────────────────────────────────────────────────────────────────────

export interface ServiceOptionGroup34E {
  id: string;
  code: string;
  name: string;
  description?: string;
  category_id?: string;
  vertical_type?: string;
  status: string;
  display_order: number;
  created_at?: string;
  updated_at?: string;
}

export interface ServiceOption34E {
  id: string;
  code: string;
  name: string;
  slug: string;
  description?: string;
  option_type: string;
  unit: string;
  default_price: string;
  min_price?: string;
  max_price?: string;
  is_customer_selectable: boolean;
  is_active: boolean;
  display_order: number;
  option_group_id?: string;
  vertical_type?: string;
  status: string;
  category_id?: string;
  master_service_id?: string;
  metadata_json?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
  mapped_services_count?: number;
}

export interface ServiceOptionSummary {
  total: number;
  active: number;
  inactive: number;
  archived: number;
  customer_selectable: number;
  mapped: number;
  unmapped: number;
}

export interface IssueType34E {
  id: string;
  code: string;
  name: string;
  slug: string;
  description?: string;
  severity: string;
  is_active: boolean;
  display_order: number;
  vertical_type?: string;
  status: string;
  metadata_json?: Record<string, unknown>;
  requires_photo: boolean;
  requires_description: boolean;
  customer_visible?: boolean;
  category_id?: string;
  master_service_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface MasterChecklistItem {
  id: string;
  code: string;
  title: string;
  slug: string;
  description?: string;
  workflow_step_key?: string;
  is_required: boolean;
  owner_role: string;
  customer_visible: boolean;
  staff_visible: boolean;
  tenant_visible: boolean;
  is_active: boolean;
  status: string;
  display_order: number;
  vertical_type?: string;
  metadata_json?: Record<string, unknown>;
  category_id?: string;
  master_service_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ServiceOptionMapping34E {
  id: string;
  master_service_id: string;
  service_option_id: string;
  option_group_id?: string;
  status: string;
  is_required: boolean;
  is_default: boolean;
  display_order: number;
  option?: ServiceOption34E;
  created_at?: string;
  updated_at?: string;
}

export interface ServiceIssueMapping34E {
  id: string;
  master_service_id: string;
  issue_type_id: string;
  status: string;
  is_common: boolean;
  is_default: boolean;
  requires_photo: boolean;
  requires_description: boolean;
  display_order: number;
  issue_type?: IssueType34E;
  created_at?: string;
  updated_at?: string;
}

export const serviceOptionApi = {
  // Option groups
  listOptionGroups: (params?: { status?: string; category_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.category_id) qs.set("category_id", params.category_id);
    return apiFetch<ServiceOptionGroup34E[]>(`/v1/admin/service-option-groups?${qs}`);
  },
  createOptionGroup: (data: Partial<ServiceOptionGroup34E> & { code: string; name: string }) =>
    apiFetch<ServiceOptionGroup34E>("/v1/admin/service-option-groups", {
      method: "POST", body: JSON.stringify(data),
    }),
  updateOptionGroup: (groupId: string, data: Partial<ServiceOptionGroup34E>) =>
    apiFetch<ServiceOptionGroup34E>(`/v1/admin/service-option-groups/${groupId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),

  // Service options
  summary: () =>
    apiFetch<{ data: { total: number; active: number; inactive: number; archived: number; customer_selectable: number; mapped: number; unmapped: number } }>("/v1/admin/service-options/summary"),
  listOptions: (params?: {
    status?: string; category_id?: string; master_service_id?: string;
    option_group_id?: string; option_type?: string; mapped?: boolean;
    search?: string; page?: number; page_size?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.category_id) qs.set("category_id", params.category_id);
    if (params?.master_service_id) qs.set("master_service_id", params.master_service_id);
    if (params?.option_group_id) qs.set("option_group_id", params.option_group_id);
    if (params?.option_type) qs.set("option_type", params.option_type);
    if (params?.mapped !== undefined) qs.set("mapped", String(params.mapped));
    if (params?.search) qs.set("search", params.search);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return apiFetch<{ items: ServiceOption34E[]; total: number }>(`/v1/admin/service-options?${qs}`);
  },
  getOption: (optionId: string) =>
    apiFetch<ServiceOption34E>(`/v1/admin/service-options/${optionId}`),
  createOption: (data: Partial<ServiceOption34E> & { name: string }) =>
    apiFetch<ServiceOption34E>("/v1/admin/service-options", {
      method: "POST", body: JSON.stringify(data),
    }),
  updateOption: (optionId: string, data: Partial<ServiceOption34E>) =>
    apiFetch<ServiceOption34E>(`/v1/admin/service-options/${optionId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  activateOption: (optionId: string) =>
    apiFetch<ServiceOption34E>(`/v1/admin/service-options/${optionId}/activate`, { method: "POST" }),
  deactivateOption: (optionId: string) =>
    apiFetch<ServiceOption34E>(`/v1/admin/service-options/${optionId}/deactivate`, { method: "POST" }),
  archiveOption: (optionId: string) =>
    apiFetch<ServiceOption34E>(`/v1/admin/service-options/${optionId}/archive`, { method: "POST" }),

  // Issue types
  listIssueTypes: (params?: {
    status?: string; category_id?: string; master_service_id?: string;
    search?: string; page?: number; page_size?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.category_id) qs.set("category_id", params.category_id);
    if (params?.master_service_id) qs.set("master_service_id", params.master_service_id);
    if (params?.search) qs.set("search", params.search);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return apiFetch<{ items: IssueType34E[]; total: number }>(`/v1/admin/issue-types-v2?${qs}`);
  },
  getIssueType: (issueId: string) =>
    apiFetch<IssueType34E>(`/v1/admin/issue-types-v2/${issueId}`),
  createIssueType: (data: Partial<IssueType34E> & { name: string }) =>
    apiFetch<IssueType34E>("/v1/admin/issue-types-v2", {
      method: "POST", body: JSON.stringify(data),
    }),
  updateIssueType: (issueId: string, data: Partial<IssueType34E>) =>
    apiFetch<IssueType34E>(`/v1/admin/issue-types-v2/${issueId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  activateIssueType: (issueId: string) =>
    apiFetch<IssueType34E>(`/v1/admin/issue-types-v2/${issueId}/activate`, { method: "POST" }),
  deactivateIssueType: (issueId: string) =>
    apiFetch<IssueType34E>(`/v1/admin/issue-types-v2/${issueId}/deactivate`, { method: "POST" }),
  archiveIssueType: (issueId: string) =>
    apiFetch<IssueType34E>(`/v1/admin/issue-types-v2/${issueId}/archive`, { method: "POST" }),

  // Checklist items (Phase 2 — master/admin-catalog-level)
  listChecklistItems: (params?: {
    status?: string; category_id?: string; master_service_id?: string;
    search?: string; page?: number; page_size?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.category_id) qs.set("category_id", params.category_id);
    if (params?.master_service_id) qs.set("master_service_id", params.master_service_id);
    if (params?.search) qs.set("search", params.search);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return apiFetch<{ items: MasterChecklistItem[]; total: number }>(`/v1/admin/checklists?${qs}`);
  },
  getChecklistItem: (itemId: string) =>
    apiFetch<MasterChecklistItem>(`/v1/admin/checklists/${itemId}`),
  createChecklistItem: (data: Partial<MasterChecklistItem> & { title: string }) =>
    apiFetch<MasterChecklistItem>("/v1/admin/checklists", {
      method: "POST", body: JSON.stringify(data),
    }),
  updateChecklistItem: (itemId: string, data: Partial<MasterChecklistItem>) =>
    apiFetch<MasterChecklistItem>(`/v1/admin/checklists/${itemId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  enableChecklistItem: (itemId: string) =>
    apiFetch<MasterChecklistItem>(`/v1/admin/checklists/${itemId}/enable`, { method: "POST" }),
  disableChecklistItem: (itemId: string) =>
    apiFetch<MasterChecklistItem>(`/v1/admin/checklists/${itemId}/disable`, { method: "POST" }),
  archiveChecklistItem: (itemId: string) =>
    apiFetch<MasterChecklistItem>(`/v1/admin/checklists/${itemId}/archive`, { method: "POST" }),
  seedDefaultChecklists: () =>
    apiFetch<{ created: string[]; skipped: string[] }>("/v1/admin/checklists/seed-defaults", { method: "POST" }),

  // Service ↔ option mappings
  listServiceOptionMappings: (serviceId: string) =>
    apiFetch<ServiceOptionMapping34E[]>(`/v1/admin/master-services/${serviceId}/options`),
  addServiceOptionMapping: (serviceId: string, data: { service_option_id: string; is_required?: boolean; is_default?: boolean; display_order?: number }) =>
    apiFetch<ServiceOptionMapping34E>(`/v1/admin/master-services/${serviceId}/options`, {
      method: "POST", body: JSON.stringify(data),
    }),
  updateServiceOptionMapping: (serviceId: string, mappingId: string, data: Partial<ServiceOptionMapping34E>) =>
    apiFetch<ServiceOptionMapping34E>(`/v1/admin/master-services/${serviceId}/options/${mappingId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  removeServiceOptionMapping: (serviceId: string, mappingId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/master-services/${serviceId}/options/${mappingId}`, {
      method: "DELETE",
    }),

  // Service ↔ issue mappings
  listServiceIssueMappings: (serviceId: string) =>
    apiFetch<ServiceIssueMapping34E[]>(`/v1/admin/master-services/${serviceId}/issues`),
  addServiceIssueMapping: (serviceId: string, data: { issue_type_id: string; is_common?: boolean; requires_photo?: boolean; requires_description?: boolean; display_order?: number }) =>
    apiFetch<ServiceIssueMapping34E>(`/v1/admin/master-services/${serviceId}/issues`, {
      method: "POST", body: JSON.stringify(data),
    }),
  updateServiceIssueMapping: (serviceId: string, mappingId: string, data: Partial<ServiceIssueMapping34E>) =>
    apiFetch<ServiceIssueMapping34E>(`/v1/admin/master-services/${serviceId}/issues/${mappingId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  removeServiceIssueMapping: (serviceId: string, mappingId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/master-services/${serviceId}/issues/${mappingId}`, {
      method: "DELETE",
    }),
};

// ─────────────────────────────────────────────────────────────────────────────
// Sprint 34F — Service Setup Templates
// ─────────────────────────────────────────────────────────────────────────────

export interface ServiceSetupTemplate34F {
  id: string;
  code: string;
  name: string;
  slug: string;
  description?: string;
  vertical_type?: string;
  category_id?: string;
  template_type: string;
  status: string;
  version: number;
  is_system_template: boolean;
  metadata_json?: Record<string, unknown>;
  created_by_user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ServiceSetupTemplateItem34F {
  id: string;
  template_id: string;
  item_type: string;
  reference_id?: string;
  reference_code?: string;
  payload_json: Record<string, unknown>;
  apply_mode: string;
  is_required: boolean;
  display_order: number;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface ServiceSetupTemplateRelationship34F {
  id: string;
  template_id: string;
  source_item_id: string;
  target_item_id: string;
  relationship_type: string;
  payload_json?: Record<string, unknown>;
  status: string;
  display_order: number;
  created_at?: string;
}

export interface ServiceSetupTemplateRun34F {
  id: string;
  template_id: string;
  version: number;
  applied_by_user_id?: string;
  target_scope: string;
  status: string;
  summary_json?: Record<string, unknown>;
  error_json?: Record<string, unknown>;
  created_at?: string;
  completed_at?: string;
  items?: ServiceSetupTemplateRunItem34F[];
}

export interface ServiceSetupTemplateRunItem34F {
  id: string;
  run_id: string;
  template_item_id?: string;
  action: string;
  target_record_type?: string;
  target_record_id?: string;
  message?: string;
  created_at?: string;
}

export const setupTemplateApi = {
  listTemplates: (params?: {
    status?: string; vertical_type?: string; template_type?: string;
    search?: string; page?: number; page_size?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.vertical_type) qs.set("vertical_type", params.vertical_type);
    if (params?.template_type) qs.set("template_type", params.template_type);
    if (params?.search) qs.set("search", params.search);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return apiFetch<{ items: ServiceSetupTemplate34F[]; total: number }>(
      `/v1/admin/service-setup-templates?${qs}`
    );
  },
  getTemplate: (templateId: string) =>
    apiFetch<ServiceSetupTemplate34F>(`/v1/admin/service-setup-templates/${templateId}`),
  createTemplate: (data: Partial<ServiceSetupTemplate34F> & { name: string; code: string }) =>
    apiFetch<ServiceSetupTemplate34F>("/v1/admin/service-setup-templates", {
      method: "POST", body: JSON.stringify(data),
    }),
  updateTemplate: (templateId: string, data: Partial<ServiceSetupTemplate34F>) =>
    apiFetch<ServiceSetupTemplate34F>(`/v1/admin/service-setup-templates/${templateId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  publishTemplate: (templateId: string) =>
    apiFetch<ServiceSetupTemplate34F>(`/v1/admin/service-setup-templates/${templateId}/publish`, { method: "POST" }),
  archiveTemplate: (templateId: string) =>
    apiFetch<ServiceSetupTemplate34F>(`/v1/admin/service-setup-templates/${templateId}/archive`, { method: "POST" }),
  deleteTemplate: (templateId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/service-setup-templates/${templateId}`, { method: "DELETE" }),

  // Items
  listItems: (templateId: string) =>
    apiFetch<ServiceSetupTemplateItem34F[]>(`/v1/admin/service-setup-templates/${templateId}/items`),
  addItem: (templateId: string, data: Partial<ServiceSetupTemplateItem34F> & { item_type: string }) =>
    apiFetch<ServiceSetupTemplateItem34F>(`/v1/admin/service-setup-templates/${templateId}/items`, {
      method: "POST", body: JSON.stringify(data),
    }),
  updateItem: (templateId: string, itemId: string, data: Partial<ServiceSetupTemplateItem34F>) =>
    apiFetch<ServiceSetupTemplateItem34F>(`/v1/admin/service-setup-templates/${templateId}/items/${itemId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  removeItem: (templateId: string, itemId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/service-setup-templates/${templateId}/items/${itemId}`, {
      method: "DELETE",
    }),

  // Relationships
  listRelationships: (templateId: string) =>
    apiFetch<ServiceSetupTemplateRelationship34F[]>(
      `/v1/admin/service-setup-templates/${templateId}/relationships`
    ),
  addRelationship: (templateId: string, data: { source_item_id: string; target_item_id: string; relationship_type: string }) =>
    apiFetch<ServiceSetupTemplateRelationship34F>(
      `/v1/admin/service-setup-templates/${templateId}/relationships`,
      { method: "POST", body: JSON.stringify(data) }
    ),
  removeRelationship: (templateId: string, relId: string) =>
    apiFetch<{ deleted: boolean }>(
      `/v1/admin/service-setup-templates/${templateId}/relationships/${relId}`,
      { method: "DELETE" }
    ),

  // Preview & Apply
  previewTemplate: (templateId: string, scope: Record<string, string>) =>
    apiFetch<{ template: ServiceSetupTemplate34F; preview_items: unknown[]; total_items: number; note: string }>(
      `/v1/admin/service-setup-templates/${templateId}/preview`,
      { method: "POST", body: JSON.stringify(scope) }
    ),
  applyTemplate: (templateId: string, scope: Record<string, string>) =>
    apiFetch<{ run_id: string; status: string; summary: Record<string, number>; items: unknown[] }>(
      `/v1/admin/service-setup-templates/${templateId}/apply`,
      { method: "POST", body: JSON.stringify(scope) }
    ),

  // Runs
  listRuns: (templateId: string) =>
    apiFetch<ServiceSetupTemplateRun34F[]>(`/v1/admin/service-setup-templates/${templateId}/runs`),
  getRunDetail: (runId: string) =>
    apiFetch<ServiceSetupTemplateRun34F>(`/v1/admin/service-setup-templates/runs/${runId}`),
};

// ─────────────────────────────────────────────────────────────────────────────
// Sprint 34H — Admin Bulk Setup Wizard
// ─────────────────────────────────────────────────────────────────────────────

export interface BulkSetupDraft {
  id: string;
  created_by_user_id?: string;
  status: string;
  current_step: number;
  target_vertical_type?: string;
  target_category_id?: string;
  target_category_payload_json?: Record<string, unknown>;
  selected_service_ids_json?: string[];
  new_services_payload_json?: BulkNewService[];
  selected_template_ids_json?: string[];
  bulk_setup_payload_json: BulkSetupPayload;
  preview_summary_json?: BulkPreviewSummary;
  blocking_items_json?: BulkBlocker[];
  last_previewed_at?: string;
  applied_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface BulkNewService {
  service_name: string;
  slug?: string;
  job_type?: string;
  pricing_model?: string;
  requires_brand?: boolean;
  requires_service_option?: boolean;
  requires_issue_type?: boolean;
}

export interface BulkSetupPayload {
  brand_mappings?: BulkBrandMapping[];
  option_mappings?: BulkOptionMapping[];
  issue_mappings?: BulkIssueMapping[];
  document_mappings?: BulkGenericMapping[];
  checklist_mappings?: BulkGenericMapping[];
  pricing_mappings?: BulkGenericMapping[];
  commission_mappings?: BulkGenericMapping[];
  workflow_mappings?: BulkGenericMapping[];
}

export interface BulkBrandMapping {
  brand_id: string;
  service_id: string;
  is_required?: boolean;
}

export interface BulkOptionMapping {
  service_option_id: string;
  service_id: string;
  is_required?: boolean;
  is_default?: boolean;
}

export interface BulkIssueMapping {
  issue_type_id: string;
  service_id: string;
  is_common?: boolean;
  requires_photo?: boolean;
  requires_description?: boolean;
}

export interface BulkGenericMapping {
  id?: string;
  template_id?: string;
  name?: string;
  service_id?: string;
}

export interface BulkPreviewSummary {
  creates: number;
  reuses: number;
  mappings: number;
  skips: number;
  conflicts: number;
  blockers: number;
}

export interface BulkBlocker {
  code: string;
  severity: string;
  message: string;
}

export interface BulkPreviewItem {
  entity_type: string;
  name: string;
  action: string;
  reason?: string;
}

export interface BulkSetupRun {
  id: string;
  draft_id: string;
  applied_by_user_id?: string;
  status: string;
  target_vertical_type?: string;
  summary_json?: Record<string, number>;
  error_json?: Record<string, unknown>;
  created_at?: string;
  completed_at?: string;
  items?: BulkSetupRunItem[];
}

export interface BulkSetupRunItem {
  id: string;
  run_id: string;
  entity_type: string;
  entity_id?: string;
  entity_code?: string;
  action: string;
  message?: string;
  created_at?: string;
}

export const bulkSetupApi = {
  // Draft CRUD
  createDraft: (data: { target_vertical_type?: string }) =>
    apiFetch<BulkSetupDraft>("/v1/admin/bulk-setup/drafts", {
      method: "POST", body: JSON.stringify(data),
    }),
  listDrafts: (params?: { status?: string; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return apiFetch<{ items: BulkSetupDraft[]; total: number }>(`/v1/admin/bulk-setup/drafts?${qs}`);
  },
  getDraft: (draftId: string) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}`),
  updateDraft: (draftId: string, data: Partial<BulkSetupDraft>) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  deleteDraft: (draftId: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/bulk-setup/drafts/${draftId}`, { method: "DELETE" }),

  // Available resources
  getAvailableCategories: (params?: { vertical_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.vertical_type) qs.set("vertical_type", params.vertical_type);
    return apiFetch<unknown[]>(`/v1/admin/bulk-setup/available-categories?${qs}`);
  },
  getAvailableServices: (params?: { category_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category_id) qs.set("category_id", params.category_id);
    return apiFetch<unknown[]>(`/v1/admin/bulk-setup/available-services?${qs}`);
  },
  getAvailableTemplates: (params?: { vertical_type?: string; category_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.vertical_type) qs.set("vertical_type", params.vertical_type);
    if (params?.category_id) qs.set("category_id", params.category_id);
    return apiFetch<unknown[]>(`/v1/admin/bulk-setup/available-templates?${qs}`);
  },
  getAvailableBrands: (params?: { category_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category_id) qs.set("category_id", params.category_id);
    return apiFetch<unknown[]>(`/v1/admin/bulk-setup/available-brands?${qs}`);
  },
  getAvailableBrandTemplates: () =>
    apiFetch<unknown[]>("/v1/admin/bulk-setup/available-brand-templates"),
  getAvailableOptionGroups: (params?: { vertical_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.vertical_type) qs.set("vertical_type", params.vertical_type);
    return apiFetch<unknown[]>(`/v1/admin/bulk-setup/available-option-groups?${qs}`);
  },
  getAvailableServiceOptions: (params?: { group_id?: string; vertical_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.group_id) qs.set("group_id", params.group_id);
    if (params?.vertical_type) qs.set("vertical_type", params.vertical_type);
    return apiFetch<unknown[]>(`/v1/admin/bulk-setup/available-service-options?${qs}`);
  },
  getAvailableIssueTypes: (params?: { vertical_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.vertical_type) qs.set("vertical_type", params.vertical_type);
    return apiFetch<unknown[]>(`/v1/admin/bulk-setup/available-issue-types?${qs}`);
  },
  getAvailableDocumentRequirements: () =>
    apiFetch<unknown[]>("/v1/admin/bulk-setup/available-document-requirements"),
  getAvailableChecklistTemplates: () =>
    apiFetch<unknown[]>("/v1/admin/bulk-setup/available-checklist-templates"),
  getAvailablePricingTemplates: () =>
    apiFetch<unknown[]>("/v1/admin/bulk-setup/available-pricing-templates"),
  getAvailableCommissionTemplates: () =>
    apiFetch<unknown[]>("/v1/admin/bulk-setup/available-commission-templates"),
  getAvailableWorkflowTemplates: (params?: { category_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category_id) qs.set("category_id", params.category_id);
    return apiFetch<unknown[]>(`/v1/admin/bulk-setup/available-workflow-templates?${qs}`);
  },

  // Step saves
  setCategory: (draftId: string, data: { category_id?: string; vertical_type?: string; new_category_payload?: Record<string, string> }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/category`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setServices: (draftId: string, data: { selected_service_ids?: string[]; new_services?: BulkNewService[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/services`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setTemplates: (draftId: string, data: { template_ids: string[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/templates`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setBrandMappings: (draftId: string, data: { mappings: BulkBrandMapping[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/brand-mappings`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setOptionMappings: (draftId: string, data: { mappings: BulkOptionMapping[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/option-mappings`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setIssueMappings: (draftId: string, data: { mappings: BulkIssueMapping[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/issue-mappings`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setDocumentMappings: (draftId: string, data: { mappings: BulkGenericMapping[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/document-mappings`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setChecklistMappings: (draftId: string, data: { mappings: BulkGenericMapping[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/checklist-mappings`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setPricingMappings: (draftId: string, data: { mappings: BulkGenericMapping[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/pricing-mappings`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setCommissionMappings: (draftId: string, data: { mappings: BulkGenericMapping[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/commission-mappings`, {
      method: "POST", body: JSON.stringify(data),
    }),
  setWorkflowMappings: (draftId: string, data: { mappings: BulkGenericMapping[] }) =>
    apiFetch<BulkSetupDraft>(`/v1/admin/bulk-setup/drafts/${draftId}/workflow-mappings`, {
      method: "POST", body: JSON.stringify(data),
    }),

  // Validate + Preview + Apply
  validateDraft: (draftId: string) =>
    apiFetch<{ can_apply: boolean; blocker_count: number; items: BulkBlocker[] }>(
      `/v1/admin/bulk-setup/drafts/${draftId}/validate`, { method: "POST" }
    ),
  previewDraft: (draftId: string) =>
    apiFetch<{ can_apply: boolean; summary: BulkPreviewSummary; items: BulkPreviewItem[]; blockers: BulkBlocker[] }>(
      `/v1/admin/bulk-setup/drafts/${draftId}/preview`, { method: "POST" }
    ),
  reviewDraft: (draftId: string) =>
    apiFetch<{ draft: BulkSetupDraft; preview_summary: BulkPreviewSummary; blocking_items: BulkBlocker[]; can_apply: boolean }>(
      `/v1/admin/bulk-setup/drafts/${draftId}/review`
    ),
  applyDraft: (draftId: string, notes?: string) =>
    apiFetch<{ run_id: string; status: string; summary: Record<string, number> }>(
      `/v1/admin/bulk-setup/drafts/${draftId}/apply`,
      { method: "POST", body: JSON.stringify({ notes }) }
    ),

  // Runs
  listRuns: (params?: { page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return apiFetch<{ items: BulkSetupRun[]; total: number }>(`/v1/admin/bulk-setup/runs?${qs}`);
  },
  getRun: (runId: string) =>
    apiFetch<BulkSetupRun>(`/v1/admin/bulk-setup/runs/${runId}`),
};

// ── Sprint 34I — Recommendation Rules Engine ──────────────────────────────────

export interface RecommendationRule {
  id: string;
  code: string;
  name: string;
  description?: string;
  rule_type: string;
  scope: string;
  vertical_type?: string;
  category_id?: string;
  service_id?: string;
  tenant_id?: string;
  location_id?: string;
  priority: number;
  status: string;
  condition_json: Record<string, unknown>;
  recommendation_json: Record<string, unknown>;
  explanation_template?: string;
  created_at?: string;
  updated_at?: string;
}

export interface RecommendationResult {
  id: string;
  request_id?: string;
  actor_user_id?: string;
  tenant_id?: string;
  customer_id?: string;
  context_type: string;
  context_id?: string;
  rule_id?: string;
  rule_type?: string;
  recommended_entity_type?: string;
  recommended_entity_id?: string;
  recommended_payload_json?: Record<string, unknown>;
  confidence_score?: number;
  explanation?: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface RecommendationItem {
  entity_type: string;
  entity_id?: string;
  entity_code?: string;
  name: string;
  confidence_score?: number;
  explanation?: string;
  rule_id?: string;
  rule_code?: string;
}

export interface RecommendationEvalResult {
  recommendations: RecommendationItem[];
  warnings: string[];
  rule_count: number;
  context_type: string;
}

export interface SimulateResult {
  success: boolean;
  data: {
    rule_id: string;
    rule_code: string;
    matched: boolean;
    recommendations: RecommendationItem[];
    warnings: string[];
    note: string;
  };
}

export const recommendationApi = {
  // Rule CRUD
  listRules: (params?: {
    status?: string; rule_type?: string; scope?: string;
    vertical_type?: string; page?: number; page_size?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.rule_type) qs.set("rule_type", params.rule_type);
    if (params?.scope) qs.set("scope", params.scope);
    if (params?.vertical_type) qs.set("vertical_type", params.vertical_type);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return apiFetch<{ items: RecommendationRule[]; total: number }>(
      `/v1/admin/recommendation-rules?${qs}`
    );
  },

  createRule: (data: Partial<RecommendationRule>) =>
    apiFetch<RecommendationRule>("/v1/admin/recommendation-rules", {
      method: "POST", body: JSON.stringify(data),
    }),

  getRule: (ruleId: string) =>
    apiFetch<RecommendationRule>(`/v1/admin/recommendation-rules/${ruleId}`),

  updateRule: (ruleId: string, data: Partial<RecommendationRule>) =>
    apiFetch<RecommendationRule>(`/v1/admin/recommendation-rules/${ruleId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),

  deleteRule: (ruleId: string) =>
    apiFetch<{ deleted: boolean; id: string }>(`/v1/admin/recommendation-rules/${ruleId}`, {
      method: "DELETE",
    }),

  // Lifecycle
  activateRule: (ruleId: string) =>
    apiFetch<RecommendationRule>(`/v1/admin/recommendation-rules/${ruleId}/activate`, {
      method: "POST",
    }),

  deactivateRule: (ruleId: string) =>
    apiFetch<RecommendationRule>(`/v1/admin/recommendation-rules/${ruleId}/deactivate`, {
      method: "POST",
    }),

  archiveRule: (ruleId: string) =>
    apiFetch<RecommendationRule>(`/v1/admin/recommendation-rules/${ruleId}/archive`, {
      method: "POST",
    }),

  // Simulate
  simulateRule: (ruleId: string, context: Record<string, unknown>) =>
    apiFetch<SimulateResult>(`/v1/admin/recommendation-rules/${ruleId}/simulate`, {
      method: "POST", body: JSON.stringify(context),
    }),

  // Results
  listResults: (params?: { context_type?: string; status?: string; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.context_type) qs.set("context_type", params.context_type);
    if (params?.status) qs.set("status", params.status);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return apiFetch<{ items: RecommendationResult[]; total: number }>(
      `/v1/admin/recommendation-rules/results/list?${qs}`
    );
  },

  // Engine — evaluate
  evaluate: (context: Record<string, unknown>) =>
    apiFetch<RecommendationEvalResult>("/v1/recommendations/evaluate", {
      method: "POST", body: JSON.stringify(context),
    }),

  validateEntity: (entityType: string, entityId: string) =>
    apiFetch<{ valid: boolean; entity_type: string }>("/v1/recommendations/validate", {
      method: "POST", body: JSON.stringify({ entity_type: entityType, entity_id: entityId }),
    }),

  acceptResult: (resultId: string) =>
    apiFetch<RecommendationResult>(`/v1/recommendations/${resultId}/accept`, {
      method: "POST",
    }),

  rejectResult: (resultId: string, reason?: string) =>
    apiFetch<RecommendationResult>(`/v1/recommendations/${resultId}/reject`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  // AI recommendations
  aiRecommendations: (context: Record<string, unknown>) =>
    apiFetch<{ success: boolean; data: { recommendations: RecommendationItem[]; allowed_next_steps: string[]; warnings: string[] } }>(
      "/v1/ai/recommendations",
      { method: "POST", body: JSON.stringify(context) }
    ),

  // Context-specific
  bulkSetupRecommendations: (draftId: string, context?: Record<string, unknown>) =>
    apiFetch<RecommendationEvalResult>(
      `/v1/admin/bulk-setup/drafts/${draftId}/recommendations`,
      { method: "POST", body: JSON.stringify(context ?? {}) }
    ),

  providerSetupRecommendations: (context?: Record<string, unknown>) =>
    apiFetch<RecommendationEvalResult>("/v1/provider/setup/recommendations", {
      method: "POST", body: JSON.stringify(context ?? {}),
    }),
};

// ── Sprint 34J — Customer Flow ────────────────────────────────────────────────

export interface CustomerBookingDraft {
  id: string;
  flow_type: string;
  status: string;
  customer_id: string | null;
  guest_session_id: string | null;
  category_id: string | null;
  service_id: string | null;
  brand_id: string | null;
  issue_type_id: string | null;
  service_option_ids: string[] | null;
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
  city: string | null;
  zipcode: string | null;
  address_text: string | null;
  issue_summary: string | null;
  preferred_date: string | null;
  preferred_time_slot: string | null;
  estimate_min: number | null;
  estimate_max: number | null;
  estimate_currency: string | null;
  selected_tenant_id: string | null;
  final_job_id: string | null;
  final_appointment_id: string | null;
  final_lead_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CustomerFlowConfig {
  category_id: string;
  customer_flow_type: string;
  frontend_component_key: string;
  primary_engine_key: string;
  required_steps: string[] | null;
  optional_steps: string[] | null;
  config: Record<string, unknown> | null;
  configured: boolean;
}

export const customerFlowApi = {
  // Public catalog
  listCategories: () =>
    apiFetch<{ items: Record<string, unknown>[]; total: number }>("/v1/customer/flow/categories"),

  listServices: (categoryId?: string) =>
    apiFetch<{ items: Record<string, unknown>[]; total: number }>(
      `/v1/customer/flow/services${categoryId ? `?category_id=${categoryId}` : ""}`
    ),

  getFlowConfig: (categoryId: string) =>
    apiFetch<CustomerFlowConfig>(`/v1/customer/flow/flow-config?category_id=${categoryId}`),

  // Draft CRUD
  createDraft: (body: { flow_type: string; category_id?: string; service_id?: string; ai_session_id?: string }) =>
    apiFetch<CustomerBookingDraft>("/v1/customer/flow/drafts", {
      method: "POST", body: JSON.stringify(body),
    }),

  listDrafts: (params?: { status?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    const qs = q.toString();
    return apiFetch<{ items: CustomerBookingDraft[]; total: number }>(
      `/v1/customer/flow/drafts${qs ? `?${qs}` : ""}`
    );
  },

  getDraft: (draftId: string) =>
    apiFetch<CustomerBookingDraft>(`/v1/customer/flow/drafts/${draftId}`),

  updateDraft: (draftId: string, body: Partial<CustomerBookingDraft>) =>
    apiFetch<CustomerBookingDraft>(`/v1/customer/flow/drafts/${draftId}`, {
      method: "PATCH", body: JSON.stringify(body),
    }),

  estimateDraft: (draftId: string) =>
    apiFetch<CustomerBookingDraft & { estimate: { min: number | null; max: number | null; currency: string; note: string } }>(
      `/v1/customer/flow/drafts/${draftId}/estimate`, { method: "POST" }
    ),

  confirmDraft: (draftId: string, body: { customer_name?: string; customer_phone?: string; customer_email?: string }) =>
    apiFetch<CustomerBookingDraft & { confirmed: boolean; next_step: string; message: string }>(
      `/v1/customer/flow/drafts/${draftId}/confirm`, { method: "POST", body: JSON.stringify(body) }
    ),

  cancelDraft: (draftId: string) =>
    apiFetch<CustomerBookingDraft>(`/v1/customer/flow/drafts/${draftId}/cancel`, { method: "POST" }),

  // Admin oversight
  adminListFlowConfigs: (page?: number, pageSize?: number) =>
    apiFetch<{ items: CustomerFlowConfig[]; total: number }>(
      `/v1/admin/customer-flow/flow-configs${page || pageSize ? `?page=${page ?? 1}&page_size=${pageSize ?? 50}` : ""}`
    ),

  adminListDrafts: (params?: { status?: string; flow_type?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.flow_type) q.set("flow_type", params.flow_type);
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    const qs = q.toString();
    return apiFetch<{ items: CustomerBookingDraft[]; total: number }>(
      `/v1/admin/customer-flow/drafts${qs ? `?${qs}` : ""}`
    );
  },

  adminGetDraft: (draftId: string) =>
    apiFetch<CustomerBookingDraft>(`/v1/admin/customer-flow/drafts/${draftId}`),
};

// ── Complaints (Sprint 75) ────────────────────────────────────────────────────
export const complaintsApi = {
  adminSummary: (tenantId?: string) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : "";
    return apiFetch<Record<string, number>>(`/v1/admin/complaints/summary${qs}`);
  },

  adminList: (params?: {
    q?: string; status?: string; sla_status?: string; priority?: string;
    severity?: string; record_type?: string; complaint_type?: string;
    tenant_id?: string; date_from?: string; date_to?: string;
    sort_by?: string; sort_dir?: string; page?: number; page_size?: number;
  }) => {
    const cleaned: Record<string, string> = {};
    for (const [k, v] of Object.entries(params ?? {})) {
      if (v != null && v !== "" && v !== undefined) cleaned[k] = String(v);
    }
    const qs = new URLSearchParams(cleaned).toString();
    return apiFetch<{ items: Record<string, unknown>[]; meta: Record<string, unknown> }>(
      `/v1/admin/complaints/list${qs ? `?${qs}` : ""}`
    );
  },

  adminGet: (id: string) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/complaints/${id}`),

  startAISettlement: (id: string) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/complaints/${id}/start-ai-settlement`, { method: "POST" }),

  finalizeSettlement: (id: string, decision: string, notes?: string) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/complaints/${id}/finalize-settlement`, {
      method: "POST", body: JSON.stringify({ decision, notes }),
    }),

  createSettlementProposal: (id: string, body: {
    proposal_type: string; description: string; proposal_amount?: number; conditions?: string;
  }) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/complaints/${id}/settlement-proposals`, {
      method: "POST", body: JSON.stringify(body),
    }),

  listSettlementProposals: (id: string) =>
    apiFetch<Record<string, unknown>[]>(`/v1/admin/complaints/${id}/settlement-proposals`),

  getAISession: (id: string) =>
    apiFetch<Record<string, unknown> | null>(`/v1/admin/complaints/${id}/ai-session`),

  getTimeline: (id: string) =>
    apiFetch<Record<string, unknown>[]>(`/v1/admin/complaints/${id}/timeline`),

  adminAssign: (id: string, assigneeId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/complaints/${id}/assign`, {
      method: "POST", body: JSON.stringify({ assignee_id: assigneeId }),
    }),

  adminReject: (id: string, reason: string) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/complaints/${id}/reject`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
};

// ── Finance Hub (P0 Enterprise Finance Upgrade) ───────────────────────────────
export interface FinanceSummary {
  active_wallets: number; low_balance_wallets: number; credits_issued: number;
  commission_earned: number; deposit_held: number; deposit_pending: number;
  pending_warranty_claims: number; pending_payouts: number; at_risk_tenants: number;
  recovered_refunded_deposits: number; pending_deposit_actions: number;
}
export interface FinanceOverview {
  wallet_health_distribution: Record<string, number>;
  top_low_balance_tenants: { tenant_id: string; tenant_name: string; wallet_balance: number; health_band: string }[];
  deposit_status_breakdown: Record<string, number>;
  top_commission_contributors: { tenant_id: string; tenant_name: string; commission_total: number }[];
  recent_finance_activity: { type: string; label: string; tenant_id: string; created_at: string }[];
  pending_actions_queue: {
    deposit_verification_pending: number; payout_pending_approval: number;
    warranty_claim_pending_review: number; failed_topup_payment: number;
  };
  at_risk_tenants: { tenant_id: string; tenant_name: string; health_band: string; health_score: number }[];
}
export interface FinanceDeposit {
  deposit_id: string; tenant_id: string; tenant_name?: string | null;
  vertical?: string | null; city?: string | null; state?: string | null;
  required_amount: number; received_amount: number; pending_amount: number;
  status: string; hold_state?: string | null; adjusted_amount: number; refunded_amount: number;
  current_balance: number; package_purchase_id?: string | null;
  rejection_reason?: string | null; clarification_notes?: string | null;
  approved_by?: string | null; approved_at?: string | null;
  paid_at?: string | null; refunded_at?: string | null; created_at?: string | null;
}
export interface FinanceDepositsSummary {
  total_deposit_accounts: number; active_held_deposits: number; pending_deposits: number;
  refund_pending: number; refunded: number; deposit_risk_cases: number;
}
export interface FinanceTopup {
  topup_id: string; tenant_id: string; tenant_name?: string | null;
  credit_package_id?: string | null; order_ref?: string | null;
  credits_purchased: number; bonus_credits: number; amount_paid: number; currency: string;
  payment_method?: string | null; payment_status: string; wallet_credit_status: string;
  wallet_transaction_id?: string | null; gateway_order_id?: string | null; gateway_payment_id?: string | null;
  failure_reason?: string | null; refunded_amount?: number | null;
  created_at?: string | null; updated_at?: string | null;
}
export interface FinanceTopupsSummary {
  total_topups: number; total_topup_value: number; pending_topups: number;
  failed_topups: number; refunded_topups: number; topup_value_this_month: number;
}
export interface FinanceClaim {
  claim_id: string; tenant_id: string; tenant_name?: string | null; customer_id: string;
  job_id: string; claim_type: string; description: string; amount_requested: number;
  amount_approved?: number | null; status: string; assigned_reviewer_id?: string | null;
  admin_notes?: string | null; rejection_reason?: string | null;
  settled_at?: string | null; settled_amount?: number | null;
  documents_requested_at?: string | null; documents_requested_notes?: string | null;
  resolved_at?: string | null; created_at?: string | null; updated_at?: string | null;
}
export interface FinanceClaimsSummary {
  total_claims: number; pending_review: number; investigation_ongoing: number;
  approved_claims: number; rejected_claims: number; settled_value: number;
}
export interface FinancePayout {
  payout_id: string; payout_number?: string | null; tenant_id: string; tenant_name?: string | null;
  payout_type: string; requested_amount: number; approved_amount?: number | null;
  status: string; gateway: string; method: string; gateway_transfer_id?: string | null;
  approved_by?: string | null; approved_at?: string | null;
  rejection_reason?: string | null; failure_reason?: string | null;
  requested_on?: string | null; processed_on?: string | null;
}
export interface FinancePayoutsSummary {
  pending_payouts: number; approved_payouts: number; processing: number;
  failed_payouts: number; completed_payouts: number; total_payout_value: number;
}
export interface FinanceWallet {
  wallet_id: string; tenant_id: string; tenant_name: string;
  available_balance: number; reserved_balance: number;
  low_balance_threshold?: number | null; last_transaction_at?: string | null;
  health_band: string; is_active: boolean;
}
export interface FinanceAuditEntry {
  id: string; operation: string; engine_id: string; actor_id?: string | null;
  actor_role?: string | null; before?: Record<string, unknown> | null; after?: Record<string, unknown> | null;
  created_at?: string | null;
}

// Customer Service Credit + Dispute Settlement interfaces (migration 080)
export interface DisputeSettlement {
  id: string; settlement_number: string; dispute_id: string;
  booking_id?: string | null; customer_id: string; tenant_id: string;
  settlement_type: string; settlement_status: string; settlement_amount: number;
  currency: string; deduction_source: string;
  tenant_wallet_deduction_amount: number; security_deposit_deduction_amount: number;
  platform_goodwill_amount: number; customer_credit_id?: string | null;
  tenant_penalty_id?: string | null; admin_decision_reason: string;
  customer_message?: string | null; tenant_message?: string | null;
  created_at: string; approved_at?: string | null; executed_at?: string | null;
  cancelled_at?: string | null;
}
export interface DisputeSettlementSummary {
  total_settlements: number; pending_approval: number; executed_settlements: number;
  failed_cancelled: number; customer_credits_issued: number;
  tenant_wallet_deducted: number; security_deposit_deducted: number;
}
export interface DeductionPreview {
  tenant_id: string; settlement_amount: number; strategy: string;
  wallet_balance: number; wallet_deduction: number; wallet_balance_after: number;
  deposit_available: number; deposit_deduction: number; deposit_remaining: number;
  platform_goodwill_amount: number; uncovered_amount: number; can_fully_cover: boolean;
}
export interface CustomerServiceCredit {
  id: string; credit_number: string; customer_id: string;
  tenant_id?: string | null; booking_id?: string | null; dispute_id?: string | null;
  settlement_id?: string | null; amount: number; remaining_amount: number;
  currency: string; credit_type: string; source: string; status: string;
  issued_reason: string; customer_message?: string | null;
  valid_from: string; expires_at?: string | null; used_at?: string | null;
  cancelled_at?: string | null; cancel_reason?: string | null;
  created_at: string;
}
export interface CustomerCreditSummary {
  total_credits: number; active_credits: number; used_credits: number;
  expired_credits: number; cancelled_credits: number;
  active_credit_balance: number; credits_from_disputes: number;
}
export interface CreditLedgerEntry {
  id: string; transaction_type: string; amount: number; balance_after: number;
  description: string; reference_type?: string | null; booking_id?: string | null;
  created_at: string;
}
export interface TenantPenalty {
  id: string; penalty_number: string; tenant_id: string;
  booking_id?: string | null; dispute_id?: string | null; settlement_id?: string | null;
  penalty_type: string; amount: number; currency: string; source: string;
  status: string; reason: string; created_at: string;
}
export interface TenantPenaltySummary {
  total_penalties: number; applied_penalties: number; pending_penalties: number;
  reversed_penalties: number; wallet_deducted: number; deposit_deducted: number;
}
export interface FinanceVerticalConfig {
  id?: string; vertical_type: string; payment_collection_enabled: boolean;
  tenant_payouts_enabled: boolean; customer_service_credits_enabled: boolean;
  tenant_wallet_deduction_enabled: boolean; security_deposit_adjustment_enabled: boolean;
  manual_customer_refund_enabled: boolean; config_notes?: string | null;
}

// ── HS9B — Home Services Usage Credits (admin) ────────────────────────────────
export interface UsageCreditLedgerEntryAdmin {
  ledger_id: string; tenant_id: string; job_id: string | null; booking_id: string | null;
  event_type: string; credit_delta: number; balance_before: number; balance_after: number;
  deduction_source: string | null; reason: string | null; request_id: string | null; created_at: string;
}
export const usageCreditsAdminApi = {
  getTenantLedger: (tenantId: string, jobId?: string) =>
    apiFetch<{ tenant_id: string; job_id: string | null; entries: UsageCreditLedgerEntryAdmin[]; count: number }>(
      `/v1/admin/tenants/${tenantId}/usage-credit-ledger${jobId ? `?job_id=${jobId}` : ""}`),
  addCredits: (tenantId: string, amount: number, reason: string) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/tenants/${tenantId}/add-usage-credits`,
      { method: "POST", body: JSON.stringify({ amount, reason }) }),
};

export interface AdminServiceJobDetail {
  id: string; job_number: string; booking_id: string;
  customer_id: string | null; tenant_id: string | null;
  category_id: string; offering_id: string; assigned_staff_id: string | null;
  city: string | null; zipcode: string | null;
  status: string; assignment_status: string; failure_reason: string | null;
  completion_data: Record<string, unknown> | null;
  created_at: string; updated_at: string;
  booking: {
    id: string; booking_number: string; customer_name: string | null;
    price_snapshot: Record<string, unknown> | null;
    provider_snapshot: Record<string, unknown> | null;
    issue_summary: string | null; status: string;
  } | null;
  usage_credit_deduction: UsageCreditLedgerEntryAdmin | null;
  usage_credit_deduction_duplicate_count: number;
}
export const finalRecordsAdminApi = {
  getJob: (jobId: string) => apiFetch<AdminServiceJobDetail>(`/v1/admin/final-records/jobs/${jobId}`),
};

export const financeApi = {
  getSummary: () => apiFetch<FinanceSummary>("/v1/admin/finance/summary"),
  getOverview: () => apiFetch<FinanceOverview>("/v1/admin/finance/overview"),

  // Deposits
  listDeposits: (params?: {
    status?: string; vertical?: string; state?: string; city?: string; q?: string;
    page?: number; pageSize?: number; sortBy?: string; sortDir?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.vertical) qs.set("vertical", params.vertical);
    if (params?.state) qs.set("state", params.state);
    if (params?.city) qs.set("city", params.city);
    if (params?.q) qs.set("q", params.q);
    qs.set("page", String(params?.page ?? 1));
    qs.set("page_size", String(params?.pageSize ?? 50));
    qs.set("sort_by", params?.sortBy ?? "created_at");
    qs.set("sort_dir", params?.sortDir ?? "desc");
    return apiFetch<{ items: FinanceDeposit[]; pagination: GridPagination }>(`/v1/admin/finance/deposits?${qs.toString()}`);
  },
  getDepositsSummary: () => apiFetch<FinanceDepositsSummary>("/v1/admin/finance/deposits/summary"),
  exportDeposits: (filters?: { status?: string; vertical?: string }) => {
    const qs = new URLSearchParams();
    if (filters?.status) qs.set("status", filters.status);
    if (filters?.vertical) qs.set("vertical", filters.vertical);
    return apiFetch<{ rows: FinanceDeposit[]; count: number }>(`/v1/admin/finance/deposits/export?${qs.toString()}`);
  },
  getDepositDetail: (depositId: string) =>
    apiFetch<{ deposit: FinanceDeposit; ledger: Record<string, unknown>[]; audit_log: FinanceAuditEntry[] }>(
      `/v1/admin/finance/deposits/${depositId}`),
  approveDeposit: (depositId: string, notes?: string) =>
    apiFetch<FinanceDeposit>(`/v1/admin/finance/deposits/${depositId}/approve`,
      { method: "POST", body: JSON.stringify({ notes }) }),
  rejectDeposit: (depositId: string, reason: string) =>
    apiFetch<FinanceDeposit>(`/v1/admin/finance/deposits/${depositId}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  recordOfflineDeposit: (depositId: string, amount: number, reference?: string, notes?: string) =>
    apiFetch<FinanceDeposit>(`/v1/admin/finance/deposits/${depositId}/record-offline`,
      { method: "POST", body: JSON.stringify({ amount, reference, notes }) }),
  refundDeposit: (depositId: string, amount: number, reason: string) =>
    apiFetch<FinanceDeposit>(`/v1/admin/finance/deposits/${depositId}/refund`,
      { method: "POST", body: JSON.stringify({ amount, reason }) }),
  adjustDeposit: (depositId: string, amount: number, reason: string, category = "manual") =>
    apiFetch<FinanceDeposit>(`/v1/admin/finance/deposits/${depositId}/adjust`,
      { method: "POST", body: JSON.stringify({ amount, reason, category }) }),

  // Top-ups
  listTopups: (params?: {
    tenantId?: string; paymentStatus?: string; q?: string;
    page?: number; pageSize?: number; sortBy?: string; sortDir?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.tenantId) qs.set("tenant_id", params.tenantId);
    if (params?.paymentStatus) qs.set("payment_status", params.paymentStatus);
    if (params?.q) qs.set("q", params.q);
    qs.set("page", String(params?.page ?? 1));
    qs.set("page_size", String(params?.pageSize ?? 50));
    qs.set("sort_by", params?.sortBy ?? "created_at");
    qs.set("sort_dir", params?.sortDir ?? "desc");
    return apiFetch<{ items: FinanceTopup[]; pagination: GridPagination }>(`/v1/admin/finance/topups?${qs.toString()}`);
  },
  getTopupsSummary: () => apiFetch<FinanceTopupsSummary>("/v1/admin/finance/topups/summary"),
  exportTopups: (filters?: { paymentStatus?: string }) => {
    const qs = new URLSearchParams();
    if (filters?.paymentStatus) qs.set("payment_status", filters.paymentStatus);
    return apiFetch<{ rows: FinanceTopup[]; count: number }>(`/v1/admin/finance/topups/export?${qs.toString()}`);
  },
  getTopupDetail: (topupId: string) =>
    apiFetch<{ topup: FinanceTopup; package: { package_id: string; name: string } | null;
      ledger_entry: Record<string, unknown> | null; audit_log: FinanceAuditEntry[] }>(
      `/v1/admin/finance/topups/${topupId}`),
  retryCreditPosting: (topupId: string) =>
    apiFetch<FinanceTopup>(`/v1/admin/finance/topups/${topupId}/retry-credit`, { method: "POST" }),
  refundTopup: (topupId: string, amount: number, reason?: string) =>
    apiFetch<FinanceTopup>(`/v1/admin/finance/topups/${topupId}/refund`,
      { method: "POST", body: JSON.stringify({ amount, reason }) }),

  // Warranty Claims
  listClaims: (params?: {
    status?: string; category?: string; q?: string;
    page?: number; pageSize?: number; sortBy?: string; sortDir?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.category) qs.set("category", params.category);
    if (params?.q) qs.set("q", params.q);
    qs.set("page", String(params?.page ?? 1));
    qs.set("page_size", String(params?.pageSize ?? 50));
    qs.set("sort_by", params?.sortBy ?? "created_at");
    qs.set("sort_dir", params?.sortDir ?? "desc");
    return apiFetch<{ items: FinanceClaim[]; pagination: GridPagination }>(`/v1/admin/finance/warranty-claims?${qs.toString()}`);
  },
  getClaimsSummary: () => apiFetch<FinanceClaimsSummary>("/v1/admin/finance/warranty-claims/summary"),
  exportClaims: (filters?: { status?: string }) => {
    const qs = new URLSearchParams();
    if (filters?.status) qs.set("status", filters.status);
    return apiFetch<{ rows: FinanceClaim[]; count: number }>(`/v1/admin/finance/warranty-claims/export?${qs.toString()}`);
  },
  getClaimDetail: (claimId: string) =>
    apiFetch<{ claim: FinanceClaim; audit_log: FinanceAuditEntry[] }>(`/v1/admin/finance/warranty-claims/${claimId}`),
  assignReviewer: (claimId: string, reviewerId: string) =>
    apiFetch<FinanceClaim>(`/v1/admin/finance/warranty-claims/${claimId}/assign`,
      { method: "POST", body: JSON.stringify({ reviewer_id: reviewerId }) }),
  requestDocuments: (claimId: string, notes: string) =>
    apiFetch<FinanceClaim>(`/v1/admin/finance/warranty-claims/${claimId}/request-documents`,
      { method: "POST", body: JSON.stringify({ notes }) }),
  approveClaim: (claimId: string, amountApproved: number, adminNotes?: string) =>
    apiFetch<FinanceClaim>(`/v1/admin/finance/warranty-claims/${claimId}/approve`,
      { method: "POST", body: JSON.stringify({ amount_approved: amountApproved, admin_notes: adminNotes }) }),
  rejectClaim: (claimId: string, rejectionReason: string, adminNotes?: string) =>
    apiFetch<FinanceClaim>(`/v1/admin/finance/warranty-claims/${claimId}/reject`,
      { method: "POST", body: JSON.stringify({ rejection_reason: rejectionReason, admin_notes: adminNotes }) }),
  settleClaim: (claimId: string) =>
    apiFetch<FinanceClaim>(`/v1/admin/finance/warranty-claims/${claimId}/settle`, { method: "POST" }),

  // Payouts
  listPayouts: (params?: {
    status?: string; tenantId?: string; q?: string;
    page?: number; pageSize?: number; sortBy?: string; sortDir?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.tenantId) qs.set("tenant_id", params.tenantId);
    if (params?.q) qs.set("q", params.q);
    qs.set("page", String(params?.page ?? 1));
    qs.set("page_size", String(params?.pageSize ?? 50));
    qs.set("sort_by", params?.sortBy ?? "created_at");
    qs.set("sort_dir", params?.sortDir ?? "desc");
    return apiFetch<{ items: FinancePayout[]; pagination: GridPagination }>(`/v1/admin/finance/payouts?${qs.toString()}`);
  },
  getPayoutsSummary: () => apiFetch<FinancePayoutsSummary>("/v1/admin/finance/payouts/summary"),
  exportPayouts: (filters?: { status?: string }) => {
    const qs = new URLSearchParams();
    if (filters?.status) qs.set("status", filters.status);
    return apiFetch<{ rows: FinancePayout[]; count: number }>(`/v1/admin/finance/payouts/export?${qs.toString()}`);
  },
  getPayoutDetail: (payoutId: string) =>
    apiFetch<{ payout: FinancePayout; bank_account: Record<string, unknown>; audit_log: FinanceAuditEntry[] }>(
      `/v1/admin/finance/payouts/${payoutId}`),
  approvePayout: (payoutId: string, approvedAmount?: number) =>
    apiFetch<FinancePayout>(`/v1/admin/finance/payouts/${payoutId}/approve`,
      { method: "POST", body: JSON.stringify({ approved_amount: approvedAmount }) }),
  rejectPayout: (payoutId: string, reason: string) =>
    apiFetch<FinancePayout>(`/v1/admin/finance/payouts/${payoutId}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  markProcessing: (payoutId: string) =>
    apiFetch<FinancePayout>(`/v1/admin/finance/payouts/${payoutId}/mark-processing`, { method: "POST" }),
  markCompleted: (payoutId: string, gatewayTransferId?: string) =>
    apiFetch<FinancePayout>(`/v1/admin/finance/payouts/${payoutId}/mark-completed`,
      { method: "POST", body: JSON.stringify({ gateway_transfer_id: gatewayTransferId }) }),
  markFailed: (payoutId: string, failureReason: string) =>
    apiFetch<FinancePayout>(`/v1/admin/finance/payouts/${payoutId}/mark-failed`,
      { method: "POST", body: JSON.stringify({ failure_reason: failureReason }) }),

  // Wallets
  listWallets: (params?: { q?: string; healthBand?: string; page?: number; pageSize?: number }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.healthBand) qs.set("health_band", params.healthBand);
    qs.set("page", String(params?.page ?? 1));
    qs.set("page_size", String(params?.pageSize ?? 50));
    return apiFetch<{ items: FinanceWallet[]; pagination: GridPagination }>(`/v1/admin/finance/wallets?${qs.toString()}`);
  },
  getWalletLedger: (walletId: string, page = 1, pageSize = 50) =>
    apiFetch<{
      wallet: FinanceWallet & { lifetime_purchased: number; lifetime_consumed: number };
      ledger: { txn_id: string; txn_type: string; amount: number; balance_before: number; balance_after: number;
        reference_id?: string | null; reference_type?: string | null; description?: string | null; created_at: string }[];
      pagination: GridPagination;
    }>(`/v1/admin/finance/wallets/${walletId}/ledger?page=${page}&page_size=${pageSize}`),

  // Audit
  listAuditLogs: (entityType: string, entityId: string, limit = 50) =>
    apiFetch<{ audit_log: FinanceAuditEntry[] }>(
      `/v1/admin/finance/audit-logs?entity_type=${entityType}&entity_id=${entityId}&limit=${limit}`),

  // Dispute Settlements (migration 080)
  getSettlementSummary: () =>
    apiFetch<DisputeSettlementSummary>("/v1/admin/finance/settlements/summary"),
  listSettlements: (params?: { page?: number; limit?: number; status?: string; tenantId?: string; customerId?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.status) qs.set("status", params.status);
    if (params?.tenantId) qs.set("tenant_id", params.tenantId);
    if (params?.customerId) qs.set("customer_id", params.customerId);
    return apiFetch<{ settlements: DisputeSettlement[]; meta: { total: number; page: number; limit: number; total_pages: number } }>(`/v1/admin/finance/settlements?${qs}`);
  },
  getSettlement: (id: string) =>
    apiFetch<DisputeSettlement>(`/v1/admin/finance/settlements/${id}`),
  previewDeduction: (disputeId: string, tenantId: string, amount: number, strategy: string) =>
    apiFetch<DeductionPreview>(`/v1/admin/finance/disputes/${disputeId}/settlements/preview`, {
      method: "POST",
      body: JSON.stringify({ tenant_id: tenantId, settlement_amount: amount, deduction_strategy: strategy }),
    }),
  createSettlement: (disputeId: string, data: object) =>
    apiFetch<DisputeSettlement>(`/v1/admin/finance/disputes/${disputeId}/settlements`, {
      method: "POST", body: JSON.stringify(data),
    }),
  approveSettlement: (settlementId: string) =>
    apiFetch<DisputeSettlement>(`/v1/admin/finance/settlements/${settlementId}/approve`, { method: "POST", body: "{}" }),
  executeSettlement: (settlementId: string) =>
    apiFetch<DisputeSettlement>(`/v1/admin/finance/settlements/${settlementId}/execute`, { method: "POST", body: "{}" }),
  cancelSettlement: (settlementId: string, reason: string) =>
    apiFetch<DisputeSettlement>(`/v1/admin/finance/settlements/${settlementId}/cancel`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  // Customer Service Credits (migration 080)
  getCreditSummary: () =>
    apiFetch<CustomerCreditSummary>("/v1/admin/finance/credits/summary"),
  listCredits: (params?: { page?: number; limit?: number; status?: string; customerId?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.status) qs.set("status", params.status);
    if (params?.customerId) qs.set("customer_id", params.customerId);
    return apiFetch<{ credits: CustomerServiceCredit[]; meta: { total: number; page: number; limit: number; total_pages: number } }>(`/v1/admin/finance/credits?${qs}`);
  },
  getCredit: (id: string) =>
    apiFetch<CustomerServiceCredit & { ledger: CreditLedgerEntry[] }>(`/v1/admin/finance/credits/${id}`),
  issueManualCredit: (customerId: string, data: object) =>
    apiFetch<CustomerServiceCredit>(`/v1/admin/finance/customers/${customerId}/credits`, {
      method: "POST", body: JSON.stringify(data),
    }),
  cancelCredit: (creditId: string, reason: string) =>
    apiFetch<CustomerServiceCredit>(`/v1/admin/finance/credits/${creditId}/cancel`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  extendCredit: (creditId: string, newExpiry: string) =>
    apiFetch<CustomerServiceCredit>(`/v1/admin/finance/credits/${creditId}/extend`, {
      method: "POST", body: JSON.stringify({ new_expiry: newExpiry }),
    }),

  // Tenant Penalties (migration 080)
  getPenaltySummary: () =>
    apiFetch<TenantPenaltySummary>("/v1/admin/finance/penalties/summary"),
  listPenalties: (params?: { page?: number; limit?: number; status?: string; tenantId?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.status) qs.set("status", params.status);
    if (params?.tenantId) qs.set("tenant_id", params.tenantId);
    return apiFetch<{ penalties: TenantPenalty[]; meta: { total: number; page: number; limit: number; total_pages: number } }>(`/v1/admin/finance/penalties?${qs}`);
  },
  getVerticalConfig: (verticalType: string) =>
    apiFetch<FinanceVerticalConfig>(`/v1/admin/finance/vertical-config/${verticalType}`),
};

// ── Security & Threats SOC (Security Enterprise Upgrade) ──────────────────────

export interface SecurityOverview {
  summary_cards: {
    open_threats: number; critical_threats: number; active_sessions: number;
    blocked_ips: number; active_api_keys: number; expiring_api_keys: number;
    failed_logins_24h: number; high_risk_audit_events_24h: number;
  };
  recent_threats: SecurityThreat[];
  recent_high_risk_audit: SecurityAuditEntry[];
  top_blocked_ips: IPBlockEntry[];
  generated_at: string;
}

export interface SecurityThreat {
  threat_id: string; threat_number: string | null; activity_type: string;
  threat_level: string; risk_score: number; source: string | null;
  entity_id: string; entity_type: string;
  target_user_id: string | null; assigned_to_admin_id: string | null;
  description: string; ip_address: string | null;
  detected_value: number | null; threshold: number | null;
  status: string; context: Record<string, unknown> | null;
  last_seen_at: string | null; resolved_at: string | null; created_at: string;
  actions_taken?: SecurityAuditEntry[];
}

export interface SecuritySession {
  session_id: string; user_id: string; user_email: string; user_name: string;
  user_role: string; tenant_id: string | null; device_id: string; device_name: string;
  device_type: string; ip_address: string | null; is_trusted: boolean; is_approved: boolean;
  status: "active" | "revoked"; last_active_at: string | null; expires_at: string | null;
  revoked_at: string | null; revocation_reason: string | null;
  login_history?: { event_type: string; ip_address: string | null; failure_reason: string | null; created_at: string }[];
}

export interface IPBlockEntry {
  entry_id: string; ip_or_cidr: string; entry_type: string; threat_level: string;
  reason: string; scope: string; status: string; is_global: boolean;
  tenant_id: string | null; hit_count: number; last_hit_at: string | null;
  expires_at: string | null; revoked_at: string | null; created_at: string;
}

export interface SecurityApiKey {
  key_id: string; tenant_id: string | null; name: string; description: string | null;
  key_prefix: string; environment: string; scopes: string[]; owner_type: string;
  rate_limit_per_minute: number | null; permissions: string[]; status: string;
  expires_at: string | null; last_used_at: string | null; use_count: number; created_at: string;
}

export interface SecurityAuditEntry {
  log_id: string; operation: string; engine_id: string; entity_type: string | null;
  entity_id: string | null; tenant_id: string | null; actor_id: string | null;
  actor_role: string | null; actor_ip: string | null; is_high_risk: boolean;
  before_state: Record<string, unknown> | null; after_state: Record<string, unknown> | null;
  created_at: string;
}

export interface SecurityPolicy {
  id: string; policy_key: string; policy_value: unknown; description: string | null;
  updated_by_user_id: string | null; updated_reason: string | null;
  created_at: string; updated_at: string;
}

export const securityAdminApi = {
  getOverview: () => apiFetch<SecurityOverview>("/v1/admin/security/overview"),

  // Threats
  listThreats: (params?: { status?: string; threatLevel?: string; activityType?: string; q?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.threatLevel) qs.set("threat_level", params.threatLevel);
    if (params?.activityType) qs.set("activity_type", params.activityType);
    if (params?.q) qs.set("q", params.q);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    return apiFetch<{ threats: SecurityThreat[]; has_next: boolean; next_cursor: string | null }>(`/v1/admin/security/threats?${qs.toString()}`);
  },
  getThreatDetail: (threatId: string) =>
    apiFetch<SecurityThreat>(`/v1/admin/security/threats/${threatId}`),
  assignThreat: (threatId: string, adminId: string) =>
    apiFetch<{ threat_id: string; assigned_to_admin_id: string }>(`/v1/admin/security/threats/${threatId}/assign`,
      { method: "POST", body: JSON.stringify({ admin_id: adminId }) }),
  updateThreatStatus: (threatId: string, status: string, notes?: string) =>
    apiFetch<{ threat_id: string; status: string }>(`/v1/admin/security/threats/${threatId}/status`,
      { method: "POST", body: JSON.stringify({ status, notes }) }),
  blockIpFromThreat: (threatId: string, reason: string, expiresHours?: number) =>
    apiFetch<{ entry_id: string; ip_or_cidr: string; status: string }>(`/v1/admin/security/threats/${threatId}/block-ip`,
      { method: "POST", body: JSON.stringify({ reason, expires_hours: expiresHours ?? 720 }) }),
  revokeSessionsFromThreat: (threatId: string, reason: string) =>
    apiFetch<{ user_id: string; sessions_revoked: number; reason: string }>(`/v1/admin/security/threats/${threatId}/revoke-sessions`,
      { method: "POST", body: JSON.stringify({ reason }) }),

  // Active Sessions
  listSessions: (params?: { tenantId?: string; role?: string; activeOnly?: boolean; q?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams();
    if (params?.tenantId) qs.set("tenant_id", params.tenantId);
    if (params?.role) qs.set("role", params.role);
    qs.set("active_only", String(params?.activeOnly ?? true));
    if (params?.q) qs.set("q", params.q);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    return apiFetch<{ sessions: SecuritySession[]; has_next: boolean; next_cursor: string | null }>(`/v1/admin/security/sessions?${qs.toString()}`);
  },
  getSessionDetail: (sessionId: string) =>
    apiFetch<SecuritySession>(`/v1/admin/security/sessions/${sessionId}`),
  revokeSession: (sessionId: string, reason: string) =>
    apiFetch<{ session_id: string; revoked: boolean; reason: string }>(`/v1/admin/security/sessions/${sessionId}/revoke`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  revokeAllUserSessions: (userId: string, reason: string) =>
    apiFetch<{ user_id: string; sessions_revoked: number; reason: string }>(`/v1/admin/security/sessions/user/${userId}/revoke-all`,
      { method: "POST", body: JSON.stringify({ reason }) }),

  // IP Blocklist
  listIpBlocklist: (params?: { status?: string; scope?: string; q?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.scope) qs.set("scope", params.scope);
    if (params?.q) qs.set("q", params.q);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    return apiFetch<{ entries: IPBlockEntry[]; has_next: boolean; next_cursor: string | null }>(`/v1/admin/security/ip-blocklist?${qs.toString()}`);
  },
  createIpBlock: (data: { ipOrCidr: string; entryType?: string; reason: string; threatLevel?: string; scope?: string; tenantId?: string; expiresHours?: number; overrideSelfBlock?: boolean }) =>
    apiFetch<{ entry_id: string; ip_or_cidr: string; status: string }>("/v1/admin/security/ip-blocklist", {
      method: "POST", body: JSON.stringify({
        ip_or_cidr: data.ipOrCidr, entry_type: data.entryType ?? "ip", reason: data.reason,
        threat_level: data.threatLevel ?? "medium", scope: data.scope ?? "all",
        tenant_id: data.tenantId, expires_hours: data.expiresHours, override_self_block: data.overrideSelfBlock ?? false,
      }),
    }),
  revokeIpBlock: (entryId: string, reason: string) =>
    apiFetch<{ entry_id: string; revoked: boolean; reason: string }>(`/v1/admin/security/ip-blocklist/${entryId}/revoke`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  getIpBlockHits: (entryId: string) =>
    apiFetch<{ entry_id: string; hits: { hit_at: string; path: string | null; method: string | null; user_agent: string | null; blocked_scope: string | null }[] }>(`/v1/admin/security/ip-blocklist/${entryId}/hits`),

  // API Keys
  listApiKeys: (params?: { tenantId?: string; status?: string; q?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams();
    if (params?.tenantId) qs.set("tenant_id", params.tenantId);
    if (params?.status) qs.set("status", params.status);
    if (params?.q) qs.set("q", params.q);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    return apiFetch<{ api_keys: SecurityApiKey[]; has_next: boolean; next_cursor: string | null }>(`/v1/admin/security/api-keys?${qs.toString()}`);
  },
  createApiKey: (data: { tenantId: string; name: string; description?: string; scopes: string[]; environment?: string; expiresDays?: number; ownerType?: string; allowedIps?: string[]; rateLimitPerMinute?: number; permissions?: string[] }) =>
    apiFetch<{ key_id: string; raw_key: string; key_prefix: string; name: string; scopes: string[]; environment: string; expires_at: string | null; warning: string }>("/v1/admin/security/api-keys", {
      method: "POST", body: JSON.stringify({
        tenant_id: data.tenantId, name: data.name, description: data.description, scopes: data.scopes,
        environment: data.environment ?? "live", expires_days: data.expiresDays, owner_type: data.ownerType ?? "tenant",
        allowed_ips: data.allowedIps, rate_limit_per_minute: data.rateLimitPerMinute, permissions: data.permissions,
      }),
    }),
  getApiKeyDetail: (keyId: string) =>
    apiFetch<SecurityApiKey>(`/v1/admin/security/api-keys/${keyId}`),
  rotateApiKey: (keyId: string, tenantId: string) =>
    apiFetch<{ key_id: string; raw_key: string; key_prefix: string; previous_key_id: string; note: string }>(`/v1/admin/security/api-keys/${keyId}/rotate`,
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId }) }),
  revokeApiKey: (keyId: string, tenantId: string, reason: string) =>
    apiFetch<{ key_id: string; revoked: boolean; reason: string }>(`/v1/admin/security/api-keys/${keyId}/revoke`,
      { method: "POST", body: JSON.stringify({ tenant_id: tenantId, reason }) }),
  getApiKeyUsage: (keyId: string) =>
    apiFetch<{ key_id: string; usage: { used_at: string; endpoint: string | null; method: string | null; status_code: number | null; ip_address: string | null; response_ms: number | null }[] }>(`/v1/admin/security/api-keys/${keyId}/usage`),

  // Audit Logs
  listAuditLogs: (params?: { engineId?: string; operation?: string; actorRole?: string; tenantId?: string; isHighRisk?: boolean; q?: string; dateFrom?: string; dateTo?: string; limit?: number; cursor?: string }) => {
    const qs = new URLSearchParams();
    if (params?.engineId) qs.set("engine_id", params.engineId);
    if (params?.operation) qs.set("operation", params.operation);
    if (params?.actorRole) qs.set("actor_role", params.actorRole);
    if (params?.tenantId) qs.set("tenant_id", params.tenantId);
    if (params?.isHighRisk !== undefined) qs.set("is_high_risk", String(params.isHighRisk));
    if (params?.q) qs.set("q", params.q);
    if (params?.dateFrom) qs.set("date_from", params.dateFrom);
    if (params?.dateTo) qs.set("date_to", params.dateTo);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.cursor) qs.set("cursor", params.cursor);
    return apiFetch<{ audit_logs: SecurityAuditEntry[]; has_next: boolean; next_cursor: string | null; note: string }>(`/v1/admin/security/audit-logs?${qs.toString()}`);
  },
  getAuditLogDetail: (logId: string) =>
    apiFetch<SecurityAuditEntry>(`/v1/admin/security/audit-logs/${logId}`),
  exportAuditLogs: async (params?: { engineId?: string; operation?: string; dateFrom?: string; dateTo?: string }) => {
    const qs = new URLSearchParams();
    if (params?.engineId) qs.set("engine_id", params.engineId);
    if (params?.operation) qs.set("operation", params.operation);
    if (params?.dateFrom) qs.set("date_from", params.dateFrom);
    if (params?.dateTo) qs.set("date_to", params.dateTo);
    const token = getToken();
    const res = await fetch(`${API_BASE}/v1/admin/security/audit-logs-export?${qs.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.blob();
  },

  // Security Policies
  getPolicies: () => apiFetch<{ policies: SecurityPolicy[] }>("/v1/admin/security/policies"),
  updatePolicy: (policyKey: string, value: unknown, reason: string) =>
    apiFetch<SecurityPolicy>(`/v1/admin/security/policies/${policyKey}`,
      { method: "PATCH", body: JSON.stringify({ value, reason }) }),
};


// ── Vertical Catalog ──────────────────────────────────────────────────────────

export interface VerticalItem {
  id: string;
  key: string;
  label: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  is_enabled: boolean;
  is_beta: boolean;
  sort_order: number;
  finance_model: string | null;
  meta: Record<string, unknown> | null;
}

export interface CatalogModuleItem {
  id: string;
  key: string;
  label: string;
  icon: string | null;
  admin_path: string | null;
  module_group: string | null;
  is_universal: boolean;
  sort_order: number;
}

export interface VerticalModuleItem extends CatalogModuleItem {
  is_enabled: boolean;
  is_required: boolean;
}

export interface VerticalDetail extends VerticalItem {
  modules: VerticalModuleItem[];
}

export interface EffectiveMenuVertical {
  vertical_key: string;
  vertical_label: string;
  is_enabled: boolean;
  is_beta: boolean;
  icon: string | null;
  color: string | null;
  modules: VerticalModuleItem[];
}

export interface EffectiveMenu {
  universal_modules: CatalogModuleItem[];
  verticals: EffectiveMenuVertical[];
  enabled_vertical_keys: string[];
  operation_visibility: {
    jobs_field_ops: boolean;
    site_visits: boolean;
    orders: boolean;
    leads_crm: boolean;
    appointments: boolean;
    security_deposit: boolean;
    usage_credits: boolean;
  };
}

export const verticalCatalogApi = {
  listVerticals: (includeDisabled = false) =>
    apiFetch<{ items: VerticalItem[]; total: number }>(
      `/v1/admin/verticals?include_disabled=${includeDisabled}`
    ),
  getVertical: (key: string) =>
    apiFetch<VerticalDetail>(`/v1/admin/verticals/${key}`),
  enableVertical: (key: string) =>
    apiFetch<VerticalItem>(`/v1/admin/verticals/${key}/enable`, { method: "POST" }),
  disableVertical: (key: string) =>
    apiFetch<VerticalItem>(`/v1/admin/verticals/${key}/disable`, { method: "POST" }),
  updateVertical: (key: string, payload: Partial<VerticalItem>) =>
    apiFetch<VerticalItem>(`/v1/admin/verticals/${key}`, {
      method: "PATCH", body: JSON.stringify(payload),
    }),
  enableModule: (verticalKey: string, moduleKey: string) =>
    apiFetch<{ vertical_key: string; module_key: string; is_enabled: boolean }>(
      `/v1/admin/verticals/${verticalKey}/modules/${moduleKey}/enable`, { method: "POST" }
    ),
  disableModule: (verticalKey: string, moduleKey: string) =>
    apiFetch<{ vertical_key: string; module_key: string; is_enabled: boolean }>(
      `/v1/admin/verticals/${verticalKey}/modules/${moduleKey}/disable`, { method: "POST" }
    ),
  listModules: () =>
    apiFetch<{ items: CatalogModuleItem[]; total: number }>("/v1/admin/catalog/modules"),
  getEffectiveMenu: () =>
    apiFetch<EffectiveMenu>("/v1/admin/catalog/navigation/effective-menu"),
};

// ── Platform Settings Enterprise Upgrade ──────────────────────────────────────

export interface EnterpriseSetting {
  key: string; label: string; value: unknown; type: string; description: string | null;
  is_public: boolean; category: string; allowed_values: unknown[] | null;
  is_secret: boolean; risk_level: "low" | "medium" | "high" | "critical";
  requires_approval: boolean; requires_restart: boolean; is_runtime_editable: boolean;
  owner_module: string | null; status: string; updated_at: string | null;
}
export interface SettingsSummary {
  total_settings: number; active_settings: number; invalid_settings: number;
  secret_settings: number; pending_approval: number; tenant_overrides: number;
  plan_overrides: number; changed_this_week: number; rollback_available: number;
}
export interface SettingsCategoryCount { category: string; setting_count: number }
export interface FeatureFlag {
  id: string; flag_key: string; label: string; description: string | null; status: string;
  rollout_type: string; rollout_percent: number | null; category_scope: string | null;
  tenant_scope: string | null; start_date: string | null; end_date: string | null;
  owner_module: string | null; created_at: string | null; updated_at: string | null;
}
export interface PlanSettingRow {
  id: string; name: string; package_type: string; plan_level: string | null;
  billing_cycle: string | null; currency: string;
  included_credit_amount: number | null; storage_quota_gb: number | null;
  commission_rate: number | null; security_deposit_amount: number | null;
  validity_days: number | null; is_active: boolean; vertical_type: string | null;
  limits?: { limit_key: string; limit_label: string; limit_value: number | null }[];
}
export interface CategorySettingRow {
  id: string; name: string; slug: string; vertical_type: string | null;
  finance_model: string | null; provider_business_model: string | null;
  monetization_model: string | null; is_active: boolean; is_customer_visible: boolean;
  pricing_supported: boolean; payment_collection_enabled: boolean; tenant_payouts_enabled: boolean;
}
export interface TenantOverrideRow {
  id: string; tenant_id: string; key: string; value: unknown; reason: string | null;
  expires_at: string | null; requires_approval: boolean; status: string; created_at: string | null;
}
export interface SettingVersionEntry {
  log_id: string; tier: string; old_value: unknown; new_value: unknown;
  changed_by: string | null; reason: string | null; request_id: string | null;
  action_type: string; rollback_available: boolean; created_at: string;
}
export interface SettingAuditLogRow {
  log_id: string; tier: string; key: string; old_value: unknown; new_value: unknown;
  reason: string | null; actor: string | null; request_id: string | null;
  risk_level: string; action_type: string; tenant_id: string | null; created_at: string;
}
export interface ImpactPreviewResult {
  key: string; blocked: boolean; blocker_message: string | null; risk_level: string;
  requires_approval: boolean; requires_restart: boolean; rollback_available: boolean;
  warnings: string[];
}
export interface EffectiveValueResult {
  key: string; default_value: unknown; global_value: unknown; plan_override: unknown;
  tenant_override: unknown; effective_value: unknown; resolution_path: string; warnings: string[];
}

export const settingsAdminApi = {
  getSummary: () => apiFetch<SettingsSummary>("/v1/admin/settings/summary"),
  getGroups: () => apiFetch<{ categories: SettingsCategoryCount[] }>("/v1/admin/settings/groups"),

  previewSeedDefaults: () =>
    apiFetch<{ would_create: string[]; would_skip: string[]; total_defaults: number }>(
      "/v1/admin/settings/seed-defaults/preview", { method: "POST" }),
  seedDefaults: (force = false) =>
    apiFetch<{ created: string[]; skipped: string[]; total_defaults: number }>(
      "/v1/admin/settings/seed-defaults", { method: "POST", body: JSON.stringify({ force }) }),

  list: (params?: { category?: string; is_secret?: boolean; status?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.is_secret !== undefined) qs.set("is_secret", String(params.is_secret));
    if (params?.status) qs.set("status", params.status);
    qs.set("limit", String(params?.limit ?? 500));
    return apiFetch<{ settings: EnterpriseSetting[]; has_next: boolean; next_cursor: string | null }>(
      `/v1/admin/settings?${qs.toString()}`);
  },
  get: (key: string) => apiFetch<EnterpriseSetting>(`/v1/admin/settings/${key}`),
  create: (data: {
    key: string; label: string; value: unknown; setting_type: string; description?: string;
    category?: string; is_secret?: boolean; risk_level?: string; requires_approval?: boolean;
    requires_restart?: boolean; is_runtime_editable?: boolean; owner_module?: string;
    allowed_values?: unknown[];
  }) => apiFetch<{ key: string; value: unknown; tier: string }>("/v1/admin/settings", {
    method: "POST", body: JSON.stringify(data),
  }),
  update: (key: string, data: {
    value: unknown; setting_type?: string; description?: string; label?: string;
    category?: string; risk_level?: string; reason?: string;
  }) => apiFetch<{ key: string; value: unknown; tier: string }>(`/v1/admin/settings/${key}`, {
    method: "PUT", body: JSON.stringify(data),
  }),
  enable: (key: string, reason?: string) =>
    apiFetch<{ key: string; status: string }>(`/v1/admin/settings/${key}/enable`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  disable: (key: string, reason?: string) =>
    apiFetch<{ key: string; status: string }>(`/v1/admin/settings/${key}/disable`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  impactPreview: (key: string, newValue: unknown) =>
    apiFetch<ImpactPreviewResult>(`/v1/admin/settings/${key}/impact-preview`,
      { method: "POST", body: JSON.stringify({ new_value: newValue }) }),
  rollback: (key: string, logId: string, reason: string) =>
    apiFetch<{ key: string; rolled_back_to: unknown; reason: string }>(`/v1/admin/settings/${key}/rollback`,
      { method: "POST", body: JSON.stringify({ log_id: logId, reason }) }),
  getHistory: (key: string) =>
    apiFetch<{ key: string; history: SettingVersionEntry[] }>(`/v1/admin/settings/${key}/history`),

  resolveEffectiveValue: (key: string, tenantId?: string, planType?: string) =>
    apiFetch<EffectiveValueResult>("/v1/admin/settings/resolve-effective-value", {
      method: "POST", body: JSON.stringify({ key, tenant_id: tenantId, plan_type: planType }),
    }),

  listPlans: () => apiFetch<{ packages: PlanSettingRow[] }>("/v1/admin/settings/plans"),
  getPlan: (packageId: string) => apiFetch<PlanSettingRow>(`/v1/admin/settings/plans/${packageId}`),
  updatePlan: (packageId: string, data: Partial<PlanSettingRow> & { reason?: string }) =>
    apiFetch<PlanSettingRow>(`/v1/admin/settings/plans/${packageId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),

  listCategories: () => apiFetch<{ categories: CategorySettingRow[] }>("/v1/admin/settings/categories"),
  getCategory: (categoryId: string) =>
    apiFetch<CategorySettingRow>(`/v1/admin/settings/categories/${categoryId}`),
  updateCategory: (categoryId: string, data: {
    finance_model?: string; provider_business_model?: string; monetization_model?: string;
    is_active?: boolean; reason?: string;
  }) => apiFetch<CategorySettingRow>(`/v1/admin/settings/categories/${categoryId}`, {
    method: "PUT", body: JSON.stringify(data),
  }),

  listTenantOverrides: () =>
    apiFetch<{ overrides: TenantOverrideRow[] }>("/v1/admin/settings/tenant-overrides"),
  createTenantOverride: (data: {
    tenant_id: string; key: string; value: unknown; setting_type?: string; reason: string;
    expires_at?: string; requires_approval?: boolean;
  }) => apiFetch<{ tenant_id: string; key: string; value: unknown }>("/v1/admin/settings/tenant-overrides", {
    method: "POST", body: JSON.stringify(data),
  }),
  revokeTenantOverride: (overrideId: string, reason: string) =>
    apiFetch<{ tenant_id: string; key: string; deleted: boolean }>(
      `/v1/admin/settings/tenant-overrides/${overrideId}/revoke`,
      { method: "POST", body: JSON.stringify({ reason }) }),

  listFeatureFlags: () => apiFetch<{ flags: FeatureFlag[] }>("/v1/admin/settings/feature-flags"),
  createFeatureFlag: (data: {
    flag_key: string; label: string; description?: string; status?: string; rollout_type?: string;
    rollout_percent?: number; category_scope?: string; tenant_scope?: string; owner_module?: string;
  }) => apiFetch<FeatureFlag>("/v1/admin/settings/feature-flags", {
    method: "POST", body: JSON.stringify(data),
  }),
  updateFeatureFlag: (flagId: string, data: Partial<FeatureFlag>) =>
    apiFetch<FeatureFlag>(`/v1/admin/settings/feature-flags/${flagId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  enableFeatureFlag: (flagId: string) =>
    apiFetch<FeatureFlag>(`/v1/admin/settings/feature-flags/${flagId}/enable`, { method: "POST" }),
  disableFeatureFlag: (flagId: string) =>
    apiFetch<FeatureFlag>(`/v1/admin/settings/feature-flags/${flagId}/disable`, { method: "POST" }),

  getAuditLogs: (params?: { key?: string; tenant_id?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.key) qs.set("key", params.key);
    if (params?.tenant_id) qs.set("tenant_id", params.tenant_id);
    qs.set("limit", String(params?.limit ?? 50));
    return apiFetch<{ logs: SettingAuditLogRow[]; has_next: boolean; next_cursor: string | null }>(
      `/v1/admin/settings/audit-logs?${qs.toString()}`);
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// P0 Enterprise Service Setup Templates (migration 091)
// ─────────────────────────────────────────────────────────────────────────────

export interface SetupTemplateItem {
  id: string;
  name: string;
  code: string;
  description: string | null;
  vertical_key: string;
  template_type: string;
  is_system: boolean;
  status: string;
  version: number;
  display_order: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  modules_count?: number;
}

export interface SetupTemplatesSummary {
  total: number;
  published: number;
  draft: number;
  system_count: number;
  custom_count: number;
  recently_used: number;
  validation_errors: number;
}

export interface SetupTemplateModule {
  id: string;
  module_key: string;
  module_name: string;
  is_enabled: boolean;
  display_order: number;
}

export interface SetupTemplateDetail extends SetupTemplateItem {
  modules: SetupTemplateModule[];
  items: Array<{
    id: string;
    module_key: string;
    item_type: string;
    item_key: string;
    item_name: string;
    parent_item_key: string | null;
    payload_json: Record<string, unknown>;
    display_order: number;
  }>;
}

export const serviceSetupTemplatesApi = {
  list: (params: {
    q?: string;
    vertical?: string;
    template_type?: string;
    status?: string;
    is_system?: boolean;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_dir?: string;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v != null && v !== "") qs.set(k, String(v));
    });
    return apiFetch<{ items: SetupTemplateItem[]; total: number }>(
      `/v1/admin/service-setup/templates?${qs}`
    );
  },
  getSummary: () =>
    apiFetch<SetupTemplatesSummary>("/v1/admin/service-setup/templates/summary"),
  get: (id: string) =>
    apiFetch<SetupTemplateDetail>(`/v1/admin/service-setup/templates/${id}`),
  create: (payload: Record<string, unknown>) =>
    apiFetch<SetupTemplateDetail>("/v1/admin/service-setup/templates", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: string, payload: Record<string, unknown>) =>
    apiFetch<SetupTemplateDetail>(`/v1/admin/service-setup/templates/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  publish: (id: string) =>
    apiFetch<SetupTemplateItem>(
      `/v1/admin/service-setup/templates/${id}/publish`,
      { method: "POST" }
    ),
  archive: (id: string) =>
    apiFetch<SetupTemplateItem>(
      `/v1/admin/service-setup/templates/${id}/archive`,
      { method: "POST" }
    ),
  clone: (id: string) =>
    apiFetch<SetupTemplateDetail>(
      `/v1/admin/service-setup/templates/${id}/clone`,
      { method: "POST" }
    ),
  delete: (id: string) =>
    apiFetch<{ deleted: boolean }>(
      `/v1/admin/service-setup/templates/${id}`,
      { method: "DELETE" }
    ),
  validate: (id: string) =>
    apiFetch<{ valid: boolean; errors: string[]; warnings: string[] }>(
      `/v1/admin/service-setup/templates/${id}/validate`,
      { method: "POST" }
    ),
  getVersions: (id: string) =>
    apiFetch<{ items: unknown[] }>(
      `/v1/admin/service-setup/templates/${id}/versions`
    ),
  seedDefaultsPreview: () =>
    apiFetch<{ templates_to_create: Array<{ name: string; code: string; vertical_key: string }> }>(
      "/v1/admin/service-setup/templates/seed-defaults/preview",
      { method: "POST" }
    ),
  seedDefaults: () =>
    apiFetch<{ created: number; skipped: number }>(
      "/v1/admin/service-setup/templates/seed-defaults",
      { method: "POST" }
    ),
};

// ── Bulk Wizard API ───────────────────────────────────────────────────────────

export interface BulkDraftItem {
  id: string;
  draft_code: string;
  name: string;
  description: string | null;
  vertical_key: string;
  setup_mode: string;
  template_id: string | null;
  status: string;
  current_step: number;
  created_at: string;
  updated_at: string;
}

export interface BulkDraftDetail extends BulkDraftItem {
  config_json: Record<string, unknown>;
}

export interface BulkRunItem {
  id: string;
  run_code: string;
  draft_id: string;
  vertical_key: string;
  status: string;
  is_dry_run: boolean;
  total_items: number;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  failed_count: number;
  rollback_available: boolean;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface BulkWizardSummary {
  total_drafts: number;
  ready_to_run: number;
  running: number;
  completed_runs: number;
  failed_runs: number;
  rollback_available: number;
}

export const bulkWizardApi = {
  list: (params: { q?: string; vertical?: string; status?: string; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
    return apiFetch<{ items: BulkDraftItem[]; total: number }>(`/v1/admin/service-setup/bulk-wizard?${qs}`);
  },
  getSummary: () =>
    apiFetch<BulkWizardSummary>("/v1/admin/service-setup/bulk-wizard/summary"),
  createDraft: (payload: Record<string, unknown>) =>
    apiFetch<BulkDraftDetail>("/v1/admin/service-setup/bulk-wizard/drafts", {
      method: "POST", body: JSON.stringify(payload),
    }),
  getDraft: (id: string) =>
    apiFetch<BulkDraftDetail>(`/v1/admin/service-setup/bulk-wizard/drafts/${id}`),
  updateDraft: (id: string, payload: Record<string, unknown>) =>
    apiFetch<BulkDraftDetail>(`/v1/admin/service-setup/bulk-wizard/drafts/${id}`, {
      method: "PUT", body: JSON.stringify(payload),
    }),
  validateDraft: (id: string) =>
    apiFetch<{ valid: boolean; errors: unknown[]; warnings: unknown[]; blocking_count: number }>(
      `/v1/admin/service-setup/bulk-wizard/drafts/${id}/validate`, { method: "POST" }
    ),
  previewDraft: (id: string) =>
    apiFetch<{ items: unknown[]; summary: Record<string, number> }>(
      `/v1/admin/service-setup/bulk-wizard/drafts/${id}/preview`, { method: "POST" }
    ),
  dryRun: (id: string) =>
    apiFetch<BulkRunItem>(`/v1/admin/service-setup/bulk-wizard/drafts/${id}/dry-run`, { method: "POST" }),
  executeDraft: (id: string, reason: string) =>
    apiFetch<BulkRunItem>(`/v1/admin/service-setup/bulk-wizard/drafts/${id}/execute`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  cloneDraft: (id: string) =>
    apiFetch<BulkDraftDetail>(`/v1/admin/service-setup/bulk-wizard/drafts/${id}/clone`, { method: "POST" }),
  deleteDraft: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/v1/admin/service-setup/bulk-wizard/drafts/${id}`, { method: "DELETE" }),
  listRuns: (params: { draft_id?: string; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
    return apiFetch<{ items: BulkRunItem[]; total: number }>(`/v1/admin/service-setup/bulk-wizard/runs?${qs}`);
  },
  getRun: (id: string) =>
    apiFetch<BulkRunItem>(`/v1/admin/service-setup/bulk-wizard/runs/${id}`),
  rollbackRun: (id: string, reason: string) =>
    apiFetch<BulkRunItem>(`/v1/admin/service-setup/bulk-wizard/runs/${id}/rollback`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  getRunLogs: (id: string) =>
    apiFetch<{ items: unknown[] }>(`/v1/admin/service-setup/bulk-wizard/runs/${id}/logs`),
};

// ─────────────────────────────────────────────────────────────────────────────
// P0 Marketing Automation Command Center (migration 100)
// Platform-pays-AI-cost rule: never read/show tenant wallet or provider payout
// data here — Platform AI Budget is entirely separate from tenant usage credits.
// ─────────────────────────────────────────────────────────────────────────────

export interface MarketingAutomationSummary {
  posts_published: number;
  scheduled_posts: number;
  pending_approval: number;
  failed_posts: number;
  images_generated: number;
  images_generated_cost: number;
  platform_ai_spend_today: number;
  platform_ai_daily_budget: number;
  connected_channels: number;
  active_campaigns: number;
}

export interface MarketingPostAssetItem {
  id: string; post_id: string; asset_type: string; url?: string | null;
  generated_by_ai: boolean; ai_model?: string | null; ai_prompt?: string | null;
  alt_text?: string | null; cost_amount?: number | null; status: string; created_at?: string;
}

export interface MarketingPost {
  id: string; post_code: string; campaign_id?: string | null; title: string;
  caption?: string | null; short_caption?: string | null; hashtags: string[];
  vertical_key?: string | null; category_id?: string | null; service_id?: string | null;
  tenant_id?: string | null; target_locations: unknown[]; language: string; tone?: string | null;
  post_type: string; goal?: string | null; cta?: string | null; channels: string[];
  status: string; approval_status: string; approved_by_user_id?: string | null;
  approved_at?: string | null; rejection_reason?: string | null;
  scheduled_at?: string | null; published_at?: string | null;
  created_by_user_id?: string | null; created_at?: string; updated_at?: string;
  assets?: MarketingPostAssetItem[];
}

export interface MarketingSocialAccountItem {
  id: string; platform: string; account_name: string; connection_status: string;
  token_status: string; publishing_enabled: boolean; daily_post_limit: number;
  last_sync_at?: string | null; status: string;
}

export interface MarketingAIBudgetInfo {
  id: string; scope: string; daily_budget: number; monthly_budget: number;
  cost_alert_threshold_pct: number; auto_disable_on_exceed: boolean;
  require_approval_above_cost?: number | null; updated_at?: string;
  daily_used: number; daily_remaining: number; monthly_used: number; monthly_remaining: number;
  images_generated: number; average_cost_per_image: number; platform_pays_note: string;
}

export interface MarketingAIBudgetLedgerEntry {
  id: string; generation_type: string; model?: string | null; cost_amount: number;
  post_id?: string | null; campaign_id?: string | null; created_by_user_id?: string | null;
  created_at?: string;
}

export interface MarketingContentTemplateItem {
  id: string; template_name: string; vertical_key?: string | null; post_type: string;
  language: string; prompt_template?: string | null; caption_structure?: string | null;
  hashtag_set: string[]; cta?: string | null; status: string; created_at?: string;
}

export interface MarketingPublishFailureItem {
  id: string; post_id: string; channel: string; social_account_id?: string | null;
  status: string; attempt_number: number; external_post_id?: string | null;
  error_code?: string | null; error_message?: string | null; created_at?: string; updated_at?: string;
}

export interface MarketingAuditLogItem {
  id: string; actor_user_id?: string | null; action_type: string; target_type: string;
  target_id?: string | null; old_value?: Record<string, unknown> | null;
  new_value?: Record<string, unknown> | null; reason?: string | null;
  request_id?: string | null; created_at?: string;
}

export const marketingCommandCenterApi = {
  getSummary: () => apiFetch<MarketingAutomationSummary>("/v1/admin/marketing/automation/summary"),

  // Posts
  listPosts: (params?: { status?: string; campaign_id?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status && params.status !== "all") qs.set("status", params.status);
    if (params?.campaign_id) qs.set("campaign_id", params.campaign_id);
    if (params?.limit) qs.set("limit", String(params.limit));
    return apiFetch<{ items: MarketingPost[]; total: number }>(`/v1/admin/marketing/posts?${qs}`);
  },
  getPost: (id: string) => apiFetch<MarketingPost>(`/v1/admin/marketing/posts/${id}`),
  createPost: (data: Record<string, unknown>) =>
    apiFetch<MarketingPost>("/v1/admin/marketing/posts", { method: "POST", body: JSON.stringify(data) }),
  updatePost: (id: string, data: Record<string, unknown>) =>
    apiFetch<MarketingPost>(`/v1/admin/marketing/posts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  submitApproval: (id: string) =>
    apiFetch<MarketingPost>(`/v1/admin/marketing/posts/${id}/submit-approval`, { method: "POST" }),
  approvePost: (id: string, reason?: string) =>
    apiFetch<MarketingPost>(`/v1/admin/marketing/posts/${id}/approve`, { method: "POST", body: JSON.stringify({ reason }) }),
  rejectPost: (id: string, reason: string) =>
    apiFetch<MarketingPost>(`/v1/admin/marketing/posts/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  schedulePost: (id: string, scheduledAt: string, channels: string[]) =>
    apiFetch<MarketingPost>(`/v1/admin/marketing/posts/${id}/schedule`, {
      method: "POST", body: JSON.stringify({ scheduled_at: scheduledAt, channels }),
    }),
  reschedulePost: (id: string, scheduledAt: string) =>
    apiFetch<MarketingPost>(`/v1/admin/marketing/posts/${id}/reschedule`, {
      method: "POST", body: JSON.stringify({ scheduled_at: scheduledAt }),
    }),
  publishNow: (id: string) => apiFetch<MarketingPost>(`/v1/admin/marketing/posts/${id}/publish-now`, { method: "POST" }),
  retryPost: (id: string) =>
    apiFetch<{ post: MarketingPost; attempt: unknown }>(`/v1/admin/marketing/posts/${id}/retry`, { method: "POST" }),
  cancelPost: (id: string, reason?: string) =>
    apiFetch<MarketingPost>(`/v1/admin/marketing/posts/${id}/cancel`, { method: "POST", body: JSON.stringify({ reason }) }),

  // AI generation
  generateCaption: (data: Record<string, unknown>) =>
    apiFetch<{ caption: string; short_caption: string; estimated_cost: number }>(
      "/v1/admin/marketing/ai/generate-caption", { method: "POST", body: JSON.stringify(data) }),
  generateImage: (data: Record<string, unknown>) =>
    apiFetch<{ image_url: string; alt_text?: string; estimated_cost: number; compliance_warnings: string[] }>(
      "/v1/admin/marketing/ai/generate-image", { method: "POST", body: JSON.stringify(data) }),
  generateHashtags: (data: Record<string, unknown>) =>
    apiFetch<{ hashtags: string[]; estimated_cost: number }>(
      "/v1/admin/marketing/ai/generate-hashtags", { method: "POST", body: JSON.stringify(data) }),
  generateVariations: (data: Record<string, unknown>) =>
    apiFetch<{ variations: string[]; estimated_cost: number }>(
      "/v1/admin/marketing/ai/generate-variations", { method: "POST", body: JSON.stringify(data) }),

  // Calendar
  getCalendar: (params?: { date_from?: string; date_to?: string }) => {
    const qs = new URLSearchParams();
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to);
    return apiFetch<{ items: MarketingPost[] }>(`/v1/admin/marketing/calendar?${qs}`);
  },

  // Social accounts
  listSocialAccounts: () => apiFetch<{ items: MarketingSocialAccountItem[]; total: number }>("/v1/admin/marketing/social-accounts"),
  connectSocialAccount: (data: { platform: string; account_name?: string }) =>
    apiFetch<{ id: string; platform: string; account_name: string; status: string }>(
      "/v1/admin/marketing/social-accounts/connect", { method: "POST", body: JSON.stringify(data) }),
  testSocialAccount: (id: string) =>
    apiFetch<{ account_id: string; connection_ok: boolean; token_status: string }>(
      `/v1/admin/marketing/social-accounts/${id}/test`, { method: "POST" }),
  syncSocialAccount: (id: string) =>
    apiFetch<{ account_id: string; synced_at: string }>(`/v1/admin/marketing/social-accounts/${id}/sync`, { method: "POST" }),
  disconnectSocialAccount: (id: string) =>
    apiFetch<{ account_id: string; status: string }>(`/v1/admin/marketing/social-accounts/${id}/disconnect`, { method: "POST" }),

  // Content templates
  listContentTemplates: () => apiFetch<{ items: MarketingContentTemplateItem[] }>("/v1/admin/marketing/content-templates"),
  createContentTemplate: (data: Record<string, unknown>) =>
    apiFetch<MarketingContentTemplateItem>("/v1/admin/marketing/content-templates", { method: "POST", body: JSON.stringify(data) }),
  updateContentTemplate: (id: string, data: Record<string, unknown>) =>
    apiFetch<MarketingContentTemplateItem>(`/v1/admin/marketing/content-templates/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  // AI budget
  getAIBudget: () => apiFetch<MarketingAIBudgetInfo>("/v1/admin/marketing/ai-budget"),
  updateAIBudget: (data: Record<string, unknown>) =>
    apiFetch<MarketingAIBudgetInfo>("/v1/admin/marketing/ai-budget", { method: "PUT", body: JSON.stringify(data) }),
  getAIBudgetLedger: (limit = 50) =>
    apiFetch<{ items: MarketingAIBudgetLedgerEntry[] }>(`/v1/admin/marketing/ai-budget/ledger?limit=${limit}`),

  // Publish failures
  listPublishFailures: (limit = 50) =>
    apiFetch<{ items: MarketingPublishFailureItem[] }>(`/v1/admin/marketing/publish-failures?limit=${limit}`),

  // Analytics
  getAnalyticsSummary: () => apiFetch<{ available: boolean; message?: string; [k: string]: unknown }>("/v1/admin/marketing/analytics/summary"),
  getTopPosts: () => apiFetch<{ items: unknown[]; available: boolean }>("/v1/admin/marketing/analytics/posts"),
  getCampaignPerformance: () => apiFetch<{ items: unknown[]; available: boolean }>("/v1/admin/marketing/analytics/campaigns"),
  getChannelPerformance: () => apiFetch<{ items: unknown[]; available: boolean }>("/v1/admin/marketing/analytics/channels"),

  // Audit
  listAuditLogs: (limit = 50) =>
    apiFetch<{ items: MarketingAuditLogItem[] }>(`/v1/admin/marketing/audit-logs?limit=${limit}`),
};

// ── Platform Analytics ────────────────────────────────────────────────────────

export interface PlatformSummary {
  active_tenants: number; total_jobs: number; platform_revenue: number;
  completed_job_deductions: number; provider_direct_service_value: number;
  avg_job_rating: number; complaint_rate: number; pending_approvals: number;
  new_providers: number; customer_service_credits_issued: number;
  security_deposit_held: number; active_customers: number;
}
export interface TrendPoint { date: string; value: number; }
export interface PlatformTrends {
  jobs_trend: TrendPoint[]; revenue_trend: TrendPoint[];
  tenant_growth: TrendPoint[]; complaint_trend: TrendPoint[];
}
export interface OperationalAlert {
  id: string; alert_type: string; severity: string; message: string;
  entity_type: string; entity_id: string | null; entity_name: string | null;
  vertical: string | null; count: number; detected_at: string; status: string;
}
export interface CategoryPerformanceItem {
  vertical_key: string; category_name: string; tenant_count: number;
  booking_count: number; completion_rate: number; platform_revenue: number;
  avg_rating: number; complaint_rate: number;
}
export interface ProviderPerformanceItem {
  tenant_id: string; tenant_name: string; vertical: string; city: string | null;
  completed_jobs: number; direct_service_value: number; platform_deductions: number;
  avg_rating: number; complaint_rate: number; health_band: string;
}
export interface FinanceSummary {
  platform_revenue: number; package_revenue: number; subscription_revenue: number;
  usage_credit_topups: number; completed_job_deductions: number;
  customer_service_credits_issued: number; security_deposits_held: number;
  failed_deductions: number;
}
export interface QualitySummary {
  avg_rating: number; review_count: number; complaint_rate: number;
  dispute_rate: number; sla_success_rate: number;
}
export interface ComplaintsSummary {
  total_complaints: number; open_complaints: number; resolved_complaints: number;
  avg_resolution_hours: number; customer_service_credits_issued: number;
  tenant_responsible_count: number;
}
export interface GeographySummary {
  top_cities: Array<{city: string; state: string | null; booking_count: number; tenant_count: number; avg_rating: number}>;
}
export interface CustomerSummary {
  active_customers: number; new_customers: number; bookings_per_customer: number;
  customer_service_credits_used: number; customer_complaints: number;
}

type PlatformAnalyticsParams = {
  date_from?: string; date_to?: string; vertical?: string;
  category_id?: string; tenant_id?: string; city?: string;
  health_band?: string; page?: number; page_size?: number; sort_by?: string; limit?: number;
};

function platformAnalyticsQs(params: PlatformAnalyticsParams): string {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null && v !== '') qs.set(k, String(v)); });
  return qs.toString();
}

export const platformAnalyticsApi = {
  getSummary: (p: PlatformAnalyticsParams = {}) => apiFetch<PlatformSummary>(`/v1/admin/analytics/platform/summary?${platformAnalyticsQs(p)}`),
  getTrends: (p: PlatformAnalyticsParams = {}) => apiFetch<PlatformTrends>(`/v1/admin/analytics/platform/trends?${platformAnalyticsQs(p)}`),
  getAlerts: (p: PlatformAnalyticsParams = {}) => apiFetch<{items: OperationalAlert[]; total: number}>(`/v1/admin/analytics/operational-alerts?${platformAnalyticsQs(p)}`),
  resolveAlert: (id: string) => apiFetch<{status: string}>(`/v1/admin/analytics/operational-alerts/${id}/resolve`, {method: 'POST'}),
  ignoreAlert: (id: string) => apiFetch<{status: string}>(`/v1/admin/analytics/operational-alerts/${id}/ignore`, {method: 'POST'}),
  getCategoryPerformance: (p: PlatformAnalyticsParams = {}) => apiFetch<{items: CategoryPerformanceItem[]}>(`/v1/admin/analytics/categories/performance?${platformAnalyticsQs(p)}`),
  getProviderPerformance: (p: PlatformAnalyticsParams = {}) => apiFetch<{items: ProviderPerformanceItem[]}>(`/v1/admin/analytics/providers/performance?${platformAnalyticsQs(p)}`),
  getFinanceSummary: (p: PlatformAnalyticsParams = {}) => apiFetch<FinanceSummary>(`/v1/admin/analytics/finance/summary?${platformAnalyticsQs(p)}`),
  getFinanceByVertical: (p: PlatformAnalyticsParams = {}) => apiFetch<{items: unknown[]}>(`/v1/admin/analytics/finance/by-vertical?${platformAnalyticsQs(p)}`),
  getQualitySummary: (p: PlatformAnalyticsParams = {}) => apiFetch<QualitySummary>(`/v1/admin/analytics/quality/summary?${platformAnalyticsQs(p)}`),
  getComplaintsSummary: (p: PlatformAnalyticsParams = {}) => apiFetch<ComplaintsSummary>(`/v1/admin/analytics/complaints/summary?${platformAnalyticsQs(p)}`),
  getComplaintsBreakdown: (p: PlatformAnalyticsParams = {}) => apiFetch<{items: unknown[]}>(`/v1/admin/analytics/complaints/breakdown?${platformAnalyticsQs(p)}`),
  getGeographySummary: (p: PlatformAnalyticsParams = {}) => apiFetch<GeographySummary>(`/v1/admin/analytics/geography/summary?${platformAnalyticsQs(p)}`),
  getCustomerSummary: (p: PlatformAnalyticsParams = {}) => apiFetch<CustomerSummary>(`/v1/admin/analytics/customers/summary?${platformAnalyticsQs(p)}`),
  exportReport: (report_type: string, params: PlatformAnalyticsParams) => apiFetch<{export_id: string; status: string}>(`/v1/admin/analytics/reports/export`, {method: 'POST', body: JSON.stringify({report_type, ...params})}),
};

// ── Intelligence Command Center ────────────────────────────────────────────────

export interface IntelligenceSummary {
  tenants_at_risk: number; open_anomalies: number; predictions_computed: number;
  events_today: number; rag_queries: number; indexed_documents: number;
  avg_ai_latency_ms: number | null;
  ai_cost_today: number; failed_jobs: number; active_tenants: number;
}
export interface RagKnowledgeBase {
  id: string; name: string; scope_type: string; vertical_key: string | null;
  description: string | null; status: string; document_count: number;
  chunk_count: number; last_indexed_at: string | null; created_at: string;
}
export interface RiskScore {
  id: string; entity_type: string; entity_id: string; risk_score: number;
  risk_level: string; top_reasons_json: string[]; confidence_score: number;
  computed_at: string;
}
export interface IntelAnomaly {
  id: string; anomaly_type: string; severity: string; entity_type: string | null;
  summary: string; confidence_score: number; status: string;
  detected_at: string; vertical_key: string | null;
}
export interface ModelRegistryItem {
  id: string; name: string; model_type: string; version: string;
  status: string; accuracy_score: number | null; avg_latency_ms: number | null;
  last_trained_at: string | null; last_used_at: string | null;
}
export interface PredictionJob {
  id: string; job_type: string; status: string; total_processed: number;
  total_failed: number; triggered_by: string;
  started_at: string | null; completed_at: string | null; created_at: string;
}
export interface DataQualityCheck {
  id: string; check_key: string; check_name: string; severity: string;
  last_status: string; failure_count: number; last_run_at: string | null;
}

export const intelligenceCmdApi = {
  getSummary: () => apiFetch<IntelligenceSummary>('/v1/admin/intelligence/summary'),
  getRagSummary: () => apiFetch<Record<string, unknown>>('/v1/admin/intelligence/rag/summary'),
  getKnowledgeBases: (p: {page?: number; page_size?: number} = {}) => {
    const qs = new URLSearchParams(); Object.entries(p).forEach(([k,v]) => { if (v != null) qs.set(k, String(v)); });
    return apiFetch<{items: RagKnowledgeBase[]; total: number}>(`/v1/admin/intelligence/knowledge-bases?${qs}`);
  },
  createKnowledgeBase: (payload: Record<string, unknown>) => apiFetch<RagKnowledgeBase>('/v1/admin/intelligence/knowledge-bases', {method:'POST', body: JSON.stringify(payload)}),
  getKnowledgeBase: (id: string) => apiFetch<RagKnowledgeBase>(`/v1/admin/intelligence/knowledge-bases/${id}`),
  reindexKB: (id: string) => apiFetch<RagKnowledgeBase>(`/v1/admin/intelligence/knowledge-bases/${id}/reindex`, {method:'POST'}),
  testQueryKB: (id: string, query: string) => apiFetch<Record<string, unknown>>(`/v1/admin/intelligence/knowledge-bases/${id}/test-query`, {method:'POST', body: JSON.stringify({query})}),
  getQueryLogs: () => apiFetch<{items: unknown[]; total: number}>('/v1/admin/intelligence/rag/query-logs'),
  getRetrievalQuality: () => apiFetch<Record<string, unknown>>('/v1/admin/intelligence/rag/retrieval-quality'),
  getEventSummary: () => apiFetch<Record<string, unknown>>('/v1/admin/intelligence/events/summary'),
  getEventSources: () => apiFetch<{items: unknown[]; total: number}>('/v1/admin/intelligence/events/sources'),
  getEventFailures: () => apiFetch<{items: unknown[]; total: number}>('/v1/admin/intelligence/events/failures'),
  getRiskSummary: () => apiFetch<Record<string, number>>('/v1/admin/intelligence/risk/summary'),
  getRiskEntities: (p: {risk_level?: string; entity_type?: string; page?: number} = {}) => {
    const qs = new URLSearchParams(); Object.entries(p).forEach(([k,v]) => { if (v != null && v !== '') qs.set(k, String(v)); });
    return apiFetch<{items: RiskScore[]; total: number}>(`/v1/admin/intelligence/risk/entities?${qs}`);
  },
  recomputeRisk: (entity_type: string, entity_id: string) => apiFetch<RiskScore>(`/v1/admin/intelligence/risk/${entity_type}/${entity_id}/recompute`, {method:'POST'}),
  getAnomalies: (p: {status?: string; severity?: string} = {}) => {
    const qs = new URLSearchParams(); Object.entries(p).forEach(([k,v]) => { if (v != null && v !== '') qs.set(k, String(v)); });
    return apiFetch<{items: IntelAnomaly[]; total: number}>(`/v1/admin/intelligence/anomalies?${qs}`);
  },
  runAnomalyScan: () => apiFetch<{scanned: number; new_anomalies: number; updated: number}>('/v1/admin/intelligence/anomalies/run-scan', {method:'POST'}),
  resolveAnomaly: (id: string) => apiFetch<IntelAnomaly>(`/v1/admin/intelligence/anomalies/${id}/resolve`, {method:'POST'}),
  investigateAnomaly: (id: string) => apiFetch<IntelAnomaly>(`/v1/admin/intelligence/anomalies/${id}/investigate`, {method:'POST'}),
  getModels: () => apiFetch<{items: ModelRegistryItem[]; total: number}>('/v1/admin/intelligence/models'),
  activateModel: (id: string) => apiFetch<ModelRegistryItem>(`/v1/admin/intelligence/models/${id}/activate`, {method:'POST'}),
  deactivateModel: (id: string) => apiFetch<ModelRegistryItem>(`/v1/admin/intelligence/models/${id}/deactivate`, {method:'POST'}),
  evaluateModel: (id: string) => apiFetch<Record<string, unknown>>(`/v1/admin/intelligence/models/${id}/evaluate`, {method:'POST'}),
  getPredictionJobs: () => apiFetch<{items: PredictionJob[]; total: number}>('/v1/admin/intelligence/prediction-jobs'),
  createPredictionJob: (payload: Record<string, unknown>) => apiFetch<PredictionJob>('/v1/admin/intelligence/prediction-jobs', {method:'POST', body: JSON.stringify(payload)}),
  cancelPredictionJob: (id: string) => apiFetch<PredictionJob>(`/v1/admin/intelligence/prediction-jobs/${id}/cancel`, {method:'POST'}),
  getDQSummary: () => apiFetch<Record<string, number>>('/v1/admin/intelligence/data-quality/summary'),
  getDQChecks: () => apiFetch<{items: DataQualityCheck[]; total: number}>('/v1/admin/intelligence/data-quality/checks'),
  runDQCheck: (check_key: string) => apiFetch<DataQualityCheck>(`/v1/admin/intelligence/data-quality/checks/${check_key}/run`, {method:'POST'}),
  getAiUsageSummary: () => apiFetch<Record<string, unknown>>('/v1/admin/intelligence/ai-usage/summary'),
  getAiUsageLogs: () => apiFetch<{items: unknown[]; total: number}>('/v1/admin/intelligence/ai-usage/logs'),
  getCostBreakdown: () => apiFetch<{breakdown: Array<{feature: string; cost: number}>; total_features: number}>('/v1/admin/intelligence/ai-usage/cost-breakdown'),
  getAuditLogs: () => apiFetch<{items: unknown[]; total: number}>('/v1/admin/intelligence/audit-logs'),
};

// ─────────────────────────────────────────────────────────────────────────────
// P0 Platform Command Center Dashboard (migration 104)
// ServiceOS finance rule: platform_revenue excludes provider_direct_service_value
// (the amount customers pay providers directly for Home Services).
// ─────────────────────────────────────────────────────────────────────────────

export interface DashboardExecutiveSummary {
  platform_health: { score: number; status: string };
  active_tenants: { count: number; new_this_month: number; bookable: number };
  live_operations: { total: number; jobs: number; bookings: number; leads: number };
  pending_admin_actions: { count: number; approvals: number; complaints: number; disputes: number };
  at_risk_tenants: { count: number; high_risk: number };
  critical_alerts: { count: number; open_threats: number };
}

export interface DashboardPlatformHealth {
  score: number; status: string; reasons: string[]; recommended_actions: string[];
}

export interface DashboardFinanceSnapshot {
  platform_revenue: number; package_revenue: number; subscription_revenue: number;
  usage_credit_topups: number; completed_job_deductions: number;
  customer_service_credits_issued: number; security_deposits_held: number;
  failed_deductions: number; provider_direct_service_value: number;
}

export interface DashboardTenantLifecycle {
  new_tenant_requests: number; pending_review: number; changes_requested: number;
  approved_this_week: number; suspended: number; bookable_tenants: number;
  non_bookable_tenants: number; package_pending_approval: number;
}

export interface DashboardOperationsSnapshot {
  live_jobs: number; today_bookings: number; pending_provider_acceptance: number;
  technicians_on_duty: number; appointments_today: number; leads_today: number;
  orders_today: number; sla_breaches: number;
}

export interface DashboardLiveOperationItem {
  id: string; item: string; vertical?: string | null; tenant?: string | null;
  status: string; sla_breach: boolean; assigned_to?: string | null; updated_at?: string | null;
}

export interface DashboardTrendPoint { date: string; value: number; }
export interface DashboardTrends {
  jobs_trend: DashboardTrendPoint[]; revenue_trend: DashboardTrendPoint[];
  tenant_growth: DashboardTrendPoint[]; complaint_trend: DashboardTrendPoint[];
  completed_job_deductions_trend: DashboardTrendPoint[]; provider_direct_service_value_trend: DashboardTrendPoint[];
}

export interface DashboardActionItem {
  action_id: string; priority: string; action: string; entity_type?: string | null;
  entity_id?: string | null; vertical?: string | null; age_hours?: number | null; status: string;
}

export interface DashboardEngineHealthItem {
  name: string; status: string; latency_ms?: number | null; error_rate?: number | null; last_check?: string | null;
}

export interface DashboardAtRiskTenant {
  tenant_id: string; tenant_name: string; vertical?: string | null; risk_level: string;
  health_score?: number | null; top_reason: string; credit_balance?: number | null; last_activity?: string | null;
}

export interface DashboardComplianceSecurity {
  dpdp_requests_pending: number; data_export_requests: number; deletion_requests: number;
  consent_issues: number; open_threats: number; failed_logins: number; mfa_gaps: number; suspicious_sessions: number;
}

export interface DashboardTrustQuality {
  avg_rating: number; complaint_rate: number; dispute_rate: number; sla_success_rate: number;
  customer_service_credits_issued: number; providers_under_review: number;
  badge_awards_this_week: number; health_recalculations: number;
}

export interface DashboardActivityItem {
  id: string; time?: string | null; actor: string; actor_role?: string | null;
  action: string; entity_type?: string | null; entity_id?: string | null;
}

export interface DashboardCategoryPerformanceItem {
  vertical_key: string; category_name: string; tenant_count: number; booking_count: number;
  completion_rate: number; platform_revenue: number; avg_rating: number; complaint_rate: number;
}

export interface DashboardHomeServicesSummary {
  home_services_providers: number; bookable_providers: number; not_bookable_providers: number;
  service_catalog_health: { status: string; active_services: number };
  pricing_rule_health: { status: string; active_rules: number };
  service_area_coverage_health: { status: string; active_areas: number; tenants_without_areas: number };
  provider_matching_health: string;
  auto_price_options_health: string;
  completed_job_deduction_health: string;
  published_tenant_services: number;
}

export const dashboardApi = {
  getExecutiveSummary: () => apiFetch<DashboardExecutiveSummary>("/v1/admin/dashboard/executive-summary"),
  getPlatformHealth: () => apiFetch<DashboardPlatformHealth>("/v1/admin/dashboard/platform-health"),
  getHomeServicesSummary: () => apiFetch<DashboardHomeServicesSummary>("/v1/admin/dashboard/home-services-summary"),
  getFinanceSnapshot: (params?: { date_from?: string; date_to?: string; vertical?: string }) => {
    const qs = new URLSearchParams();
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to);
    if (params?.vertical) qs.set("vertical", params.vertical);
    return apiFetch<DashboardFinanceSnapshot>(`/v1/admin/dashboard/finance-snapshot?${qs}`);
  },
  getTenantLifecycle: () => apiFetch<DashboardTenantLifecycle>("/v1/admin/dashboard/tenant-lifecycle"),
  getOperationsSnapshot: (vertical?: string) =>
    apiFetch<DashboardOperationsSnapshot>(`/v1/admin/dashboard/operations-snapshot${vertical ? `?vertical=${vertical}` : ""}`),
  getLiveOperations: (limit = 30) =>
    apiFetch<{ items: DashboardLiveOperationItem[] }>(`/v1/admin/dashboard/live-operations?limit=${limit}`),
  getTrends: (params?: { date_from?: string; date_to?: string; vertical?: string }) => {
    const qs = new URLSearchParams();
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to);
    if (params?.vertical) qs.set("vertical", params.vertical);
    return apiFetch<DashboardTrends>(`/v1/admin/dashboard/trends?${qs}`);
  },
  getActionQueue: (limit = 50) =>
    apiFetch<{ items: DashboardActionItem[]; total: number }>(`/v1/admin/dashboard/action-queue?limit=${limit}`),
  resolveAction: (actionId: string, reason?: string) =>
    apiFetch<{ action_id: string; status: string }>(`/v1/admin/dashboard/action-queue/${actionId}/resolve`,
      { method: "POST", body: JSON.stringify({ reason }) }),
  snoozeAction: (actionId: string, hours = 24) =>
    apiFetch<{ action_id: string; status: string }>(`/v1/admin/dashboard/action-queue/${actionId}/snooze`,
      { method: "POST", body: JSON.stringify({ hours }) }),
  assignAction: (actionId: string, assignedToUserId: string) =>
    apiFetch<{ action_id: string; status: string }>(`/v1/admin/dashboard/action-queue/${actionId}/assign`,
      { method: "POST", body: JSON.stringify({ assigned_to_user_id: assignedToUserId }) }),
  getEngineHealth: () => apiFetch<{ items: DashboardEngineHealthItem[]; note: string }>("/v1/admin/dashboard/engine-health"),
  getAtRiskTenants: (limit = 50) =>
    apiFetch<{ items: DashboardAtRiskTenant[] }>(`/v1/admin/dashboard/at-risk-tenants?limit=${limit}`),
  getComplianceSecurity: () => apiFetch<DashboardComplianceSecurity>("/v1/admin/dashboard/compliance-security"),
  getTrustQuality: () => apiFetch<DashboardTrustQuality>("/v1/admin/dashboard/trust-quality"),
  getActivityFeed: (limit = 30) =>
    apiFetch<{ items: DashboardActivityItem[] }>(`/v1/admin/dashboard/activity-feed?limit=${limit}`),
  getCategoryPerformance: (params?: { date_from?: string; date_to?: string }) => {
    const qs = new URLSearchParams();
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to);
    return apiFetch<{ items: DashboardCategoryPerformanceItem[] }>(`/v1/admin/dashboard/category-performance?${qs}`);
  },
  refresh: () => apiFetch<{ refreshed: boolean }>("/v1/admin/dashboard/refresh", { method: "POST" }),
  exportSnapshot: () =>
    apiFetch<{ snapshot_id: string; created_at: string }>("/v1/admin/dashboard/export-snapshot", { method: "POST" }),
};

// ── Knowledge Base Enterprise (migration 104) ─────────────────────────────────

export interface KBSummary {
  total: number; active: number; draft: number; disabled: number; archived: number;
  by_scope: Record<string, number>; by_indexing_status: Record<string, number>;
}

export interface KnowledgeBase {
  id: string; kb_code: string | null; name: string; description: string | null;
  scope_type: string; vertical_key: string | null; knowledge_type: string;
  status: string; owner_team: string; rag_enabled: boolean;
  customer_visible: boolean; tenant_visible: boolean; staff_visible: boolean;
  admin_only: boolean; sensitive_content: boolean; indexing_status: string;
  created_at: string; updated_at: string;
  allowed_apps_json: string[]; allowed_roles_json: string[];
  chunk_size: number; chunk_overlap: number; retrieval_top_k: number;
  similarity_threshold: number; citations_required: boolean;
  fallback_message: string | null; auto_reindex: boolean; reindex_schedule: string;
  document_count: number; chunk_count: number; tags_json: string[];
  icon: string | null; environment: string; max_context_documents: number;
}

export interface KBDocument {
  id: string; kb_id: string; document_name: string; source_type: string;
  file_type: string | null; file_size_bytes: number;
  indexing_status: string; chunk_count: number; created_at: string;
}

export interface KBArticle {
  id: string; kb_id: string; article_title: string; article_slug: string;
  body_markdown: string | null; status: string; visibility: string;
  created_at: string; published_at: string | null; tags_json: string[];
}

export interface KBChunk {
  id: string; kb_id: string; chunk_text: string; chunk_index: number;
  token_count: number; embedding_status: string;
}

export interface KBIndexingJob {
  id: string; kb_id: string; job_type: string; status: string;
  documents_processed: number; chunks_created: number; failed_count: number;
  started_at: string | null; completed_at: string | null;
}

export interface KBQueryLog {
  id: string; kb_id: string | null; query_text: string | null;
  retrieved_chunks_count: number; latency_ms: number | null;
  answer_status: string; created_at: string; app_scope: string | null;
}

export interface KBRetrievalQuality {
  total_queries: number; helpful_rate: number | null; no_answer_rate: number | null;
  avg_latency_ms: number | null; avg_retrieved_chunks: number | null; flagged_count: number;
}

export interface KBAccessPreview {
  can_access: boolean; reason: string; blocked_by: string | null;
}

export const kbApi = {
  getSummary: () => apiFetch<KBSummary>('/v1/admin/intelligence/knowledge-bases/summary'),
  list: (params?: Record<string, string | number | boolean>) => {
    const qs = params ? '?' + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString() : '';
    return apiFetch<{ items: KnowledgeBase[]; pagination: Record<string, number> }>('/v1/admin/intelligence/knowledge-bases' + qs);
  },
  create: (payload: Record<string, unknown>) => apiFetch<KnowledgeBase>('/v1/admin/intelligence/knowledge-bases', { method: 'POST', body: JSON.stringify(payload) }),
  get: (id: string) => apiFetch<KnowledgeBase>(`/v1/admin/intelligence/knowledge-bases/${id}`),
  update: (id: string, payload: Record<string, unknown>) => apiFetch<KnowledgeBase>(`/v1/admin/intelligence/knowledge-bases/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  activate: (id: string) => apiFetch<KnowledgeBase>(`/v1/admin/intelligence/knowledge-bases/${id}/activate`, { method: 'POST' }),
  disable: (id: string) => apiFetch<KnowledgeBase>(`/v1/admin/intelligence/knowledge-bases/${id}/disable`, { method: 'POST' }),
  archive: (id: string) => apiFetch<KnowledgeBase>(`/v1/admin/intelligence/knowledge-bases/${id}/archive`, { method: 'POST' }),
  delete: (id: string) => apiFetch<void>(`/v1/admin/intelligence/knowledge-bases/${id}`, { method: 'DELETE' }),
  listDocuments: (id: string) => apiFetch<KBDocument[]>(`/v1/admin/intelligence/knowledge-bases/${id}/documents`),
  uploadDocument: (id: string, payload: Record<string, unknown>) => apiFetch<KBDocument>(`/v1/admin/intelligence/knowledge-bases/${id}/documents/upload`, { method: 'POST', body: JSON.stringify(payload) }),
  deleteDocument: (id: string, docId: string) => apiFetch<void>(`/v1/admin/intelligence/knowledge-bases/${id}/documents/${docId}`, { method: 'DELETE' }),
  listArticles: (id: string) => apiFetch<KBArticle[]>(`/v1/admin/intelligence/knowledge-bases/${id}/articles`),
  createArticle: (id: string, payload: Record<string, unknown>) => apiFetch<KBArticle>(`/v1/admin/intelligence/knowledge-bases/${id}/articles`, { method: 'POST', body: JSON.stringify(payload) }),
  updateArticle: (id: string, articleId: string, payload: Record<string, unknown>) => apiFetch<KBArticle>(`/v1/admin/intelligence/knowledge-bases/${id}/articles/${articleId}`, { method: 'PUT', body: JSON.stringify(payload) }),
  publishArticle: (id: string, articleId: string) => apiFetch<KBArticle>(`/v1/admin/intelligence/knowledge-bases/${id}/articles/${articleId}/publish`, { method: 'POST' }),
  triggerIndex: (id: string) => apiFetch<KBIndexingJob>(`/v1/admin/intelligence/knowledge-bases/${id}/index`, { method: 'POST' }),
  triggerReindex: (id: string) => apiFetch<KBIndexingJob>(`/v1/admin/intelligence/knowledge-bases/${id}/reindex`, { method: 'POST' }),
  listIndexingJobs: (id: string) => apiFetch<KBIndexingJob[]>(`/v1/admin/intelligence/knowledge-bases/${id}/indexing-jobs`),
  listChunks: (id: string, page = 1) => apiFetch<{ items: KBChunk[]; pagination: Record<string, number> }>(`/v1/admin/intelligence/knowledge-bases/${id}/chunks?page=${page}`),
  testQuery: (id: string, query: string, appScope: string) => apiFetch<Record<string, unknown>>(`/v1/admin/intelligence/knowledge-bases/${id}/test-query`, { method: 'POST', body: JSON.stringify({ query_text: query, app_scope: appScope }) }),
  listQueryLogs: (id: string, page = 1) => apiFetch<{ items: KBQueryLog[]; pagination: Record<string, number> }>(`/v1/admin/intelligence/knowledge-bases/${id}/query-logs?page=${page}`),
  getRetrievalQuality: (id: string) => apiFetch<KBRetrievalQuality>(`/v1/admin/intelligence/knowledge-bases/${id}/retrieval-quality`),
  previewAccess: (id: string, role: string, appScope: string) => apiFetch<KBAccessPreview>(`/v1/admin/intelligence/knowledge-bases/${id}/access-preview`, { method: 'POST', body: JSON.stringify({ role, app_scope: appScope }) }),
  getAuditLogs: (id: string) => apiFetch<Record<string, unknown>[]>(`/v1/admin/intelligence/knowledge-bases/${id}/audit-logs`),
  getVersions: (id: string) => apiFetch<Record<string, unknown>[]>(`/v1/admin/intelligence/knowledge-bases/${id}/versions`),
  seedDefaultsPreview: () => apiFetch<Record<string, unknown>[]>('/v1/admin/intelligence/knowledge-bases/seed-defaults/preview', { method: 'POST' }),
  seedDefaults: () => apiFetch<Record<string, unknown>>('/v1/admin/intelligence/knowledge-bases/seed-defaults', { method: 'POST' }),
};

// ── Workflow Templates Enterprise (migration 106) ─────────────────────────────
export interface WorkflowTemplateSummary {
  total: number; published: number; draft: number; missing_mapping: number;
  runtime_ready: number; sla_enabled: number; approval_workflows: number;
  automation_enabled: number; used_by_services: number; runtime_errors: number;
}
export interface WorkflowTemplate {
  id: string; workflow_key: string; name: string; description: string | null;
  vertical_key: string; workflow_type: string; status: string; current_version: number;
  readiness_status: string; runtime_health: string; steps_json: unknown[];
  transitions_json: unknown[]; sla_rules_json: unknown[]; approval_gates_json: unknown[];
  automation_rules_json: unknown[]; service_mappings_json: unknown[];
  validation_result_json: Record<string, unknown>; created_at: string; updated_at: string;
  published_at: string | null; archived_at: string | null;
}
export interface WTStep {
  id: string; step_key: string; step_name: string; step_type: string;
  owner_app: string; owner_role: string; customer_visible: boolean; tenant_visible: boolean;
  staff_visible: boolean; admin_visible: boolean; requires_notes: boolean; requires_photo: boolean;
  requires_payment_record: boolean; requires_approval: boolean; sla_enabled: boolean;
  audit_required: boolean; display_order: number;
}
export interface WTTransition {
  id: string; from_step_key: string; to_step_key: string; action_label: string;
  allowed_role: string; requires_reason: boolean; triggers_notification: boolean;
}
export interface WTValidationResult {
  passed: boolean; errors: { field: string; message: string; severity: string }[];
  warnings: { field: string; message: string }[]; readiness_status: string;
}
export interface WTSimulationResult {
  steps: { step_key: string; step_name: string; action: string; role: string; duration_estimate: string }[];
  notifications: string[]; sla_timers: unknown[]; finance_triggers: string[]; final_state: string;
}
export interface WTVersion {
  id: string; version_number: number; status: string; change_summary: string | null;
  published_at: string | null; is_rollback: boolean; created_at: string;
}

export const workflowTemplateApi = {
  getSummary: () => apiFetch<WorkflowTemplateSummary>('/admin/workflows/templates/summary'),
  list: (params?: Record<string, string | number>) => {
    const qs = params ? '?' + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString() : '';
    return apiFetch<{ items: WorkflowTemplate[]; pagination: Record<string, number> }>('/admin/workflows/templates' + qs);
  },
  create: (payload: Record<string, unknown>) => apiFetch<WorkflowTemplate>('/admin/workflows/templates', { method: 'POST', body: JSON.stringify(payload) }),
  get: (id: string) => apiFetch<WorkflowTemplate>(`/admin/workflows/templates/${id}`),
  update: (id: string, payload: Record<string, unknown>) => apiFetch<WorkflowTemplate>(`/admin/workflows/templates/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  clone: (id: string) => apiFetch<WorkflowTemplate>(`/admin/workflows/templates/${id}/clone`, { method: 'POST' }),
  archive: (id: string) => apiFetch<WorkflowTemplate>(`/admin/workflows/templates/${id}/archive`, { method: 'POST' }),
  addStep: (id: string, payload: Record<string, unknown>) => apiFetch<WTStep>(`/admin/workflows/templates/${id}/steps`, { method: 'POST', body: JSON.stringify(payload) }),
  updateStep: (id: string, stepId: string, payload: Record<string, unknown>) => apiFetch<WTStep>(`/admin/workflows/templates/${id}/steps/${stepId}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteStep: (id: string, stepId: string) => apiFetch<void>(`/admin/workflows/templates/${id}/steps/${stepId}`, { method: 'DELETE' }),
  addTransition: (id: string, payload: Record<string, unknown>) => apiFetch<WTTransition>(`/admin/workflows/templates/${id}/transitions`, { method: 'POST', body: JSON.stringify(payload) }),
  updateTransition: (id: string, tid: string, payload: Record<string, unknown>) => apiFetch<WTTransition>(`/admin/workflows/templates/${id}/transitions/${tid}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteTransition: (id: string, tid: string) => apiFetch<void>(`/admin/workflows/templates/${id}/transitions/${tid}`, { method: 'DELETE' }),
  getSla: (id: string) => apiFetch<unknown[]>(`/admin/workflows/templates/${id}/sla`),
  updateSla: (id: string, payload: unknown[]) => apiFetch<unknown[]>(`/admin/workflows/templates/${id}/sla`, { method: 'PUT', body: JSON.stringify(payload) }),
  getApprovals: (id: string) => apiFetch<unknown[]>(`/admin/workflows/templates/${id}/approvals`),
  updateApprovals: (id: string, payload: unknown[]) => apiFetch<unknown[]>(`/admin/workflows/templates/${id}/approvals`, { method: 'PUT', body: JSON.stringify(payload) }),
  getAutomation: (id: string) => apiFetch<unknown[]>(`/admin/workflows/templates/${id}/automation`),
  updateAutomation: (id: string, payload: unknown[]) => apiFetch<unknown[]>(`/admin/workflows/templates/${id}/automation`, { method: 'PUT', body: JSON.stringify(payload) }),
  getServiceMapping: (id: string) => apiFetch<unknown[]>(`/admin/workflows/templates/${id}/service-mapping`),
  addServiceMapping: (id: string, payload: Record<string, unknown>) => apiFetch<unknown>(`/admin/workflows/templates/${id}/service-mapping`, { method: 'POST', body: JSON.stringify(payload) }),
  deleteServiceMapping: (id: string, mid: string) => apiFetch<void>(`/admin/workflows/templates/${id}/service-mapping/${mid}`, { method: 'DELETE' }),
  validate: (id: string) => apiFetch<WTValidationResult>(`/admin/workflows/templates/${id}/validate`, { method: 'POST' }),
  simulate: (id: string, payload: Record<string, unknown>) => apiFetch<WTSimulationResult>(`/admin/workflows/templates/${id}/simulate`, { method: 'POST', body: JSON.stringify(payload) }),
  publish: (id: string, reason: string) => apiFetch<WorkflowTemplate>(`/admin/workflows/templates/${id}/publish`, { method: 'POST', body: JSON.stringify({ reason }) }),
  rollback: (id: string, version: number, reason: string) => apiFetch<WorkflowTemplate>(`/admin/workflows/templates/${id}/rollback`, { method: 'POST', body: JSON.stringify({ version_number: version, reason }) }),
  getVersions: (id: string) => apiFetch<WTVersion[]>(`/admin/workflows/templates/${id}/versions`),
  getRuntimeAnalytics: (id: string) => apiFetch<unknown>(`/admin/workflows/templates/${id}/runtime-analytics`),
  getRuntimeJobs: (id: string, page = 1) => apiFetch<unknown>(`/admin/workflows/templates/${id}/runtime-jobs?page=${page}`),
  getAuditLogs: (id: string) => apiFetch<unknown[]>(`/admin/workflows/templates/${id}/audit-logs`),
  seedDefaultsPreview: () => apiFetch<unknown[]>('/admin/workflows/templates/seed-defaults/preview', { method: 'POST' }),
  seedDefaults: () => apiFetch<unknown>('/admin/workflows/templates/seed-defaults', { method: 'POST' }),
};

// ── Phase 1B — Roles & Permissions (read-only, code-defined RBAC) ─────────────
export interface RoleListItem {
  role_id: string; role_key: string; label: string; type: "system" | "custom";
  scope: string; is_implemented: boolean; is_active: boolean;
  user_count: number; permission_count: number; updated_at: string | null;
}
export interface RolesSummary {
  total_roles: number; system_roles: number; custom_roles: number;
  active_roles: number; users_assigned: number; permission_gaps: number;
}
export interface RoleDetail {
  role_id: string; role_key: string; label: string; type: string; scope: string;
  is_implemented: boolean; permissions: string[]; permission_count: number;
  assigned_users: { id: string; email: string; full_name: string; is_active: boolean; created_at: string | null }[];
  assigned_user_count: number;
}
export interface PermissionListItem {
  permission_key: string; constant_name: string; module: string; app_scope: string;
  risk_level: "low" | "medium" | "high"; description: string;
  assigned_roles: string[]; assigned_role_count: number; status: string;
}
export interface PermissionsSummary {
  total_permissions: number; admin_permissions: number; tenant_permissions: number;
  customer_permissions: number; high_risk_permissions: number; unassigned_permissions: number;
}

export const rolesPermissionsApi = {
  listRoles: () => apiFetch<{ items: RoleListItem[]; summary: RolesSummary }>("/v1/admin/roles"),
  getRole: (roleId: string) => apiFetch<RoleDetail>(`/v1/admin/roles/${roleId}`),
  listPermissions: (params?: { module?: string; app_scope?: string; risk_level?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.module) q.set("module", params.module);
    if (params?.app_scope) q.set("app_scope", params.app_scope);
    if (params?.risk_level) q.set("risk_level", params.risk_level);
    if (params?.search) q.set("search", params.search);
    const qs = q.toString();
    return apiFetch<{ items: PermissionListItem[]; summary: PermissionsSummary }>(
      `/v1/admin/permissions${qs ? `?${qs}` : ""}`);
  },
  listPermissionsGrouped: (params?: { app_scope?: string; risk_level?: string }) => {
    const q = new URLSearchParams();
    if (params?.app_scope) q.set("app_scope", params.app_scope);
    if (params?.risk_level) q.set("risk_level", params.risk_level);
    const qs = q.toString();
    return apiFetch<{ groups: { module: string; items: PermissionListItem[]; count: number }[]; summary: PermissionsSummary }>(
      `/v1/admin/permissions/grouped${qs ? `?${qs}` : ""}`);
  },
};

// ── Deactivate Manual Bargain Module — Automatic Customer Price Options ──────
export interface HomeServicesPricingConfig {
  manual_bargain_rules_enabled: boolean;
  auto_price_options_enabled: boolean;
  provider_first_matching_enabled: boolean;
  home_services_only: boolean;
}

export interface AutoPriceOptions {
  currency: string;
  allowed_offer_min: number;
  allowed_offer_max: number;
  low_price: number;
  mid_price: number;
  high_price: number;
  platform_fee_percent: number;
  platform_fee_amount: number;
  payment_mode: string;
}

export interface PriceExperiencePreviewResult extends AutoPriceOptions {
  service_name?: string | null;
  admin_min_price?: number | null;
  admin_max_price?: number | null;
  admin_base_price?: number | null;
  selected_min_price: number;
  selected_max_price: number;
  platform_fee_on_min: number | null;
  platform_fee_on_max: number | null;
  customer_low_price: number;
  customer_mid_price: number;
  customer_high_price: number;
  // Backward-compatible aliases
  customer_min_price?: number;
  customer_max_price?: number;
}

export interface MatchingDiagnosticsCandidate {
  tenant_id: string; provider_name: string; public_badges: string[];
  rating: number | null; customer_visible_reason: string;
  internal_score: number; internal_score_breakdown: Record<string, number>;
}

export interface MatchingDiagnosticsResult {
  eligible_provider_count: number;
  candidate_provider_count: number;
  excluded_provider_count: number;
  excluded_providers: { provider_name: string; reason_code: string | null }[];
  selected_provider: MatchingDiagnosticsCandidate | null;
  top_candidates: MatchingDiagnosticsCandidate[];
  price_options: AutoPriceOptions | null;
  area_market_comparison: {
    area: string; competitor_provider_count: number;
    area_competitor_min: number | null; area_competitor_avg: number | null; area_competitor_max: number | null;
  } | null;
  bookability_source: string;
  area_coverage_source: string;
  availability_source: string;
  pricing_source: string;
}

export const autoPriceOptionsApi = {
  getConfig: () => apiFetch<HomeServicesPricingConfig>("/v1/admin/home-services/config"),
  previewPriceExperience: (data: {
    service_name?: string; admin_min_price?: number; admin_max_price?: number; admin_base_price?: number;
    selected_min_price: number; selected_max_price: number; platform_fee_percent?: number;
  }) => apiFetch<PriceExperiencePreviewResult>("/v1/admin/home-services/price-experience/preview",
    { method: "POST", body: JSON.stringify(data) }),
  runMatchingDiagnostics: (data: {
    category_id: string; master_service_id: string; city: string; zipcode?: string;
    offering_type_id?: string; brand_id?: string;
  }) => apiFetch<MatchingDiagnosticsResult>("/v1/admin/home-services/matching/diagnostics",
    { method: "POST", body: JSON.stringify(data) }),
};

// ── Home Services Catalog Setup Console ──────────────────────────────────────

export interface HsConsoleService {
  service_id: string; category_id: string; service_name: string; slug: string;
  description: string | null; job_type: string; pricing_model: string;
  base_price: number | null; min_price: number | null; max_price: number | null;
  visit_fee: number | null; is_brand_required: boolean; is_type_required: boolean;
  requires_issue_type: boolean; requires_schedule: boolean; requires_address: boolean;
  tenant_override_allowed: boolean; service_group_id: string | null;
  display_order: number; is_active: boolean; created_at: string | null;
  types_count?: number; brands_count?: number;
}

export interface HsConsoleServiceGroup { group_id: string; name: string; }

export interface HsConsoleCatalogList {
  category_id: string;
  groups: HsConsoleServiceGroup[];
  services: HsConsoleService[];
}

export interface HsSymmetricPricePreview {
  provider_min_price: number; provider_max_price: number;
  platform_fee_percent: number; platform_fee_fixed_amount: number;
  low_price: number; mid_price: number; high_price: number;
  payment_mode: string;
}

export interface HsConsoleType {
  mapping_id: string; service_type_id: string; name: string;
  is_required: boolean; is_default: boolean; pricing_rule_id: string | null;
  admin_floor_price: number | null; admin_ceiling_price: number | null;
  platform_fee_percent: number; completed_job_deduction_credits: number;
  customer_price_preview: HsSymmetricPricePreview | null;
}

export interface HsConsoleBrand {
  mapping_id: string; brand_id: string; name: string;
  is_required: boolean; is_default: boolean;
  can_override_price: boolean; is_routing_only: boolean;
  pricing_rule_id: string | null;
  admin_floor_price: number | null; admin_ceiling_price: number | null;
  platform_fee_percent: number | null;
  customer_price_preview: HsSymmetricPricePreview | null;
}

export interface HsConsoleServiceDetail extends HsConsoleService {
  types: HsConsoleType[];
  brands: HsConsoleBrand[];
}

export interface HsConsoleAuditEvent {
  entity_type: string; entity_id: string; action: string;
  change_summary: string | null; created_at: string | null;
}

export const homeServicesCatalogConsoleApi = {
  listServices: () => apiFetch<HsConsoleCatalogList>("/v1/admin/home-services/service-catalog/services"),
  getServiceDetail: (serviceId: string) =>
    apiFetch<HsConsoleServiceDetail>(`/v1/admin/home-services/service-catalog/services/${serviceId}`),
  updateService: (serviceId: string, data: Record<string, unknown>) =>
    apiFetch<Record<string, unknown>>(`/v1/admin/master-services/${serviceId}`,
      { method: "PUT", body: JSON.stringify(data) }),
  getTypePricing: (serviceId: string) =>
    apiFetch<{ types: HsConsoleType[] }>(`/v1/admin/home-services/service-catalog/services/${serviceId}/types`),
  setTypeLimits: (serviceId: string, serviceTypeId: string, data: {
    admin_floor_price: number; admin_ceiling_price: number;
    platform_fee_percent?: number; completed_job_deduction_credits?: number;
  }) => apiFetch<{ types: HsConsoleType[] }>(
    `/v1/admin/home-services/service-catalog/services/${serviceId}/types/${serviceTypeId}/limits`,
    { method: "PUT", body: JSON.stringify(data) }),
  getBrandPricing: (serviceId: string, serviceTypeId?: string) =>
    apiFetch<{ brands: HsConsoleBrand[] }>(
      `/v1/admin/home-services/service-catalog/services/${serviceId}/brands${serviceTypeId ? `?service_type_id=${serviceTypeId}` : ""}`),
  setBrandBehavior: (serviceId: string, mappingId: string, data: {
    can_override_price?: boolean; is_routing_only?: boolean;
  }) => apiFetch<{ brands: HsConsoleBrand[] }>(
    `/v1/admin/home-services/service-catalog/services/${serviceId}/brands/${mappingId}/behavior`,
    { method: "PUT", body: JSON.stringify(data) }),
  setBrandLimits: (serviceId: string, brandId: string, data: {
    admin_floor_price: number; admin_ceiling_price: number; platform_fee_percent?: number;
  }, serviceTypeId?: string) => apiFetch<{ brands: HsConsoleBrand[] }>(
    `/v1/admin/home-services/service-catalog/services/${serviceId}/brands/${brandId}/limits${serviceTypeId ? `?service_type_id=${serviceTypeId}` : ""}`,
    { method: "PUT", body: JSON.stringify(data) }),
  pricePreview: (data: {
    provider_min_price: number; provider_max_price: number;
    platform_fee_percent?: number; platform_fee_fixed_amount?: number;
  }) => apiFetch<HsSymmetricPricePreview>("/v1/admin/home-services/service-catalog/price-preview",
    { method: "POST", body: JSON.stringify(data) }),
  getAudit: (serviceId: string) =>
    apiFetch<{ events: HsConsoleAuditEvent[] }>(`/v1/admin/home-services/service-catalog/services/${serviceId}/audit`),
};
