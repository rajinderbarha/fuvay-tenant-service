"use client";
/**
 * DESIGN PHASE UX-04A — Inspection workflow presentation. ServiceJob-scoped
 * only. No safety/legal claims beyond the free-text findings/observations
 * fields; `quoteRequired` is a flag prompting a human quote-creation step,
 * never an auto-quote trigger.
 */
import React from "react";
import type { InspectionView } from "../../lib/ux04/types";

export function InspectionSummary({ inspection }: { inspection: InspectionView }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <p style={{ margin: 0, fontWeight: 600 }}>Inspection — Service Job {inspection.serviceJobId}</p>
      <p style={{ fontSize: "0.8125rem" }}>Customer reported: {inspection.customerReportedIssue}</p>
      <p style={{ fontSize: "0.8125rem" }}>Findings: {inspection.findings}</p>
      {inspection.observations.length > 0 && (
        <ul style={{ fontSize: "0.8125rem", margin: "0.25rem 0", paddingLeft: "1rem" }}>
          {inspection.observations.map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ul>
      )}
      {inspection.recommendedWork.length > 0 && (
        <>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, margin: "0.5rem 0 0" }}>Recommended work</p>
          <ul style={{ fontSize: "0.8125rem", margin: "0.25rem 0", paddingLeft: "1rem" }}>
            {inspection.recommendedWork.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </>
      )}
      {inspection.requiredParts.length > 0 && (
        <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
          Required parts: {inspection.requiredParts.map((p) => `${p.name} x${p.qty}`).join(", ")}
        </p>
      )}
      <p style={{ fontSize: "0.75rem", color: inspection.quoteRequired ? "var(--warning-text)" : "var(--text-secondary)" }}>
        {inspection.quoteRequired ? "A quote is required before work proceeds." : "No quote required for this inspection."}
      </p>
      <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>Checklist status: {inspection.checklistStatus.replace(/_/g, " ")}</p>
    </div>
  );
}
