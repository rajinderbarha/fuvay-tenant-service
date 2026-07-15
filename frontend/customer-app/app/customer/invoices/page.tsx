"use client";
/**
 * MODULE-L5-18 — Customer invoices (list).
 *
 * The customer's invoice history. Home-services payment is pay-provider-directly,
 * so from an invoice the customer can confirm it paid and view a receipt (detail
 * page). Wired to the invoice_payment customer engine.
 */
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import { listMyInvoices, Invoice } from "../../../lib/api/customer-invoices";

const STATUS_LABEL: Record<string, string> = {
  issued: "Issued", payment_pending: "Payment due", payment_collected: "Paid",
  paid: "Paid", cancelled: "Cancelled", void: "Void",
};
function statusColor(s: string): string {
  if (["paid", "payment_collected"].includes(s)) return "#0a7c3f";
  if (["cancelled", "void"].includes(s)) return "#8a8a8a";
  return "#b45309";
}

export default function CustomerInvoicesPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    listMyInvoices().then(setInvoices).catch(setError);
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>Invoices</h1>
      <ErrorBanner error={error} />

      {invoices === null ? (
        <div className="co-card">Loading…</div>
      ) : invoices.length === 0 ? (
        <div className="co-card" style={{ textAlign: "center", padding: 24, color: "var(--text-tertiary)" }}>
          No invoices yet.
        </div>
      ) : (
        invoices.map((inv) => (
          <button key={inv.id} onClick={() => router.push(`/customer/invoices/${inv.id}`)}
            className="co-card" style={{ marginBottom: 10, width: "100%", textAlign: "left",
              border: "none", cursor: "pointer", display: "flex", justifyContent: "space-between",
              alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 700 }}>{inv.currency}{Number(inv.customer_payable_amount).toLocaleString()}</div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>
                #{inv.invoice_number}
                {inv.issued_at ? ` · ${new Date(inv.issued_at).toLocaleDateString()}` : ""}
              </div>
            </div>
            <span style={{ fontSize: 12, fontWeight: 600, color: statusColor(inv.status) }}>
              {STATUS_LABEL[inv.status] ?? inv.status}
            </span>
          </button>
        ))
      )}

      <BottomNav />
    </div>
  );
}
