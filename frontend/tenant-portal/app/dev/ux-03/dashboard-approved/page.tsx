import { PageShell, PageHeader, Card, StatusBadge } from "@serviceos/design-system";
import {
  FIXTURE_TENANT_PROFILE, FIXTURE_PACKAGE_CREDIT, FIXTURE_SECURITY_DEPOSIT,
  FIXTURE_SERVICE_JOBS, FIXTURE_AUDIT_EVENTS,
} from "../../../../lib/ux03/fixtures";

export default function DashboardApproved() {
  return (
    <PageShell>
      <PageHeader title="Dashboard" description={`${FIXTURE_TENANT_PROFILE.displayName} — approved-business variant`} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px,1fr))", gap: "1rem" }}>
        <Card title="Business Snapshot">
          <p>{FIXTURE_TENANT_PROFILE.teamSize} team members · {FIXTURE_TENANT_PROFILE.serviceAreaCount} service areas</p>
        </Card>
        <Card title="Action Center">
          <p>1 parts request awaiting approval</p>
          <p>1 open complaint</p>
        </Card>
        <Card title="Operations Overview">
          <p>{FIXTURE_SERVICE_JOBS.filter(j => j.status === "in_progress").length} jobs in progress</p>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>Chart: jobs-by-status (recharts) — see dashboard-widget-inventory.csv</p>
        </Card>
        <Card title="Finance Overview">
          <p>Package credit: ₹{FIXTURE_PACKAGE_CREDIT.creditBalance.toLocaleString()}</p>
          <p>Commission rate: {(FIXTURE_PACKAGE_CREDIT.commissionRateBps / 100).toFixed(1)}%</p>
          <p>Security deposit: ₹{FIXTURE_SECURITY_DEPOSIT.heldAmount.toLocaleString()} <StatusBadge status={FIXTURE_SECURITY_DEPOSIT.status} /></p>
          <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Credit / commission / deposit are separate concepts — never a single balance.</p>
        </Card>
        <Card title="Business Health"><p>On-time completion 94% · avg rating 4.6</p></Card>
        <Card title="Recent Activity">
          {FIXTURE_AUDIT_EVENTS.map(a => <p key={a.id} style={{ fontSize: "0.8rem" }}>{a.actorName} {a.action}</p>)}
        </Card>
      </div>
    </PageShell>
  );
}
