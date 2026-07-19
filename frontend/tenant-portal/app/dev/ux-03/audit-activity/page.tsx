"use client";
import { StatusBadge } from "@serviceos/design-system";
import { TenantListPage } from "../../../../components/ux03/patterns/TenantListPage";
import { FIXTURE_AUDIT_EVENTS } from "../../../../lib/ux03/fixtures";
import type { AuditEventFixture } from "../../../../lib/ux03/types";

export default function AuditActivity() {
  return (
    <TenantListPage<AuditEventFixture>
      title="Activity"
      description="Tenant-scoped only — never platform-wide events, other tenants' events, secrets, or tokens."
      rows={FIXTURE_AUDIT_EVENTS}
      rowKey={(a) => a.id}
      columns={[
        { key: "at", header: "When", render: (a) => new Date(a.at).toLocaleString() },
        { key: "actorName", header: "Actor", render: (a) => `${a.actorName} (${a.actorRole})` },
        { key: "action", header: "Action", accessor: (a) => a.action },
        { key: "result", header: "Result", render: (a) => <StatusBadge status={a.result === "success" ? "approved" : a.result === "denied" ? "rejected" : "failed"} /> },
      ]}
    />
  );
}
