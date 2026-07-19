import { PageShell, PageHeader, Card, StatusBadge } from "@serviceos/design-system";
import { FIXTURE_CUSTOMERS, FIXTURE_COMPLAINTS } from "../../../../lib/ux03/fixtures";

export default function CustomersComplaints() {
  return (
    <PageShell>
      <PageHeader title="Customers & Complaints" description="Contact info masked by default; no invented dispute-resolution authority — provider has proposal/response authority only." />
      <Card title="Customers">
        {FIXTURE_CUSTOMERS.map((c) => (
          <p key={c.id}>{c.name} — {c.maskedPhone} · {c.maskedEmail} · {c.totalServiceJobs} jobs</p>
        ))}
      </Card>
      <Card title="Complaints">
        {FIXTURE_COMPLAINTS.map((c) => (
          <p key={c.id}><StatusBadge status={c.status} /> — {c.category} (job {c.jobRef})</p>
        ))}
      </Card>
    </PageShell>
  );
}
