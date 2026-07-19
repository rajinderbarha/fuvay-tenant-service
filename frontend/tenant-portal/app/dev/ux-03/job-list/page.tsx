"use client";
import { StatusBadge } from "@serviceos/design-system";
import { TenantListPage } from "../../../../components/ux03/patterns/TenantListPage";
import { PipelineBadge } from "../../../../components/ux03/widgets/PipelineBadge";
import { FIXTURE_SERVICE_JOBS } from "../../../../lib/ux03/fixtures";
import type { ServiceJobFixture } from "../../../../lib/ux03/types";
import Link from "next/link";

export default function JobList() {
  return (
    <TenantListPage<ServiceJobFixture>
      title="Jobs"
      description="ServiceBooking -> ServiceJob pipeline — distinct from the Booking (field_ops.Job) pipeline above."
      rows={FIXTURE_SERVICE_JOBS}
      rowKey={(j) => j.id}
      columns={[
        { key: "pipeline", header: "Pipeline", render: (j) => <PipelineBadge pipeline={j.pipeline} canonicalId={j.canonicalId} /> },
        { key: "customerName", header: "Customer", render: (j) => <Link href="/dev/ux-03/job-detail">{j.customerName}</Link> },
        { key: "serviceName", header: "Service", accessor: (j) => j.serviceName },
        { key: "status", header: "Status", render: (j) => <StatusBadge status={j.status} /> },
      ]}
      emptyTitle="No jobs assigned yet"
    />
  );
}
