"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { SLAExplanation } from "../../../../components/ux04/SLAExplanation";
import { slaGalleryFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04A — SLA/risk state gallery, all 9 SLAState values. */
export default function SLARiskGallery() {
  return (
    <PageShell>
      <PageHeader title="SLA / Risk States" description="All 9 states, backend-provided or typed-fixture values only." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(16rem, 1fr))", gap: "0.75rem" }}>
        {slaGalleryFixture.map((sla) => (
          <SLAExplanation key={sla.state} sla={sla} />
        ))}
      </div>
    </PageShell>
  );
}
