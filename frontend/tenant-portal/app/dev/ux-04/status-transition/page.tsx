"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { StatusTransitionPanel } from "../../../../components/ux04/StatusTransitionPanel";
import { jobDetailFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04A — standalone Status Transition workspace, extracted
 * from Job Detail Workspace so it can be shown/tested independently. */
export default function StatusTransition() {
  return (
    <PageShell>
      <PageHeader title="Status Transition" description="Repository-backed states only — no invented options, no skip-ahead." />
      <StatusTransitionPanel transition={jobDetailFixture.statusTransition} />
    </PageShell>
  );
}
