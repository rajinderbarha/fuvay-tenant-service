"use client";
// Replaced by the consolidated 9-tab workspace at /admin/home-services/finance
// (Overview, Provider Charges, Credits & Top-ups, Security Deposits,
// Invoices, Customer Refunds, Warranty Claims, Financial Events). Kept as a
// redirect-only stub so old links/bookmarks still resolve.
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card } from "../../../../components/shared/ui";

export default function HomeServicesFinanceRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin/home-services/finance");
  }, [router]);
  return (
    <AdminLayout activeNav="hs-finance">
      <Card style={{ maxWidth: 480, margin: "48px auto", padding: 32, textAlign: "center" }}>
        <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>Redirecting…</p>
      </Card>
    </AdminLayout>
  );
}
