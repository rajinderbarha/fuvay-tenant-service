"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { OperationalActionQueue } from "../../../../components/ux04/OperationalActionQueue";
import { actionQueueFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04A — Staff Operational Home. Canonical `staff` role
 * only — no dispatcher/manager alias. Reuses OperationalActionQueue with a
 * queue pre-filtered to permission-compatible items; the parts-approval
 * item is intentionally shown as unavailable here to demonstrate a
 * limited-staff (no finance/approval permission) composition, vs. the
 * tenant_owner composition shown on the Command Center page. */
const STAFF_LIMITED_QUEUE = actionQueueFixture.map((item) => ({
  ...item,
  actions: item.actions.map((a) => ({ ...a, available: false, reason: "Requires tenant_owner or a staff member with the relevant permission." })),
}));

export default function StaffOperationalHome() {
  return (
    <PageShell>
      <PageHeader title="Staff Operational Home" description="Canonical staff role, permission-limited composition of the same Command Center queue." />
      <OperationalActionQueue items={STAFF_LIMITED_QUEUE} />
    </PageShell>
  );
}
