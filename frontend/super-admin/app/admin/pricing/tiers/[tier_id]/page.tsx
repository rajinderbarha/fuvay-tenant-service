"use client";
import { AlertTriangle } from "lucide-react";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Card, Btn } from "../../../../../components/shared/ui";

/**
 * Retired (business-model change) — see /admin/pricing-tiers for the full
 * notice. Kept (not deleted) as a retired-feature notice, unlinked from
 * navigation. Backing API writes now return 410 PRICING_TIER_WRITES_RETIRED;
 * reads remain available for historical data.
 */
export default function PricingTierDetailRetiredPage() {
  return (
    <AdminLayout activeNav="verticals">
      <Card style={{ maxWidth: 640, margin: "48px auto", padding: 32, textAlign: "center" }}>
        <AlertTriangle size={32} style={{ color: "var(--warning, #b45309)", marginBottom: 12 }} />
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>
          Pricing Tiers is retired
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", lineHeight: 1.6 }}>
          This tier detail page is retired along with Pricing Tiers. Existing tier data
          is preserved for historical reference only.
        </p>
        <Btn onClick={() => { window.location.href = "/admin/service-area-requests"; }}>
          Go to Service Area Requests
        </Btn>
      </Card>
    </AdminLayout>
  );
}
