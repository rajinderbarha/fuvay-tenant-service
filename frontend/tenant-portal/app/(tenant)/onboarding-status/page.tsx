"use client";
import React, { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Btn, Badge, Skeleton } from "../../../components/shared/ui";
import {
  providerOnboardingApi,
  providerPackageApi,
  type ProviderOnboardingStatus,
  type ProviderOnboardingItem,
  type PackageAssignmentSummary,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  CheckCircle2, Clock, XCircle, AlertCircle, RefreshCw,
  ChevronRight, CheckCheck, Info,
} from "lucide-react";

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
  completed:      "success",
  pending:        "warning",
  blocked:        "danger",
  skipped:        "muted",
  overridden:     "info",
  not_applicable: "muted",
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  completed:      <CheckCircle2 size={14} style={{ color: "#059669" }}/>,
  pending:        <Clock size={14} style={{ color: "#d97706" }}/>,
  blocked:        <XCircle size={14} style={{ color: "#dc2626" }}/>,
  skipped:        <Info size={14} style={{ color: "#94a3b8" }}/>,
  overridden:     <CheckCheck size={14} style={{ color: "#2563eb" }}/>,
  not_applicable: <Info size={14} style={{ color: "#94a3b8" }}/>,
};

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div style={{ height: 8, background: "var(--surface-sunken)", borderRadius: 99, overflow: "hidden",
      border: "1px solid var(--border)" }}>
      <div style={{
        height: "100%", borderRadius: 99, transition: "width 0.4s",
        width: `${Math.max(0, Math.min(100, pct))}%`,
        background: pct >= 100 ? "#059669" : pct >= 60 ? "#d97706" : "#2563eb",
      }}/>
    </div>
  );
}

function StatusSummary({ s }: { s: ProviderOnboardingStatus }) {
  return (
    <Card>
      <div style={{ padding: "4px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start",
          marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
          <div>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 2px", fontWeight: 500 }}>
              {s.category_name ?? "Onboarding"} Checklist
            </p>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              {s.progress_percentage}% Complete
            </h2>
          </div>
          <Badge variant={s.onboarding_ready ? "success" : "warning"}>
            {s.onboarding_ready ? "Onboarding Ready" : "Onboarding Pending"}
          </Badge>
        </div>

        <ProgressBar pct={s.progress_percentage}/>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(100px,1fr))",
          gap: 10, marginTop: 16 }}>
          {[
            { label: "Total", value: s.total_items, color: "var(--text-primary)" },
            { label: "Completed", value: s.completed_items, color: "#059669" },
            { label: "Pending", value: s.pending_items, color: "#d97706" },
            { label: "Blocked", value: s.blocked_items, color: "#dc2626" },
          ].map(stat => (
            <div key={stat.label} style={{ background: "var(--surface-sunken)", borderRadius: 10,
              padding: "10px 14px", border: "1px solid var(--border)" }}>
              <p style={{ fontSize: 20, fontWeight: 700, color: stat.color, margin: 0 }}>{stat.value}</p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{stat.label}</p>
            </div>
          ))}
        </div>

        {s.last_refreshed_at && (
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "12px 0 0" }}>
            Last refreshed {new Date(s.last_refreshed_at).toLocaleString()}
          </p>
        )}
      </div>
    </Card>
  );
}

function NextActionCard({ action }: { action: NonNullable<ProviderOnboardingStatus["next_action"]> }) {
  const router = useRouter();
  return (
    <div style={{ background: "linear-gradient(135deg,var(--brand) 0%,var(--accent) 100%)",
      borderRadius: 14, padding: "18px 20px", color: "white" }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase",
        opacity: 0.75, margin: "0 0 6px" }}>Next Step</p>
      <p style={{ fontSize: 15, fontWeight: 700, margin: "0 0 4px" }}>{action.title}</p>
      <p style={{ fontSize: 12, opacity: 0.85, margin: "0 0 14px" }}>{action.description}</p>
      <Btn size="sm" variant="secondary" onClick={() => router.push(action.route)}>
        {action.action_label} <ChevronRight size={13}/>
      </Btn>
    </div>
  );
}

