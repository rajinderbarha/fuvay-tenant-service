"use client";
import { AlertTriangle } from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Btn } from "../../../components/shared/ui";

/**
 * Retired (business-model change): admin no longer maps cities/zipcodes to
 * a pricing tier. Tenants now select the cities/zipcodes they want to serve
 * and submit them for admin approval — see /admin/service-area-requests.
 * Kept (not deleted) as a retired-feature notice, unlinked from navigation.
 * Backing API writes (/v1/admin/catalog/tier-locations*) now return 410
 * PRICING_TIER_WRITES_RETIRED; reads remain available for historical data.
 */
export default function LocationMappingRetiredPage() {
  return (
    <AdminLayout activeNav="verticals">
      <Card style={{ maxWidth: 640, margin: "48px auto", padding: 32, textAlign: "center" }}>
        <AlertTriangle size={32} style={{ color: "var(--warning, #b45309)", marginBottom: 12 }} />
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>
          City/Zipcode → Tier Mapping is retired
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", lineHeight: 1.6 }}>
          Admin no longer creates global city/zipcode-to-tier mappings. Tenants now
          select their own service areas and submit them for admin review and
          approval. Existing mapping data is preserved for historical reference only.
        </p>
        <Btn onClick={() => { window.location.href = "/admin/service-area-requests"; }}>
          Go to Service Area Requests
        </Btn>
      </Card>
    </AdminLayout>
  );
}
