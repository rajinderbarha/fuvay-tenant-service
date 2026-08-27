"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useState, useCallback, useEffect } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Btn, Badge, Skeleton, Input, Modal, StatCard, Pagination } from "../../../components/shared/ui";
import { SearchBar, ActionMenu } from "../../../components/shared/layout";
import { PageHeader, PageShell } from "@serviceos/design-system";
import {
  Mail, Users, CheckCircle2, Lock, Star, ShieldAlert, Clock, UserX, RefreshCw,
} from "lucide-react";
import {
  authApi, platformUsersApi, type PlatformUserRow, type PlatformUserDetail,
  type PlatformUserInvite, type PlatformUserAuditEntry,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { RequirePermission } from "../../../components/shared/PermissionGate";

const TH: React.CSSProperties = {
  padding: "9px 10px", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
  letterSpacing: "0.06em", textTransform: "uppercase", background: "var(--surface-sunken)",
  borderBottom: "1px solid var(--border)", textAlign: "left",
};
const TD: React.CSSProperties = { padding: "10px 10px", fontSize: 13, borderBottom: "1px solid var(--border)" };

// FINAL-L5-05N: these 5 values must match app.core.permissions.ROLE_PERMISSIONS
// and app.engines.auth.service.AuthService.VALID_PLATFORM_ROLES exactly --
// they are the real, enforced role strings, not invented labels. The
// previous 8-value list (platform_admin/compliance_officer/support_admin/
// operations_admin/finance_admin/security_admin/read_only_admin) matched
// no real authorization role; the backend silently granted every invited
// user real super_admin access regardless of which of those labels was
// selected here (fixed in the same sprint -- see FINAL_L5_05N_ROLE_EDITOR_REPAIR.md).
const PLATFORM_ROLES = [
  { value: "super_admin", label: "Platform Super Admin" },
  { value: "admin_operations", label: "Operations Admin" },
  { value: "admin_finance", label: "Finance Admin" },
  { value: "admin_security", label: "Security Admin" },
  { value: "admin_readonly", label: "Admin Read Only" },
];
const ACCESS_SCOPES = [
  { value: "global", label: "Global" },
  { value: "operations", label: "Operations" },
  { value: "finance", label: "Finance" },
  { value: "compliance", label: "Compliance" },
  { value: "support", label: "Support" },
  { value: "tenant_scoped", label: "Tenant Scoped" },
  { value: "customer_support_limited", label: "Customer Support Limited" },
];
const roleLabel = (v: string | null) => PLATFORM_ROLES.find(r => r.value === v)?.label ?? (v ?? "—");
const scopeLabel = (v: string | null) => ACCESS_SCOPES.find(s => s.value === v)?.label ?? (v ?? "—");

function statusBadge(status: string) {
  const map: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
    active: "success", inactive: "muted", invited: "info", locked: "danger",
    suspended: "warning", password_reset_required: "warning", deactivated: "muted",
  };
  return <Badge variant={map[status] ?? "muted"} size="sm">{status.replace(/_/g, " ")}</Badge>;
}
function mfaBadge(mfa: string) {
  const map: Record<string, "success" | "warning" | "danger"> = { on: "success", off: "warning", required: "danger" };
  return <Badge variant={map[mfa] ?? "warning"} size="sm">{mfa}</Badge>;
}
function deriveRisk(u: PlatformUserRow): { label: string; variant: "success" | "warning" | "danger" } {
  if (u.status === "locked" || u.failed_login_attempts >= 3) return { label: "High", variant: "danger" };
  if (u.mfa_status !== "on" || u.status === "password_reset_required") return { label: "Medium", variant: "warning" };
  return { label: "Low", variant: "success" };
}

