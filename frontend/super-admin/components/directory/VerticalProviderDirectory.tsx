"use client";
import React, { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { VerticalDirectoryShell, StatusBadge } from "./VerticalDirectoryShell";
import { verticalDirectoryApi } from "../../lib/api";
import { useApi } from "../../hooks/useApi";

// VERTICAL-DIRECTORY-FRAMEWORK: reused verbatim for every Business
// Vertical -- `vertical` (URL slug, e.g. "home-services") is the only
// thing that changes between call sites. Row click always goes to the
// SAME generic detail URL shape (/admin/{vertical}/providers/{id}) --
// only Home Services has a real 360 backend today (see the detail page's
// own honest-gap message for every other vertical), but the URL pattern
// itself doesn't change once that backend exists for other verticals.
export function VerticalProviderDirectory({ vertical, verticalLabel }: { vertical: string; verticalLabel: string }) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const listApi = useApi(useCallback(() => verticalDirectoryApi.listProviders(vertical, { search: search || undefined, page_size: 25 }), [vertical, search]));
  const summaryApi = useApi(useCallback(() => verticalDirectoryApi.providersSummary(vertical), [vertical]));
  const rows = (listApi.data?.items ?? []) as Record<string, unknown>[];
  const s = summaryApi.data as Record<string, number> | null;

  return (
    <VerticalDirectoryShell
      verticalLabel={`${verticalLabel} / Providers`}
      domainTitle={`${verticalLabel} Providers`}
      description={`Businesses registered to provide ${verticalLabel}.`}
      metrics={[
        { label: "Total Providers", value: s?.total_providers },
        { label: "Pending Verification", value: s?.pending_verification },
        { label: "Active", value: s?.active },
        { label: "Suspended", value: s?.suspended },
      ]}
      search={search} onSearchChange={setSearch}
      loading={listApi.loading} error={listApi.error} onRetry={listApi.refetch}
      rows={rows} rowKey={r => r.tenant_id as string}
      onRowClick={r => router.push(`/admin/${vertical}/providers/${r.tenant_id}`)}
      columns={[
        { key: "business_name", label: "Provider / Business", render: r => <span style={{ fontWeight: 600 }}>{r.business_name as string}</span> },
        { key: "registration_status", label: "Registration", render: r => <StatusBadge value={r.registration_status as string}/> },
        { key: "verification_status", label: "Verification", render: r => r.verification_status as string },
        { key: "vertical_status", label: "Vertical Status", render: r => r.vertical_status as string },
      ]}
    />
  );
}
