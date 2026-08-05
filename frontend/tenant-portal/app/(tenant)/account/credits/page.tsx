"use client";
import { useCallback, useState } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, Badge, Btn, SectionHeader } from "../../../../components/shared/ui";
import { customerCreditsApi, MyServiceCredit, MyCreditSummary } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  active: "success", partially_used: "info", used: "muted",
  expired: "warning", cancelled: "danger", reversed: "danger",
};
const fmt = (n: number) => `₹${Number(n).toLocaleString("en-IN")}`;

export default function MyCreditsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const summary = useApi(useCallback(() => customerCreditsApi.getMySummary(), []));
  const list = useApi(useCallback(() =>
    customerCreditsApi.listMyCredits({ page, limit: 20, status: statusFilter || undefined }),
    [page, statusFilter]));

  const s: MyCreditSummary | undefined = summary.data;

  return (
    <TenantLayout activeNav="account">
      <SectionHeader
        title="My Service Credits"
        subtitle="ServiceOS platform credits you can apply on your next booking."
      />

      {s && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 20 }}>
          {[
            { label: "Active Balance", value: fmt(s.active_credit_balance), highlight: true },
            { label: "Active Credits", value: s.active_credits },
            { label: "Used", value: s.used_credits },
            { label: "Expired", value: s.expired_credits },
          ].map(c => (
            <Card key={c.label} padding={14}>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>{c.label}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: c.highlight ? "var(--color-primary, #1a6fd8)" : "inherit" }}>{c.value}</div>
            </Card>
          ))}
        </div>
      )}

      <Card padding={0}>
        <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)", display: "flex", gap: 8, alignItems: "center" }}>
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-input, var(--bg))", fontSize: 13 }}
          >
            <option value="">All credits</option>
            <option value="active">Active</option>
            <option value="partially_used">Partially Used</option>
            <option value="used">Used</option>
            <option value="expired">Expired</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        {list.loading && (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>Loading…</div>
        )}
        {!list.loading && !list.data?.credits?.length && (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>
            <p style={{ margin: 0, fontWeight: 600 }}>No service credits yet</p>
            <p style={{ margin: "8px 0 0", fontSize: 13 }}>Credits are issued after dispute settlements are resolved in your favour.</p>
          </div>
        )}
        {list.data?.credits?.map((c: MyServiceCredit) => (
          <div key={c.id} style={{ padding: "14px 16px", borderBottom: "1px solid var(--border-subtle, var(--border))", display: "flex", alignItems: "flex-start", gap: 14 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text-secondary)" }}>{c.credit_number}</span>
                <Badge variant={STATUS_VARIANT[c.status] ?? "muted"}>{c.status.replace(/_/g, " ")}</Badge>
                <Badge variant="muted">{c.credit_type.replace(/_/g, " ")}</Badge>
              </div>
              {c.customer_message && (
                <p style={{ margin: "0 0 6px", fontSize: 13, color: "var(--text-secondary)" }}>{c.customer_message}</p>
              )}
              {c.expires_at && (
                <p style={{ margin: 0, fontSize: 12, color: "var(--text-tertiary)" }}>
                  Expires: {new Date(c.expires_at).toLocaleDateString("en-IN")}
                </p>
              )}
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{fmt(c.remaining_amount)}</div>
              {c.amount !== c.remaining_amount && (
                <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>of {fmt(c.amount)}</div>
              )}
            </div>
          </div>
        ))}

        {(list.data?.meta?.total_pages ?? 1) > 1 && (
          <div style={{ padding: "12px 14px", display: "flex", gap: 8 }}>
            <Btn size="sm" variant="ghost" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</Btn>
            <span style={{ fontSize: 13, padding: "6px 0" }}>Page {page} / {list.data?.meta?.total_pages}</span>
            <Btn size="sm" variant="ghost" disabled={page >= (list.data?.meta?.total_pages ?? 1)} onClick={() => setPage(p => p + 1)}>Next</Btn>
          </div>
        )}
      </Card>

      <Card padding={16} style={{ marginTop: 16, background: "var(--bg-info, var(--bg-subtle, #f0f7ff))" }}>
        <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
          <strong>About ServiceOS Credits:</strong> These are platform credits, not cash. They can be applied to reduce
          the amount you pay on your next booking. Credits are issued as part of dispute settlement — they are not cash refunds.
        </p>
      </Card>
    </TenantLayout>
  );
}
