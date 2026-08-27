"use client";
import { useEffect, useState } from "react";
import { adminAnalyticsApi } from "@/lib/api";
import { PageHeader } from "@serviceos/design-system";
import {
  AnalyticsKpiCard,
  AnalyticsDateFilter,
  AnalyticsBreakdownTable,
  AnalyticsExportButton,
} from "@/components/analytics";

const today = () => new Date().toISOString().slice(0, 10);
const ago30  = () => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10); };

export default function FinancialAnalyticsPage() {
  const [df, setDf] = useState(ago30);
  const [dt, setDt] = useState(today);
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAnalyticsApi.getFinancialSummary({ date_from: df, date_to: dt });
      setData(r?.data ?? null);
    } catch { setData(null); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [df, dt]);

  const s  = data?.summary ?? {};
  const bd = data?.breakdown ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <PageHeader
        title="Financial Analytics"
        description="Platform-wide revenue, commissions, and wallet activity."
        eyebrow="Analytics"
        actions={
          <div style={{ display: "flex", alignItems: "center", gap: "var(--layout-control-gap)", flexWrap: "wrap" }}>
          <AnalyticsDateFilter dateFrom={df} dateTo={dt} onChange={(f, t) => { setDf(f); setDt(t); }} loading={loading} />
          <AnalyticsExportButton
            reportKey="admin_financial"
            filters={{ date_from: df, date_to: dt }}
            onRun={(body) => adminAnalyticsApi.runReport(body).then((r: any) => r?.data ?? {})}
          />
          </div>
        }
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        <AnalyticsKpiCard label="Gross Revenue"       value={s.gross_revenue}        unit="AED" loading={loading} />
        <AnalyticsKpiCard label="Platform Commission" value={s.platform_commission}  unit="AED" loading={loading} />
        <AnalyticsKpiCard label="Provider Payouts"    value={s.provider_payouts}     unit="AED" loading={loading} />
        <AnalyticsKpiCard label="Refunds Issued"      value={s.refunds_issued}       unit="AED" loading={loading} severity={Number(s.refunds_issued) > 5000 ? "warning" : "normal"} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 16 }}>
        <AnalyticsKpiCard label="Total Invoices"   value={s.total_invoices}    loading={loading} />
        <AnalyticsKpiCard label="Paid Invoices"    value={s.paid_invoices}     loading={loading} />
        <AnalyticsKpiCard label="Overdue Invoices" value={s.overdue_invoices}  loading={loading} severity={Number(s.overdue_invoices) > 0 ? "warning" : "normal"} />
      </div>

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>Revenue by Category</h2>
        <AnalyticsBreakdownTable
          rows={bd}
          loading={loading}
          emptyText="No financial data for this period"
          columns={[
            { key: "category_name",    label: "Category" },
            { key: "gross_revenue",    label: "Revenue (AED)",    numeric: true },
            { key: "commission",       label: "Commission (AED)", numeric: true },
            { key: "refunds",          label: "Refunds (AED)",    numeric: true },
            { key: "invoice_count",    label: "Invoices",         numeric: true },
          ]}
        />
      </div>
    </div>
  );
}
