"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { PartsRequestSummary } from "../../../../components/ux04/PartsRequestSummary";
import { partsRequestFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04 — Parts approval showcase. ServiceJob-only; never
 * links a field_ops.Job; approve/reject is provider-side staff only. */
export default function PartsApproval() {
  return (
    <PageShell>
      <PageHeader title="Parts request approval" description="Provider-side review — technicians request/view only." />
      <div style={{ marginTop: "1rem" }}>
        <PartsRequestSummary view={partsRequestFixture} />
      </div>
    </PageShell>
  );
}
