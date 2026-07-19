import { PageShell, PageHeader, Card, PermissionDeniedState } from "@serviceos/design-system";
import { ReadinessTag } from "../../../../components/ux03/widgets/ReadinessTag";

export default function ReadOnlyRestricted() {
  return (
    <PageShell>
      <PageHeader title="Read-Only / Restricted Examples" description="Nav visibility is never an authorization boundary — these examples show UI-side read-only and permission-denied treatments only." />
      <Card title="Visible, read-only view">
        <p>Service Areas <ReadinessTag state="PRODUCT_DECISION_REQUIRED" /></p>
        <p style={{ color: "var(--text-secondary)" }}>Zone edit controls are disabled pending the frozen-slice geo-authorization decision.</p>
      </Card>
      <Card title="Permission denied (staff without a required override)">
        <PermissionDeniedState title="You don't have access to this section" description="Ask your business owner to grant the auth:permissions:manage permission." />
      </Card>
    </PageShell>
  );
}
