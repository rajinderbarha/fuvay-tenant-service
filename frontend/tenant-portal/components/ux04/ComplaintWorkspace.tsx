"use client";
/**
 * DESIGN PHASE UX-04A — Complaint list+detail workspace and, in the same
 * file, a read-only Dispute presentation (the two are related but distinct
 * concepts per the brief). No tenant dispute-resolution authority is
 * rendered anywhere here — no "resolve"/"issue refund" button exists for
 * either.
 */
import React from "react";
import Link from "next/link";
import type { ComplaintDetailView, DisputeView } from "../../lib/ux04/types";

export function ComplaintWorkspace({ complaint }: { complaint: ComplaintDetailView }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <p style={{ margin: 0, fontWeight: 600 }}>Case {complaint.complaint.id}</p>
        <span style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase" }}>{complaint.complaint.status.replace(/_/g, " ")}</span>
      </div>
      <p style={{ fontSize: "0.8125rem" }}>{complaint.complaint.category} — customer {complaint.complaint.customerId}</p>
      <p style={{ fontSize: "0.8125rem" }}>&quot;{complaint.customerStatement}&quot;</p>
      <Link href={complaint.relatedEntity.href} style={{ fontSize: "0.75rem" }}>
        Related: {complaint.relatedEntity.label}
      </Link>
      <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
        Assigned staff: {complaint.assignedStaffId ?? "Unassigned"} · provider can respond:{" "}
        {complaint.complaint.providerCanRespond ? "yes" : "no"}
      </p>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {complaint.timeline.map((t, i) => (
          <li key={i} style={{ fontSize: "0.75rem", padding: "0.125rem 0" }}>
            {t.at} · {t.actor}: {t.note} {!t.customerVisible && <em style={{ color: "var(--warning-text)" }}>(internal)</em>}
          </li>
        ))}
      </ul>
      <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", fontStyle: "italic" }}>
        Final dispute adjudication authority belongs to the platform. This workspace only presents proposal/
        response actions available to the tenant — it never renders a resolve or refund control.
      </p>
    </div>
  );
}

export function DisputePresentation({ dispute }: { dispute: DisputeView }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <p style={{ margin: 0, fontWeight: 600 }}>Dispute {dispute.id}</p>
        <span style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase" }}>{dispute.status.replace(/_/g, " ")}</span>
      </div>
      <p style={{ fontSize: "0.8125rem" }}>{dispute.reason}</p>
      <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{dispute.amountContextLabel}</p>
      <Link href={dispute.relatedEntity.href} style={{ fontSize: "0.75rem" }}>
        Related: {dispute.relatedEntity.label}
      </Link>
      {dispute.tenantResponse ? (
        <p style={{ fontSize: "0.8125rem" }}>Tenant response: {dispute.tenantResponse}</p>
      ) : (
        <p style={{ fontSize: "0.75rem", fontStyle: "italic", color: "var(--text-secondary)" }}>No tenant response submitted yet.</p>
      )}
      {dispute.decision && <p style={{ fontSize: "0.8125rem" }}>Platform decision: {dispute.decision}</p>}
      <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", fontStyle: "italic" }}>
        If upheld, the platform issues a Customer Service Credit — never a cash refund — and tenant package
        credit is deducted per policy. No tenant-side control exists to issue a refund, payout, or settlement
        here.
      </p>
    </div>
  );
}
