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

export default function ClaimDetailPage() {
  const { claim_id } = useParams<{ claim_id: string }>();
  const router = useRouter();
  const detail = useApi(useCallback(() => financeApi.getClaimDetail(claim_id), [claim_id]));
  const d = detail.data;

  return (
    <AdminLayout activeNav="finance-claims">
      <SectionHeader title="Warranty Claim Detail" subtitle="Claim summary, booking context, statements, evidence, review notes, settlement decision, and audit logs."/>
      <div style={{ padding: "0 28px 32px", display: "flex", flexDirection: "column", gap: 16 }}>
        <Btn variant="ghost" size="sm" onClick={() => router.push("/admin/finance/claims")}>
          <ArrowLeft size={13}/> Back to Warranty Claims
        </Btn>

        {detail.loading && <Card padding={16}>Loading…</Card>}
        {detail.error && <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Could not load finance data. {detail.error}</p></Card>}

        {d && (
          <>
            <Section title="Claim Summary">
              <InfoRow label="Tenant">{d.claim.tenant_name}</InfoRow>
              <InfoRow label="Booking / Job">{d.claim.job_id}</InfoRow>
              <InfoRow label="Issue Type"><span style={{ textTransform: "capitalize" }}>{d.claim.claim_type.replace(/_/g, " ")}</span></InfoRow>
              <InfoRow label="Description">{d.claim.description}</InfoRow>
              <InfoRow label="Amount Requested">₹{d.claim.amount_requested.toLocaleString("en-IN")}</InfoRow>
              {d.claim.amount_approved != null && <InfoRow label="Amount Approved">₹{d.claim.amount_approved.toLocaleString("en-IN")}</InfoRow>}
              <InfoRow label="Status"><Badge variant="info">{d.claim.status.replace(/_/g, " ")}</Badge></InfoRow>
              {d.claim.rejection_reason && <InfoRow label="Rejection Reason">{d.claim.rejection_reason}</InfoRow>}
              {d.claim.admin_notes && <InfoRow label="Admin Notes">{d.claim.admin_notes}</InfoRow>}
              {d.claim.documents_requested_notes && <InfoRow label="Documents Requested">{d.claim.documents_requested_notes}</InfoRow>}
              {d.claim.settled_amount != null && <InfoRow label="Settled Amount">₹{d.claim.settled_amount.toLocaleString("en-IN")}</InfoRow>}
              {d.claim.settled_at && <InfoRow label="Settled At">{new Date(d.claim.settled_at).toLocaleString("en-IN")}</InfoRow>}
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
