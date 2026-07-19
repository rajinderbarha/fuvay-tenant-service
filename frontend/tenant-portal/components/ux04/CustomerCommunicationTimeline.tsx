"use client";
import React from "react";
import type { CommunicationEventView } from "../../lib/ux04/types";

/** DESIGN PHASE UX-04 — never renders an internal (customerVisible=false)
 * event as if the customer saw it; internal items are shown with an
 * explicit "internal only" marker so staff never mistake them for
 * delivered customer communication. */
export function CustomerCommunicationTimeline({ events }: { events: CommunicationEventView[] }) {
  return (
    <ol style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      {events.map((e) => (
        <li key={e.id} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", borderLeft: `2px solid ${e.deliveryState === "failed" ? "var(--danger-text)" : "var(--border)"}`, paddingLeft: "0.75rem" }}>
          <div>
            <p style={{ margin: 0, fontWeight: 600 }}>{e.kind.replace(/_/g, " ")} {!e.customerVisible && <span style={{ color: "var(--warning-text)", fontSize: "0.6875rem" }}>(internal only)</span>}</p>
            <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "0.75rem" }}>{e.at} · {e.actorName} · {e.channel}</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <span style={{ fontSize: "0.75rem", color: e.deliveryState === "failed" ? "var(--danger-text)" : "var(--success-text)" }}>{e.deliveryState}</span>
            {e.deliveryState === "failed" && e.failureCanRetry && (
              <p style={{ margin: 0, fontSize: "0.6875rem", color: "var(--info-text)" }}>Retry available</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
