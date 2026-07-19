import { PageShell } from "@serviceos/design-system";
import { TeamMemberDetail } from "../../../../components/ux03/widgets/TeamMemberDetail";
import { FIXTURE_TEAM_MEMBERS } from "../../../../lib/ux03/fixtures";

export default function TeamStaffDetail() {
  const member = FIXTURE_TEAM_MEMBERS.find((m) => m.id === "staff_2")!;
  return (
    <PageShell>
      <TeamMemberDetail member={member} />
    </PageShell>
  );
}
