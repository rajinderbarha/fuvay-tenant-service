"use client";
import { useState } from "react";
import {
  platformAnalyticsApi,
  PlatformSummary,
  PlatformTrends,
  OperationalAlert,
  CategoryPerformanceItem,
  ProviderPerformanceItem,
  FinanceSummary,
  QualitySummary,
  ComplaintsSummary,
  GeographySummary,
  CustomerSummary,
} from "@/lib/api";
import { useApi, useAction } from "@/hooks/useApi";
import { Btn } from "@/components/shared/ui";

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (n: number | null | undefined) => (n ?? 0).toLocaleString("en-IN");
const fmtMoney = (n: number | null | undefined) => "₹" + fmt(n);
const fmtPct = (n: number | null | undefined) => ((n ?? 0).toFixed(1)) + "%";
const fmtRating = (n: number | null | undefined) => (n ?? 0).toFixed(1);

const cardStyle: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: "16px 20px",
};

const today = () => new Date().toISOString().slice(0, 10);
const daysAgo = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
};

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({
  label, value, helpText, href, loading,
}: {
  label: string;
  value: string | number;
  helpText?: string;
  href?: string;
  loading: boolean;
}) {
  const inner = (
    <div style={{
      ...cardStyle,
      cursor: href ? "pointer" : "default",
      transition: "box-shadow 0.15s",
    }}>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {label}
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 32, width: 80, borderRadius: 6 }} />
      ) : (
        <div style={{ fontSize: 26, fontWeight: 700, color: "var(--text-primary)", fontVariantNumeric: "tabular-nums" }}>
          {value}
        </div>
      )}
      {helpText && !loading && (
        <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>{helpText}</div>
      )}
    </div>
  );
  if (href) return <a href={href} style={{ textDecoration: "none" }}>{inner}</a>;
  return inner;
}

function TrendChart({
  title, data, color, loading,
}: {
  title: string;
  data: Array<{ date: string; value: number }>;
  color: string;
  loading: boolean;
}) {
  if (loading) return <div className="skeleton" style={{ height: 180, borderRadius: 10 }} />;
  if (!data?.length) {
    return (
      <div style={{ ...cardStyle, height: 200, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 8 }}>
        <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 600 }}>{title}</div>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No trend data for this period</div>
      </div>
    );
  }
  const w = 400, h = 120, pad = 20;
  const max = Math.max(...data.map(d => d.value), 1);
  const pts = data.map((d, i) => {
    const x = pad + (i / (data.length - 1 || 1)) * (w - 2 * pad);
    const y = h - pad - (d.value / max) * (h - 2 * pad);
    return `${x},${y}`;
  }).join(" ");
  return (
    <div style={{ ...cardStyle }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>{title}</div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: 120 }}>
        <polyline fill="none" stroke={color} strokeWidth="2" points={pts} />
        {data.map((d, i) => {
          const x = pad + (i / (data.length - 1 || 1)) * (w - 2 * pad);
          const y = h - pad - (d.value / max) * (h - 2 * pad);
          return <circle key={i} cx={x} cy={y} r="3" fill={color} />;
        })}
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-tertiary)", marginTop: 4 }}>
        <span>{data[0]?.date}</span><span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, { bg: string; text: string; border: string }> = {
    critical: { bg: "var(--danger-bg)", text: "var(--danger-text)", border: "var(--danger-border)" },
    high: { bg: "var(--warning-bg)", text: "var(--warning-text)", border: "var(--warning-border)" },
    medium: { bg: "var(--accent-muted)", text: "var(--accent)", border: "var(--accent)" },
    low: { bg: "var(--surface-sunken)", text: "var(--text-tertiary)", border: "var(--border)" },
  };
  const s = map[severity] ?? map.low;
  return (
    <span style={{
      background: s.bg, color: s.text, border: `1px solid ${s.border}`,
      borderRadius: 4, fontSize: 10, fontWeight: 600, padding: "2px 6px", textTransform: "uppercase",
    }}>
      {severity}
    </span>
  );
}

