"use client";
/**
 * Shows the provider commission actually charged on this tenant's completed
 * jobs, per category.
 *
 * Replaces MonetizationStatusWidget, which read
 * `provider_monetization_statuses` -- a table that does NOT exist in this
 * schema. Its endpoint (`/v1/tenant/monetization/status`) wraps the query in
 * a bare try/except and returns a hardcoded
 * `{is_monetization_ready: false, monetization_model: null}` fallback, so
 * every tenant on every dashboard was shown a fabricated "not ready"
 * status with no relationship to what they are actually charged. It also
 * used a model taxonomy (subscription/freemium/fixed_billing) that the
 * Home Services charging path does not implement.
 *
 * This widget instead reads /commission-rates, which resolves the rate the
 * same way execution/usage_credit_deduction.py::resolve_commission_credits
 * does at job completion -- category rate first, vertical policy default as
 * fallback -- so the number shown is the number charged.
 */
import React, { useCallback } from "react";
import { Percent, AlertTriangle } from "lucide-react";
import { Card, Badge } from "../shared/ui";
import { homeServicesFinanceApi, type HsCommissionRates } from "../../lib/api-hs-finance-tenant";
import { useApi } from "../../hooks/useApi";

function pct(v: string | null): string {
  if (v === null) return "—";
  const n = Number(v);
  return Number.isFinite(n) ? `${n % 1 === 0 ? n.toFixed(0) : n.toFixed(2).replace(/0$/, "")}%` : `${v}%`;
}

export function CommissionRatesWidget() {
  const rates = useApi(useCallback(() => homeServicesFinanceApi.getCommissionRates(), []));
  const d = rates.data as HsCommissionRates | undefined;

  if (rates.loading) {
    return (
      <Card>
        <div style={{ padding: "20px 24px" }}>
          <div style={{ height: 14, width: 180, borderRadius: 6, background: "var(--surface-sunken)", marginBottom: 10 }} />
          <div style={{ height: 11, width: 240, borderRadius: 6, background: "var(--surface-sunken)" }} />
        </div>
      </Card>
    );
  }

  // Not enrolled / no published policy / no permission -- stay silent rather
  // than showing a misleading zero or an error box on the dashboard.
  if (rates.error || !d) return null;

  return (
    <Card>
      <div style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <Percent size={17} style={{ color: "var(--brand)", flexShrink: 0 }} />
          <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>Your Commission</span>
          {d.is_live
            ? <Badge variant="success">Active</Badge>
            : <Badge variant="warning">Not charged</Badge>}
        </div>

        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 14px" }}>
          {d.basis}. {d.charged_as}.
        </p>

        {!d.is_live && d.not_live_reason && (
          <div style={{ display: "flex", gap: 8, padding: "8px 10px", borderRadius: 8, marginBottom: 12,
            background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
            <AlertTriangle size={14} style={{ color: "var(--warning-text)", flexShrink: 0, marginTop: 1 }} />
            <span style={{ fontSize: 12, color: "var(--warning-text)" }}>{d.not_live_reason}</span>
          </div>
        )}

        {d.categories.length === 0 ? (
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
            {d.default_rate_pct
              ? `${pct(d.default_rate_pct)} applies once you enable services.`
              : "No commission rate has been published yet."}
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {d.categories.map(c => (
              <div key={c.category_id}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10,
                  padding: "7px 0", borderTop: "1px solid var(--border)" }}>
                <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{c.category_name}</span>
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                    {pct(c.effective_rate_pct)}
                  </span>
                  {c.using_default && (
                    <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>default</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
