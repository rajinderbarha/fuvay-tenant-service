"use client";
import { StatusBadge } from "@serviceos/design-system";
import { TenantListPage } from "../../../../components/ux03/patterns/TenantListPage";
import { PipelineBadge } from "../../../../components/ux03/widgets/PipelineBadge";
import { FIXTURE_BOOKINGS } from "../../../../lib/ux03/fixtures";
import type { BookingFixture } from "../../../../lib/ux03/types";

export default function BookingList() {
  return (
    <TenantListPage<BookingFixture>
      title="Bookings"
      description="Booking -> field_ops.Job pipeline — kept separate from the Job (ServiceJob) pipeline below. Customer cancel/reschedule for this pipeline is unresolved (mock only)."
      rows={FIXTURE_BOOKINGS}
      rowKey={(b) => b.id}
      columns={[
        { key: "pipeline", header: "Pipeline", render: (b) => <PipelineBadge pipeline={b.pipeline} canonicalId={b.canonicalId} /> },
        { key: "customerName", header: "Customer", accessor: (b) => b.customerName },
        { key: "serviceName", header: "Service", accessor: (b) => b.serviceName },
        { key: "status", header: "Status", render: (b) => <StatusBadge status={b.status} /> },
        { key: "scheduledAt", header: "Scheduled", render: (b) => new Date(b.scheduledAt).toLocaleString() },
      ]}
      emptyTitle="No bookings scheduled yet"
    />
  );
}
