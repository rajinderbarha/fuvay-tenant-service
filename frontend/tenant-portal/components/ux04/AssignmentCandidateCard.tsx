"use client";
/**
 * DESIGN PHASE UX-04 — one technician candidate row inside the
 * Assignment/Dispatch workspace. All fields are read literally from
 * AssignmentCandidateView; `distanceLabel`/`ratingLabel` render "Not
 * available" when null rather than a fabricated number — this component
 * never invents an AI-matching score.
 */
import React from "react";
import type { AssignmentCandidateView } from "../../lib/ux04/types";

export function AssignmentCandidateCard({ candidate, onAssign }: { candidate: AssignmentCandidateView; onAssign?: (technicianId: string) => void }) {
  return (
    <div
      style={{
        border: `1px solid ${candidate.isCurrentAssignee ? "var(--brand)" : "var(--border)"}`,
        borderRadius: "var(--radius-md)",
        padding: "0.75rem 1rem",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "1rem",
      }}
    >
      <div>
        <p style={{ margin: 0, fontWeight: 600, fontSize: "0.875rem" }}>
          {candidate.name} {candidate.isCurrentAssignee && <span style={{ color: "var(--brand)", fontSize: "0.6875rem" }}>Currently assigned</span>}
        </p>
        <p style={{ margin: "0.25rem 0", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
          {candidate.availability.replace(/_/g, " ")} · workload {candidate.currentWorkload} · skill {candidate.skillMatch} · zone {candidate.coversZone ? "covered" : "not covered"}
          {candidate.distanceLabel ? ` · ${candidate.distanceLabel}` : " · distance not available"}
          {candidate.ratingLabel ? ` · ${candidate.ratingLabel}` : " · rating not available"}
        </p>
        {candidate.warnings.map((w) => (
          <p key={w} style={{ margin: 0, fontSize: "0.75rem", color: "var(--warning-text)" }}>
            {w}
          </p>
        ))}
      </div>
      {!candidate.isCurrentAssignee && (
        <button
          type="button"
          onClick={() => onAssign?.(candidate.technicianId)}
          style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--brand)", background: "none", border: "1px solid var(--brand)", borderRadius: "var(--radius-md)", padding: "0.375rem 0.75rem" }}
        >
          Assign
        </button>
      )}
    </div>
  );
}
