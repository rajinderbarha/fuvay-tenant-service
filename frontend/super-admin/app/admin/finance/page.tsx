"use client";
import { useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  RefreshCw, Download, Wallet, Shield, ArrowUpRight, AlertTriangle, Activity, ListChecks,
} from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Badge, Btn } from "../../../components/shared/ui";
import { Card, PageHeader, PageShell, SummaryCardsRow } from "@serviceos/design-system";
import { financeApi } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";

const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`;

const HEALTH_BAND_LABELS: Record<string, string> = {
  platinum: "Platinum", gold: "Healthy", silver: "Watchlist",
  bronze: "Low Balance", at_risk: "At Risk", critical: "Critical",
};
const HEALTH_BAND_VARIANT: Record<string, "success" | "info" | "warning" | "danger" | "muted"> = {
  platinum: "success", gold: "success", silver: "info",
  bronze: "warning", at_risk: "warning", critical: "danger",
};

const ACTIVITY_LABELS: Record<string, string> = {
  wallet_transaction: "Wallet",
  warranty_claim: "Warranty Claim",
  payout: "Payout",
};

function InsightCard({ title, icon, children, emptyText, isEmpty }: {
  title: string; icon: React.ReactNode; children: React.ReactNode;
  emptyText: string; isEmpty: boolean;
}) {
  return (
    <Card padding="md">
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
        {icon}
        <span style={{ fontWeight: 700, fontSize: 14 }}>{title}</span>
      </div>
      {isEmpty ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0, padding: "12px 0" }}>{emptyText}</p>
      ) : children}
    </Card>
  );
}

export default function FinanceHubPage() {
  const router = useRouter();
  const summary = useApi(useCallback(() => financeApi.getSummary(), []));
  const overview = useApi(useCallback(() => financeApi.getOverview(), []));

  function refetchAll() { summary.refetch(); overview.refetch(); }

  const s = summary.data;
  const o = overview.data;

  return (
    <AdminLayout activeNav="finance">
      <PageShell>
      <PageHeader
        title="Finance Hub"
        description="Monitor wallets, top-ups, claims, payouts, and platform earnings."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={refetchAll}>Refresh</Btn>
            <Btn variant="secondary" size="sm" icon={<Download size={13}/>} onClick={() => window.print()}>Export Snapshot</Btn>
          </div>
        }
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {summary.error && <Card padding="md"><p style={{ color: "var(--danger-text)" }}>Could not load finance data. {summary.error}</p></Card>}

        {s && (
          <>
            <SummaryCardsRow cards={[
              { label: "Active Wallets", value: s.active_wallets },
              { label: "Low Balance Wallets", value: s.low_balance_wallets, accent: s.low_balance_wallets > 0 },
              { label: "Credits Issued", value: fmt(s.credits_issued) },
              { label: "Commission Earned", value: fmt(s.commission_earned) },
            ]}/>
            <SummaryCardsRow cards={[
              { label: "Pending Warranty Claims", value: s.pending_warranty_claims, onClick: () => router.push("/admin/finance/claims") },
              { label: "Pending Payouts", value: s.pending_payouts, onClick: () => router.push("/admin/finance/payouts") },
              { label: "At-Risk Tenants", value: s.at_risk_tenants, accent: s.at_risk_tenants > 0 },
            ]}/>
          </>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <InsightCard title="Wallet Health Distribution" icon={<Wallet size={16} color="var(--brand)"/>}
            isEmpty={!o || Object.keys(o.wallet_health_distribution).length === 0}
            emptyText="No active tenant wallets yet.">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {o && Object.entries(o.wallet_health_distribution).map(([band, count]) => (
                <div key={band} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Badge variant={HEALTH_BAND_VARIANT[band] ?? "muted"}>{HEALTH_BAND_LABELS[band] ?? band}</Badge>
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{count}</span>
                </div>
              ))}
            </div>
          </InsightCard>

          <InsightCard title="Top Low-Balance Tenants" icon={<AlertTriangle size={16} color="var(--warning-text)"/>}
            isEmpty={!o || o.top_low_balance_tenants.length === 0}
            emptyText="No low-balance tenants right now.">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {o?.top_low_balance_tenants.map(t => (
                <div key={t.tenant_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13,
                  cursor: "pointer" }} onClick={() => router.push(`/admin/tenants/${t.tenant_id}`)}>
                  <span>{t.tenant_name}</span>
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Badge variant={HEALTH_BAND_VARIANT[t.health_band] ?? "muted"} size="sm">{HEALTH_BAND_LABELS[t.health_band] ?? t.health_band}</Badge>
                    <strong>{fmt(t.wallet_balance)}</strong>
                  </span>
                </div>
              ))}
            </div>
          </InsightCard>

          <InsightCard title="Top Commission Contributors" icon={<ArrowUpRight size={16} color="var(--brand)"/>}
            isEmpty={!o || o.top_commission_contributors.length === 0}
            emptyText="No commission collected yet.">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {o?.top_commission_contributors.map(t => (
                <div key={t.tenant_id} style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <span>{t.tenant_name}</span>
                  <strong>{fmt(t.commission_total)}</strong>
                </div>
              ))}
            </div>
          </InsightCard>
        </div>

        <InsightCard title="Recent Finance Activity" icon={<Activity size={16} color="var(--brand)"/>}
          isEmpty={!o || o.recent_finance_activity.length === 0}
          emptyText="No finance activity recorded yet.">
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {o?.recent_finance_activity.map((a, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "6px 0",
                borderBottom: i < o.recent_finance_activity.length - 1 ? "1px solid var(--border)" : undefined }}>
                <span><Badge variant="muted" size="sm">{ACTIVITY_LABELS[a.type] ?? a.type}</Badge> <span style={{ marginLeft: 8 }}>{a.label}</span></span>
                <span style={{ color: "var(--text-tertiary)" }}>{new Date(a.created_at).toLocaleString("en-IN")}</span>
              </div>
            ))}
          </div>
        </InsightCard>

        <InsightCard title="Finance Action Queue" icon={<ListChecks size={16} color="var(--brand)"/>}
          isEmpty={!o}
          emptyText="Loading pending actions…">
          {o && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
              {[
                { label: "Payout Pending Approval", value: o.pending_actions_queue.payout_pending_approval, href: "/admin/finance/payouts?status=pending" },
                { label: "Warranty Claim Pending Review", value: o.pending_actions_queue.warranty_claim_pending_review, href: "/admin/finance/claims?status=pending" },
                { label: "Failed Top-up Payments", value: o.pending_actions_queue.failed_topup_payment, href: "/admin/finance/topups?payment_status=failed" },
              ].map(q => (
                <div key={q.label} onClick={() => router.push(q.href)} style={{
                  padding: "12px 14px", borderRadius: 10, background: "var(--surface-sunken)",
                  border: "1px solid var(--border)", cursor: "pointer",
                }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: q.value > 0 ? "var(--warning-text)" : "var(--text-primary)" }}>{q.value}</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>{q.label}</div>
                </div>
              ))}
            </div>
          )}
        </InsightCard>
      </div>
      </PageShell>
    </AdminLayout>
  );
}
