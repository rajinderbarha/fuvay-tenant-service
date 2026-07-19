import { PageShell, PageHeader, Card, StatusBadge } from "@serviceos/design-system";
import { FIXTURE_SECURITY_DEPOSIT } from "../../../../lib/ux03/fixtures";

export default function SecurityDeposit() {
  const d = FIXTURE_SECURITY_DEPOSIT;
  return (
    <PageShell>
      <PageHeader title="Security Deposit" description="Separate from package credits and job payments." />
      <Card title="Status">
        <p><StatusBadge status={d.status} /> — ₹{d.heldAmount.toLocaleString()} of ₹{d.requiredAmount.toLocaleString()} required</p>
      </Card>
      <Card title="History">
        {d.history.map((h) => <p key={h.id}>{h.type} ₹{h.amount.toLocaleString()} — {new Date(h.at).toLocaleDateString()} — {h.note}</p>)}
      </Card>
    </PageShell>
  );
}
