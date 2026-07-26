"use client";
import { AlertTriangle } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Btn } from "../../../../components/shared/ui";

/**
 * Retired (business-model change): admin no longer sets service-level
 * min/max price boundaries ("Admin Minimum Price" / "Admin Maximum Price")
 * that providers were required to price inside. This platform is
 * provider-set-price, not admin-defined price boundaries — providers set
 * their own price entirely in tenant Service Setup. Kept (not deleted) as
 * a retired-feature notice for anyone reaching it via a bookmarked/typed
 * URL or an old cross-link; no longer linked from navigation. Backing API
 * writes (POST/PUT /v1/admin/pricing-rules) are NOT hardened to reject
 * writes the way Pricing Tiers/City-Zip Mapping are (still callable from
 * the separately-deprecated global /admin/pricing-rules screen) — a real,
 * documented gap, not claimed as closed.
 */
export default function HomeServicesPricingRulesRetiredPage() {
  return (
    <AdminLayout activeNav="hs-service-catalog">
      <Card style={{ maxWidth: 640, margin: "48px auto", padding: 32, textAlign: "center" }}>
        <AlertTriangle size={32} style={{ color: "var(--warning, #b45309)", marginBottom: 12 }} />
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>
          Home Services Pricing Rules is retired
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", lineHeight: 1.6 }}>
          Admin no longer sets min/max price boundaries for a service. Providers set their
          own price entirely — configure job types, dimensions, and workflow in the Catalog
          Workspace instead; pricing itself is set by the tenant in Service Setup.
        </p>
        <Btn onClick={() => { window.location.href = "/admin/catalog-workspace"; }}>
          Go to Catalog Workspace
        </Btn>
      </Card>
    </AdminLayout>
  );
}
