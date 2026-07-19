import { PageShell, Card } from "@serviceos/design-system";
import { ReviewStateBanner } from "../../../../components/ux03/widgets/ReviewStateBanner";
import { FIXTURE_TENANT_PROFILE } from "../../../../lib/ux03/fixtures";

export default function ProfileUnderReview() {
  const t = FIXTURE_TENANT_PROFILE;
  return (
    <PageShell>
      <ReviewStateBanner state="under_review" completionPct={100} />
      <Card title="Business Info"><p>{t.legalName} · {t.categories.join(", ")}</p></Card>
      <Card title="Registration / Tax"><p>Reg no. {t.registrationNumber} · Tax ID {t.taxId}</p></Card>
      <Card title="Addresses">{t.addresses.map(a => <p key={a.id}>{a.line1}, {a.city}, {a.region} {a.postalCode}</p>)}</Card>
    </PageShell>
  );
}
