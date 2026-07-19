"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { PartsRequestSummary } from "../../../../components/ux04/PartsRequestSummary";
import { partsRequestFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04A — read-only + restricted-action state example.
 * Same component as the Parts Approval page, but every action forced
 * unavailable, to show the "no fake disabled button" pattern: an
 * explanatory reason renders instead of a control. */
const READ_ONLY_VIEW = {
  ...partsRequestFixture,
  actions: partsRequestFixture.actions.map((a) => ({ ...a, available: false, reason: "Read-only mode — no mutation permitted." })),
};

export default function ReadOnlyRestricted() {
  return (
    <PageShell>
      <PageHeader title="Read-Only / Restricted Action States" description="Data is fully navigable; every mutation control is replaced with its restriction reason, never a disabled fake control." />
      <PartsRequestSummary view={READ_ONLY_VIEW} />
    </PageShell>
  );
}
