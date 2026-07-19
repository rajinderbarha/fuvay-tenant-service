import { PageShell, PageHeader, Card, StatusBadge } from "@serviceos/design-system";
import { FIXTURE_COMPLIANCE } from "../../../../lib/ux03/fixtures";

export default function Compliance() {
  return (
    <PageShell>
      <PageHeader title="Compliance" description="Requirement / submission / status / documents / review / history." />
      {FIXTURE_COMPLIANCE.map((c) => (
        <Card key={c.id} title={c.requirement}>
          <p><StatusBadge status={c.status} /></p>
          {c.history.map((h) => <p key={h.id} style={{ fontSize: "0.8rem" }}>{h.at} — {h.actor} {h.action}</p>)}
        </Card>
      ))}
    </PageShell>
  );
}
