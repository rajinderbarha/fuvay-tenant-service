"use client";
import React from "react";
import type { ChecklistView } from "../../lib/ux04/types";

/** DESIGN PHASE UX-04 — shared checklist rendering. `mode` distinguishes the
 * three required presentations: technician execution (editable in the real
 * app, read-only here), provider review (reviewer note visible), and
 * customer-visible summary (only customerVisible items, no internal notes). */
export function ChecklistProgress({ checklist, mode }: { checklist: ChecklistView; mode: "technician_execution" | "provider_review" | "customer_summary" }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <p style={{ margin: 0, fontWeight: 600 }}>Checklist {checklist.id}</p>
        <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>{checklist.progressPct}% complete</span>
      </div>
      {checklist.sections.map((sec) => {
        const items = mode === "customer_summary" ? sec.items.filter((it) => it.customerVisible) : sec.items;
        if (items.length === 0) return null;
        return (
          <div key={sec.id} style={{ marginTop: "0.75rem" }}>
            <p style={{ fontWeight: 600, fontSize: "0.8125rem", margin: "0 0 0.25rem" }}>{sec.label}</p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {items.map((it) => (
                <li key={it.id} style={{ fontSize: "0.8125rem", padding: "0.25rem 0", display: "flex", justifyContent: "space-between" }}>
                  <span>
                    {it.completed ? "✓" : "○"} {it.label} {it.required && <span style={{ color: "var(--text-secondary)" }}>(required)</span>}
                  </span>
                  {it.passFail && <span style={{ color: it.passFail === "pass" ? "var(--success-text)" : "var(--danger-text)" }}>{it.passFail}</span>}
                </li>
              ))}
              {mode !== "customer_summary" &&
                items.map((it) =>
                  it.technicianNote ? (
                    <li key={`${it.id}-note`} style={{ fontSize: "0.75rem", color: "var(--text-secondary)", paddingLeft: "1rem" }}>
                      Technician note: {it.technicianNote}
                    </li>
                  ) : null
                )}
              {mode === "provider_review" &&
                items.map((it) =>
                  it.reviewerNote ? (
                    <li key={`${it.id}-rev`} style={{ fontSize: "0.75rem", color: "var(--info-text)", paddingLeft: "1rem" }}>
                      Reviewer note: {it.reviewerNote}
                    </li>
                  ) : null
                )}
            </ul>
          </div>
        );
      })}
      {checklist.completionLocked && <p style={{ fontSize: "0.75rem", color: "var(--warning-text)" }}>Completion is locked until all required items pass.</p>}
    </div>
  );
}
