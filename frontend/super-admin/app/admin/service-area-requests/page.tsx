"use client";

/**
 * Service Area Requests — the admin review queue for provider coverage
 * expansion. Dashboard opportunity links include city/zipcode, so those URL
 * filters are authoritative and are forwarded to the backend item query.
 */
import { TableSurface } from "@serviceos/design-system";
import React, { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Badge, Btn, Card, Input, Pagination, SectionHeader, Select, Skeleton, Spinner,
} from "../../../components/shared/ui";
import { RequirePermission } from "../../../components/shared/PermissionGate";
import { useApi } from "../../../hooks/useApi";
import { serviceAreaRequestAdminApi } from "../../../lib/api";

const PAGE_SIZE = 25;
const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "SUBMITTED", label: "Submitted" },
  { value: "UNDER_REVIEW", label: "Under Review" },
  { value: "CHANGES_REQUESTED", label: "Changes Requested" },
  { value: "PARTIALLY_APPROVED", label: "Partially Approved" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "WITHDRAWN", label: "Withdrawn" },
];

function statusVariant(status: string): "success" | "warning" | "danger" | "default" {
  if (status === "APPROVED") return "success";
  if (status === "REJECTED" || status === "WITHDRAWN") return "danger";
  if (status === "PARTIALLY_APPROVED" || status === "CHANGES_REQUESTED") return "warning";
  return "default";
}

function readableStatus(status: string) {
  return status.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}

function formatDate(value?: string | null) {
  return value
    ? new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
    : "—";
}

function compactList(values?: string[], fallback = "—") {
  if (!values?.length) return fallback;
  if (values.length <= 2) return values.join(", ");
  return `${values.slice(0, 2).join(", ")} +${values.length - 2}`;
}

export default function ServiceAreaRequestsPage() {
  return (
    <Suspense fallback={<AdminLayout activeNav="verticals"><Skeleton height={420} /></AdminLayout>}>
      <ServiceAreaRequestsWorkspace />
    </Suspense>
  );
}

