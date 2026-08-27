"use client";
import { TableSurface } from "@serviceos/design-system";
import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Badge, Btn, Skeleton, Modal } from "../../../../components/shared/ui";
import { useApi } from "../../../../hooks/useApi";
import { engineMgmtApi } from "../../../../lib/api";
import type {
  PlatformEngine, EngineImpactPreview, EngineHealthCheckItem,
  EnterpriseEnginePermission, EngineDependencyItem,
} from "../../../../lib/api";
import {
  ArrowLeft, CheckCircle2, XCircle, RefreshCw,
  ToggleLeft, ToggleRight, Lock,
} from "lucide-react";
import { PageHeader } from "@serviceos/design-system";

function StatusBadge({ status }: { status: string }) {
  const v = status === "enabled" ? "success" : status === "disabled" ? "danger" : "warning";
  return <Badge variant={v}>{status}</Badge>;
}

function HealthDot({ status }: { status: string }) {
  const c = status === "healthy" ? "var(--success)" : status === "degraded" ? "var(--warning)" : "var(--danger)";
  return <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: c }} />;
}

function SkeletonRows({ n = 6 }: { n?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {[...Array(n)].map((_, i) => <Skeleton key={i} height={28} />)}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 13 }}>
      <span style={{ width: 200, color: "var(--text-secondary)", flexShrink: 0 }}>{label}</span>
      <span style={{ color: "var(--text-primary)" }}>{value}</span>
    </div>
  );
}

