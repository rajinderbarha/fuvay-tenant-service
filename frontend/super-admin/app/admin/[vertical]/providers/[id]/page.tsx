"use client";
/**
 * Generic per-vertical provider detail — same URL shape and design for
 * every Business Vertical (/admin/{vertical}/providers/{id}), reusing the
 * exact ProviderDetailWorkspace component the dedicated Home Services route
 * mounts. Only Home Services has a real 360 backend today
 * (HomeServicesProviderDirectoryService) -- every other vertical shows an
 * honest "not built yet" card instead of mounting the workspace against
 * data that doesn't exist, so this route can never silently show wrong or
 * fabricated data for a vertical it doesn't actually support.
 */
import { Suspense } from "react";
import { useParams } from "next/navigation";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Card, Btn, Skeleton } from "../../../../../components/shared/ui";
import { ProviderDetailWorkspace } from "../../../../../components/directory/ProviderDetailWorkspace";

const SUPPORTED_VERTICALS = new Set(["home-services", "home_services"]);

export default function GenericVerticalProviderDetailPage() {
  return (
    <Suspense fallback={<Skeleton height={400} />}>
      <Inner />
    </Suspense>
  );
}

function Inner() {
  const params = useParams();
  const vertical = String(params.vertical);
  const providerId = String(params.id);

  if (!SUPPORTED_VERTICALS.has(vertical)) {
    const label = vertical.replace(/[-_]/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    return (
      <AdminLayout>
        <Card padding={24}>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 8px" }}>Provider 360° isn&apos;t built for {label} yet</h2>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>
            Only Home Services has a dedicated provider directory backend today. This page will use the
            same design shown for Home Services providers once {label} gets its own directory service —
            nothing here fabricates data for a vertical that doesn&apos;t have it yet.
          </p>
          <Btn variant="ghost" onClick={() => history.back()}>Back</Btn>
        </Card>
      </AdminLayout>
    );
  }

  return (
    <ProviderDetailWorkspace
      providerId={providerId}
      basePath={`/admin/${vertical}/providers`}
      breadcrumbVertical="Home Services"
    />
  );
}
