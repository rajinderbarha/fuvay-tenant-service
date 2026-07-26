"use client";
import { AlertTriangle } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Btn } from "../../../../components/shared/ui";

/**
 * Retired along with /admin/service-options (see that page's comment) --
 * option detail/editing now happens only through the exact Job Type it is
 * mapped to, in the Job-Type Blueprint's Options & Add-ons tab.
 */
export default function ServiceOptionDetailRetiredPage() {
  return (
    <AdminLayout activeNav="hs-service-catalog">
      <Card style={{ maxWidth: 640, margin: "48px auto", padding: 32, textAlign: "center" }}>
        <AlertTriangle size={32} style={{ color: "var(--warning, #b45309)", marginBottom: 12 }} />
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>
          Service Option detail is retired as a standalone page
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", lineHeight: 1.6 }}>
          Configure this option through the exact Job Type it applies to, in the Job-Type Blueprint's
          Options &amp; Add-ons tab.
        </p>
        <Btn onClick={() => { window.location.href = "/admin/catalog-workspace"; }}>
          Go to Catalog Workspace
        </Btn>
      </Card>
    </AdminLayout>
  );
}
