"use client";
import { PageShell } from "@serviceos/design-system";
import { ReviewApprovalWorkspace } from "../../../../components/ux02/patterns/ReviewApprovalWorkspace";
import { FIXTURE_VERIFICATIONS, FIXTURE_TENANTS } from "../../../../lib/ux02/fixtures";

export default function VerificationReviewShowcase() {
  const submission = FIXTURE_VERIFICATIONS[0];
  const tenant = FIXTURE_TENANTS.find((t) => t.id === submission.tenantId);
  return (
    <PageShell>
      <ReviewApprovalWorkspace
        title={`Verification Review — ${submission.applicantName}`}
        summary={<div><p>Tenant: {tenant?.displayName}</p><p>Submitted: {submission.submittedAt}</p></div>}
        checklist={submission.checklist}
        documents={submission.documents}
        onDecision={(decision, reason) => console.log("design-only decision", decision, reason)}
      />
    </PageShell>
  );
}
