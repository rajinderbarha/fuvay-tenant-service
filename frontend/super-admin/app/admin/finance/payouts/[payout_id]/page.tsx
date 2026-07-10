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

export default function PayoutDetailPage() {
  const { payout_id } = useParams<{ payout_id: string }>();
  const router = useRouter();
  const detail = useApi(useCallback(() => financeApi.getPayoutDetail(payout_id), [payout_id]));
  const d = detail.data;

  return (
    <AdminLayout activeNav="finance-payouts">
      <SectionHeader title="Payout Detail" subtitle="Overview, beneficiary, source/reason, approval workflow, transfer metadata, failure/retry history, and audit logs."/>
      <div style={{ padding: "0 28px 32px", display: "flex", flexDirection: "column", gap: 16 }}>
        <Btn variant="ghost" size="sm" onClick={() => router.push("/admin/finance/payouts")}>
          <ArrowLeft size={13}/> Back to Payouts
        </Btn>

        {detail.loading && <Card padding={16}>Loading…</Card>}
        {detail.error && <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Could not load finance data. {detail.error}</p></Card>}

        {d && (
          <>
            <Section title="Overview">
              <InfoRow label="Payout Ref">{d.payout.payout_number ?? d.payout.payout_id}</InfoRow>
              <InfoRow label="Beneficiary">{d.payout.tenant_name}</InfoRow>
              <InfoRow label="Payout Type"><span style={{ textTransform: "capitalize" }}>{d.payout.payout_type.replace(/_/g, " ")}</span></InfoRow>
              <InfoRow label="Requested Amount">₹{d.payout.requested_amount.toLocaleString("en-IN")}</InfoRow>
              {d.payout.approved_amount != null && <InfoRow label="Approved Amount">₹{d.payout.approved_amount.toLocaleString("en-IN")}</InfoRow>}
              <InfoRow label="Status"><Badge variant="info">{d.payout.status}</Badge></InfoRow>
              <InfoRow label="Method">{d.payout.method}</InfoRow>
              {d.payout.rejection_reason && <InfoRow label="Rejection Reason">{d.payout.rejection_reason}</InfoRow>}
              {d.payout.failure_reason && <InfoRow label="Failure Reason">{d.payout.failure_reason}</InfoRow>}
              <InfoRow label="Requested On">{d.payout.requested_on ? new Date(d.payout.requested_on).toLocaleString("en-IN") : "—"}</InfoRow>
              <InfoRow label="Processed On">{d.payout.processed_on ? new Date(d.payout.processed_on).toLocaleString("en-IN") : "—"}</InfoRow>
            </Section>

            <Section title="Beneficiary Bank Account">
              {Object.keys(d.bank_account || {}).length === 0 ? (
                <p style={{ margin: 0, fontSize: 13, color: "var(--text-tertiary)" }}>No bank account on file.</p>
              ) : (
                <pre style={{ fontSize: 12, background: "var(--surface-sunken)", padding: 12, borderRadius: 8, overflowX: "auto" }}>
                  {JSON.stringify(d.bank_account, null, 2)}
                </pre>
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