function HealthBand({ band }: { band: string }) {
  const map: Record<string, string> = {
    healthy: "var(--success-text)",
    warning: "var(--warning-text)",
    at_risk: "var(--danger-text)",
  };
  return <span style={{ color: map[band] ?? "var(--text-secondary)", fontWeight: 600, fontSize: 12 }}>{band.replace("_", " ")}</span>;
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function PlatformAnalyticsDashboard() {
  const [dateFrom, setDateFrom] = useState(daysAgo(30));
  const [dateTo, setDateTo] = useState(today());
  const [vertical, setVertical] = useState("");
  const [providerTab, setProviderTab] = useState<"jobs" | "rating" | "risk">("jobs");

  // All useApi calls use stable primitives as deps
  const { data: summary, loading: sumLoading } = useApi(
    () => platformAnalyticsApi.getSummary({ date_from: dateFrom, date_to: dateTo, vertical: vertical || undefined }),
    [dateFrom, dateTo, vertical],
  );
  const { data: trends, loading: trendsLoading } = useApi(
    () => platformAnalyticsApi.getTrends({ date_from: dateFrom, date_to: dateTo, vertical: vertical || undefined }),
    [dateFrom, dateTo, vertical],
  );
  const { data: alertsData, loading: alertsLoading, refetch: refetchAlerts } = useApi(
    () => platformAnalyticsApi.getAlerts(),
    [],
  );
  const { data: catPerf, loading: catLoading } = useApi(
    () => platformAnalyticsApi.getCategoryPerformance({ date_from: dateFrom, date_to: dateTo, vertical: vertical || undefined }),
    [dateFrom, dateTo, vertical],
  );
  const { data: provPerf, loading: provLoading } = useApi(
    () => platformAnalyticsApi.getProviderPerformance({ date_from: dateFrom, date_to: dateTo, vertical: vertical || undefined, sort_by: providerTab === "rating" ? "avg_rating" : "completed_jobs", health_band: providerTab === "risk" ? "at_risk" : undefined }),
    [dateFrom, dateTo, vertical, providerTab],
  );
  const { data: finance, loading: finLoading } = useApi(
    () => platformAnalyticsApi.getFinanceSummary({ date_from: dateFrom, date_to: dateTo, vertical: vertical || undefined }),
    [dateFrom, dateTo, vertical],
  );
  const { data: quality, loading: qualLoading } = useApi(
    () => platformAnalyticsApi.getQualitySummary({ date_from: dateFrom, date_to: dateTo, vertical: vertical || undefined }),
    [dateFrom, dateTo, vertical],
  );
  const { data: complaints, loading: compLoading } = useApi(
    () => platformAnalyticsApi.getComplaintsSummary({ date_from: dateFrom, date_to: dateTo, vertical: vertical || undefined }),
    [dateFrom, dateTo, vertical],
  );
  const { data: geo, loading: geoLoading } = useApi(
    () => platformAnalyticsApi.getGeographySummary({ date_from: dateFrom, date_to: dateTo, vertical: vertical || undefined }),
    [dateFrom, dateTo, vertical],
  );
  const { data: customers, loading: custLoading } = useApi(
    () => platformAnalyticsApi.getCustomerSummary({ date_from: dateFrom, date_to: dateTo }),
    [dateFrom, dateTo],
  );

  const { execute: doResolve } = useAction((id: string) => platformAnalyticsApi.resolveAlert(id));
  const { execute: doIgnore } = useAction((id: string) => platformAnalyticsApi.ignoreAlert(id));

  const s = summary ?? ({} as Partial<PlatformSummary>);
  const t = trends ?? ({} as Partial<PlatformTrends>);
  const alerts: OperationalAlert[] = alertsData?.items ?? [];
  const catItems: CategoryPerformanceItem[] = catPerf?.items ?? [];
  const provItems: ProviderPerformanceItem[] = provPerf?.items ?? [];
  const fin = finance ?? ({} as Partial<FinanceSummary>);
  const qual = quality ?? ({} as Partial<QualitySummary>);
  const comp = complaints ?? ({} as Partial<ComplaintsSummary>);
  const topCities = geo?.top_cities ?? [];
  const cust = customers ?? ({} as Partial<CustomerSummary>);

  function setQuickRange(days: number) {
    setDateTo(today());
    setDateFrom(daysAgo(days));
  }

  function setThisMonth() {
    const now = new Date();
    setDateFrom(new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10));
    setDateTo(today());
  }

  function setLastMonth() {
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const last = new Date(now.getFullYear(), now.getMonth(), 0);
    setDateFrom(first.toISOString().slice(0, 10));
    setDateTo(last.toISOString().slice(0, 10));
  }

  function setYTD() {
    setDateFrom(new Date(new Date().getFullYear(), 0, 1).toISOString().slice(0, 10));
    setDateTo(today());
  }

  const verticals = ["home_services", "coaching", "real_estate", "healthcare", "automotive", "beauty", "events", "logistics", "legal", "finance"];

  const quickBtn = (label: string, fn: () => void) => (
    <button onClick={fn} style={{
      padding: "4px 10px", fontSize: 12, borderRadius: 6, border: "1px solid var(--border)",
      background: "var(--surface)", color: "var(--text-secondary)", cursor: "pointer",
    }}>
      {label}
    </button>
  );

  const thStyle: React.CSSProperties = { textAlign: "left", padding: "8px 10px", fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" };
  const tdStyle: React.CSSProperties = { padding: "8px 10px", fontSize: 13, color: "var(--text-primary)", borderBottom: "1px solid var(--border)" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28, paddingBottom: 48 }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Analytics / Platform Overview</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Platform Analytics</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Enterprise intelligence across all tenants, verticals, and operations</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn size="sm" variant="secondary" onClick={() => platformAnalyticsApi.exportReport("platform_summary", { date_from: dateFrom, date_to: dateTo })}>Export Report</Btn>
          <Btn size="sm" variant="primary" onClick={() => window.location.reload()}>Refresh</Btn>
        </div>
      </div>

      {/* Date & Filter Bar */}
      <div style={{ ...cardStyle, padding: "14px 20px" }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {quickBtn("7d", () => setQuickRange(7))}
            {quickBtn("30d", () => setQuickRange(30))}
            {quickBtn("90d", () => setQuickRange(90))}
            {quickBtn("This Month", setThisMonth)}
            {quickBtn("Last Month", setLastMonth)}
            {quickBtn("YTD", setYTD)}
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
              style={{ padding: "4px 8px", fontSize: 13, border: "1px solid var(--border)", borderRadius: 6, background: "var(--surface)", color: "var(--text-primary)" }} />
            <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>to</span>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
              style={{ padding: "4px 8px", fontSize: 13, border: "1px solid var(--border)", borderRadius: 6, background: "var(--surface)", color: "var(--text-primary)" }} />
          </div>
          <select value={vertical} onChange={e => setVertical(e.target.value)}
            style={{ padding: "4px 8px", fontSize: 13, border: "1px solid var(--border)", borderRadius: 6, background: "var(--surface)", color: "var(--text-primary)" }}>
            <option value="">All Verticals</option>
            {verticals.map(v => <option key={v} value={v}>{v.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</option>)}
          </select>
        </div>
      </div>

      {/* KPI Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
        <KpiCard label="Active Tenants" value={fmt(s.active_tenants)} href="/admin/tenants?status=active" loading={sumLoading} />
        <KpiCard label="Total Jobs" value={fmt(s.total_jobs)} href="/admin/home-services/service-jobs" loading={sumLoading} />
        <KpiCard label="Platform Revenue" value={fmtMoney(s.platform_revenue)} helpText="Top-ups + packages" loading={sumLoading} />
        <KpiCard label="Completed Job Deductions" value={fmtMoney(s.completed_job_deductions)} href="/admin/home-services/completed-job-deduction" loading={sumLoading} />
        <KpiCard label="Provider Direct Service Value" value={fmtMoney(s.provider_direct_service_value)} helpText="Paid directly to provider" loading={sumLoading} />
        <KpiCard label="Avg Job Rating" value={fmtRating(s.avg_job_rating)} loading={sumLoading} />
        <KpiCard label="Complaint Rate" value={fmtPct(s.complaint_rate)} href="/admin/complaints" loading={sumLoading} />
        <KpiCard label="Pending Approvals" value={fmt(s.pending_approvals)} href="/admin/tenants?status=pending_review" loading={sumLoading} />
        <KpiCard label="New Providers" value={fmt(s.new_providers)} loading={sumLoading} />
        <KpiCard label="Customer Service Credits Issued" value={fmtMoney(s.customer_service_credits_issued)} href="/admin/finance/customer-credits" loading={sumLoading} />
        <KpiCard label="Security Deposit Held" value={fmtMoney(s.security_deposit_held)} loading={sumLoading} />
        <KpiCard label="Active Customers" value={fmt(s.active_customers)} loading={sumLoading} />
      </div>

      {/* Trend Charts */}
      <div>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 14px" }}>Platform Trends</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          <TrendChart title="Jobs / Bookings Trend" data={t.jobs_trend ?? []} color="var(--accent)" loading={trendsLoading} />
          <TrendChart title="Platform Revenue Trend" data={t.revenue_trend ?? []} color="var(--success-text)" loading={trendsLoading} />
          <TrendChart title="Tenant Growth" data={t.tenant_growth ?? []} color="var(--warning-text)" loading={trendsLoading} />
        </div>
      </div>

      {/* Operational Alerts */}
      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
            Operational Alerts {alerts.length > 0 && <span style={{ fontSize: 12, color: "var(--danger-text)", marginLeft: 8 }}>({alerts.length})</span>}
          </h2>
          <Btn size="sm" variant="secondary" onClick={refetchAlerts}>Refresh</Btn>
        </div>
        {alertsLoading ? (
          <div className="skeleton" style={{ height: 80, borderRadius: 8 }} />
        ) : alerts.length === 0 ? (
          <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
            No active operational alerts. All monitored systems are healthy.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={thStyle}>Alert</th>
                  <th style={thStyle}>Severity</th>
                  <th style={thStyle}>Entity</th>
                  <th style={thStyle}>Count</th>
                  <th style={thStyle}>Detected</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map(a => (
                  <tr key={a.id}>
                    <td style={tdStyle}>{a.message}</td>
                    <td style={tdStyle}><SeverityBadge severity={a.severity} /></td>
                    <td style={tdStyle}>{a.entity_name ?? a.entity_type}</td>
                    <td style={{ ...tdStyle, fontVariantNumeric: "tabular-nums" }}>{a.count}</td>
                    <td style={{ ...tdStyle, fontSize: 11, color: "var(--text-tertiary)" }}>{a.detected_at?.slice(0, 10)}</td>
                    <td style={tdStyle}>
                      <div style={{ display: "flex", gap: 6 }}>
                        <Btn size="sm" variant="secondary" onClick={async () => { await doResolve(a.id); refetchAlerts(); }}>Resolve</Btn>
                        <Btn size="sm" variant="ghost" onClick={async () => { await doIgnore(a.id); refetchAlerts(); }}>Ignore</Btn>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Category Performance */}
      <div style={cardStyle}>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 14px" }}>Category Performance</h2>
        {catLoading ? <div className="skeleton" style={{ height: 120, borderRadius: 8 }} /> : catItems.length === 0 ? (
          <div style={{ textAlign: "center", padding: "28px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
            No category data for this period. Adjust your date range or vertical filter.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={thStyle}>Vertical / Category</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Tenants</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Bookings</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Completion %</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Platform Revenue</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Avg Rating</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Complaint Rate</th>
                </tr>
              </thead>
              <tbody>
                {catItems.map(c => (
                  <tr key={c.vertical_key}>
                    <td style={tdStyle}>{c.category_name}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(c.tenant_count)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(c.booking_count)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtPct(c.completion_rate)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtMoney(c.platform_revenue)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtRating(c.avg_rating)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtPct(c.complaint_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Provider Performance */}
      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>Provider Performance</h2>
          <div style={{ display: "flex", gap: 4 }}>
            {(["jobs", "rating", "risk"] as const).map(tab => (
              <button key={tab} onClick={() => setProviderTab(tab)} style={{
                padding: "4px 12px", fontSize: 12, borderRadius: 6,
                background: providerTab === tab ? "var(--brand)" : "var(--surface)",
                color: providerTab === tab ? "var(--text-on-brand)" : "var(--text-secondary)",
                border: "1px solid var(--border)", cursor: "pointer", fontWeight: 500,
              }}>
                {tab === "jobs" ? "By Jobs" : tab === "rating" ? "By Rating" : "At Risk"}
              </button>
            ))}
          </div>
        </div>
        {provLoading ? <div className="skeleton" style={{ height: 140, borderRadius: 8 }} /> : provItems.length === 0 ? (
          <div style={{ textAlign: "center", padding: "28px 0", color: "var(--text-tertiary)", fontSize: 13 }}>No provider data for this period.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={thStyle}>Provider</th>
                  <th style={thStyle}>Vertical</th>
                  <th style={thStyle}>City</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Jobs</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Direct Service Value</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Platform Deductions</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Rating</th>
                  <th style={thStyle}>Health</th>
                </tr>
              </thead>
              <tbody>
                {provItems.map(p => (
                  <tr key={p.tenant_id}>
                    <td style={tdStyle}>
                      <a href={`/admin/tenants/${p.tenant_id}`} style={{ color: "var(--accent)", textDecoration: "none" }}>{p.tenant_name}</a>
                    </td>
                    <td style={{ ...tdStyle, fontSize: 12, color: "var(--text-secondary)" }}>{p.vertical}</td>
                    <td style={{ ...tdStyle, fontSize: 12, color: "var(--text-secondary)" }}>{p.city ?? "—"}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(p.completed_jobs)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtMoney(p.direct_service_value)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtMoney(p.platform_deductions)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtRating(p.avg_rating)}</td>
                    <td style={tdStyle}><HealthBand band={p.health_band} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Finance Summary */}
      <div>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 14px" }}>Finance Summary</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
          <KpiCard label="Platform Revenue" value={fmtMoney(fin.platform_revenue)} helpText="Top-ups + packages" loading={finLoading} />
          <KpiCard label="Package Revenue" value={fmtMoney(fin.package_revenue)} loading={finLoading} />
          <KpiCard label="Usage Credit Top-ups" value={fmtMoney(fin.usage_credit_topups)} loading={finLoading} />
          <KpiCard label="Completed Job Deductions" value={fmtMoney(fin.completed_job_deductions)} loading={finLoading} />
          <KpiCard label="Customer Service Credits Issued" value={fmtMoney(fin.customer_service_credits_issued)} loading={finLoading} />
          <KpiCard label="Security Deposits Held" value={fmtMoney(fin.security_deposits_held)} loading={finLoading} />
        </div>
      </div>

      {/* Quality & Complaints */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div style={cardStyle}>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 14px" }}>Quality Summary</h2>
          {qualLoading ? <div className="skeleton" style={{ height: 80, borderRadius: 8 }} /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                ["Avg Rating", fmtRating(qual.avg_rating) + " / 5"],
                ["Total Reviews", fmt(qual.review_count)],
                ["Complaint Rate", fmtPct(qual.complaint_rate)],
                ["Dispute Rate", fmtPct(qual.dispute_rate)],
              ].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{k}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div style={cardStyle}>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 14px" }}>Complaints Summary</h2>
          {compLoading ? <div className="skeleton" style={{ height: 80, borderRadius: 8 }} /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                ["Total Complaints", fmt(comp.total_complaints)],
                ["Open", fmt(comp.open_complaints)],
                ["Resolved", fmt(comp.resolved_complaints)],
                ["Avg Resolution Time", (comp.avg_resolution_hours ?? 0).toFixed(1) + " hrs"],
                ["Credits Issued", fmtMoney(comp.customer_service_credits_issued)],
                ["Tenant Responsible", fmt(comp.tenant_responsible_count)],
              ].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{k}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Geography */}
      <div style={cardStyle}>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 14px" }}>Top Cities by Booking Volume</h2>
        {geoLoading ? <div className="skeleton" style={{ height: 100, borderRadius: 8 }} /> : topCities.length === 0 ? (
          <div style={{ textAlign: "center", padding: "24px 0", color: "var(--text-tertiary)", fontSize: 13 }}>No geographic data available.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={thStyle}>City</th>
                  <th style={thStyle}>State</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Bookings</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Tenants</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Avg Rating</th>
                </tr>
              </thead>
              <tbody>
                {topCities.map((c, i) => (
                  <tr key={i}>
                    <td style={tdStyle}>{c.city}</td>
                    <td style={{ ...tdStyle, color: "var(--text-secondary)", fontSize: 12 }}>{c.state ?? "—"}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(c.booking_count)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(c.tenant_count)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtRating(c.avg_rating)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Customer Analytics */}
      <div>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 14px" }}>Customer Analytics</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
          <KpiCard label="Active Customers" value={fmt(cust.active_customers)} loading={custLoading} />
          <KpiCard label="New Customers" value={fmt(cust.new_customers)} loading={custLoading} />
          <KpiCard label="Bookings / Customer" value={(cust.bookings_per_customer ?? 0).toFixed(1)} loading={custLoading} />
          <KpiCard label="Customer Credits Used" value={fmtMoney(cust.customer_service_credits_used)} loading={custLoading} />
        </div>
      </div>

    </div>
  );
}
