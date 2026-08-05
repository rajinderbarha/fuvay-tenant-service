"use client";
import React, { useCallback, useState } from "react";
import { VerticalDirectoryShell } from "./VerticalDirectoryShell";
import { verticalDirectoryApi } from "../../lib/api";
import { useApi } from "../../hooks/useApi";

export function VerticalCustomerDirectory({ vertical, verticalLabel }: { vertical: string; verticalLabel: string }) {
  const [search, setSearch] = useState("");
  const listApi = useApi(useCallback(() => verticalDirectoryApi.listCustomers(vertical, { search: search || undefined, page_size: 25 }), [vertical, search]));
  const summaryApi = useApi(useCallback(() => verticalDirectoryApi.customersSummary(vertical), [vertical]));
  const rows = (listApi.data?.items ?? []) as Record<string, unknown>[];
  const s = summaryApi.data as Record<string, number> | null;

  return (
    <VerticalDirectoryShell
      verticalLabel={`${verticalLabel} / Customers`}
      domainTitle={`${verticalLabel} Customers`}
      description={`Customers with verified activity in ${verticalLabel}.`}
      metrics={[
        { label: "Total Customers", value: s?.total_customers },
        { label: "Active Customers", value: s?.active_customers },
      ]}
      search={search} onSearchChange={setSearch}
      loading={listApi.loading} error={listApi.error} onRetry={listApi.refetch}
      rows={rows} rowKey={r => r.customer_id as string}
      columns={[
        { key: "full_name", label: "Customer", render: r => <span style={{ fontWeight: 600 }}>{r.full_name as string}</span> },
        { key: "first_activity_at", label: "First Activity", render: r => new Date(r.first_activity_at as string).toLocaleDateString() },
        { key: "last_activity_at", label: "Last Activity", render: r => new Date(r.last_activity_at as string).toLocaleDateString() },
        { key: "booking_count", label: "Bookings", render: r => String(r.booking_count) },
      ]}
    />
  );
}
