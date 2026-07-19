"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { OperationalRiskBanner } from "../../../../components/ux04/OperationalRiskBanner";
import { operationalExceptionsFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04A — operational exception gallery. Explicitly NOT the
 * blocked Booking Exception Resolution engine — explanation/safe-actions/
 * escalation only, no "resolve" action anywhere. */
export default function OperationalExceptions() {
  return (
    <PageShell>
      <PageHeader title="Operational Exceptions" description="Read-only explanation patterns. Not an active resolution engine." />
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {operationalExceptionsFixture.map((ex) => (
          <OperationalRiskBanner key={ex.kind} exception={ex} />
        ))}
      </div>
    </PageShell>
  );
}
