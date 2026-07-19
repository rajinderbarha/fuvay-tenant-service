"use client";
import { TenantListPage } from "../../../../components/ux03/patterns/TenantListPage";
import { FIXTURE_PRICING } from "../../../../lib/ux03/fixtures";
import type { PricingFixture } from "../../../../lib/ux03/types";

export default function Pricing() {
  return (
    <TenantListPage<PricingFixture>
      title="Pricing"
      description="Platform min/max always visible; tenant price below platform minimum is flagged."
      rows={FIXTURE_PRICING}
      rowKey={(p) => p.serviceId}
      columns={[
        { key: "serviceName", header: "Service", accessor: (p) => p.serviceName },
        { key: "jobType", header: "Job Type", accessor: (p) => p.jobType },
        { key: "platform", header: "Platform Min–Max", render: (p) => `₹${p.platformMinPrice} – ₹${p.platformMaxPrice}` },
        { key: "tenantPrice", header: "Tenant Price", render: (p) => (
          <span style={{ color: p.belowPlatformMin ? "var(--danger-text)" : undefined }}>
            ₹{p.tenantPrice}{p.belowPlatformMin ? " (below platform minimum)" : ""}
          </span>
        ) },
        { key: "effective", header: "Effective Preview", render: (p) => `₹${p.effectivePricePreview}` },
      ]}
    />
  );
}
