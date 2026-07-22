'use client';
import { useCallback } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { tenantSetupApi, usageCreditsApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { PageHeader, Card, Skeleton } from "@serviceos/design-system";

const safeNum = (v: unknown): number => (typeof v === "number" && isFinite(v)) ? v : 0;

function Row({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>{label}</span>
      <span style={{ fontWeight: 600, color: highlight ? "var(--success)" : "var(--text-primary)", fontSize: "0.875rem" }}>
        {String(value)}
      </span>
    </div>
  );
}

export default function PackagePage() {
  const { data: pkg, loading, error } = useApi(useCallback(() => tenantSetupApi.getPackage(), []));
  // E2E-11 fix: this card previously read tenantSetupApi.getWallet()
  // (/v1/provider/wallet), the same stale Sprint 23 wallet concept HS9B
  // already found and rewired away from on the ledger page — it showed
  // a hardcoded-looking 0 while the real Usage Credit Ledger page (same
  // tenant, same moment) correctly showed 3937. Rewired to the real,
  // live HS9/HS9B balance endpoint so this page's balance always
  // matches the ledger page's.
  const { data: balance, loading: balLoading } = useApi(useCallback(() => usageCreditsApi.getBalance(), []));

  const p = pkg as Record<string, unknown>;

  return (
    <TenantLayout activeNav="finance-package">
      <PageHeader
        title="Package & Credits"
        description="Your current package details and usage credit balance."
      />

      {error && <div style={{ color: "var(--danger-text)", margin: "16px 0" }}>Error loading package info.</div>}

      {loading ? (
        <Skeleton height="7.5rem" radius="12px" />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, margin: "16px 0 24px" }}>
          <Card>
            <h2 style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 15, margin: "0 0 14px" }}>Package Details</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <Row label="Package Name"             value={String(p?.package_name ?? p?.plan_type ?? "—")} />
              <Row label="Package Code"             value={String(p?.package_code ?? p?.code ?? "—")} />
              <Row label="Status"                   value={String(p?.status ?? "—")} highlight={p?.status === "active"} />
              <Row label="Staff Limit"              value={safeNum(p?.staff_limit ?? 5)} />
              <Row label="Service Area Limit"       value={safeNum(p?.service_area_limit ?? 5)} />
              <Row label="Included Usage Credits"   value={safeNum(p?.included_credits ?? p?.jobs_included)} />
              <Row label="Started At"               value={p?.started_at ? new Date(p.started_at as string).toLocaleDateString() : "—"} />
            </div>
          </Card>

          <Card>
            <h2 style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 15, margin: "0 0 14px" }}>Usage Credit Balance</h2>
            {balLoading ? (
              <Skeleton height="3.75rem" radius="8px" />
            ) : (
              <>
                <p style={{ fontSize: "2rem", fontWeight: 700, color: balance?.low_credit ? "var(--danger-text)" : "var(--brand)", margin: "0 0 4px" }}>
                  {safeNum(balance?.usage_credit_balance)}
                </p>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", margin: "0 0 16px" }}>credits available</p>
                {balance?.low_credit && (
                  <div style={{ padding: 12, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 8, fontSize: "0.875rem", color: "var(--danger-text)", marginBottom: 12 }}>
                    Low Usage Credits — completed jobs may fail to deduct. Contact Platform Admin to add Provider Usage Credits.
                  </div>
                )}
                <div style={{ padding: 12, background: "var(--surface-sunken)", borderRadius: 8, fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                  Each completed job deducts usage credits from your balance.
                  Credits are provisioned when your package is active.
                </div>
              </>
            )}
          </Card>
        </div>
      )}

      <Card>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", margin: 0 }}>
          Package and credit settings are managed by your administrator. Contact support to change your package or add credits.
          To view your credit transaction history, visit <a href="/finance/usage-credit-ledger" style={{ color: "var(--brand)" }}>Usage Credit Ledger</a>.
          For security deposit information, visit <a href="/finance/security-deposit" style={{ color: "var(--brand)" }}>Security Deposit</a>.
        </p>
      </Card>
    </TenantLayout>
  );
}
