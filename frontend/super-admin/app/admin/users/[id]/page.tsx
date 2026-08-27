"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * Admin User Security Detail Page
 * Route: /admin/users/[id]
 * Sections: Account Status · Password Security · Active Sessions · Login History · Actions
 */
import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import {
  Card, SectionHeader, Btn, Badge, Spinner, Modal,
} from "../../../../components/shared/ui";
import { authApi, type UserSecurityStatus } from "../../../../lib/api";

// ── local helpers ────────────────────────────────────────────────────────────
function fmt(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}
function statusVariant(s: string): "success" | "danger" | "warning" | "muted" {
  if (s === "active")   return "success";
  if (s === "locked")   return "danger";
  if (s === "disabled") return "muted";
  return "warning";
}

// ── types ────────────────────────────────────────────────────────────────────
interface Session {
  session_id: string; device_name: string; device_type: string;
  ip_address: string | null; last_active_at: string;
  is_trusted: boolean; is_approved: boolean; created_at: string;
}
interface LoginHistoryEvent {
  event_id: string; event_type: string; failure_reason: string | null;
  ip_address: string | null; device_id: string | null; created_at: string;
}
interface FullSecurityStatus extends UserSecurityStatus {
  account_status: string;
  lock_reason: string | null;
  locked_until: string | null;
  deactivated_at: string | null;
  deactivation_reason: string | null;
  password_changed_at: string | null;
  failed_login_attempts: number;
  force_password_change: boolean;
}

// ── row component ─────────────────────────────────────────────────────────────
function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start",
      padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ fontSize: 12, color: "var(--text-tertiary)", fontWeight: 500,
        textTransform: "uppercase", letterSpacing: "0.05em", flexShrink: 0, marginRight: 16 }}>
        {label}
      </span>
      <span style={{ fontSize: 13, color: "var(--text-primary)", textAlign: "right" }}>
        {value ?? "—"}
      </span>
    </div>
  );
}

