import { PageShell } from "@serviceos/design-system";
import { ReviewStateBanner } from "../../../../components/ux03/widgets/ReviewStateBanner";
import { FIXTURE_TENANT_PROFILE } from "../../../../lib/ux03/fixtures";

export default function ProfileChangesRequested() {
  const t = FIXTURE_TENANT_PROFILE;
  return (
    <PageShell>
      <ReviewStateBanner state="changes_requested" completionPct={t.completionPct} changesRequested={t.changesRequested} />
    </PageShell>
  );
}
