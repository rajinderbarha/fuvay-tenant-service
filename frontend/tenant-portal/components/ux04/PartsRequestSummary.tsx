"use client";
import React from "react";
import type { PartsRequestView } from "../../lib/ux04/types";

/** DESIGN PHASE UX-04 — PartsRequest is ServiceJob-only. This component
 * NEVER accepts or links a field_ops.Job id, and never renders a
 * technician-facing "mark installed" control — only provider-side staff
 * with the approve action available may act (see actions[].available). */
export function PartsRequestSummary({ view }: { view: PartsRequestView }) {
  const { request, actions } = view;
  const approveAction = actions.find((a) => a.actionKey.includes("approve"));
  const total = request.items.reduce((sum, i) => sum + i.qty * i.unitCost, 0);
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <p style={{ margin: 0, fontWeight: 600 }}>Parts request {request.id}</p>
        <span style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase" }}>{request.status}</span>
      </div>
      <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>ServiceJob {request.serviceJobId} · requested by technician {request.requestedByTechnicianId}</p>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {request.items.map((i) => (
          <li key={i.id} style={{ fontSize: "0.8125rem", display: "flex", justifyContent: "space-between" }}>
            <span>{i.name} × {i.qty}</span>
            <span>{(i.qty * i.unitCost).toLocaleString()}</span>
          </li>
        ))}
      </ul>
      <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
        <span>Total</span>
        <span>{total.toLocaleString()}</span>
      </div>
      {request.status === "requested" ? (
        approveAction?.available ? (
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
            <button type="button" style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--success-text)", border: "1px solid var(--success-text)", borderRadius: "var(--radius-md)", padding: "0.25rem 0.75rem", background: "none" }}>Approve</button>
            <button type="button" style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--danger-text)", border: "1px solid var(--danger-text)", borderRadius: "var(--radius-md)", padding: "0.25rem 0.75rem", background: "none" }}>Reject</button>
          </div>
        ) : (
          <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontStyle: "italic" }}>{approveAction?.reason ?? "Approval not available with your current permissions."}</p>
        )
      ) : (
        <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Decided by staff {request.decidedByStaffId} at {request.decidedAt}.</p>
      )}
    </div>
  );
}
