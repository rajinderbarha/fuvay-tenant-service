"use client";
import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { TenantLayout } from "../../../../../components/layout/TenantLayout";
import { Card, SectionHeader, Badge, Btn, Spinner, Modal, Input, Select } from "../../../../../components/shared/ui";
import { providerInvoiceApi } from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";

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

function money(v?: string) {
  if (v == null) return "—";
  const n = Number(v);
  return Number.isFinite(n) ? `₹${n.toLocaleString("en-IN")}` : String(v);
}

export default function ServiceInvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const invoiceId = params?.id ?? "";

  const detail = useApi(useCallback(() => providerInvoiceApi.get(invoiceId), [invoiceId]), [invoiceId]);
  const timeline = useApi(useCallback(() => providerInvoiceApi.timeline(invoiceId), [invoiceId]), [invoiceId]);

  const [showPayment, setShowPayment] = useState(false);
  const [paymentMode, setPaymentMode] = useState("cash");
  const [collectedAmount, setCollectedAmount] = useState("");
  const [toast, setToast] = useState("");

  const issueAction = useAction(useCallback(() => providerInvoiceApi.issue(invoiceId), [invoiceId]));
  const paymentAction = useAction(useCallback(
    () => providerInvoiceApi.recordPayment(invoiceId, {
      payment_mode: paymentMode,
      collected_amount: Number(collectedAmount),
    }),
    [invoiceId, paymentMode, collectedAmount]));

  async function handleIssue() {
    await issueAction.execute();
    setToast("Invoice issued.");
    detail.refetch();
  }

  async function handleRecordPayment() {
    await paymentAction.execute();
    setShowPayment(false);
    setCollectedAmount("");
    setToast("Payment recorded.");
    detail.refetch();
    timeline.refetch();
  }

  const inv = detail.data;

  return (
    <TenantLayout>
      <div style={{ padding: "var(--space-6, 24px)" }}>
        <SectionHeader
          title={inv ? `Invoice ${inv.invoice_number ?? inv.id.slice(0, 8)}` : "Service Invoice"}
          subtitle="Invoice overview, payment status, and financial timeline."
        />
        <div style={{ margin: "0 0 16px" }}>
          <Link href="/provider/service-invoices" style={{ fontSize: 13, color: "var(--text-link)" }}>← Back to Service Invoices</Link>
        </div>

        {toast && (
          <div style={{
            background: "var(--color-success-subtle, #ecfdf5)", color: "var(--color-success, var(--success))",
            border: "1px solid var(--color-success, var(--success))", borderRadius:"var(--radius-md)",
            padding: "10px 14px", marginBottom: 16,
          }}>
            {toast}
            <button onClick={() => setToast("")} style={{ marginLeft: 8, cursor: "pointer" }}>✕</button>
          </div>
        )}

        {detail.loading && <Spinner />}
        {detail.error && <p style={{ color: "var(--danger, var(--danger))" }}>Could not load invoice.</p>}

        {inv && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Section title="Overview">
              <InfoRow label="Status"><Badge variant="info">{inv.invoice_status?.replace(/_/g, " ")}</Badge></InfoRow>
              <InfoRow label="Payment Status"><Badge variant="muted">{inv.payment_status?.replace(/_/g, " ")}</Badge></InfoRow>
              <InfoRow label="Source">{inv.source?.replace(/_/g, " ") ?? "—"}</InfoRow>
              <InfoRow label="Job">{inv.job_id ? inv.job_id.slice(0, 8) : "—"}</InfoRow>
              <InfoRow label="Subtotal">{money(inv.subtotal)}</InfoRow>
              <InfoRow label="Tax">{money(inv.tax_amount)}</InfoRow>
              <InfoRow label="Discount">{money(inv.discount_amount)}</InfoRow>
              <InfoRow label="Customer Payable">{money(inv.customer_payable_amount)}</InfoRow>
              <InfoRow label="Commission">{money(inv.commission_amount)}</InfoRow>
              <InfoRow label="Issued">{inv.issued_at ? new Date(inv.issued_at).toLocaleString("en-IN") : "—"}</InfoRow>
              <InfoRow label="Paid">{inv.paid_at ? new Date(inv.paid_at).toLocaleString("en-IN") : "—"}</InfoRow>
              {inv.notes && <InfoRow label="Notes">{inv.notes}</InfoRow>}
            </Section>

            <div style={{ display: "flex", gap: 8 }}>
              {inv.invoice_status === "draft" && (
                <Btn onClick={handleIssue} loading={issueAction.loading}>Issue Invoice</Btn>
              )}
              {inv.invoice_status === "issued" && inv.payment_status !== "paid" && (
                <Btn variant="secondary" onClick={() => setShowPayment(true)}>Record Payment</Btn>
              )}
            </div>

            <Section title={`Financial Timeline (${timeline.data?.length ?? 0})`}>
              {timeline.loading && <Spinner />}
              {!timeline.loading && (timeline.data?.length ?? 0) === 0 ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No timeline events yet.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {(timeline.data ?? []).map((e, i) => {
                    const ev = e as { event_type?: string; created_at?: string; description?: string };
                    return (
                      <div key={i} style={{ fontSize: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                        <strong style={{ textTransform: "capitalize" }}>{(ev.event_type ?? "event").replace(/_/g, " ")}</strong>
                        {ev.description && <span style={{ color: "var(--text-tertiary)" }}> · {ev.description}</span>}
                        {ev.created_at && <span style={{ color: "var(--text-tertiary)" }}> · {new Date(ev.created_at).toLocaleString("en-IN")}</span>}
                      </div>
                    );
                  })}
                </div>
              )}
            </Section>
          </div>
        )}
      </div>

      <Modal open={showPayment} onClose={() => setShowPayment(false)} title="Record Payment" size="sm">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Select
            label="Payment Mode"
            value={paymentMode}
            onChange={setPaymentMode}
            options={[
              { value: "cash", label: "Cash" },
              { value: "upi", label: "UPI" },
              { value: "card", label: "Card" },
              { value: "bank_transfer", label: "Bank Transfer" },
            ]}
          />
          <Input label="Collected Amount" type="number" value={collectedAmount} onChange={setCollectedAmount} placeholder="0.00" />
          {paymentAction.error && <p style={{ color: "var(--danger)", fontSize: 12 }}>{paymentAction.error}</p>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={() => setShowPayment(false)}>Cancel</Btn>
            <Btn onClick={handleRecordPayment} loading={paymentAction.loading} disabled={!collectedAmount}>Record Payment</Btn>
          </div>
        </div>
      </Modal>
    </TenantLayout>
  );
}
