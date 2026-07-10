'use client';
import { useCallback } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { tenantSetupApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

const safeNum = (v: unknown): number => (typeof v === "number" && isFinite(v)) ? v : 0;

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between" }}>
      <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>{label}</span>
      <span style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.875rem" }}>{String(value)}</span>
    </div>
  );
}

export default function SecurityDepositPage() {
  const { data, loading, error } = useApi(useCallback(() => tenantSetupApi.getWallet(), []));

  const w = data as Record<string, unknown> | null;
  const deposit = (w?.security_deposit ?? w?.deposit ?? null) as Record<string, unknown> | null;

  return (
    <TenantLayout activeNav="finance-deposit">
      <div style={{ padding: "var(--space-6)" }}>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.75rem", margin: "0 0 4px" }}>Finance &rsaquo; Security Deposit</p>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Security Deposit</h1>
        <p style={{ color: "var(--text-secondary)", margin: "0 0 24px" }}>
          View your security deposit status and details. Security deposit is separate from usage credits.
        </p>

        {error && <div style={{ color: "var(--danger-text)", marginBottom: 16 }}>Error loading security deposit info.</div>}

        {loading ? (
          <div style={{ height: 120, background: "var(--surface-sunken)", borderRadius: 12, marginBottom: 16 }} />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "18px 20px" }}>
              <h2 style={{ fontWeight: 600, marginBottom: 14, color: "var(--text-primary)", fontSize: 15, margin: "0 0 14px" }}>Deposit Status</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <Row label="Status"          value={String(deposit?.status ?? "pending")} />
                <Row label="Required Amount" value={`${safeNum(deposit?.required_amount ?? 5000)}`} />
                <Row label="Currency"        value={String(deposit?.currency ?? "INR")} />
                <Row label="Amount Received" value={safeNum(deposit?.amount_received ?? deposit?.total_paid ?? deposit?.amount)} />
                {deposit?.received_at && (
                  <Row label="Received At" value={new Date(deposit.received_at as string).toLocaleDateString()} />
                )}
              </div>
            </div>

            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "18px 20px" }}>
              <h2 style={{ fontWeight: 600, marginBottom: 14, color: "var(--text-primary)", fontSize: 15, margin: "0 0 14px" }}>Important Notes</h2>
              <ul style={{ color: "var(--text-secondary)", fontSize: "0.875rem", listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 10, margin: 0 }}>
                <li>&#8226; Security deposit is separate from your usage credit balance.</li>
                <li>&#8226; Deposit status is managed by your administrator.</li>
                <li>&#8226; Contact support for questions about your security deposit.</li>
                <li>&#8226; For credit balance, see <a href="/finance/package" style={{ color: "var(--brand)" }}>Package &amp; Credits</a>.</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </TenantLayout>
  );
}
