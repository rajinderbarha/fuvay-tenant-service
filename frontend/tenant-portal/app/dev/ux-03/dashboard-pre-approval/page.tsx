import { PageShell, PageHeader, Card } from "@serviceos/design-system";
import { ReviewStateBanner } from "../../../../components/ux03/widgets/ReviewStateBanner";
import { FIXTURE_TENANT_PROFILE } from "../../../../lib/ux03/fixtures";

export default function DashboardPreApproval() {
  const t = { ...FIXTURE_TENANT_PROFILE, reviewState: "in_progress" as const, completionPct: 55 };
  return (
    <PageShell>
      <PageHeader title="Dashboard" description="Pre-approval variant — shown before a tenant is approved." />
      <ReviewStateBanner state={t.reviewState} completionPct={t.completionPct} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px,1fr))", gap: "1rem" }}>
        <Card title="Profile Completion"><p>{t.completionPct}% complete — resume setup wizard.</p></Card>
        <Card title="Documents"><p>1 of 2 compliance documents submitted.</p></Card>
        <Card title="Package / Deposit Readiness"><p>Growth plan selected. Deposit not yet collected.</p></Card>
        <Card title="Review Status"><p>Not yet submitted for review.</p></Card>
      </div>
    </PageShell>
  );
}
