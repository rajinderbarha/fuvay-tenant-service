"use client";
import { StatusBadge } from "@serviceos/design-system";
import { TenantListPage } from "../../../../components/ux03/patterns/TenantListPage";
import { ReadinessTag } from "../../../../components/ux03/widgets/ReadinessTag";
import { FIXTURE_SERVICE_AREAS } from "../../../../lib/ux03/fixtures";
import type { ServiceAreaFixture } from "../../../../lib/ux03/types";

export default function ServiceAreas() {
  return (
    <TenantListPage<ServiceAreaFixture>
      title="Service Areas"
      description="Geo authorization is only closed for a frozen slice — mutation actions default to read-only/mock unless proven otherwise per row."
      rows={FIXTURE_SERVICE_AREAS}
      rowKey={(a) => a.id}
      columns={[
        { key: "city", header: "City / District", render: (a) => `${a.city} — ${a.district}` },
        { key: "zoneId", header: "Zone", accessor: (a) => a.zoneId },
        { key: "coverageStatus", header: "Coverage", render: (a) => <StatusBadge status={a.coverageStatus} /> },
        { key: "mutation", header: "Edit Readiness", render: (a) => <ReadinessTag state={a.mutationReadiness} /> },
      ]}
    />
  );
}
