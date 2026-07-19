"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { ChecklistProgress } from "../../../../components/ux04/ChecklistProgress";
import { checklistFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04A — technician-execution checklist presentation,
 * distinct from the provider-review mode shown in Job Detail Workspace.
 * Same component, mode="technician_execution": all technician notes
 * visible, no reviewer note surfaced. */
export default function ChecklistExecution() {
  return (
    <PageShell>
      <PageHeader title="Checklist — Technician Execution" description="Technician-facing presentation, distinct from provider review." />
      <ChecklistProgress checklist={checklistFixture} mode="technician_execution" />
    </PageShell>
  );
}
