"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { ComplaintWorkspace, DisputePresentation } from "../../../../components/ux04/ComplaintWorkspace";
import { complaintDetailFixture, disputeFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04A — Complaint case detail + Dispute presentation. No
 * tenant dispute-resolution or refund control exists on this page. */
export default function Complaints() {
  return (
    <PageShell>
      <PageHeader title="Complaints & Disputes" description="Provider-side proposal/response only — platform holds final adjudication authority." />
      <ComplaintWorkspace complaint={complaintDetailFixture} />
      <DisputePresentation dispute={disputeFixture} />
    </PageShell>
  );
}