// ── Generic reason-required action modal ─────────────────────────────────────
function ReasonModal({
  open, title, description, confirmLabel, danger, requireReason = true,
  onClose, onConfirm, loading,
}: {
  open: boolean; title: string; description?: string; confirmLabel: string; danger?: boolean;
  requireReason?: boolean; onClose: () => void; onConfirm: (reason: string) => void; loading: boolean;
}) {
  const [reason, setReason] = useState("");
  return (
    <Modal open={open} onClose={onClose} title={title} size="sm">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {description && <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>{description}</p>}
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
            Reason {requireReason && <span style={{ color: "var(--danger)" }}>*</span>}
          </label>
          <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
            placeholder="Explain why this action is being taken…"
            style={{ width: "100%", fontSize: 13, padding: "8px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
                     background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit", boxSizing: "border-box" }} />
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn variant={danger ? "danger" : "primary"} onClick={() => onConfirm(reason)}
               disabled={requireReason && reason.trim().length < 3} loading={loading}>
            {confirmLabel}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ── User Detail drawer with tabs ──────────────────────────────────────────────
type DetailTab = "overview" | "roles" | "security" | "sessions" | "history" | "risk" | "audit";

function UserDetailDrawer({
  userId, onClose, onChanged, currentAdminId,
}: { userId: string | null; onClose: () => void; onChanged: () => void; currentAdminId: string | null }) {
  const [tab, setTab] = useState<DetailTab>("overview");
  const detail = useApi(useCallback(() => userId ? platformUsersApi.get(userId) : Promise.resolve(null), [userId]), [userId]);
  const sessions = useApi(useCallback(() => userId && tab === "sessions" ? platformUsersApi.listSessions(userId) : Promise.resolve({ sessions: [], total: 0 }), [userId, tab]), [userId, tab]);
  const history = useApi(useCallback(() => userId && tab === "history" ? platformUsersApi.loginHistory(userId) : Promise.resolve({ events: [], total: 0 }), [userId, tab]), [userId, tab]);
  const risk = useApi(useCallback(() => userId && tab === "risk" ? platformUsersApi.riskSignals(userId) : Promise.resolve(null), [userId, tab]), [userId, tab]);
  const audit = useApi(useCallback(() => userId && tab === "audit" ? platformUsersApi.userAuditLogs(userId) : Promise.resolve({ logs: [], meta: { total: 0 } }), [userId, tab]), [userId, tab]);

  const [tempPw, setTempPw] = useState<string | null>(null);
  const [pendingReasonAction, setPendingReasonAction] = useState<
    "suspend" | "unsuspend" | "deactivate" | "reactivate" | "lock" | "unlock" |
    "require_mfa" | "reset_mfa" | "force_password_reset" | "send_reset_link" |
    "generate_temp_password" | "revoke_sessions" | null
  >(null);
  const actionRunning = useAction(async (reason: string) => {
    if (!userId || !pendingReasonAction) return;
    switch (pendingReasonAction) {
      case "suspend": await platformUsersApi.suspend(userId, reason); break;
      case "unsuspend": await platformUsersApi.unsuspend(userId, reason); break;
      case "deactivate": await platformUsersApi.deactivate(userId, reason); break;
      case "reactivate": await platformUsersApi.reactivate(userId, reason); break;
      case "lock": await platformUsersApi.lock(userId, reason); break;
      case "unlock": await platformUsersApi.unlock(userId, reason); break;
      case "require_mfa": await platformUsersApi.requireMfa(userId, reason); break;
      case "reset_mfa": await platformUsersApi.resetMfa(userId, reason); break;
      case "force_password_reset": await platformUsersApi.forcePasswordReset(userId, reason); break;
      case "send_reset_link": await platformUsersApi.sendResetLink(userId, reason); break;
      case "generate_temp_password": {
        const res = await platformUsersApi.generateTempPassword(userId, reason);
        setTempPw(res.temporary_password);
        break;
      }
      case "revoke_sessions": await platformUsersApi.revokeAllSessions(userId, reason); break;
    }
    setPendingReasonAction(null);
    detail.refetch(); onChanged();
  });

  const [roleModal, setRoleModal] = useState(false);
  const [scopeModal, setScopeModal] = useState(false);
  const [newRole, setNewRole] = useState("");
  const [newScope, setNewScope] = useState("");
  const changeRole = useAction(async (reason: string) => {
    if (!userId) return;
    await platformUsersApi.changeRole(userId, newRole, reason);
    setRoleModal(false); detail.refetch(); onChanged();
  });
  const changeScope = useAction(async (reason: string) => {
    if (!userId) return;
    await platformUsersApi.changeAccessScope(userId, newScope, reason);
    setScopeModal(false); detail.refetch(); onChanged();
  });

  const u = detail.data as PlatformUserDetail | null;
  const isSelf = currentAdminId && userId === currentAdminId;

  const TABS: { key: DetailTab; label: string }[] = [
    { key: "overview", label: "Overview" }, { key: "roles", label: "Roles & Access" },
    { key: "security", label: "MFA & Security" }, { key: "sessions", label: "Sessions" },
    { key: "history", label: "Login History" }, { key: "risk", label: "Risk Signals" },
    { key: "audit", label: "Audit Logs" },
  ];

  return (
    <Modal open={!!userId} onClose={onClose} title="User Detail" size="xl">
      {detail.loading && <Skeleton height={120} />}
      {detail.error && (
        <div style={{ padding: 16, background: "var(--danger-bg)", borderRadius:"var(--radius-md)", color: "var(--danger-text)", fontSize: 13 }}>
          Could not load user detail. <button onClick={() => detail.refetch()} style={{ textDecoration: "underline", background: "none", border: "none", color: "inherit", cursor: "pointer" }}>Retry</button>
        </div>
      )}
      {!detail.loading && u && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Header */}
          <div style={{ display: "flex", gap: 14, alignItems: "center", padding: "14px 18px", background: "var(--surface-sunken)", borderRadius: 10 }}>
            <div style={{ width: 48, height: 48, borderRadius: "50%", background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: 18, flexShrink: 0 }}>
              {u.full_name[0]?.toUpperCase()}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ margin: "0 0 3px", fontWeight: 700, fontSize: 15 }}>{u.full_name}</p>
              <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>{u.email}{u.phone ? ` · ${u.phone}` : ""}</p>
              <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                <Badge variant="info" size="sm">{roleLabel(u.platform_role)}</Badge>
                {statusBadge(u.status)}
                {mfaBadge(u.mfa_status)}
                <Badge variant="muted" size="sm">{scopeLabel(u.access_scope)}</Badge>
                {u.password_reset_required && <Badge variant="warning" size="sm">Password Reset Required</Badge>}
              </div>
            </div>
          </div>

          {/* Header actions */}
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <Btn size="xs" variant="secondary" onClick={() => { setNewRole(u.platform_role ?? ""); setRoleModal(true); }}>Change Role</Btn>
            <Btn size="xs" variant="secondary" onClick={() => { setNewScope(u.access_scope ?? ""); setScopeModal(true); }}>Change Access Scope</Btn>
            <Btn size="xs" variant="secondary" onClick={() => setPendingReasonAction("require_mfa")}>Require MFA</Btn>
            <Btn size="xs" variant="secondary" onClick={() => setPendingReasonAction("force_password_reset")}>Force Password Reset</Btn>
            {u.status === "locked"
              ? <Btn size="xs" variant="secondary" onClick={() => setPendingReasonAction("unlock")}>Unlock Account</Btn>
              : <Btn size="xs" variant="secondary" onClick={() => setPendingReasonAction("lock")}>Lock Account</Btn>}
            {!isSelf && (u.status === "deactivated"
              ? <Btn size="xs" variant="secondary" onClick={() => setPendingReasonAction("reactivate")}>Reactivate</Btn>
              : <Btn size="xs" variant="danger" onClick={() => setPendingReasonAction("deactivate")}>Deactivate</Btn>)}
            {isSelf && <Badge variant="muted" size="sm">This is your own account — deactivate/suspend disabled</Badge>}
          </div>

          {/* Tabs */}
          <div style={{ display: "flex", gap: 4, borderBottom: "2px solid var(--border)", overflowX: "auto" }}>
            {TABS.map(t => (
              <button key={t.key} onClick={() => setTab(t.key)} style={{
                padding: "8px 14px", border: "none", background: "none", cursor: "pointer",
                fontSize: 12, fontWeight: tab === t.key ? 700 : 500, whiteSpace: "nowrap",
                color: tab === t.key ? "var(--accent)" : "var(--text-secondary)",
                borderBottom: tab === t.key ? "2px solid var(--accent)" : "2px solid transparent", marginBottom: -2,
              }}>{t.label}</button>
            ))}
          </div>

          {/* Tab content */}
          <div style={{ minHeight: 240 }}>
            {tab === "overview" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[
                  ["User ID", u.id], ["Full Name", u.full_name], ["Email", u.email], ["Phone", u.phone ?? "—"],
                  ["User Group", u.user_group], ["Primary Role", roleLabel(u.platform_role)],
                  ["Access Scope", scopeLabel(u.access_scope)], ["Status", u.status],
                  ["Created", u.created_at ? new Date(u.created_at).toLocaleString() : "—"],
                  ["Last Login", u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "Never"],
                  ["Invited By", u.invited_by_user_id ?? "—"],
                  ["Last Password Reset", u.last_password_reset_at ? new Date(u.last_password_reset_at).toLocaleString() : "—"],
                ].map(([label, val]) => (
                  <div key={label} style={{ padding: "9px 12px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
                    <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "0 0 3px", textTransform: "uppercase", fontWeight: 700 }}>{label}</p>
                    <p style={{ fontSize: 13, margin: 0, wordBreak: "break-all" }}>{val}</p>
                  </div>
                ))}
              </div>
            )}

            {tab === "roles" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ padding: "10px 14px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", fontWeight: 700, margin: "0 0 4px" }}>Primary Role</p>
                  <p style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>{roleLabel(u.platform_role)}</p>
                </div>
                <div style={{ padding: "10px 14px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", fontWeight: 700, margin: "0 0 4px" }}>Access Scope</p>
                  <p style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>{scopeLabel(u.access_scope)}</p>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                  Effective permissions are derived from platform role + access scope. Read-only admins cannot perform mutating actions anywhere in Platform Users.
                </p>
              </div>
            )}

            {tab === "security" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {tempPw && (
                  <div style={{ padding: "12px 14px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius:"var(--radius-md)" }}>
                    <p style={{ margin: "0 0 6px", fontWeight: 600, fontSize: 13, color: "var(--warning-text)" }}>Temporary Password (copy now — shown once)</p>
                    <code style={{ fontFamily: "monospace", fontWeight: 700, fontSize: 15 }}>{tempPw}</code>
                  </div>
                )}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {[
                    ["MFA Status", u.mfa_status], ["MFA Required by Policy", u.mfa_required ? "Yes" : "No"],
                    ["Password Reset Required", u.password_reset_required ? "Yes" : "No"],
                    ["Temporary Password Active", u.temporary_password_active ? "Yes" : "No"],
                    ["Failed Login Count", String(u.failed_login_attempts)],
                    ["Lock Reason", u.lock_reason ?? "—"], ["Locked Until", u.locked_until ? new Date(u.locked_until).toLocaleString() : "—"],
                  ].map(([label, val]) => (
                    <div key={label} style={{ padding: "9px 12px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
                      <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "0 0 3px", textTransform: "uppercase", fontWeight: 700 }}>{label}</p>
                      <p style={{ fontSize: 13, margin: 0 }}>{val}</p>
                    </div>
                  ))}
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <Btn size="xs" variant="secondary" onClick={() => setPendingReasonAction("reset_mfa")}>Reset MFA</Btn>
                  <Btn size="xs" variant="secondary" onClick={() => setPendingReasonAction("send_reset_link")}>Send Reset Link</Btn>
                  <Btn size="xs" variant="warning" onClick={() => setPendingReasonAction("generate_temp_password")}>
                    Generate Temp Password (Super Admin only)
                  </Btn>
                  <Btn size="xs" variant="danger" onClick={() => setPendingReasonAction("revoke_sessions")}>Revoke All Sessions</Btn>
                </div>
              </div>
            )}

            {tab === "sessions" && (
              <div style={{ overflowX: "auto" }}>
                {sessions.loading && <Skeleton height={80} />}
                {!sessions.loading && (
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead><tr>{["Device", "IP Hint", "Trusted", "Last Seen", "Created"].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                    <tbody>
                      {(sessions.data?.sessions ?? []).map(s => (
                        <tr key={s.session_id}>
                          <td style={TD}>{s.device_name} <span style={{ color: "var(--text-tertiary)" }}>({s.device_type})</span></td>
                          <td style={TD}>{s.ip_address ?? "—"}</td>
                          <td style={TD}>{s.is_trusted ? <CheckCircle2 size={14} style={{ color: "var(--success)" }} /> : "—"}</td>
                          <td style={TD}>{new Date(s.last_active_at).toLocaleString()}</td>
                          <td style={TD}>{new Date(s.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                      {(sessions.data?.sessions ?? []).length === 0 && <tr><td colSpan={5} style={{ padding: 20, textAlign: "center", color: "var(--text-tertiary)" }}>No active sessions.</td></tr>}
                    </tbody>
                  </TableSurface>
                )}
              </div>
            )}

            {tab === "history" && (
              <div style={{ overflowX: "auto" }}>
                {history.loading && <Skeleton height={80} />}
                {!history.loading && (
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead><tr>{["Time", "Result", "IP Hint", "Failure Reason"].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                    <tbody>
                      {(history.data?.events ?? []).map(e => (
                        <tr key={e.event_id}>
                          <td style={TD}>{new Date(e.created_at).toLocaleString()}</td>
                          <td style={TD}><Badge variant={e.event_type.includes("success") ? "success" : "danger"} size="sm">{e.event_type}</Badge></td>
                          <td style={TD}>{e.ip_address ?? "—"}</td>
                          <td style={TD}>{e.failure_reason ?? "—"}</td>
                        </tr>
                      ))}
                      {(history.data?.events ?? []).length === 0 && <tr><td colSpan={4} style={{ padding: 20, textAlign: "center", color: "var(--text-tertiary)" }}>No login history.</td></tr>}
                    </tbody>
                  </TableSurface>
                )}
              </div>
            )}

            {tab === "risk" && (
              <div>
                {risk.loading && <Skeleton height={80} />}
                {!risk.loading && risk.data && (
                  <>
                    <div style={{ marginBottom: 12 }}>
                      <Badge variant={risk.data.risk_score === "critical" || risk.data.risk_score === "high" ? "danger" : risk.data.risk_score === "medium" ? "warning" : "success"}>
                        Risk Score: {risk.data.risk_score}
                      </Badge>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {risk.data.signals.map((s, i) => (
                        <div key={i} style={{ display: "flex", gap: 10, padding: "10px 12px", background: "var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
                          <ShieldAlert size={16} style={{ color: s.risk_level === "high" ? "var(--danger)" : s.risk_level === "medium" ? "var(--warning)" : "var(--text-tertiary)", flexShrink: 0 }} />
                          <div>
                            <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{s.risk_type.replace(/_/g, " ")}</p>
                            <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>{s.description}</p>
                          </div>
                        </div>
                      ))}
                      {risk.data.signals.length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No active risk signals.</p>}
                    </div>
                  </>
                )}
              </div>
            )}

            {tab === "audit" && (
              <div style={{ overflowX: "auto" }}>
                {audit.loading && <Skeleton height={80} />}
                {!audit.loading && (
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead><tr>{["Time", "Action", "Reason", "IP Hint"].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                    <tbody>
                      {(audit.data?.logs ?? []).map((l: PlatformUserAuditEntry) => (
                        <tr key={l.id}>
                          <td style={TD}>{l.created_at ? new Date(l.created_at).toLocaleString() : "—"}</td>
                          <td style={TD}><Badge variant="muted" size="sm">{l.action_type}</Badge></td>
                          <td style={TD}>{l.reason ?? "—"}</td>
                          <td style={TD}>{l.ip_hint ?? "—"}</td>
                        </tr>
                      ))}
                      {(audit.data?.logs ?? []).length === 0 && <tr><td colSpan={4} style={{ padding: 20, textAlign: "center", color: "var(--text-tertiary)" }}>No audit history yet.</td></tr>}
                    </tbody>
                  </TableSurface>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <ReasonModal
        open={!!pendingReasonAction}
        title={pendingReasonAction ? pendingReasonAction.replace(/_/g, " ") : ""}
        confirmLabel="Confirm"
        danger={pendingReasonAction === "deactivate" || pendingReasonAction === "lock" || pendingReasonAction === "revoke_sessions"}
        onClose={() => setPendingReasonAction(null)}
        onConfirm={actionRunning.execute}
        loading={actionRunning.loading}
      />

      <Modal open={roleModal} onClose={() => setRoleModal(false)} title="Change Role" size="sm">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <select value={newRole} onChange={e => setNewRole(e.target.value)}
            style={{ height: 38, borderRadius:"var(--radius-md)", border: "1px solid var(--border)", padding: "0 10px", fontSize: 13 }}>
            {PLATFORM_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
          <ReasonInline onConfirm={changeRole.execute} loading={changeRole.loading} onCancel={() => setRoleModal(false)} confirmLabel="Change Role" />
        </div>
      </Modal>
      <Modal open={scopeModal} onClose={() => setScopeModal(false)} title="Change Access Scope" size="sm">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <select value={newScope} onChange={e => setNewScope(e.target.value)}
            style={{ height: 38, borderRadius:"var(--radius-md)", border: "1px solid var(--border)", padding: "0 10px", fontSize: 13 }}>
            {ACCESS_SCOPES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
          <ReasonInline onConfirm={changeScope.execute} loading={changeScope.loading} onCancel={() => setScopeModal(false)} confirmLabel="Change Scope" />
        </div>
      </Modal>
    </Modal>
  );
}

function ReasonInline({ onConfirm, onCancel, loading, confirmLabel }: { onConfirm: (reason: string) => void; onCancel: () => void; loading: boolean; confirmLabel: string }) {
  const [reason, setReason] = useState("");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <textarea value={reason} onChange={e => setReason(e.target.value)} rows={2} placeholder="Reason…"
        style={{ width: "100%", fontSize: 13, padding: "8px 10px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)", boxSizing: "border-box" }} />
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onCancel}>Cancel</Btn>
        <Btn onClick={() => onConfirm(reason)} disabled={reason.trim().length < 3} loading={loading}>{confirmLabel}</Btn>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function PlatformUsersPage() {
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [mfaFilter, setMfaFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [scopeFilter, setScopeFilter] = useState("");
  const [inactiveDaysMin, setInactiveDaysMin] = useState<number | undefined>(undefined);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detailUserId, setDetailUserId] = useState<string | null>(null);
  const [inviteModal, setInviteModal] = useState(false);
  const [invitesModal, setInvitesModal] = useState(false);
  const [toast, setToast] = useState("");
  const [bulkReasonAction, setBulkReasonAction] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  const me = useApi(useCallback(() => authApi.me(), []), []);
  const summary = useApi(useCallback(() => platformUsersApi.getSummary(), []), []);
  const users = useApi(useCallback(() => platformUsersApi.list({
    user_group: "platform", q: q || undefined, platform_role: roleFilter || undefined,
    status: statusFilter || undefined, mfa_status: mfaFilter || undefined,
    access_scope: scopeFilter || undefined, inactive_days_min: inactiveDaysMin,
    page, limit: pageSize,
  }), [q, roleFilter, statusFilter, mfaFilter, scopeFilter, inactiveDaysMin, page, pageSize]),
    [q, roleFilter, statusFilter, mfaFilter, scopeFilter, inactiveDaysMin, page, pageSize]);
  const invites = useApi(useCallback(() => invitesModal ? platformUsersApi.listInvites() : Promise.resolve({ invites: [], total: 0 }), [invitesModal]), [invitesModal]);

  useEffect(() => { setPage(1); setSelected(new Set()); }, [q, roleFilter, statusFilter, mfaFilter, scopeFilter, inactiveDaysMin, pageSize]);

  // Phase 2A Slice 2: default/reset state previously referenced
  // "platform_admin" — a placeholder role removed by FINAL-L5-05N that
  // does not appear in PLATFORM_ROLES above (only the 5 real canonical
  // admin roles do). A <select> bound to an unmatched value renders
  // blank/unselected, so a user who never touches the dropdown would
  // submit an invalid platform_role. Defaults to the least-privileged
  // real role instead.
  const [inv, setInv] = useState({ full_name: "", email: "", phone: "", platform_role: "admin_readonly", access_scope: "operations", require_mfa: true, invite_expiry_days: 7 });
  const invite = useAction(async () => {
    await platformUsersApi.invite(inv);
    setInviteModal(false);
    setInv({ full_name: "", email: "", phone: "", platform_role: "admin_readonly", access_scope: "operations", require_mfa: true, invite_expiry_days: 7 });
    await Promise.all([users.refetch(), summary.refetch()]);
    notify("Invitation sent.");
  });

  const resendInvite = useAction(async (inviteId: string) => {
    await platformUsersApi.resendInvite(inviteId);
    await invites.refetch();
    notify("Invitation resent.");
  });
  const revokeInvite = useAction(async (inviteId: string) => {
    await platformUsersApi.revokeInvite(inviteId, "Revoked by admin");
    await Promise.all([invites.refetch(), users.refetch(), summary.refetch()]);
    notify("Invitation revoked.");
  });

  const bulkRunning = useAction(async (reason: string) => {
    if (!bulkReasonAction) return;
    const ids = Array.from(selected);
    const res = await platformUsersApi.bulkAction(bulkReasonAction, ids, reason);
    setBulkReasonAction(null); setSelected(new Set());
    await Promise.all([users.refetch(), summary.refetch()]);
    notify(`Bulk ${bulkReasonAction.replace(/_/g, " ")}: ${res.succeeded}/${res.total} succeeded.`);
  });

  function clearFilters() {
    setQ(""); setStatusFilter(""); setMfaFilter(""); setRoleFilter(""); setScopeFilter(""); setInactiveDaysMin(undefined);
  }

  const rows = users.data?.users ?? [];
  const meta = users.data?.meta;
  const totalPages = meta?.total_pages ?? 1;
  const totalUsers = meta?.total ?? rows.length;
  const s = summary.data;

  function toggleRow(id: string) {
    setSelected(prev => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next; });
  }
  function toggleAll() {
    setSelected(prev => prev.size === rows.length ? new Set() : new Set(rows.map(r => r.id)));
  }

  const currentAdminId: string | null = me.data?.id ?? null;

  return (
    <AdminLayout activeNav="users">
      <RequirePermission requiredPermission="auth:users:read" parentLabel="Dashboard">
      <PageShell>
        <PageHeader
          title="Platform Users"
          description="Manage platform administrator accounts, roles, MFA, sessions, security, and platform-level access."
          actions={<><ActionMenu items={[
            { label: "View Invitations", onClick: () => setInvitesModal(true) },
            { label: "Export Filtered Users", onClick: async () => {
                const res = await platformUsersApi.export({
                  user_group: "platform",
                  q: q || undefined,
                  platform_role: roleFilter || undefined,
                  status: statusFilter || undefined,
                  mfa_status: mfaFilter || undefined,
                  access_scope: scopeFilter || undefined,
                  inactive_days_min: inactiveDaysMin,
                });
                notify(`Exported ${res.count} users.`);
              } },
          ]}/><Btn size="sm" onClick={() => setInviteModal(true)} icon={<Mail size={14} />}>Invite User</Btn></>}
        />

        {toast && (
          <div style={{ padding: "12px 16px", background: "var(--success-bg)", border: "1px solid var(--success-border)", borderRadius: 10, color: "var(--success-text)", fontSize: 13 }}>
            ✓ {toast}
          </div>
        )}

        {/* Summary cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
          {summary.loading ? (
            [...Array(8)].map((_, i) => (
              <Card key={i} padding={18}><Skeleton height={12} width={80} style={{ marginBottom: 10 }} /><Skeleton height={28} width={50} /></Card>
            ))
          ) : s && <>
            <StatCard label="Total Platform Users" value={s.total_platform_users} icon={<Users />} />
            <StatCard label="Active Users" value={s.active_users} icon={<CheckCircle2 />} trend="up" />
            <StatCard label="MFA Enabled" value={s.mfa_enabled} icon={<Lock />} trend={s.mfa_enabled < s.total_platform_users / 2 ? "down" : "up"} />
            <StatCard label="Administrators" value={s.administrators} icon={<Star />} />
            <StatCard label="MFA Missing" value={s.mfa_missing} icon={<ShieldAlert />} alert={s.mfa_missing > 0} onClick={() => setMfaFilter("off")} />
            <StatCard label="Pending Invites" value={s.pending_invites} icon={<Mail />} onClick={() => setInvitesModal(true)} />
            <StatCard label="Locked Accounts" value={s.locked_accounts} icon={<Lock />} alert={s.locked_accounts > 0} onClick={() => setStatusFilter("locked")} />
            <StatCard label="Suspicious Logins" value={s.suspicious_logins} icon={<ShieldAlert />} alert={s.suspicious_logins > 0} onClick={() => setInactiveDaysMin(undefined)} />
            <StatCard label="Inactive 30+ Days" value={s.inactive_30_days} icon={<Clock />} onClick={() => setInactiveDaysMin(30)} />
          </>}
        </div>

        {/* Toolbar */}
        <Card padding={0}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ flex: 1, minWidth: 220 }}>
              <SearchBar value={q} onChange={setQ} placeholder="Search by name, email, or phone…" />
            </div>
            <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)} style={{ height: 38, borderRadius:"var(--radius-md)", border: "1px solid var(--border)", padding: "0 10px", fontSize: 13 }}>
              <option value="">All Roles</option>
              {PLATFORM_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ height: 38, borderRadius:"var(--radius-md)", border: "1px solid var(--border)", padding: "0 10px", fontSize: 13 }}>
              <option value="">All Statuses</option>
              {["active", "invited", "locked", "suspended", "password_reset_required", "deactivated"].map(v => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
            </select>
            <select value={mfaFilter} onChange={e => setMfaFilter(e.target.value)} style={{ height: 38, borderRadius:"var(--radius-md)", border: "1px solid var(--border)", padding: "0 10px", fontSize: 13 }}>
              <option value="">All MFA</option>
              <option value="on">MFA On</option>
              <option value="off">MFA Off</option>
              <option value="required">MFA Required</option>
            </select>
            <select value={scopeFilter} onChange={e => setScopeFilter(e.target.value)} style={{ height: 38, borderRadius:"var(--radius-md)", border: "1px solid var(--border)", padding: "0 10px", fontSize: 13 }}>
              <option value="">All Access Scopes</option>
              {ACCESS_SCOPES.map(s2 => <option key={s2.value} value={s2.value}>{s2.label}</option>)}
            </select>
            <Btn size="sm" variant="secondary" onClick={() => { users.refetch(); summary.refetch(); }}><RefreshCw size={13} style={{ marginRight: 4 }} />Refresh</Btn>
            <Btn size="sm" variant="ghost" onClick={clearFilters}>Clear Filters</Btn>
          </div>

          {(q || statusFilter || mfaFilter || roleFilter || scopeFilter || inactiveDaysMin) && (
            <div style={{ padding: "10px 20px", display: "flex", gap: 6, flexWrap: "wrap", borderBottom: "1px solid var(--border)" }}>
              {q && <Badge variant="info" size="sm">Search: {q}</Badge>}
              {roleFilter && <Badge variant="info" size="sm">Role: {roleLabel(roleFilter)}</Badge>}
              {statusFilter && <Badge variant="info" size="sm">Status: {statusFilter}</Badge>}
              {mfaFilter && <Badge variant="info" size="sm">MFA: {mfaFilter}</Badge>}
              {scopeFilter && <Badge variant="info" size="sm">Scope: {scopeLabel(scopeFilter)}</Badge>}
              {inactiveDaysMin && <Badge variant="info" size="sm">Inactive {inactiveDaysMin}+ days</Badge>}
            </div>
          )}

          {selected.size > 0 && (
            <div style={{ padding: "10px 20px", display: "flex", gap: 8, alignItems: "center", background: "var(--accent-muted)", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{selected.size} selected</span>
              <Btn size="xs" variant="secondary" onClick={() => setBulkReasonAction("require_mfa")}>Require MFA</Btn>
              <Btn size="xs" variant="secondary" onClick={() => setBulkReasonAction("force_password_reset")}>Force Password Reset</Btn>
              <Btn size="xs" variant="secondary" onClick={() => setBulkReasonAction("revoke_sessions")}>Revoke Sessions</Btn>
              <Btn size="xs" variant="warning" onClick={() => setBulkReasonAction("suspend")}>Suspend</Btn>
              <Btn size="xs" variant="danger" onClick={() => setBulkReasonAction("deactivate")}>Deactivate</Btn>
              <Btn size="xs" variant="ghost" onClick={() => setSelected(new Set())}>Clear Selection</Btn>
            </div>
          )}

          {users.loading ? (
            <div style={{ padding: 20 }}>{[...Array(5)].map((_, i) => <div key={i} style={{ padding: "10px 0" }}><Skeleton height={14} /></div>)}</div>
          ) : users.error ? (
            <div style={{ padding: 24, textAlign: "center", color: "var(--danger-text)", fontSize: 13 }}>
              Could not load platform users. <button onClick={() => users.refetch()} style={{ textDecoration: "underline", background: "none", border: "none", color: "inherit", cursor: "pointer" }}>Retry</button>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={{ ...TH, width: 32 }}><input type="checkbox" checked={rows.length > 0 && selected.size === rows.length} onChange={toggleAll} /></th>
                    {["User", "Role", "Access Scope", "Status", "MFA", "Last Login", "Risk", "Created", "Actions"].map(h => <th key={h} style={TH}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(u => {
                    const risk = deriveRisk(u);
                    return (
                      <tr key={u.id}>
                        <td style={TD}><input type="checkbox" checked={selected.has(u.id)} onChange={() => toggleRow(u.id)} /></td>
                        <td style={TD}>
                          <div style={{ display: "flex", flexDirection: "column" }}>
                            <span style={{ fontWeight: 600 }}>{u.full_name}</span>
                            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{u.email}</span>
                          </div>
                        </td>
                        <td style={TD}><Badge variant="info" size="sm">{roleLabel(u.platform_role)}</Badge></td>
                        <td style={TD}><Badge variant="muted" size="sm">{scopeLabel(u.access_scope)}</Badge></td>
                        <td style={TD}>{statusBadge(u.status)}</td>
                        <td style={TD}>{mfaBadge(u.mfa_status)}</td>
                        <td style={TD}><span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "Never"}</span></td>
                        <td style={TD}><Badge variant={risk.variant} size="sm">{risk.label}</Badge></td>
                        <td style={TD}><span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</span></td>
                        <td style={TD}>
                          <ActionMenu items={[
                            { label: "View User", onClick: () => setDetailUserId(u.id) },
                            { label: "Change Role", onClick: () => setDetailUserId(u.id) },
                            { label: "Require MFA", onClick: async () => { await platformUsersApi.requireMfa(u.id, "Required from list view"); users.refetch(); notify("MFA required."); } },
                            { label: u.status === "locked" ? "Unlock Account" : "Lock Account", onClick: () => setDetailUserId(u.id) },
                            { label: "View Login History", onClick: () => setDetailUserId(u.id) },
                            { label: "View Audit Logs", onClick: () => setDetailUserId(u.id) },
                          ]} />
                        </td>
                      </tr>
                    );
                  })}
                  {rows.length === 0 && (
                    <tr><td colSpan={10} style={{ padding: 40, textAlign: "center", color: "var(--text-tertiary)" }}>
                      {q || statusFilter || mfaFilter || roleFilter || scopeFilter
                        ? "No users match these filters. Clear filters or broaden your search."
                        : "No platform users found. Invite your first platform user to manage internal access."}
                    </td></tr>
                  )}
                </tbody>
              </TableSurface>
              <Pagination page={page} pageSize={pageSize} total={totalUsers} pageCount={totalPages} onPage={setPage}
                pageSizes={[25, 50, 100, 200]} onPageSize={size => { setPageSize(size); setPage(1); }} itemLabel="users" alwaysShow />
            </div>
          )}
        </Card>
      </PageShell>

      <UserDetailDrawer
        userId={detailUserId}
        onClose={() => setDetailUserId(null)}
        onChanged={() => { users.refetch(); summary.refetch(); }}
        currentAdminId={currentAdminId}
      />

      {/* Invite Modal */}
      <Modal open={inviteModal} onClose={() => setInviteModal(false)} title="Invite Platform User" size="md">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Input label="Full Name" value={inv.full_name} onChange={v => setInv(p => ({ ...p, full_name: v }))} required />
          <Input label="Email" value={inv.email} onChange={v => setInv(p => ({ ...p, email: v }))} required />
          <Input label="Phone (optional)" value={inv.phone} onChange={v => setInv(p => ({ ...p, phone: v }))} />
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Platform Role</label>
            <select value={inv.platform_role} onChange={e => setInv(p => ({ ...p, platform_role: e.target.value }))}
              style={{ width: "100%", height: 38, padding: "0 12px", border: "1px solid var(--border)", borderRadius: 10, fontSize: 13 }}>
              {PLATFORM_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Access Scope</label>
            <select value={inv.access_scope} onChange={e => setInv(p => ({ ...p, access_scope: e.target.value }))}
              style={{ width: "100%", height: 38, padding: "0 12px", border: "1px solid var(--border)", borderRadius: 10, fontSize: 13 }}>
              {ACCESS_SCOPES.map(s2 => <option key={s2.value} value={s2.value}>{s2.label}</option>)}
            </select>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
            <input type="checkbox" checked={inv.require_mfa} onChange={e => setInv(p => ({ ...p, require_mfa: e.target.checked }))} />
            Require MFA on first login
          </label>
          <Input label="Invite Expiry (days)" value={String(inv.invite_expiry_days)} onChange={v => setInv(p => ({ ...p, invite_expiry_days: Number(v) || 7 }))} />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={() => setInviteModal(false)}>Cancel</Btn>
            <Btn onClick={invite.execute} loading={invite.loading} disabled={!inv.full_name || !inv.email}>Send Invitation</Btn>
          </div>
          {invite.error && <p style={{ color: "var(--danger-text)", fontSize: 12, margin: 0 }}>{invite.error}</p>}
        </div>
      </Modal>

      {/* Invitations list modal */}
      <Modal open={invitesModal} onClose={() => setInvitesModal(false)} title="Pending Invitations" size="lg">
        {invites.loading && <Skeleton height={100} />}
        {!invites.loading && (
          <div style={{ overflowX: "auto" }}>
            <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr>{["Email", "Role", "Access Scope", "Status", "Expires", "Actions"].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
              <tbody>
                {(invites.data?.invites ?? []).map((inv2: PlatformUserInvite) => (
                  <tr key={inv2.invite_id}>
                    <td style={TD}>{inv2.email}</td>
                    <td style={TD}><Badge variant="info" size="sm">{roleLabel(inv2.platform_role)}</Badge></td>
                    <td style={TD}><Badge variant="muted" size="sm">{scopeLabel(inv2.access_scope)}</Badge></td>
                    <td style={TD}><Badge variant={inv2.status === "pending" ? "info" : "muted"} size="sm">{inv2.status}</Badge></td>
                    <td style={TD}>{inv2.expires_at ? new Date(inv2.expires_at).toLocaleDateString() : "—"}</td>
                    <td style={TD}>
                      <div style={{ display: "flex", gap: 6 }}>
                        <Btn size="xs" variant="secondary" onClick={() => resendInvite.execute(inv2.invite_id)} loading={resendInvite.loading}>Resend</Btn>
                        <Btn size="xs" variant="danger" onClick={() => revokeInvite.execute(inv2.invite_id)} loading={revokeInvite.loading}>Revoke</Btn>
                      </div>
                    </td>
                  </tr>
                ))}
                {(invites.data?.invites ?? []).length === 0 && <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>No pending invitations.</td></tr>}
              </tbody>
            </TableSurface>
          </div>
        )}
      </Modal>

      <ReasonModal
        open={!!bulkReasonAction}
        title={`Bulk ${bulkReasonAction?.replace(/_/g, " ") ?? ""}`}
        description={`This will apply to ${selected.size} selected user(s).`}
        confirmLabel="Confirm Bulk Action"
        danger={bulkReasonAction === "deactivate" || bulkReasonAction === "suspend"}
        onClose={() => setBulkReasonAction(null)}
        onConfirm={bulkRunning.execute}
        loading={bulkRunning.loading}
      />
      </RequirePermission>
    </AdminLayout>
  );
}