// ── page ─────────────────────────────────────────────────────────────────────
export default function UserSecurityPage() {
  const params = useParams();
  const userId = params?.id as string;

  const [security, setSecurity] = useState<FullSecurityStatus | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [history, setHistory] = useState<LoginHistoryEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [confirmModal, setConfirmModal] = useState<{
    title: string; body: string; action: () => Promise<void>
  } | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [reason, setReason] = useState("");
  const [tempPw, setTempPw] = useState<string | null>(null);

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 4000); };

  const load = useCallback(async () => {
    if (!userId) return;
    setLoading(true); setError("");
    try {
      const [sec, sess, hist] = await Promise.all([
        authApi.getUserSecurityStatus(userId) as Promise<FullSecurityStatus>,
        (authApi as any).adminListSessions(userId) as Promise<{ sessions: Session[] }>,
        (authApi as any).adminGetLoginHistory(userId) as Promise<{ events: LoginHistoryEvent[] }>,
      ]);
      setSecurity(sec as FullSecurityStatus);
      setSessions((sess as any).sessions ?? []);
      setHistory((hist as any).events ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load user security data.");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { load(); }, [load]);

  async function runConfirm() {
    if (!confirmModal) return;
    setConfirmLoading(true);
    try {
      await confirmModal.action();
      setConfirmModal(null);
      setReason("");
      await load();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setConfirmLoading(false);
    }
  }

  function openConfirm(title: string, body: string, action: () => Promise<void>) {
    setReason("");
    setConfirmModal({ title, body, action });
  }

  if (loading) return (
    <AdminLayout activeNav="users">
      <div style={{ display: "flex", justifyContent: "center", padding: 60 }}><Spinner /></div>
    </AdminLayout>
  );

  if (error || !security) return (
    <AdminLayout activeNav="users">
      <div style={{ padding: 40, textAlign: "center", color: "var(--danger-text)" }}>
        {error || "User not found."}
      </div>
    </AdminLayout>
  );

  const acctStatus = (security as FullSecurityStatus).account_status ?? (security.is_active ? "active" : "disabled");

  return (
    <AdminLayout activeNav="users">
      <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 900 }}>

        <SectionHeader
          title={security.full_name}
          subtitle={`${security.email} · ${security.role.replace(/_/g, " ")}`}
          actions={
            <Btn size="sm" variant="ghost" onClick={() => window.history.back()}>
              ← Back to Users
            </Btn>
          }
        />

        {toast && (
          <div style={{ padding: "12px 16px", background: "var(--success-bg)",
            border: "1px solid var(--success-border)", borderRadius: 10,
            color: "var(--success-text)", fontSize: 13 }}>
            {toast}
          </div>
        )}

        {tempPw && (
          <div style={{ padding: "16px 20px", background: "var(--warning-bg)",
            border: "1px solid var(--warning-border)", borderRadius: 10 }}>
            <p style={{ margin: "0 0 8px", fontWeight: 600, color: "var(--warning-text)", fontSize: 13 }}>
              Temporary Password — copy now, shown once only
            </p>
            <code style={{ fontSize: 16, fontFamily: "monospace", fontWeight: 700,
              letterSpacing: "0.08em", color: "var(--text-primary)" }}>{tempPw}</code>
            <Btn size="xs" variant="ghost" style={{ marginLeft: 12 }} onClick={() => setTempPw(null)}>
              Dismiss
            </Btn>
          </div>
        )}

        {/* ── Account Status ─────────────────────────────────────────────── */}
        <Card padding={24}>
          <p style={{ fontWeight: 700, fontSize: 14, margin: "0 0 16px" }}>Account Status</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" }}>
            <div>
              <InfoRow label="Status"
                value={<Badge variant={statusVariant(acctStatus)} size="sm">{acctStatus}</Badge>} />
              <InfoRow label="Active" value={security.is_active ? "Yes" : "No"} />
              <InfoRow label="MFA"
                value={<Badge variant={security.mfa_enabled ? "success" : "warning"} size="sm">
                  {security.mfa_enabled ? "Enabled" : "Disabled"}</Badge>} />
              <InfoRow label="Active Sessions" value={security.active_sessions} />
            </div>
            <div>
              <InfoRow label="Lock Reason" value={(security as FullSecurityStatus).lock_reason} />
              <InfoRow label="Locked Until" value={fmt((security as FullSecurityStatus).locked_until)} />
              <InfoRow label="Deactivated" value={fmt((security as FullSecurityStatus).deactivated_at)} />
              <InfoRow label="Deactivation Reason" value={(security as FullSecurityStatus).deactivation_reason} />
            </div>
          </div>
        </Card>

        {/* ── Password Security ──────────────────────────────────────────── */}
        <Card padding={24}>
          <p style={{ fontWeight: 700, fontSize: 14, margin: "0 0 16px" }}>Password Security</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" }}>
            <div>
              <InfoRow label="Force Change"
                value={<Badge variant={security.password_reset_required ? "warning" : "success"} size="sm">
                  {security.password_reset_required ? "Required" : "No"}</Badge>} />
              <InfoRow label="Temp PW Active"
                value={<Badge variant={security.temporary_password_active ? "warning" : "success"} size="sm">
                  {security.temporary_password_active ? "Yes" : "No"}</Badge>} />
            </div>
            <div>
              <InfoRow label="Last Login" value={fmt(security.last_login_at)} />
              <InfoRow label="Last Reset" value={fmt(security.last_password_reset_at)} />
            </div>
          </div>
        </Card>

        {/* ── Security Actions ───────────────────────────────────────────── */}
        <Card padding={24}>
          <p style={{ fontWeight: 700, fontSize: 14, margin: "0 0 16px" }}>Security Actions</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {acctStatus !== "locked" ? (
              <Btn size="sm" variant="danger" onClick={() => openConfirm(
                "Lock Account",
                "This will prevent the user from logging in and revoke all active sessions.",
                async () => {
                  await (authApi as any).lockUser(userId, reason || "Admin security review", true);
                  notify("Account locked and sessions revoked.");
                },
              )}>Lock Account</Btn>
            ) : (
              <Btn size="sm" variant="secondary" onClick={() => openConfirm(
                "Unlock Account", "This will allow the user to log in again.",
                async () => {
                  await (authApi as any).unlockUser(userId, reason || "Issue resolved");
                  notify("Account unlocked.");
                },
              )}>Unlock Account</Btn>
            )}

            {security.is_active ? (
              <Btn size="sm" variant="danger" onClick={() => openConfirm(
                "Deactivate User",
                "This will disable the account and revoke all sessions. The user cannot log in until reactivated.",
                async () => {
                  await (authApi as any).deactivateUser(userId, reason || "Deactivated by admin", true);
                  notify("User deactivated.");
                },
              )}>Deactivate User</Btn>
            ) : (
              <Btn size="sm" variant="secondary" onClick={() => openConfirm(
                "Reactivate User", "This will allow the user to log in again.",
                async () => {
                  await (authApi as any).reactivateUser(userId, reason || "Reactivated by admin");
                  notify("User reactivated.");
                },
              )}>Reactivate User</Btn>
            )}

            <Btn size="sm" variant="secondary" onClick={() => openConfirm(
              "Revoke All Sessions",
              "All active sessions will be immediately invalidated. The user will need to log in again.",
              async () => {
                await (authApi as any).adminRevokeAllSessions(userId, reason || "Security reset");
                notify("All sessions revoked.");
              },
            )}>Revoke Sessions</Btn>

            <Btn size="sm" variant="secondary" onClick={() => openConfirm(
              "Force Password Change",
              "The user will be required to change their password on next login.",
              async () => {
                await authApi.adminForcePasswordChange(userId, reason || "Admin initiated", true);
                notify("Force password change set.");
              },
            )}>Force PW Change</Btn>

            <Btn size="sm" variant="secondary" onClick={async () => {
              try {
                const res = await authApi.adminGenerateTemporaryPassword(
                  userId, "Admin generated", true);
                setTempPw((res as any).temporary_password);
                notify("Temporary password generated.");
                await load();
              } catch (e: unknown) {
                notify(e instanceof Error ? e.message : "Failed.");
              }
            }}>Generate Temp PW</Btn>
          </div>
        </Card>

        {/* ── Active Sessions ────────────────────────────────────────────── */}
        <Card padding={0}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)",
            display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <p style={{ margin: 0, fontWeight: 700, fontSize: 14 }}>Active Sessions ({sessions.length})</p>
          </div>
          {sessions.length === 0 ? (
            <p style={{ padding: 20, margin: 0, color: "var(--text-tertiary)", fontSize: 13 }}>
              No active sessions.
            </p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)" }}>
                    {["Device", "IP", "Last Active", "Created", ""].map(h => (
                      <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600,
                        fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase",
                        letterSpacing: "0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sessions.map(s => (
                    <tr key={s.session_id} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 16px" }}>
                        <div style={{ fontWeight: 600 }}>{s.device_name}</div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{s.device_type}</div>
                      </td>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12 }}>
                        {s.ip_address ?? "—"}
                      </td>
                      <td style={{ padding: "10px 16px", color: "var(--text-secondary)", fontSize: 12 }}>
                        {fmt(s.last_active_at)}
                      </td>
                      <td style={{ padding: "10px 16px", color: "var(--text-secondary)", fontSize: 12 }}>
                        {fmt(s.created_at)}
                      </td>
                      <td style={{ padding: "10px 16px" }}>
                        <Btn size="xs" variant="danger" onClick={() => openConfirm(
                          "Revoke Session",
                          `Revoke session for ${s.device_name}? The user will be logged out from that device.`,
                          async () => {
                            await (authApi as any).adminRevokeAllSessions(userId, "Admin revoked individual session");
                            notify("Session revoked.");
                          },
                        )}>Revoke</Btn>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableSurface>
            </div>
          )}
        </Card>

        {/* ── Login History ──────────────────────────────────────────────── */}
        <Card padding={0}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
            <p style={{ margin: 0, fontWeight: 700, fontSize: 14 }}>Recent Login History</p>
          </div>
          {history.length === 0 ? (
            <p style={{ padding: 20, margin: 0, color: "var(--text-tertiary)", fontSize: 13 }}>
              No login events recorded.
            </p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)" }}>
                    {["Time", "Event", "IP Address", "Device", "Failure Reason"].map(h => (
                      <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600,
                        fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase",
                        letterSpacing: "0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {history.map(ev => (
                    <tr key={ev.event_id} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 16px", color: "var(--text-secondary)", fontSize: 12 }}>
                        {fmt(ev.created_at)}
                      </td>
                      <td style={{ padding: "10px 16px" }}>
                        <Badge
                          variant={ev.event_type === "login_success" ? "success"
                            : ev.event_type === "login_failed" ? "danger" : "muted"}
                          size="sm">
                          {ev.event_type.replace(/_/g, " ")}
                        </Badge>
                      </td>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12 }}>
                        {ev.ip_address ?? "—"}
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                        {ev.device_id ?? "—"}
                      </td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--danger-text)" }}>
                        {ev.failure_reason ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableSurface>
            </div>
          )}
        </Card>

      </div>

      {/* ── Confirm Modal ──────────────────────────────────────────────────── */}
      <Modal open={!!confirmModal} onClose={() => !confirmLoading && setConfirmModal(null)}
        title={confirmModal?.title ?? ""} size="sm">
        {confirmModal && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              {confirmModal.body}
            </p>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)",
                display: "block", marginBottom: 5 }}>
                Reason (optional)
              </label>
              <textarea
                value={reason}
                onChange={e => setReason(e.target.value)}
                rows={2}
                placeholder="Describe why you are taking this action…"
                style={{ width: "100%", padding: "8px 12px", fontSize: 13,
                  border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
                  background: "var(--surface)", color: "var(--text-primary)",
                  fontFamily: "inherit", resize: "vertical", boxSizing: "border-box" as const }}
              />
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => setConfirmModal(null)} disabled={confirmLoading}>
                Cancel
              </Btn>
              <Btn variant="danger" onClick={runConfirm} loading={confirmLoading}>
                Confirm
              </Btn>
            </div>
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}
