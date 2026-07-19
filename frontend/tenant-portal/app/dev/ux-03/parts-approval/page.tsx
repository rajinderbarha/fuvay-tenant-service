import { PageShell, PageHeader, Card, StatusBadge } from "@serviceos/design-system";
import { FIXTURE_PARTS_REQUESTS } from "../../../../lib/ux03/fixtures";

export default function PartsApproval() {
  return (
    <PageShell>
      <PageHeader title="Parts Request Approval" description="ServiceJob-only (field_ops.Job has no PartsRequest concept). Only provider-side staff may approve/reject/mark-installed — technicians request/view only, never install-authority." />
      {FIXTURE_PARTS_REQUESTS.map((p) => (
        <Card key={p.id} title={`Request ${p.id}`}>
          <p>Status: <StatusBadge status={p.status} /></p>
          <ul>{p.items.map((it) => <li key={it.id}>{it.name} x{it.qty} — ₹{it.unitCost}</li>)}</ul>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button disabled>Approve</button>
            <button disabled>Reject</button>
            <button disabled>Mark Installed</button>
          </div>
          <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Buttons disabled — MOCK_DESIGN_ONLY, real mutation not wired.</p>
        </Card>
      ))}
    </PageShell>
  );
}