function ServiceAreaRequestsWorkspace() {
  const router = useRouter();
  const params = useSearchParams();
  const status = params.get("status") || "";
  const tenantId = params.get("tenant_id") || "";
  const city = params.get("city") || "";
  const zipcode = params.get("zipcode") || "";
  const page = Math.max(1, Number(params.get("page") || "1") || 1);

  const [statusInput, setStatusInput] = useState(status);
  const [tenantInput, setTenantInput] = useState(tenantId);
  const [cityInput, setCityInput] = useState(city);
  const [zipcodeInput, setZipcodeInput] = useState(zipcode);

  useEffect(() => {
    setStatusInput(status);
    setTenantInput(tenantId);
    setCityInput(city);
    setZipcodeInput(zipcode);
  }, [status, tenantId, city, zipcode]);

  const requests = useApi(useCallback(
    () => serviceAreaRequestAdminApi.list({
      status_filter: status || undefined,
      tenant_id: tenantId || undefined,
      city: city || undefined,
      zipcode: zipcode || undefined,
      limit: PAGE_SIZE,
      cursor: String((page - 1) * PAGE_SIZE),
    }),
    [status, tenantId, city, zipcode, page],
  ), [status, tenantId, city, zipcode, page]);

  function replaceQuery(next: Record<string, string | number | undefined>) {
    const query = new URLSearchParams(params.toString());
    query.set("view", "requests");
    Object.entries(next).forEach(([key, value]) => {
      if (value === undefined || value === "") query.delete(key);
      else query.set(key, String(value));
    });
    router.replace(`/admin/service-area-requests?${query.toString()}`);
  }

  function applyFilters() {
    replaceQuery({
      status: statusInput,
      tenant_id: tenantInput.trim(),
      city: cityInput.trim(),
      zipcode: zipcodeInput.trim(),
      page: 1,
    });
  }

  function clearFilters() {
    setStatusInput("");
    setTenantInput("");
    setCityInput("");
    setZipcodeInput("");
    router.replace("/admin/service-area-requests?view=requests");
  }

  const rows = requests.data?.requests ?? [];
  const locationContext = [city, zipcode].filter(Boolean).join(" · ");

  return (
    <AdminLayout activeNav="verticals">
      <RequirePermission requiredPermission="platform:admin" parentLabel="Service Area Requests">
        <SectionHeader
          title="Service Area Requests"
          subtitle="Review provider requests to expand service coverage. Location filters from Demand Intelligence are preserved on this page."
        />

        {locationContext && (
          <Card style={{ marginBottom: 12, padding: "12px 16px", borderColor: "var(--brand)" }}>
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Demand opportunity</div>
            <div style={{ marginTop: 3, fontSize: 15, fontWeight: 700 }}>{locationContext}</div>
            <div style={{ marginTop: 3, fontSize: 12, color: "var(--text-tertiary)" }}>
              Showing only provider coverage requests containing this location.
            </div>
          </Card>
        )}

        <Card style={{ marginBottom: 16, padding: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, alignItems: "end" }}>
            <div>
              <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Status</label>
              <Select value={statusInput} onChange={setStatusInput} options={STATUS_OPTIONS} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Provider / Tenant ID</label>
              <Input value={tenantInput} onChange={setTenantInput} placeholder="Tenant UUID" />
            </div>
            <div>
              <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>City</label>
              <Input value={cityInput} onChange={setCityInput} placeholder="e.g. Bassi Pathana" />
            </div>
            <div>
              <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Pincode</label>
              <Input value={zipcodeInput} onChange={setZipcodeInput} placeholder="6-digit pincode" />
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={clearFilters}>Clear</Btn>
            <Btn variant="secondary" onClick={() => requests.refetch()}>Refresh</Btn>
            <Btn onClick={applyFilters}>Apply filters</Btn>
          </div>
        </Card>

        {requests.loading ? <Spinner /> : requests.error ? (
          <Card><p style={{ color: "var(--danger)" }}>{requests.error}</p></Card>
        ) : rows.length === 0 ? (
          <Card style={{ padding: 32, textAlign: "center" }}>
            <strong style={{ display: "block", marginBottom: 6 }}>
              {locationContext ? `No coverage requests for ${locationContext}` : "No service area requests found"}
            </strong>
            <span style={{ color: "var(--text-secondary)", fontSize: 13 }}>
              {locationContext
                ? "Demand exists here, but no provider has submitted a matching coverage-expansion request yet."
                : "Provider-submitted coverage requests will appear here for review."}
            </span>
          </Card>
        ) : (
          <>
            <Card padding={0}>
              <div style={{ overflowX: "auto" }}>
                <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                  <thead>
                    <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                      <th style={{ padding: "12px 16px" }}>Provider</th>
                      <th style={{ padding: "12px 16px" }}>Requested location</th>
                      <th style={{ padding: "12px 16px" }}>Services</th>
                      <th style={{ padding: "12px 16px" }}>Status</th>
                      <th style={{ padding: "12px 16px" }}>Submitted</th>
                      <th style={{ padding: "12px 16px" }}>Review</th>
                      <th style={{ padding: "12px 16px" }} />
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(request => (
                      <tr key={request.id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "12px 16px" }}>
                          <div style={{ fontWeight: 700 }}>{request.tenant_name || "Service provider"}</div>
                          <div style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)", marginTop: 3 }}>
                            {request.tenant_id.slice(0, 8)} · {request.category_name || "Home Services"}
                          </div>
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          <div style={{ fontWeight: 600 }}>{compactList(request.cities, "City not supplied")}</div>
                          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 3 }}>
                            {compactList(request.zipcodes, "City-wide coverage")}
                          </div>
                        </td>
                        <td style={{ padding: "12px 16px", maxWidth: 260 }}>
                          <div>{compactList(request.service_names, "Service details unavailable")}</div>
                          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 3 }}>
                            {request.item_count ?? 0} item{request.item_count === 1 ? "" : "s"}
                            {(request.pending_item_count ?? 0) > 0 ? ` · ${request.pending_item_count} pending` : ""}
                          </div>
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          <Badge variant={statusVariant(request.status)}>{readableStatus(request.status)}</Badge>
                        </td>
                        <td style={{ padding: "12px 16px" }}>{formatDate(request.submitted_at)}</td>
                        <td style={{ padding: "12px 16px" }}>{formatDate(request.reviewed_at)}</td>
                        <td style={{ padding: "12px 16px", textAlign: "right" }}>
                          <Btn variant="ghost" onClick={() => router.push(`/admin/service-area-requests/${request.id}`)}>
                            Review
                          </Btn>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </TableSurface>
              </div>
            </Card>
            <div style={{ marginTop: 14 }}>
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={requests.data?.total ?? 0}
                onPage={nextPage => replaceQuery({ page: nextPage })}
                itemLabel="requests"
              />
            </div>
          </>
        )}
      </RequirePermission>
    </AdminLayout>
  );
}
