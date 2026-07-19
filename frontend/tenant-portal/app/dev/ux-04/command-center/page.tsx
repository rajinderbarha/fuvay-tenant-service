"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { OperationalActionQueue } from "../../../../components/ux04/OperationalActionQueue";
import { actionQueueFixture } from "../../../../lib/ux04/fixtures";

/** DESIGN PHASE UX-04 — Operations Command Center dev showcase. One
 * composition, role-sensitive via ActionPermissionView.available on each
 * queue item — not a separate implementation per role. */
export default function CommandCenter() {
  return (
    <PageShell>
      <PageHeader title="Operations Command Center" description="Today's action queue, dispatch overview, and financial/compliance alerts." />
      <section style={{ marginTop: "1rem" }}>
        <h2 style={{ fontSize: "0.9375rem", marginBottom: "0.5rem" }}>Action queue</h2>
        <OperationalActionQueue items={actionQueueFixture} />
      </section>
    </PageShell>
  );
}
