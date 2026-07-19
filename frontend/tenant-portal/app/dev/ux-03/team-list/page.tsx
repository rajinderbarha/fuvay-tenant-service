"use client";
import { StatusBadge } from "@serviceos/design-system";
import { TenantListPage } from "../../../../components/ux03/patterns/TenantListPage";
import { FIXTURE_TEAM_MEMBERS } from "../../../../lib/ux03/fixtures";
import type { TeamMemberFixture } from "../../../../lib/ux03/types";
import Link from "next/link";

export default function TeamList() {
  return (
    <TenantListPage<TeamMemberFixture>
      title="Team Members"
      description="All members: owner, staff, technicians, invitations."
      searchable
      searchPredicate={(m, q) => m.name.toLowerCase().includes(q) || m.jobTitle.toLowerCase().includes(q)}
      rows={FIXTURE_TEAM_MEMBERS}
      rowKey={(m) => m.id}
      columns={[
        { key: "name", header: "Name", accessor: (m) => m.name, render: (m) => <Link href={`/dev/ux-03/team-${m.role === "technician" ? "technician" : "staff"}-detail`}>{m.name}</Link> },
        { key: "role", header: "Role", render: (m) => m.role },
        { key: "jobTitle", header: "Title (descriptive only)", render: (m) => m.jobTitle },
        { key: "status", header: "Status", render: (m) => <StatusBadge status={m.status} /> },
      ]}
      emptyTitle="No team members yet"
    />
  );
}
