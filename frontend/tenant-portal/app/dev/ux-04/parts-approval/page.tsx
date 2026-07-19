"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { PartsRequestSummary } from "../../../../components/ux04/PartsRequestSummary";
import { partsRequestFixture, partsRequestListFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04 (fixture corrected UX-04B) — Parts approval showcase.
 * ServiceJob-only; never links a field_ops.Job; approve/reject is
 * provider-side staff only. Renders a `status: "requested"` row (from
 * partsRequestListFixture, converted to a PartsRequestView) so the
 * Approve/Reject controls this page is named for actually appear, plus
 * the already-decided baseline fixture underneath for the decided-state
 * presentation. */
export default function PartsApproval() {
  const pendingView = {
    meta: partsRequestFixture.meta,
    request: partsRequestListFixture[1].request, // pr_302, status: "requested"
    actions: partsRequestListFixture[1].actions,
  };
  return (
    <PageShell>
      <PageHeader title="Parts request approval" description="Provider-side review — technicians request/view only." />
      <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <PartsRequestSummary view={pendingView} />
        <PartsRequestSummary view={partsRequestFixture} />
      </div>
    </PageShell>
  );
}
