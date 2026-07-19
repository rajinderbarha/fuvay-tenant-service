"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { InspectionSummary } from "../../../../components/ux04/InspectionSummary";
import { inspectionFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04A — Inspection workflow, ServiceJob-scoped only. */
export default function Inspection() {
  return (
    <PageShell>
      <PageHeader title="Inspection" description="ServiceJob-scoped. No auto-quote trigger, no invented safety/legal claims." />
      <InspectionSummary inspection={inspectionFixture} />
    </PageShell>
  );
}
