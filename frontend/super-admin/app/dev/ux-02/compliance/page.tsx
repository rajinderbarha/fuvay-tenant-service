"use client";
import Link from "next/link";
import { PageShell, StatusBadge } from "@serviceos/design-system";
import { EnterpriseListPage } from "../../../../components/ux02/patterns/EnterpriseListPage";
import { FIXTURE_COMPLIANCE_CASES } from "../../../../lib/ux02/fixtures";
import type { ComplianceCaseFixture } from "../../../../lib/ux02/types";

export default function ComplianceListShowcase() {
  return (
    <PageShell>
      <EnterpriseListPage<ComplianceCaseFixture>
        title="Compliance Cases"
        description="Cross-tenant compliance case list — reuses the same enterprise list pattern as Tenants."
        readiness="MOCK_DESIGN_ONLY"
        rows={FIXTURE_COMPLIANCE_CASES}
        rowKey={(c) => c.id}
        searchFields={(c) => `${c.title} ${c.category}`}
        filters={[{ key: "severity", label: "Severity", values: ["low", "medium", "high", "critical"] }, { key: "status", label: "Status", values: ["open", "in_review", "resolved", "escalated"] }]}
        getFilterValue={(c, key) => (c as any)[key]}
        columns={[
          { key: "title", header: "Case", accessor: (c) => c.title, render: (c) => <Link href={`/dev/ux-02/compliance/${c.id}`}>{c.title}</Link> },
          { key: "severity", header: "Severity", render: (c) => <StatusBadge status={c.severity} /> },
          { key: "status", header: "Status", render: (c) => <StatusBadge status={c.status} /> },
          { key: "assignedTo", header: "Assigned To", accessor: (c) => c.assignedTo },
          { key: "openedAt", header: "Opened", accessor: (c) => c.openedAt },
        ]}
      />
    </PageShell>
  );
}
