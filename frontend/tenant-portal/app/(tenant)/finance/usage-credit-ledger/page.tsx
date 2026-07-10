'use client';
import { useCallback } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { usageCreditsApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

const safeNum = (v: unknown): number => (typeof v === "number" && isFinite(v)) ? v : 0;

export default function UsageCreditLedgerPage() {
  // HS9B fix: this page previously called tenantSetupApi.getLedger(), a
  // Sprint 23 "wallet" endpoint (/v1/provider/wallet/ledger) — a
  // different, unrelated invoice/commission concept that doesn't exist
  // as a live route for this tenant's Home Services usage credits (its
  // own fallback copy said "endpoint unavailable"). Rewired to the real
  // Home Services usage-credit balance/ledger built in HS9/HS9B.
  const balance = useApi(useCallback(() => usageCreditsApi.getBalance(), []));
  const ledger  = useApi(useCallback(() => usageCreditsApi.getLedger(), []));

  const entries = ledger.data?.entries ?? [];
  const lastDeduction = entries.find(e => e.event_type === "completed_job_deduction");
  const deductedThisSet = entries
    .filter(e => e.event_type === "completed_job_deduction")
    .reduce((sum, e) => sum + Math.abs(e.credit_delta), 0);

  return (
    <TenantLayout activeNav="finance-credit-ledger">
      <div style={{ padding: "var(--space-6)" }}>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.75rem", margin: "0 0 4px" }}>Finance &rsaquo; Usage Credits</p>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Usage Credits</h1>
        <p style={{ color: "var(--text-secondary)", margin: "0 0 24px" }}>
          Track your Home Services usage credit balance, completed job deductions, and credit activity.
        </p>

        {(balance.error || ledger.error) && (
          <div style={{ background: "var(--danger-bg, #fef2f2)", border: "1px solid var(--danger-border, #fca5a5)", borderRadius: 12, padding: 20, marginBottom: 20, color: "var(--danger-text, #dc2626)" }}>
            Usage credit activity could not be loaded. Retry or contact support with request ID.
            {(balance.requestId || ledger.requestId) && (
              <div style={{ fontSize: 12, marginTop: 4 }}>Request ID: {balance.requestId ?? ledger.requestId}</div>
            )}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
          {[
            { label: "Usage Credit Balance",   value: safeNum(balance.data?.usage_credit_balance) },
            { label: "Credits Deducted",       value: deductedThisSet },
            { label: "Completed Jobs",         value: entries.filter(e => e.event_type === "completed_job_deduction").length },
            { label: "Low Credit Status",      value: balance.data?.low_credit ? "Low" : "Healthy" },
          ].map(card => (
            <div key={card.label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 18px" }}>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: "0 0 4px" }}>{card.label}</p>
              <p style={{ fontSize: "1.5rem", fontWeight: 700, color: card.label === "Low Credit Status" && balance.data?.low_credit ? "var(--danger-text, #dc2626)" : "var(--brand)", margin: 0 }}>{card.value}</p>
            </div>
          ))}
        </div>

        {lastDeduction && (
          <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 16 }}>
            Last Deduction: {Math.abs(lastDeduction.credit_delta)} credits on {new Date(lastDeduction.created_at).toLocaleDateString()}
          </p>
        )}

        {ledger.loading ? (
          <div style={{ height: 200, background: "var(--surface-sunken)", borderRadius: 12 }} />
        ) : entries.length === 0 ? (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 48, textAlign: "center", color: "var(--text-secondary)" }}>
            No credit transactions found.
          </div>
        ) : (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)" }}>
                  {["Date", "Job ID", "Event Type", "Credit Change", "Balance Before", "Balance After", "Reason", "Request ID"].map(col => (
                    <th key={col} style={{ padding: "10px 14px", textAlign: "left", fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.ledger_id} style={{ borderTop: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                      {entry.created_at ? new Date(entry.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>{entry.job_id ? entry.job_id.slice(0, 8) : "—"}</td>
                    <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-primary)" }}>
                      {entry.event_type === "completed_job_deduction" ? "Completed Job Deduction" : entry.event_type}
                    </td>
                    <td style={{ padding: "10px 14px", fontSize: "0.875rem", fontWeight: 600, color: entry.credit_delta < 0 ? "var(--danger-text, #dc2626)" : "var(--success, #16a34a)" }}>
                      {entry.credit_delta > 0 ? "+" : ""}{safeNum(entry.credit_delta)}
                    </td>
                    <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>{safeNum(entry.balance_before)}</td>
                    <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>{safeNum(entry.balance_after)}</td>
                    <td style={{ padding: "10px 14px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>{entry.reason ?? "—"}</td>
                    <td style={{ padding: "10px 14px", fontSize: "0.75rem", color: "var(--text-tertiary)" }}>{entry.request_id ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </TenantLayout>
  );
}
