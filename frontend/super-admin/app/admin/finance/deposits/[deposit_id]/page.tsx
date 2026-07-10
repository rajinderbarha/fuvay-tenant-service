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

export default function DepositDetailPage() {
  const { deposit_id } = useParams<{ deposit_id: string }>();
  const router = useRouter();
  const detail = useApi(useCallback(() => financeApi.getDepositDetail(deposit_id), [deposit_id]));
  const d = detail.data;

  return (
    <AdminLayout activeNav="finance-deposits">
      <SectionHeader title="Deposit Detail" subtitle="Overview, provider/tenant, package link, payment evidence, ledger, adjustments, refunds, and audit logs."/>
      <div style={{ padding: "0 28px 32px", display: "flex", flexDirection: "column", gap: 16 }}>
        <Btn variant="ghost" size="sm" onClick={() => router.push("/admin/finance/deposits")}>
          <ArrowLeft size={13}/> Back to Security Deposits
        </Btn>

        {detail.loading && <Card padding={16}>Loading…</Card>}
        {detail.error && <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Could not load finance data. {detail.error}</p></Card>}

        {d && (
          <>
            <Section title="Overview">
              <InfoRow label="Tenant">{d.deposit.tenant_name}</InfoRow>
              <InfoRow label="Vertical">{d.deposit.vertical ?? "—"}</InfoRow>
              <InfoRow label="Location">{[d.deposit.city, d.deposit.state].filter(Boolean).join(", ") || "—"}</InfoRow>
              <InfoRow label="Required Amount">₹{d.deposit.required_amount.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Received Amount">₹{d.deposit.received_amount.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Current Balance">₹{d.deposit.current_balance.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Status"><Badge variant="info">{d.deposit.status.replace(/_/g, " ")}</Badge></InfoRow>
              <InfoRow label="Hold State">{d.deposit.hold_state ?? "—"}</InfoRow>
              {d.deposit.rejection_reason && <InfoRow label="Rejection Reason">{d.deposit.rejection_reason}</InfoRow>}
              {d.deposit.clarification_notes && <InfoRow label="Clarification Notes">{d.deposit.clarification_notes}</InfoRow>}
              <InfoRow label="Approved At">{d.deposit.approved_at ? new Date(d.deposit.approved_at).toLocaleString("en-IN") : "—"}</InfoRow>
              <InfoRow label="Refunded At">{d.deposit.refunded_at ? new Date(d.deposit.refunded_at).toLocaleString("en-IN") : "—"}</InfoRow>
            </Section>

            <Section title={`Deposit Ledger (${d.ledger.length})`}>
              {d.ledger.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No ledger entries yet.</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      {["Type", "Amount", "Balance After", "Notes", "Date"].map(h => (
                        <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {d.ledger.map((t) => {
                      const tx = t as { txn_id: string; txn_type: string; amount: number; balance_after: number; notes?: string; created_at: string };
                      return (
                        <tr key={tx.txn_id} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "8px" }}>{tx.txn_type}</td>
                          <td style={{ padding: "8px" }}>₹{tx.amount.toLocaleString("en-IN")}</td>
                          <td style={{ padding: "8px" }}>₹{tx.balance_after.toLocaleString("en-IN")}</td>
                          <td style={{ padding: "8px", color: "var(--text-tertiary)" }}>{tx.notes ?? "—"}</td>
                          <td style={{ padding: "8px" }}>{new Date(tx.created_at).toLocaleDateString("en-IN")}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </Section>

            <div id="audit">
              <Section title={`Audit Logs (${d.audit_log.length})`}>
                {d.audit_log.length === 0 ? (
                  <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No audit history yet.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {d.audit_log.map(a => (
                      <div key={a.id} style={{ fontSize: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                        <strong style={{ textTransform: "capitalize" }}>{a.operation}</strong>
                        {a.actor_role && <span style={{ color: "var(--text-tertiary)" }}> · {a.actor_role}</span>}
                        {a.created_at && <span style={{ color: "var(--text-tertiary)" }}> · {new Date(a.created_at).toLocaleString("en-IN")}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </Section>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
