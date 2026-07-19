"use client";
import Link from "next/link";
import { PageShell } from "@serviceos/design-system";
import { StatusBadge } from "@serviceos/design-system";
import { EnterpriseListPage } from "../../../../components/ux02/patterns/EnterpriseListPage";
import { FIXTURE_TENANTS } from "../../../../lib/ux02/fixtures";
import type { TenantFixture } from "../../../../lib/ux02/types";

export default function TenantListShowcase() {
  return (
    <PageShell>
      <EnterpriseListPage<TenantFixture>
        title="Tenants"
        description="All tenants across verticals. READ_ONLY_READY against admin_catalog/tenant_service; actions below are design-only."
        readiness="READ_ONLY_READY"
        rows={FIXTURE_TENANTS}
        rowKey={(t) => t.id}
        searchFields={(t) => `${t.displayName} ${t.ownerName} ${t.city}`}
        filters={[
          { key: "vertical", label: "Vertical", values: ["home_services", "real_estate", "coaching"] },
          { key: "status", label: "Status", values: ["active", "suspended", "pending_verification", "onboarding", "deactivated"] },
        ]}
        getFilterValue={(t, key) => (t as any)[key]}
        bulkActions={[{ key: "suspend", label: "Suspend selected" }, { key: "export", label: "Export selected" }]}
        columns={[
          { key: "displayName", header: "Tenant", sortable: true, accessor: (t) => t.displayName, render: (t) => <Link href={`/dev/ux-02/tenants/${t.id}`}>{t.displayName}</Link> },
          { key: "vertical", header: "Vertical", accessor: (t) => t.vertical },
          { key: "status", header: "Status", render: (t) => <StatusBadge status={t.status} /> },
          { key: "plan", header: "Plan", accessor: (t) => t.planPackage },
          { key: "credit", header: "Package Credit", align: "right", accessor: (t) => t.packageCreditBalance, render: (t) => `$${t.packageCreditBalance.toLocaleString()}` },
          { key: "risk", header: "Risk", render: (t) => <StatusBadge status={t.riskScore} variant="dot" /> },
          { key: "city", header: "City", accessor: (t) => `${t.city}, ${t.region}` },
        ]}
        mobileCard={(t) => (
          <div style={{ padding: "0.75rem", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <Link href={`/dev/ux-02/tenants/${t.id}`}>{t.displayName}</Link>
              <StatusBadge status={t.status} size="sm" />
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>{t.city}, {t.region} · {t.planPackage}</div>
          </div>
        )}
      />
    </PageShell>
  );
}
