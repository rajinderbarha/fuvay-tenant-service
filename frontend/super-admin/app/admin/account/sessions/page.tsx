"use client";
import React, { useState, useEffect, useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Badge, Spinner } from "../../../../components/shared/ui";
import { authApi, type SessionInfo } from "../../../../lib/api";

function fmt(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export default function SelfSessionsPage() {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [revoking, setRevoking] = useState(false);

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 4000); };

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const res = await authApi.getSelfSessions();
      setSessions(res.sessions ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load sessions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function revokeOthers() {
    setRevoking(true);
    try {
      const res = await authApi.revokeSelfOtherSessions();
      notify(`${res.revoked_count} session(s) revoked.`);
      await load();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Failed to revoke sessions.");
    } finally {
      setRevoking(false);
    }
  }

  return (
    <AdminLayout activeNav="account">
      <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 860 }}>
        <SectionHeader
          title="Active Sessions"
          subtitle="All devices currently signed in to your account"
          actions={
            <Btn size="sm" variant="danger" onClick={revokeOthers} loading={revoking}
              disabled={sessions.filter(s => !s.is_current).length === 0}>
              Sign Out All Other Devices
            </Btn>
          }
        />

        {toast && (
          <div style={{ padding: "10px 16px", background: "var(--success-bg)",
            border: "1px solid var(--success-border)", borderRadius: 10,
            color: "var(--success-text)", fontSize: 13 }}>
            {toast}
          </div>
        )}

        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: 48 }}><Spinner /></div>
        ) : error ? (
          <div style={{ padding: 24, color: "var(--danger-text)", fontSize: 13 }}>{error}</div>
        ) : sessions.length === 0 ? (
          <Card padding={24}>
            <p style={{ margin: 0, color: "var(--text-tertiary)", fontSize: 13 }}>
              No active sessions found.
            </p>
          </Card>
        ) : (
          <Card padding={0}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)" }}>
                  {["Device", "Type", "IP Address", "Last Active", "Created", "Status"].map(h => (
                    <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600,
                      fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase",
                      letterSpacing: "0.06em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sessions.map(s => (
                  <tr key={s.session_id} style={{ borderTop: "1px solid var(--border)" }}>
                    <td style={{ padding: "12px 16px" }}>
                      <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{s.device_name}</div>
                      {s.is_current && (
                        <span style={{ fontSize: 11, color: "var(--success-text)", fontWeight: 600 }}>
                          ● This device
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "12px 16px", color: "var(--text-secondary)" }}>{s.device_type}</td>
                    <td style={{ padding: "12px 16px", fontFamily: "monospace", fontSize: 12,
                      color: "var(--text-secondary)" }}>{s.ip_address ?? "—"}</td>
                    <td style={{ padding: "12px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {fmt(s.last_active_at)}
                    </td>
                    <td style={{ padding: "12px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {fmt(s.created_at)}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <Badge variant={s.is_trusted ? "success" : "warning"} size="sm">
                        {s.is_trusted ? "Trusted" : "Unverified"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </AdminLayout>
  );
}