function BlockersList({ blockers }: { blockers: ProviderOnboardingStatus["blockers"] }) {
  const router = useRouter();
  if (!blockers.length) return null;
  return (
    <Card>
      <p style={{ fontSize: 13, fontWeight: 600, color: "#dc2626", margin: "0 0 12px",
        display: "flex", alignItems: "center", gap: 6 }}>
        <AlertCircle size={14}/> {blockers.length} Blocker{blockers.length !== 1 ? "s" : ""}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {blockers.map((b, i) => (
          <div key={i} style={{ padding: "10px 14px", borderRadius: 10,
            background: "rgba(220,38,38,0.06)", border: "1px solid rgba(220,38,38,0.2)",
            display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: "#dc2626", margin: 0 }}>{b.message}</p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0",
                fontFamily: "monospace" }}>{b.code}</p>
            </div>
            {b.route && (
              <Btn size="xs" variant="ghost" onClick={() => router.push(b.route!)}>
                Fix <ChevronRight size={11}/>
              </Btn>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

function PackageStatusCard({ pkg }: { pkg: PackageAssignmentSummary }) {
  const isPending = !pkg.starts_at;
  const isActive  = pkg.status === "active";
  const isRejected = pkg.status === "rejected";

  const borderColor = isRejected ? "rgba(220,38,38,0.3)"
    : isPending ? "rgba(245,158,11,0.3)"
    : "rgba(5,150,105,0.3)";
  const bg = isRejected ? "rgba(220,38,38,0.06)"
    : isPending ? "rgba(245,158,11,0.06)"
    : "rgba(5,150,105,0.06)";
  const iconColor = isRejected ? "#dc2626" : isPending ? "#d97706" : "#059669";
  const Icon = isRejected ? XCircle : isPending ? Clock : CheckCircle2;

  return (
    <div style={{ padding: "16px 20px", borderRadius: 14, background: bg,
      border: `1px solid ${borderColor}`, display: "flex", alignItems: "flex-start", gap: 14 }}>
      <Icon size={22} style={{ color: iconColor, flexShrink: 0, marginTop: 2 }}/>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
          <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            {pkg.package_name ?? "Package"}
          </p>
          <Badge variant={isRejected ? "danger" : isPending ? "warning" : "success"} size="sm">
            {(pkg.status ?? "unknown").replace(/_/g, " ")}
          </Badge>
        </div>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 8px", lineHeight: 1.5 }}>
          {pkg.message}
        </p>
        {isActive && pkg.starts_at && (
          <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              Active from: <strong style={{ color: "var(--text-primary)" }}>
                {new Date(pkg.starts_at).toLocaleDateString()}
              </strong>
            </span>
            {pkg.expires_at && (
              <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                Expires: <strong style={{ color: "var(--text-primary)" }}>
                  {new Date(pkg.expires_at).toLocaleDateString()}
                </strong>
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ChecklistTable({ items }: { items: ProviderOnboardingItem[] }) {
  const router = useRouter();
  return (
    <Card padding={0}>
      <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
          Checklist Items
        </p>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
              {["Item", "Status", "Type", "Required", "Blocking", "Source", "Completed", "Action"].map(h => (
                <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700,
                  color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em",
                  whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={item.id}
                style={{ borderBottom: i < items.length - 1 ? "1px solid var(--border)" : "none" }}>
                <td style={{ padding: "10px 14px", minWidth: 180 }}>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                    {item.title}
                  </p>
                  {item.description && (
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                      {item.description}
                    </p>
                  )}
                  {item.blocked_reason && (
                    <p style={{ fontSize: 11, color: "#dc2626", margin: "4px 0 0" }}>
                      {item.blocked_reason}
                    </p>
                  )}
                </td>
                <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {STATUS_ICON[item.status]}
                    <Badge variant={STATUS_VARIANT[item.status] ?? "muted"} size="sm">
                      {item.status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                </td>
                <td style={{ padding: "10px 14px" }}>
                  <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    {item.item_type.replace(/_/g, " ")}
                  </span>
                </td>
                <td style={{ padding: "10px 14px" }}>
                  <Badge variant={item.is_required ? "danger" : "muted"} size="sm">
                    {item.is_required ? "Required" : "Optional"}
                  </Badge>
                </td>
                <td style={{ padding: "10px 14px" }}>
                  <Badge variant={item.is_blocking ? "danger" : "muted"} size="sm">
                    {item.is_blocking ? "Blocking" : "Non-blocking"}
                  </Badge>
                </td>
                <td style={{ padding: "10px 14px" }}>
                  <span style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text-secondary)" }}>
                    {item.completion_source.replace(/_/g, " ")}
                  </span>
                </td>
                <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                  {item.completed_at ? (
                    <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                      {new Date(item.completed_at).toLocaleDateString()}
                    </span>
                  ) : (
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>
                  )}
                </td>
                <td style={{ padding: "10px 14px" }}>
                  {item.provider_action_route && item.status !== "completed" && (
                    <Btn size="xs" variant="primary"
                      onClick={() => router.push(item.provider_action_route!)}>
                      {item.provider_action_label ?? "Complete"}
                    </Btn>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export default function OnboardingStatusPage() {
  const status  = useApi(useCallback(() => providerOnboardingApi.getStatus(), []));
  const items   = useApi(useCallback(() => providerOnboardingApi.getItems(), []));
  const pkgSummary = useApi(useCallback(() => providerPackageApi.packageSummary(), []));
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const refreshAction = useAction(useCallback(async () => {
    await providerOnboardingApi.refresh();
    status.refetch();
    items.refetch();
    setToastMsg("Onboarding status refreshed.");
    setTimeout(() => setToastMsg(null), 3000);
  }, [status, items]));

  const s = status.data;
  const itemList = items.data?.items ?? [];
  const loading = status.loading || items.loading;
  const pkg = pkgSummary.data;

  return (
    <TenantLayout activeNav="onboarding-status">
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
          flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              Onboarding Checklist
            </h1>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
              Complete all required steps to start accepting bookings
            </p>
          </div>
          <Btn size="sm" variant="secondary" loading={refreshAction.loading}
            onClick={() => refreshAction.execute()}>
            <RefreshCw size={13}/> Refresh Status
          </Btn>
        </div>

        {/* Toast */}
        {(toastMsg || refreshAction.error) && (
          <div style={{ padding: "12px 16px", borderRadius: 10,
            background: refreshAction.error ? "rgba(220,38,38,0.08)" : "rgba(5,150,105,0.08)",
            border: `1px solid ${refreshAction.error ? "rgba(220,38,38,0.25)" : "rgba(5,150,105,0.25)"}`,
            fontSize: 13, fontWeight: 600,
            color: refreshAction.error ? "#dc2626" : "#059669" }}>
            {refreshAction.error ?? toastMsg}
          </div>
        )}

        {/* Package assignment status (P1 — starts after admin approval) */}
        {pkgSummary.loading && <Skeleton height={70}/>}
        {!pkgSummary.loading && pkg?.has_package && <PackageStatusCard pkg={pkg}/>}

        {/* Loading */}
        {loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Skeleton height={160}/>
            <Skeleton height={80}/>
            <Skeleton height={300}/>
          </div>
        )}

        {/* Error */}
        {!loading && status.error && (
          <Card>
            <div style={{ textAlign: "center", padding: "32px 0" }}>
              <AlertCircle size={32} style={{ color: "#dc2626", margin: "0 auto 12px", display: "block" }}/>
              <p style={{ fontSize: 14, color: "#dc2626", margin: "0 0 12px" }}>{status.error}</p>
              <Btn size="sm" variant="primary" onClick={status.refetch}>Retry</Btn>
            </div>
          </Card>
        )}

        {/* Success state */}
        {!loading && s?.onboarding_ready && (
          <div style={{ padding: "20px 24px", borderRadius: 14,
            background: "rgba(5,150,105,0.08)", border: "1px solid rgba(5,150,105,0.3)",
            display: "flex", alignItems: "center", gap: 14 }}>
            <CheckCircle2 size={28} style={{ color: "#059669", flexShrink: 0 }}/>
            <div>
              <p style={{ fontSize: 15, fontWeight: 700, color: "#059669", margin: 0 }}>
                Your onboarding is complete!
              </p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 0" }}>
                Your business is fully set up and ready to accept bookings.
              </p>
            </div>
          </div>
        )}

        {/* Main content */}
        {!loading && s && (
          <>
            <StatusSummary s={s}/>
            {s.next_action && <NextActionCard action={s.next_action}/>}
            {s.blockers.length > 0 && <BlockersList blockers={s.blockers}/>}
            {itemList.length > 0 && <ChecklistTable items={itemList}/>}
            {itemList.length === 0 && !items.loading && (
              <Card>
                <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)" }}>
                  <CheckCircle2 size={28} style={{ display: "block", margin: "0 auto 10px" }}/>
                  <p style={{ fontSize: 13, margin: 0 }}>No checklist items configured for your category yet.</p>
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </TenantLayout>
  );
}
