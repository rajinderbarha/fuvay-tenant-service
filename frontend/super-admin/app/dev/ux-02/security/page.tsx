"use client";
import { PageShell, StatusBadge } from "@serviceos/design-system";
import { EnterpriseListPage } from "../../../../components/ux02/patterns/EnterpriseListPage";
import { FIXTURE_SECURITY_OBSERVATIONS } from "../../../../lib/ux02/fixtures";
import type { SecurityObservationFixture } from "../../../../lib/ux02/types";

/**
 * Security status language is deliberately careful: "observation" and
 * "needs_verification" must never be presented as a confirmed live
 * incident. StatusBadge falls back to a neutral badge with humanized text
 * for any status key not in the shared tone registry.
 */
export default function SecurityObservationsShowcase() {
  return (
    <PageShell>
      <EnterpriseListPage<SecurityObservationFixture>
        title="Security Observations"
        description="SECURITY_CONTRACT_PENDING — presentation only; underlying detection pipeline coverage is partial. Status language is intentionally conservative."
        readiness="SECURITY_CONTRACT_PENDING"
        rows={FIXTURE_SECURITY_OBSERVATIONS}
        rowKey={(o) => o.id}
        searchFields={(o) => o.title}
        filters={[{ key: "status", label: "Status", values: ["observation", "needs_verification", "confirmed_finding", "investigating", "action_required", "remediated", "false_positive", "product_policy_blocked"] }]}
        getFilterValue={(o, key) => (o as any)[key]}
        columns={[
          { key: "title", header: "Observation", accessor: (o) => o.title },
          { key: "status", header: "Status", render: (o) => <StatusBadge status={o.status} /> },
          { key: "risk", header: "Risk", render: (o) => <StatusBadge status={o.riskLevel} variant="dot" /> },
          { key: "detectedAt", header: "Detected", accessor: (o) => o.detectedAt },
          { key: "correlationId", header: "Correlation ID", accessor: (o) => o.correlationId },
        ]}
      />
    </PageShell>
  );
}
