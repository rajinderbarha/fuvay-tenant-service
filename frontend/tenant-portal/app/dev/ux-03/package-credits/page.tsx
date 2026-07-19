import { PageShell, PageHeader, Card } from "@serviceos/design-system";
import { FIXTURE_PACKAGE_CREDIT, FIXTURE_SECURITY_DEPOSIT } from "../../../../lib/ux03/fixtures";

export default function PackageCredits() {
  const c = FIXTURE_PACKAGE_CREDIT;
  return (
    <PageShell>
      <PageHeader title="Package & Credits" description="Package credit, commission, and security deposit are three separate concepts — never a single balance, never a payout/withdrawal action (the platform does not process on-site job payments)." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px,1fr))", gap: "1rem" }}>
        <Card title="Package Plan"><p>{c.planName}</p></Card>
        <Card title="Credit Balance"><p>₹{c.creditBalance.toLocaleString()}</p><p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Issued this cycle: ₹{c.creditIssuedThisCycle.toLocaleString()} · Consumed: ₹{c.creditConsumedThisCycle.toLocaleString()}</p></Card>
        <Card title="Commission Rate"><p>{(c.commissionRateBps / 100).toFixed(1)}% — deducted from credit balance on job completion</p></Card>
        <Card title="Security Deposit (separate)"><p>₹{FIXTURE_SECURITY_DEPOSIT.heldAmount.toLocaleString()} held</p></Card>
      </div>
    </PageShell>
  );
}
