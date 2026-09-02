"use client";
import React, { useCallback } from "react";
import { StaffLayout } from "../../../../components/layout/StaffLayout";
import { Badge, Btn, Card, EmptyState, Skeleton } from "../../../../components/shared/ui";
import { useAction, useApi } from "../../../../hooks/useApi";
import { authApi } from "../../../../lib/api";
import { ShieldCheck } from "lucide-react";

export default function StaffSessionsPage() {
  const sessions = useApi(useCallback(() => authApi.getSessions(), []));
  const revoke = useAction(async (sessionId: string) => {
    await authApi.deleteSession(sessionId);
    sessions.refetch();
  });
  const revokeAll = useAction(async () => {
    await authApi.logoutAll();
    localStorage.removeItem("serviceos_tenant_token");
    localStorage.removeItem("serviceos_tenant_refresh");
    window.location.href = "/staff/login";
  });

  return (
    <StaffLayout activeNav="sessions">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Security / Sessions</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Review and manage your active sign-in sessions.
        </p>
      </div>
      <Card padding={16}>
        {sessions.loading ? <Skeleton height={180}/> : sessions.error ? (
          <div role="alert" style={{ color: "var(--danger-text)", fontSize: 13 }}>
            Could not load your sessions. {sessions.requestId ? `Request ID: ${sessions.requestId}` : ""}
          </div>
        ) : (sessions.data?.sessions ?? []).length === 0 ? (
          <EmptyState icon={<ShieldCheck/>} title="No active sessions found." description="Sign in again if you believe this is incorrect."/>
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 14 }}>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 700 }}>
                Active sessions ({sessions.data?.total ?? 0})
              </p>
              <Btn variant="danger" size="sm" onClick={() => revokeAll.execute()} disabled={revokeAll.loading}>Sign out everywhere</Btn>
            </div>
            {(revoke.error || revokeAll.error) && (
              <p role="alert" style={{ color: "var(--danger-text)", fontSize: 12 }}>{revoke.error || revokeAll.error}</p>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {(sessions.data?.sessions ?? []).map(session => (
                <div key={session.session_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "12px 14px", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
                  <div>
                    <p style={{ margin: "0 0 3px", fontSize: 13, fontWeight: 600 }}>
                      {session.device_display_name || "Unknown device"}
                      {session.is_current && <span style={{ marginLeft: 8 }}><Badge variant="success">Current</Badge></span>}
                    </p>
                    <p style={{ margin: 0, color: "var(--text-tertiary)", fontSize: 11 }}>
                      {session.channel} · Last active {new Date(session.last_active_at).toLocaleString()}
                      {session.approximate_location ? ` · ${session.approximate_location}` : ""}
                    </p>
                  </div>
                  {!session.is_current && session.allowed_actions.includes("revoke") && (
                    <Btn variant="ghost" size="sm" onClick={() => revoke.execute(session.session_id)} disabled={revoke.loading}>Revoke</Btn>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </Card>
    </StaffLayout>
  );
}
