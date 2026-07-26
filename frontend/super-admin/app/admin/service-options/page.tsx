"use client";
import { AlertTriangle } from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Btn } from "../../../components/shared/ui";

/**
 * Retired (Job-Type Blueprint consolidation): the standalone Service Options
 * library page duplicated the Options & Add-ons tab inside the Job-Type
 * Blueprint (Catalog Workspace), and made a structural extra editable from
 * two disconnected places. Admin now attaches/configures options only
 * through the exact Job Type it applies to -- Catalog Workspace >
 * [Master Service] > [Job Type] > Options & Add-ons. Kept (not deleted) as
 * a clear retired-feature notice for anyone reaching it via a bookmarked or
 * typed URL; no longer linked from navigation. The backend ServiceOption /
 * ServiceOptionMapping models, tenant pricing, and customer/technician
 * selection runtime are all retained and unchanged -- only this duplicate
 * admin surface is retired.
 */
export default function ServiceOptionsRetiredPage() {
  return (
    <AdminLayout activeNav="hs-service-catalog">
      <Card style={{ maxWidth: 640, margin: "48px auto", padding: 32, textAlign: "center" }}>
        <AlertTriangle size={32} style={{ color: "var(--warning, #b45309)", marginBottom: 12 }} />
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>
          Service Options is retired as a standalone page
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", lineHeight: 1.6 }}>
          Options and add-ons are now configured only through the exact Job Type they apply to, in the
          Job-Type Blueprint's Options &amp; Add-ons tab. This avoids the same extra being editable from two
          disconnected places. Existing option mappings, tenant pricing and selections are unaffected.
        </p>
        <Btn onClick={() => { window.location.href = "/admin/catalog-workspace"; }}>
          Go to Catalog Workspace
        </Btn>
      </Card>
    </AdminLayout>
  );
}
