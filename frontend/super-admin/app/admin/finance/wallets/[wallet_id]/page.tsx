"use client";
import { useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Badge, Btn } from "../../../../../components/shared/ui";
import { financeApi } from "../../../../../lib/api";
import { useApi } from "../../../../../hooks/useApi";

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 12, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ fontSize: 12, color: "var(--text-tertiary)", minWidth: 180, fontWeight: 500 }}>{label}</span>
      <div style={{ fontSize: 13, color: "var(--text-primary)", flex: 1 }}>{children}</div>
    </div>
  );
}
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card padding={16}>
      <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 700 }}>{title}</h3>
      {children}
    </Card>
  );
}

export default function WalletLedgerPage() {
  const { wallet_id } = useParams<{ wallet_id: string }>();
  const router = useRouter();
  const detail = useApi(useCallback(() => financeApi.getWalletLedger(wallet_id), [wallet_id]));
  const d = detail.data;

  return (
    <AdminLayout activeNav="finance">
      <SectionHeader title="Wallet Ledger" subtitle="Balance summary, ledger entries, top-ups, deductions, and threshold rules."/>
      <div style={{ padding: "0 28px 32px", display: "flex", flexDirection: "column", gap: 16 }}>
        <Btn variant="ghost" size="sm" onClick={() => router.push("/admin/finance/wallets")}>
          <ArrowLeft size={13}/> Back to Wallet Directory
        </Btn>

        {detail.loading && <Card padding={16}>Loading…</Card>}
        {detail.error && <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Could not load finance data. {detail.error}</p></Card>}

        {d && (
          <>
            <Section title="Balance Summary">
              <InfoRow label="Tenant">{d.wallet.tenant_name}</InfoRow>
              <InfoRow label="Available Balance">₹{d.wallet.available_balance.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Reserved Balance">₹{d.wallet.reserved_balance.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Lifetime Purchased">₹{d.wallet.lifetime_purchased.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Lifetime Consumed">₹{d.wallet.lifetime_consumed.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Low-Balance Threshold">{d.wallet.low_balance_threshold != null ? `₹${d.wallet.low_balance_threshold.toLocaleString("en-IN")}` : "—"}</InfoRow>
              <InfoRow label="Health Band"><Badge variant="info">{d.wallet.health_band}</Badge></InfoRow>
              <InfoRow label="Status"><Badge variant={d.wallet.is_active ? "success" : "muted"}>{d.wallet.is_active ? "Active" : "Inactive"}</Badge></InfoRow>
            </Section>

            <Section title={`Ledger Entries (${d.pagination.total})`}>
              {d.ledger.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No ledger entries yet.</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      {["Type", "Amount", "Balance After", "Reference", "Description", "Date"].map(h => (
                        <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {d.ledger.map(t => (
                      <tr key={t.txn_id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "8px" }}>{t.txn_type}</td>
                        <td style={{ padding: "8px" }}>₹{t.amount.toLocaleString("en-IN")}</td>
                        <td style={{ padding: "8px" }}>₹{t.balance_after.toLocaleString("en-IN")}</td>
                        <td style={{ padding: "8px", color: "var(--text-tertiary)" }}>{t.reference_type ?? "—"}</td>
                        <td style={{ padding: "8px", color: "var(--text-tertiary)" }}>{t.description ?? "—"}</td>
                        <td style={{ padding: "8px" }}>{new Date(t.created_at).toLocaleDateString("en-IN")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Section>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
