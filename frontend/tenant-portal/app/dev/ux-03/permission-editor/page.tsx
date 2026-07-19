"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { PermissionEditor } from "../../../../components/ux03/widgets/PermissionEditor";
import { FIXTURE_TEAM_MEMBERS } from "../../../../lib/ux03/fixtures";

export default function PermissionEditorShowcase() {
  const member = FIXTURE_TEAM_MEMBERS.find((m) => m.id === "tech_3")!;
  return (
    <PageShell>
      <PageHeader title={`Permissions — ${member.name}`} description="Deny is visually distinct from not-granted; a grant never overrides an explicit deny." />
      <PermissionEditor permissions={member.permissions} onToggle={() => {}} />
    </PageShell>
  );
}