export default function EngineDetailPage() {
  const params = useParams();
  const engineKey = params?.engine_key as string;

  const engine = useApi(useCallback(() => engineMgmtApi.get(engineKey), [engineKey]), [engineKey]);
  const health = useApi(useCallback(() => engineMgmtApi.getEngineHealthHistory(engineKey, 10), [engineKey]), [engineKey]);
  const perms = useApi(useCallback(() => engineMgmtApi.getEnginePermissions(engineKey), [engineKey]), [engineKey]);

  const eng = engine.data as PlatformEngine | null;

  const [impactPreview, setImpactPreview] = useState<EngineImpactPreview | null>(null);
  const [impactAction, setImpactAction] = useState<"enable" | "disable">("disable");
  const [impactLoading, setImpactLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [reason, setReason] = useState("");
  const [healthRunning, setHealthRunning] = useState(false);

  async function openImpact(action: "enable" | "disable") {
    setImpactAction(action);
    setImpactLoading(true);
    try {
      const res = await engineMgmtApi.impactPreview(engineKey, action);
      setImpactPreview(res as unknown as EngineImpactPreview);
      setReason("");
    } finally {
      setImpactLoading(false);
    }
  }

  async function confirmAction() {
    setActionLoading(true);
    try {
      if (impactAction === "enable") {
        await engineMgmtApi.enableGlobally(engineKey, reason);
      } else {
        await engineMgmtApi.disableGlobally(engineKey, reason);
      }
      engine.refetch();
      setImpactPreview(null);
    } finally {
      setActionLoading(false);
    }
  }

  async function runHealthCheck() {
    setHealthRunning(true);
    try {
      await engineMgmtApi.checkEngineHealth(engineKey);
      health.refetch();
    } finally {
      setHealthRunning(false);
    }
  }

  return (
    <AdminLayout>
      <div style={{ marginBottom: 16 }}>
        <Link href="/admin/engines" style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)", textDecoration: "none" }}>
          <ArrowLeft size={14} /> Back to Engine Management
        </Link>
      </div>

      {engine.loading && <SkeletonRows n={8} />}
      {!engine.loading && eng && (
        <>
          {/* Header */}
          <PageHeader
            title={eng.display_name}
            description={eng.description || `Engine key: ${eng.engine_key}`}
            eyebrow="Engine Management"
            actions={<div style={{ display: "flex", gap: "var(--layout-control-gap)", flexWrap: "wrap", alignItems: "center" }}>
                <StatusBadge status={eng.global_status} />
                {eng.is_core && <Badge variant="default">Core</Badge>}
                {eng.is_locked && (
                  <Badge variant="muted"><Lock size={10} style={{ marginRight: 3 }} />Locked</Badge>
                )}
                {!eng.is_locked && (eng.global_status !== "enabled" ? (
                  <Btn variant="success" onClick={() => openImpact("enable")} disabled={impactLoading}>
                    <ToggleRight size={14} style={{ marginRight: 4 }} />
                    Enable Engine
                  </Btn>
                ) : (
                  <Btn variant="danger" onClick={() => openImpact("disable")} disabled={impactLoading}>
                    <ToggleLeft size={14} style={{ marginRight: 4 }} />
                    Disable Engine
                  </Btn>
                ))}
            </div>}
          />

          {/* Details grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
            <Card>
              <SectionHeader title="Engine Details" />
              <DetailRow label="Engine Key" value={<code>{eng.engine_key}</code>} />
              <DetailRow label="Type" value={<Badge variant="muted">{eng.engine_type}</Badge>} />
              <DetailRow label="Lifecycle Status" value={<Badge variant="muted">{eng.lifecycle_status}</Badge>} />
              <DetailRow label="Version" value={eng.version || "—"} />
              <DetailRow label="Owner Team" value={eng.owner_team || "—"} />
              <DetailRow label="Customer Visible" value={
                eng.is_customer_visible
                  ? <CheckCircle2 size={14} style={{ color: "var(--success)" }} />
                  : <XCircle size={14} style={{ color: "var(--text-tertiary)" }} />
              } />
              <DetailRow label="Tenant Visible" value={
                eng.is_tenant_visible
                  ? <CheckCircle2 size={14} style={{ color: "var(--success)" }} />
                  : <XCircle size={14} style={{ color: "var(--text-tertiary)" }} />
              } />
              <DetailRow label="Is Core" value={eng.is_core ? "Yes" : "No"} />
              <DetailRow label="Created" value={new Date(eng.created_at).toLocaleDateString()} />
              <DetailRow label="Updated" value={new Date(eng.updated_at).toLocaleString()} />
            </Card>

            <Card>
              <SectionHeader title="Usage Summary" />
              <DetailRow label="Category Mappings" value={<strong>{eng.category_usage_count ?? 0}</strong>} />
              <DetailRow label="Active Tenant Overrides" value={<strong>{eng.active_overrides ?? 0}</strong>} />
              <DetailRow
                label="Latest Health"
                value={
                  eng.latest_health ? (
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <HealthDot status={eng.latest_health.health_status} />
                      {eng.latest_health.health_status}
                      {eng.latest_health.response_ms != null && (
                        <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>({eng.latest_health.response_ms}ms)</span>
                      )}
                    </div>
                  ) : "Not checked"
                }
              />
              <DetailRow
                label="Dependencies"
                value={
                  (eng.dependencies?.length ?? 0) > 0 ? (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {(eng.dependencies ?? []).map((d: EngineDependencyItem, i: number) => (
                        <Badge key={i} variant="muted">{d.depends_on_engine_key}</Badge>
                      ))}
                    </div>
                  ) : "None"
                }
              />
            </Card>
          </div>

          {/* Health History */}
          <Card style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <SectionHeader title="Health History" subtitle="Last 10 checks" />
              <Btn variant="secondary" size="sm" onClick={runHealthCheck} disabled={healthRunning}>
                <RefreshCw size={12} style={{ marginRight: 4 }} />
                {healthRunning ? "Running…" : "Run Check"}
              </Btn>
            </div>
            {health.loading && <SkeletonRows n={4} />}
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    {["Status", "Type", "Latency", "Error", "Checked At"].map((h, i) => (
                      <th key={i} style={{ padding: "9px 10px", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", letterSpacing: "0.07em", textTransform: "uppercase" as const, background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)", textAlign: "left" as const }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(health.data?.history ?? []).map((c: EngineHealthCheckItem, i: number) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "7px 10px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <HealthDot status={c.health_status} />
                          {c.health_status}
                        </div>
                      </td>
                      <td style={{ padding: "7px 10px" }}><Badge variant="muted">{c.check_type}</Badge></td>
                      <td style={{ padding: "7px 10px", color: "var(--text-secondary)" }}>
                        {c.response_ms != null ? `${c.response_ms}ms` : "—"}
                      </td>
                      <td style={{ padding: "7px 10px", color: "var(--text-secondary)", fontSize: 12 }}>{c.error_message || "—"}</td>
                      <td style={{ padding: "7px 10px", fontSize: 11, color: "var(--text-tertiary)" }}>
                        {new Date(c.checked_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                  {!health.loading && (health.data?.history ?? []).length === 0 && (
                    <tr><td colSpan={5} style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>No health checks yet.</td></tr>
                  )}
                </tbody>
              </TableSurface>
            </div>
          </Card>

          {/* Permissions */}
          <Card>
            <SectionHeader title="Engine Permissions" subtitle={`${perms.data?.meta?.total ?? 0} permissions`} />
            {perms.loading && <SkeletonRows n={4} />}
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    {["Permission Key", "Label", "Scope", "Sensitive", "Description"].map((h, i) => (
                      <th key={i} style={{ padding: "9px 10px", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", letterSpacing: "0.07em", textTransform: "uppercase" as const, background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)", textAlign: "left" as const }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(perms.data?.permissions ?? []).map((p: EnterpriseEnginePermission, i: number) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "7px 10px" }}><code style={{ fontSize: 12 }}>{p.permission_key}</code></td>
                      <td style={{ padding: "7px 10px", fontSize: 13 }}>{p.label}</td>
                      <td style={{ padding: "7px 10px" }}><Badge variant="muted">{p.scope}</Badge></td>
                      <td style={{ padding: "7px 10px" }}>
                        {p.is_sensitive ? <Lock size={13} style={{ color: "var(--warning)" }} /> : "—"}
                      </td>
                      <td style={{ padding: "7px 10px", color: "var(--text-secondary)" }}>{p.description || "—"}</td>
                    </tr>
                  ))}
                  {!perms.loading && (perms.data?.permissions ?? []).length === 0 && (
                    <tr><td colSpan={5} style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>No permissions defined.</td></tr>
                  )}
                </tbody>
              </TableSurface>
            </div>
          </Card>
        </>
      )}

      {/* Impact Modal */}
      <Modal
        open={!!impactPreview}
        onClose={() => setImpactPreview(null)}
        title={`${impactAction === "enable" ? "Enable" : "Disable"} — ${engineKey}`}
      >
        {impactPreview && (
          <div>
            {!impactPreview.can_proceed && (
              <div style={{ padding: "10px 12px", background: "var(--danger-bg)", borderRadius: 6, marginBottom: 12 }}>
                <strong style={{ color: "var(--danger)", fontSize: 13 }}>Cannot Proceed</strong>
                <ul style={{ margin: "6px 0 0", paddingLeft: 16, fontSize: 12 }}>
                  {(impactPreview.blockers || []).map((b, i) => <li key={i}>{b}</li>)}
                </ul>
              </div>
            )}
            {(impactPreview.warnings || []).length > 0 && (
              <div style={{ padding: "10px 12px", background: "var(--warning-bg)", borderRadius: 6, marginBottom: 12 }}>
                <strong style={{ color: "var(--warning)", fontSize: 13 }}>Warnings</strong>
                <ul style={{ margin: "6px 0 0", paddingLeft: 16, fontSize: 12 }}>
                  {(impactPreview.warnings || []).map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}
            <p style={{ fontSize: 13, marginBottom: 10 }}>
              Affects <strong>{impactPreview.categories_affected}</strong> category entries.{" "}
              Risk: <Badge variant={impactPreview.risk_level === "high" ? "danger" : impactPreview.risk_level === "medium" ? "warning" : "default"}>{impactPreview.risk_level}</Badge>
            </p>
            <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>
              Reason {impactAction === "disable" ? "(required)" : "(optional)"}
            </label>
            <textarea
              value={reason}
              onChange={e => setReason(e.target.value)}
              rows={2}
              placeholder={`Reason for ${impactAction}…`}
              style={{ width: "100%", fontSize: 13, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", boxSizing: "border-box" }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
              <Btn variant="secondary" onClick={() => setImpactPreview(null)}>Cancel</Btn>
              <Btn
                variant={impactAction === "enable" ? "success" : "danger"}
                onClick={confirmAction}
                disabled={!impactPreview.can_proceed || actionLoading || (impactAction === "disable" && !reason.trim())}
              >
                {actionLoading ? "Processing…" : `Confirm ${impactAction}`}
              </Btn>
            </div>
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}
