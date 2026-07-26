"use client";
import { AlertTriangle } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Btn } from "../../../../components/shared/ui";

/**
 * Retired (MODULE-L5-57): this page was an admin-editable Customer Price
 * Experience simulator built entirely around Admin Allowed Min/Max/Base
 * Price -- the same retired "admin sets the price boundary" paradigm
 * already locked out of Master Service and Service Option edits. Its one
 * compute action (`POST .../price-experience/preview`) was already removed
 * backend-side by earlier work; this page had been silently broken (404 on
 * Preview) with zero real save path. Super Admin does not own service price
 * amounts -- Low/Mid/High preview now lives where the tenant's own price
 * actually is: Tenant Service Setup's Coverage & Pricing step and its
 * Customer Price Preview page, both backed by the same canonical
 * TenantCatalogService.resolve_tenant_price resolver real bookings use.
 * Kept (not deleted) as a clear retired-feature notice for anyone reaching
 * it via a bookmarked or typed URL; no longer linked from navigation.
 */
export default function CustomerPriceExperienceRetiredPage() {
  return (
    <AdminLayout activeNav="hs-service-catalog">
      <Card style={{ maxWidth: 640, margin: "48px auto", padding: 32, textAlign: "center" }}>
        <AlertTriangle size={32} style={{ color: "var(--warning, #b45309)", marginBottom: 12 }} />
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>
          Customer Price Experience is retired
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", lineHeight: 1.6 }}>
          Super Admin does not set or preview service prices. Each tenant configures and previews their own
          customer-facing price in their Service Setup wizard, using the same calculation the real customer
          booking flow uses.
        </p>
        <Btn onClick={() => { window.location.href = "/admin/catalog-workspace"; }}>
          Go to Catalog Workspace
        </Btn>
      </Card>
    </AdminLayout>
  );
}
