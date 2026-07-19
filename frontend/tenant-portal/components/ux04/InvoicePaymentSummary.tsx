"use client";
/**
 * DESIGN PHASE UX-04A — invoice / on-site payment record presentation.
 * Language is deliberately accurate: "payment recorded" (what happened
 * on-site), never "processed by ServiceOS"; "commission deducted from
 * tenant credit", never "payout". No capture/refund/payout action exists
 * anywhere in this component.
 */
import React from "react";
import type { InvoiceView } from "../../lib/ux04/types";

const STATE_LABEL: Record<InvoiceView["state"], string> = {
  not_generated: "Not generated",
  draft: "Draft",
  issued: "Issued",
  payment_expected_on_site: "Payment expected on-site",
  payment_recorded: "Payment recorded",
  partial: "Partially recorded",
  disputed: "Disputed",
  voided: "Voided",
};

export function InvoicePaymentSummary({ invoice }: { invoice: InvoiceView }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <p style={{ margin: 0, fontWeight: 600 }}>Invoice {invoice.id ?? "(not generated)"}</p>
        <span style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase" }}>{STATE_LABEL[invoice.state]}</span>
      </div>
      {invoice.quoteTotal !== null && <p style={{ fontSize: "0.8125rem" }}>Quote total: {invoice.quoteTotal.toLocaleString()}</p>}
      <p style={{ fontSize: "0.8125rem" }}>Invoice total: {invoice.invoiceTotal.toLocaleString()}</p>
      <p style={{ fontSize: "0.8125rem" }}>
        On-site payment record: {invoice.paymentMethodRecord ?? "not yet recorded"}
      </p>
      <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
        Commission deducted from tenant credit: {invoice.commissionDeductionAmount.toLocaleString()} · Service credit applied: {invoice.creditDeductionAmount.toLocaleString()}
      </p>
      <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", fontStyle: "italic" }}>
        ServiceOS does not process this on-site payment — this is a record of what the technician reported, not
        a platform transaction. No capture/refund/payout action is available here.
      </p>
    </div>
  );
}
