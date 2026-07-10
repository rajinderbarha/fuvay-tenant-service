"use client";
import { useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Skeleton } from "../../../../../components/shared/ui";
import { securityAdminApi } from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";

const LEVEL_VARIANT: Record<string, "danger" | "warning" | "info" | "muted"> = {
  critical: "danger", high: "warning", medium: "info", low: "muted",
};

export default function ThreatDetailPage() {
  const params = useParams();
  const router = useRouter();
  const threatId = String(params.threat_id);
  const threat = useApi(useCallback(() => securityAdminApi.getThreatDetail(threatId), [threatId]));
  const statusAction = useAction(useCallback((s: string) => securityAdminApi.updateThreatStatus(threatId, s), [threatId]));
  const blockAction = useAction(useCallback((reason: string) => securityAdminApi.blockIpFromThreat(threatId, reason), [threatId]));
  const revokeAction = useAction(useCallback((reason: string) => securityAdminApi.revokeSessionsFromThreat(threatId, reason), [threatId]));

  const t = threat.data;

  return (
    <AdminLayout activeNav="security">
      <SectionHeader
        title={t ? `Threat ${t.threat_number ?? t.threat_id.slice(0, 8)}` : "Threat Detail"}
        subtitle={t?.activity_type.replace(/_/g, " ")}
        actions={<Btn variant="ghost" size="sm" icon={<ArrowLeft size={14} />} onClick={() => router.push("/admin/security")}>Back to Security</Btn>}
      />
      <div style={{ padding: "0 28px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
        {threat.loading ? <Skeleton height={300} /> : !t ? (
          <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Could not load threat. {threat.error}</p></Card>
        ) : (
          <>
            <Card padding={20}>
              <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
                <Badge variant={LEVEL_VARIANT[t.threat_level] ?? "muted"}>{t.threat_level.toUpperCase()}</Badge>
                <Badge variant={t.status === "open" ? "danger" : t.status === "resolved" ? "success" : "muted"}>{t.status}</Badge>
                <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Risk Score: {t.risk_score}</span>
              </div>
              <p style={{ fontSize: 14, margin: "0 0 12px" }}>{t.description}</p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, fontSize: 13 }}>
                <div><strong>IP Address</strong><p style={{ margin: "4px 0 0", color: "var(--text-tertiary)" }}>{t.ip_address ?? "—"}</p></div>
                <div><strong>Source</strong><p style={{ margin: "4px 0 0", color: "var(--text-tertiary)" }}>{t.source ?? "—"}</p></div>
                <div><strong>Entity</strong><p style={{ margin: "4px 0 0", color: "var(--text-tertiary)" }}>{t.entity_type}: {t.entity_id}</p></div>
                <div><strong>Target User</strong><p style={{ margin: "4px 0 0", color: "var(--text-tertiary)" }}>{t.target_user_id ?? "—"}</p></div>
                <div><strong>Detected</strong><p style={{ margin: "4px 0 0", color: "var(--text-tertiary)" }}>{new Date(t.created_at).toLocaleString("en-IN")}</p></div>
                <div><strong>Last Seen</strong><p style={{ margin: "4px 0 0", color: "var(--text-tertiary)" }}>{t.last_seen_at ? new Date(t.last_seen_at).toLocaleString("en-IN") : "—"}</p></div>
              </div>
            </Card>

            <Card padding={20}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Recommended Actions</h3>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <Btn variant="secondary" size="sm" loading={statusAction.loading} onClick={async () => { await statusAction.execute("investigating"); threat.refetch(); }}>Mark Investigating</Btn>
                <Btn variant="danger" size="sm" disabled={!t.ip_address} loading={blockAction.loading}
                  onClick={async () => { await blockAction.execute("Blocked from threat detail"); threat.refetch(); }}>Block IP</Btn>
                <Btn variant="danger" size="sm" disabled={!t.target_user_id} loading={revokeAction.loading}
                  onClick={async () => { await revokeAction.execute("Sessions revoked from threat detail"); threat.refetch(); }}>Revoke Sessions</Btn>
                <Btn variant="secondary" size="sm" onClick={async () => { await statusAction.execute("resolved"); threat.refetch(); }}>Mark Resolved</Btn>
                <Btn variant="ghost" size="sm" onClick={async () => { await statusAction.execute("false_positive"); threat.refetch(); }}>Mark False Positive</Btn>
              </div>
            </Card>

            <Card padding={20}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Actions Taken (Audit Trail)</h3>
              {(t.actions_taken ?? []).length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No actions recorded yet for this threat.</p>
              ) : (t.actions_taken ?? []).map(a => (
                <div key={a.log_id} style={{ display: "flex", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 12, flex: 1 }}>{a.operation}</span>
                  <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{new Date(a.created_at).toLocaleString("en-IN")}</span>
                </div>
              ))}
            </Card>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
