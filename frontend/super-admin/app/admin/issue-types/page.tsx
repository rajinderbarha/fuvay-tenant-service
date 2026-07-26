"use client";
import { AlertTriangle } from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Btn } from "../../../components/shared/ui";

/**
 * Retired (Job-Type Blueprint consolidation): this page managed the older,
 * category/global-scoped MasterIssueType + ServiceIssueMapping list outside
 * the Job-Type Blueprint context. Problems and Questions are now configured
 * only for an exact Job Type, in the Job-Type Blueprint's Problems &
 * Questions tab (Catalog Workspace) -- a category-only mapping must never
 * activate a problem at runtime. Kept (not deleted) as a clear
 * retired-feature notice for anyone reaching it via a bookmarked or typed
 * URL; no longer linked from navigation. Backend issue/problem/question
 * models and runtime resolution are retained and unchanged.
 */
export default function IssueTypesRetiredPage() {
  return (
    <AdminLayout activeNav="hs-service-catalog">
      <Card style={{ maxWidth: 640, margin: "48px auto", padding: 32, textAlign: "center" }}>
        <AlertTriangle size={32} style={{ color: "var(--warning, #b45309)", marginBottom: 12 }} />
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>
          Issue Types is retired as a standalone page
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", lineHeight: 1.6 }}>
          Problems and Questions are now configured only for the exact Job Type they apply to, in the
          Job-Type Blueprint's Problems &amp; Questions tab. A category-only mapping can never activate a
          problem at runtime. Existing issue/problem/question data is unaffected.
        </p>
        <Btn onClick={() => { window.location.href = "/admin/catalog-workspace"; }}>
          Go to Catalog Workspace
        </Btn>
      </Card>
    </AdminLayout>
  );
}
