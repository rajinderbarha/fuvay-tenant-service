'use client';
import { useCallback } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { tenantSetupApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { PageHeader, Card, Skeleton } from "@serviceos/design-system";

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
      <PageHeader
        title="Security Deposit"
        description="View your security deposit status and details. Security deposit is separate from usage credits."
      />

      {error && <div style={{ color: "var(--danger-text)", margin: "16px 0" }}>Error loading security deposit info.</div>}

      {loading ? (
        <Skeleton height="7.5rem" radius="12px" />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, margin: "16px 0 24px" }}>
          <Card>
            <h2 style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 15, margin: "0 0 14px" }}>Deposit Status</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <Row label="Status"          value={String(deposit?.status ?? "pending")} />
              <Row label="Required Amount" value={`${safeNum(deposit?.required_amount ?? 5000)}`} />
              <Row label="Currency"        value={String(deposit?.currency ?? "INR")} />
              <Row label="Amount Received" value={safeNum(deposit?.amount_received ?? deposit?.total_paid ?? deposit?.amount)} />
              {deposit?.received_at && (
                <Row label="Received At" value={new Date(deposit.received_at as string).toLocaleDateString()} />
              )}
            </div>
          </Card>

          <Card>
            <h2 style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 15, margin: "0 0 14px" }}>Important Notes</h2>
            <ul style={{ color: "var(--text-secondary)", fontSize: "0.875rem", listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 10, margin: 0 }}>
              <li>&#8226; Security deposit is separate from your usage credit balance.</li>
              <li>&#8226; Deposit status is managed by your administrator.</li>
              <li>&#8226; Contact support for questions about your security deposit.</li>
              <li>&#8226; For credit balance, see <Link href="/finance/package" style={{ color: "var(--brand)" }}>Package &amp; Credits</Link>.</li>
            </ul>
          </Card>
        </div>
      )}
    </TenantLayout>
  );
}
