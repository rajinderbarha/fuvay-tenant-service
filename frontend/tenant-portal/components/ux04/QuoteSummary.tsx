"use client";
import React from "react";
import type { QuoteView } from "../../lib/ux04/types";

/** DESIGN PHASE UX-04 — quote line items + status, shared by Job Detail and
 * the standalone Quote Workflow showcase. Renders subtotal/total from the
 * fixture/adapter only — never recomputed client-side beyond a plain sum
 * matching what's already provided. */
export function QuoteSummary({ quote }: { quote: QuoteView }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p style={{ margin: 0, fontWeight: 600 }}>Quote {quote.id} · rev {quote.revisionNumber}</p>
        <span style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase", color: "var(--info-text)" }}>{quote.status.replace(/_/g, " ")}</span>
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: "0.75rem 0" }}>
        {quote.lineItems.map((li, i) => (
          <li key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", padding: "0.25rem 0" }}>
            <span>{li.label} <span style={{ color: "var(--text-secondary)" }}>({li.kind})</span></span>
            <span>{li.amount.toLocaleString()}</span>
          </li>
        ))}
      </ul>
      <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, borderTop: "1px solid var(--border)", paddingTop: "0.5rem" }}>
        <span>Total</span>
        <span>{quote.total.toLocaleString()}</span>
      </div>
      {quote.customerResponseAt ? (
        <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Customer responded {quote.customerResponseAt}: {quote.customerResponseNote}</p>
      ) : (
        <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontStyle: "italic" }}>Awaiting customer response.</p>
      )}
    </div>
  );
}
