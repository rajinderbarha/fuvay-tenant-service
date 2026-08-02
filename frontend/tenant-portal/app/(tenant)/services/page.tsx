"use client";
import React, { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import {
  SectionHeader, Btn, Badge, DataTable, EmptyState, Input,
} from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { serviceSetupApi, type TenantEnabledService, type AdminMasterServiceRow } from "../../../lib/api";
import { Boxes, Plus, Search, Wrench } from "lucide-react";

// Setup status -> badge variant. Real statuses returned by the backend
// (TenantService.setup_status is "draft"|"published" today; is_enabled/
// is_active layer on top). Kept as a lookup, not scattered conditionals.
const STATUS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger" | "info"> = {
  published: "success", draft: "warning",
};
function statusLabel(svc: TenantEnabledService): string {
  if (!svc.is_active) return "Archived";
  if (!svc.is_enabled) return "Suspended";
  if (svc.setup_status === "published") return "Published";
  return "Draft";
}

export default function ServicesLandingPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  const enabledRes = useApi(useCallback(() => serviceSetupApi.listEnabledServices(), []), []);
  const availableRes = useApi(useCallback(() => serviceSetupApi.listAvailableServices(), []), []);

  const services = enabledRes.data?.services ?? [];
  const availableCount = (availableRes.data?.services ?? []).filter(
    (s: AdminMasterServiceRow) => !s.is_enabled,
  ).length;

  const filtered = useMemo(() => {
    return services.filter(s => {
      if (statusFilter && statusLabel(s) !== statusFilter) return false;
      if (search && !(s.tenant_display_name ?? "").toLowerCase().includes(search.toLowerCase())
          && !s.master_service_id.includes(search)) return false;
      return true;
    });
  }, [services, search, statusFilter]);

  const publishedCount = services.filter(s => s.setup_status === "published").length;

  return (
    <TenantLayout activeNav="services">
      <div style={{ maxWidth: 1200 }}>
        <SectionHeader
          title="Services"
          subtitle="Set up the services you offer, one job type at a time. Coverage and pricing are entirely yours to configure."
          icon={<Boxes />}
          actions={
            <Btn icon={<Plus size={14} />} onClick={() => router.push("/services/setup/new")}>
              Add Service
            </Btn>
          }
        />

        <div style={{ display: "flex", gap: 14, marginBottom: 20, flexWrap: "wrap" }}>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
            padding: "14px 18px", minWidth: 160 }}>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", fontWeight: 700 }}>Configured</p>
            <p style={{ margin: "4px 0 0", fontSize: 22, fontWeight: 800 }}>{services.length}</p>
          </div>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
            padding: "14px 18px", minWidth: 160 }}>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", fontWeight: 700 }}>Published</p>
            <p style={{ margin: "4px 0 0", fontSize: 22, fontWeight: 800, color: "var(--success-text)" }}>{publishedCount}</p>
          </div>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
            padding: "14px 18px", minWidth: 160 }}>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", fontWeight: 700 }}>Available to add</p>
            <p style={{ margin: "4px 0 0", fontSize: 22, fontWeight: 800 }}>{availableCount}</p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
          <div style={{ position: "relative", flex: "1 1 240px", minWidth: 200 }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: 11, color: "var(--text-tertiary)" }} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search services…"
              style={{ width: "100%", height: 36, paddingLeft: 32, paddingRight: 10, borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)", background: "var(--input-bg)", color: "var(--text-primary)", fontSize: 13,
                boxSizing: "border-box" }} />
          </div>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            style={{ height: 36, borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
              background: "var(--input-bg)", color: "var(--text-primary)", fontSize: 13, padding: "0 10px" }}>
            <option value="">All statuses</option>
            {["Draft", "Published", "Suspended", "Archived"].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {enabledRes.loading ? (
          <p style={{ color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</p>
        ) : enabledRes.error ? (
          <p style={{ color: "var(--danger)", fontSize: 13 }}>{enabledRes.error}</p>
        ) : filtered.length === 0 && services.length === 0 ? (
          <EmptyState icon={<Wrench size={22} />} title="No services configured yet"
            description="Add your first service to start accepting bookings. You control every price — nothing is set for you."
            action={<Btn icon={<Plus size={14} />} onClick={() => router.push("/services/setup/new")}>Add Service</Btn>} />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px,1fr))", gap: 14 }}>
            {filtered.map(svc => (
              <div key={svc.tenant_service_id}
                onClick={() => router.push(`/services/setup/${svc.tenant_service_id}`)}
                style={{ cursor: "pointer", background: "var(--surface)", border: "1px solid var(--border)",
                  borderRadius: "var(--radius-lg)", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <p style={{ margin: 0, fontWeight: 700, fontSize: 15 }}>
                    {svc.tenant_display_name || "Untitled service"}
                  </p>
                  <Badge variant={STATUS_VARIANT[statusLabel(svc).toLowerCase()] ?? "muted"}>{statusLabel(svc)}</Badge>
                </div>
                <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
                  Job type: {svc.job_type}
                  {svc.requires_type ? " · Type-based" : ""}
                  {svc.requires_brand ? " · Brand-based" : ""}
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "var(--text-tertiary)" }}>
                  {svc.tenant_min_price != null && svc.tenant_max_price != null
                    ? `Your price: ₹${svc.tenant_min_price}–₹${svc.tenant_max_price}`
                    : svc.tenant_visit_fee != null
                    ? `Visit fee: ₹${svc.tenant_visit_fee}`
                    : "Pricing not configured yet"}
                </p>
                <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                  <Btn size="sm" variant="secondary" onClick={() => router.push(`/services/setup/${svc.tenant_service_id}`)}>
                    {svc.setup_status === "published" ? "Edit" : "Continue setup"}
                  </Btn>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </TenantLayout>
  );
}
