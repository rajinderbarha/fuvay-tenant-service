"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { AssignmentCandidateCard } from "../../../../components/ux04/AssignmentCandidateCard";
import { assignmentCandidatesFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04 — Assignment/Dispatch workspace. Real candidate
 * signal fields only (no fabricated AI-matching score); assign/reassign
 * requires a reason in the real workflow (not modeled interactively here —
 * design-phase showcase, not a wired mutation). */
export default function AssignmentWorkspace() {
  return (
    <PageShell>
      <PageHeader title="Assignment / Dispatch" description="Service Job sj_7001 — Washing Machine Repair" />
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "1rem" }}>
        {assignmentCandidatesFixture.map((c) => (
          <AssignmentCandidateCard key={c.technicianId} candidate={c} />
        ))}
      </div>
    </PageShell>
  );
}
