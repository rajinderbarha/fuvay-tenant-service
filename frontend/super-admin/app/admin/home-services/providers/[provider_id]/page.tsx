"use client";
/**
 * Home Services Provider 360° — dedicated detail page for a single provider.
 *
 * The actual workspace UI lives in components/directory/ProviderDetailWorkspace
 * so the SAME design + URL shape can be reused at the generic per-vertical
 * route (/admin/[vertical]/providers/[id]) once other verticals get their
 * own backend directory service — see that route's own honest-gap message
 * for why only Home Services works today. Nothing here duplicates that file.
 * Previous (pre-rebuild) version preserved at ../_legacy/provider-detail-v1.page.tsx.bak.
 */
import { Suspense } from "react";
import { useParams } from "next/navigation";
import { Skeleton } from "../../../../../components/shared/ui";
import { ProviderDetailWorkspace } from "../../../../../components/directory/ProviderDetailWorkspace";

export default function ProviderDetailPage() {
  return (
    <Suspense fallback={<Skeleton height={400} />}>
      <Inner />
    </Suspense>
  );
}

function Inner() {
  const params = useParams();
  const providerId = String(params.provider_id);
  return (
    <ProviderDetailWorkspace
      providerId={providerId}
      basePath="/admin/home-services/providers"
      breadcrumbVertical="Home Services"
    />
  );
}
