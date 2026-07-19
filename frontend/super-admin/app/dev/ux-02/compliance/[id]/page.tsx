"use client";
import { PageShell, Card, Section, StatusBadge } from "@serviceos/design-system";
import { EnterpriseDetailPage } from "../../../../../components/ux02/patterns/EnterpriseDetailPage";
import { ReviewApprovalWorkspace } from "../../../../../components/ux02/patterns/ReviewApprovalWorkspace";
import { FIXTURE_COMPLIANCE_CASES } from "../../../../../lib/ux02/fixtures";

export default function ComplianceDetailShowcase({ params }: { params: { id: string } }) {
  const c = FIXTURE_COMPLIANCE_CASES.find((x) => x.id === params.id) ?? FIXTURE_COMPLIANCE_CASES[0];
  const sections = [
    { id: "summary", label: "Summary", content: <Card><Section title="Summary"><p>{c.title}</p><StatusBadge status={c.status} /> <StatusBadge status={c.severity} /></Section></Card> },
    {
      id: "resolution", label: "Resolution Workflow",
      content: (
        <ReviewApprovalWorkspace
          title="Resolve Case"
          summary={<p>Category: {c.category} · Assigned to {c.assignedTo}</p>}
          checklist={[{ id: "chk1", label: "Root cause identified", status: "pending" }, { id: "chk2", label: "Tenant notified", status: "pending" }]}
          documents={[]}
          onDecision={() => {}}
        />
      ),
    },
  ];
  return (
    <PageShell>
      <EnterpriseDetailPage title={c.title} subtitle={`Case ${c.id}`} readiness="MOCK_DESIGN_ONLY" sections={sections} />
    </PageShell>
  );
}
