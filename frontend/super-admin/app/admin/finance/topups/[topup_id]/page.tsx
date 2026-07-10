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

export default function TopupDetailPage() {
  const { topup_id } = useParams<{ topup_id: string }>();
  const router = useRouter();
  const detail = useApi(useCallback(() => financeApi.getTopupDetail(topup_id), [topup_id]));
  const d = detail.data;

  return (
    <AdminLayout activeNav="finance-topups">
      <SectionHeader title="Top-up Detail" subtitle="Overview, payment info, wallet credit posting, package used, provider info, ledger, refunds, and audit logs."/>
      <div style={{ padding: "0 28px 32px", display: "flex", flexDirection: "column", gap: 16 }}>
        <Btn variant="ghost" size="sm" onClick={() => router.push("/admin/finance/topups")}>
          <ArrowLeft size={13}/> Back to Credit Top-ups
        </Btn>

        {detail.loading && <Card padding={16}>Loading…</Card>}
        {detail.error && <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Could not load finance data. {detail.error}</p></Card>}

        {d && (
          <>
            <Section title="Overview">
              <InfoRow label="Tenant">{d.topup.tenant_name}</InfoRow>
              <InfoRow label="Order Ref">{d.topup.order_ref ?? "—"}</InfoRow>
              <InfoRow label="Credits Purchased">{d.topup.credits_purchased.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Bonus Credits">{d.topup.bonus_credits.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Amount Paid">₹{d.topup.amount_paid.toLocaleString("en-IN")}</InfoRow>
              <InfoRow label="Payment Method">{d.topup.payment_method ?? "—"}</InfoRow>
              <InfoRow label="Payment Status"><Badge variant="info">{d.topup.payment_status.replace(/_/g, " ")}</Badge></InfoRow>
              <InfoRow label="Wallet Credit Status">{d.topup.wallet_credit_status}</InfoRow>
              {d.topup.failure_reason && <InfoRow label="Failure Reason">{d.topup.failure_reason}</InfoRow>}
              {d.topup.refunded_amount != null && <InfoRow label="Refunded Amount">₹{d.topup.refunded_amount.toLocaleString("en-IN")}</InfoRow>}
            </Section>

            <Section title="Package Used">
              {d.package ? <p style={{ margin: 0, fontSize: 13 }}>{d.package.name}</p> : <p style={{ margin: 0, fontSize: 13, color: "var(--text-tertiary)" }}>No package linked.</p>}
            </Section>

            <Section title="Wallet Credit Posting">
              {d.ledger_entry ? (
                <>
                  <InfoRow label="Ledger Amount">₹{(d.ledger_entry as { amount: number }).amount.toLocaleString("en-IN")}</InfoRow>
                  <InfoRow label="Balance After">₹{(d.ledger_entry as { balance_after: number }).balance_after.toLocaleString("en-IN")}</InfoRow>
                </>
              ) : <p style={{ margin: 0, fontSize: 13, color: "var(--text-tertiary)" }}>Credits not yet posted to the wallet.</p>}
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
