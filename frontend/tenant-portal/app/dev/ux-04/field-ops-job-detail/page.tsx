"use client";
import { PageShell } from "@serviceos/design-system";
import { FieldOpsJobDetail } from "../../../../components/ux04/FieldOpsJobDetail";
import { fieldOpsJobDetailFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04B — field_ops.Job detail, distinct model-specific page
 * (was previously dispositioned NOT_APPLICABLE at UX-04A; corrected). */
export default function FieldOpsJobDetailPage() {
  return (
    <PageShell>
      <FieldOpsJobDetail view={fieldOpsJobDetailFixture} />
    </PageShell>
  );
}
