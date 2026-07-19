"use client";
import React from "react";
import type { CreditCommissionView } from "../../lib/ux04/types";

/** DESIGN PHASE UX-04 — package credit, commission, and (elsewhere) security
 * deposit are THREE separate concepts. This component only ever shows
 * credit + commission — it never merges in deposit or on-site payment
 * numbers, and never renders a payout/withdrawal action. */
export function CreditCommissionSummary({ view }: { view: CreditCommissionView }) {
  const { packageCredit, estimatedCommissionForJob, creditAfterDeduction, lowCreditWarning, insufficientCreditBlocker, duplicateDeductionPrevented } = view;
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <p style={{ margin: 0, fontWeight: 600 }}>{packageCredit.planName} — package credit</p>
      <p style={{ fontSize: "0.8125rem" }}>Current balance: {packageCredit.creditBalance.toLocaleString()}</p>
      <p style={{ fontSize: "0.8125rem" }}>Estimated commission for this job: {estimatedCommissionForJob.toLocaleString()} ({packageCredit.commissionRateBps / 100}%)</p>
      <p style={{ fontSize: "0.8125rem" }}>Credit after deduction: {creditAfterDeduction.toLocaleString()}</p>
      {lowCreditWarning && <p style={{ fontSize: "0.75rem", color: "var(--warning-text)" }}>Low credit — cycle balance is running low.</p>}
      {insufficientCreditBlocker && <p style={{ fontSize: "0.75rem", color: "var(--danger-text)" }}>Insufficient credit — job completion may be blocked until credit is topped up.</p>}
      {duplicateDeductionPrevented && <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>Duplicate deduction guard: verified — commission deducted at most once for this job.</p>}
      <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", fontStyle: "italic" }}>
        Package credit is not customer money. Commission is not a payout. Security deposit and on-site payment are tracked separately.
      </p>
    </div>
  );
}
