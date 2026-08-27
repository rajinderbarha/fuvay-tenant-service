"use client";
import { useCallback, useState } from "react";
import { adminRatingApi, type TenantRatingSummaryRecord, type StaffRatingSummaryRecord } from "../../../lib/api";
import { Card, Badge, Btn, Skeleton, Toaster, SectionHeader, type ToastItem } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import { BarChart2, RefreshCw, Users, RefreshCcw } from "lucide-react";

export default function AdminRatingSummariesPage() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const addToast = useCallback((title: string, variant: ToastItem["variant"] = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, title, variant }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);

  const [tab, setTab] = useState<"tenant"|"staff">("tenant");

  const { data: tenantData, loading: tenantLoading, refetch: refetchTenants } = useApi(
    useCallback(() => adminRatingApi.listTenants(), [])
  );
  const { data: staffData, loading: staffLoading, refetch: refetchStaff } = useApi(
    useCallback(() => adminRatingApi.listStaff(), [])
  );

  const tenants: TenantRatingSummaryRecord[] = (Array.isArray(tenantData) ? tenantData : []) as TenantRatingSummaryRecord[];
  const staff:   StaffRatingSummaryRecord[]   = (Array.isArray(staffData)  ? staffData  : []) as StaffRatingSummaryRecord[];

  const recomputeAction = useAction(useCallback((tid: string) => adminRatingApi.recompute(tid), []));

  const handleRecompute = async (tenantId: string) => {
    const result = await recomputeAction.execute(tenantId);
    if (result) { addToast("Summary recomputed.", "success"); refetchTenants(); }
    else { addToast(recomputeAction.error ?? "Failed.", "danger"); }
  };

  function ratingVariant(r: string): "success"|"warning"|"danger" {
    const n = parseFloat(r);
    if (n >= 4) return "success";
    if (n >= 3) return "warning";
    return "danger";
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <Toaster toasts={toasts} onRemove={id => setToasts(p => p.filter(t => t.id !== id))} />

      <SectionHeader eyebrow="Trust & quality" title="Rating Summaries"
        description="Aggregated ratings by tenant and staff member." icon={<BarChart2 />}
        actions={<Btn variant="ghost" onClick={() => tab === "tenant" ? refetchTenants() : refetchStaff()}>
          <RefreshCw size={14} /> Refresh
        </Btn>} />

      <div style={{ display: "flex", gap: 8 }}>
        {(["tenant", "staff"] as const).map(t => (
          <Btn key={t} size="sm" variant={tab === t ? "primary" : "ghost"} onClick={() => setTab(t)}>
            {t === "tenant" ? <><BarChart2 size={12} /> Tenants</> : <><Users size={12} /> Staff</>}
          </Btn>
        ))}
      </div>

      {tab === "tenant" && (
        tenantLoading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[0,1,2].map(i => <Skeleton key={i} height={90} />)}
          </div>
        ) : tenants.length === 0 ? (
          <Card padding={48} style={{ textAlign: "center" }}>
            <p style={{ color: "var(--text-secondary)", margin: 0 }}>No tenant summaries yet.</p>
          </Card>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {tenants.map((s: TenantRatingSummaryRecord) => (
              <Card key={s.id} padding={16}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                  <div>
                    <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)", margin: 0 }}>
                      Tenant: {s.tenant_id?.slice(0, 12)}...
                    </p>
                    <div style={{ display: "flex", gap: 12, marginTop: 6, fontSize: 11, color: "var(--text-tertiary)", flexWrap: "wrap" }}>
                      <span>Total: {s.total_reviews} reviews</span>
                      <span>5★: {s.five_star_count} · 4★: {s.four_star_count} · 3★: {s.three_star_count}</span>
                      <span>2★: {s.two_star_count} · 1★: {s.one_star_count}</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <Badge variant={ratingVariant(s.average_rating)}>★ {s.average_rating}</Badge>
                    <Btn size="sm" variant="ghost" onClick={() => handleRecompute(s.tenant_id)}
                      loading={recomputeAction.loading}>
                      <RefreshCcw size={12} /> Recompute
                    </Btn>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )
      )}

      {tab === "staff" && (
        staffLoading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[0,1,2].map(i => <Skeleton key={i} height={70} />)}
          </div>
        ) : staff.length === 0 ? (
          <Card padding={48} style={{ textAlign: "center" }}>
            <p style={{ color: "var(--text-secondary)", margin: 0 }}>No staff summaries yet.</p>
          </Card>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {staff.map((s: StaffRatingSummaryRecord) => (
              <Card key={s.id} padding={14}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                  <div>
                    <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)", margin: 0 }}>
                      Staff: {s.staff_member_id?.slice(0, 12)}...
                    </p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                      Tenant: {s.tenant_id?.slice(0, 8)} · {s.total_reviews} review{s.total_reviews !== 1 ? "s" : ""}
                    </p>
                  </div>
                  <Badge variant={ratingVariant(s.average_rating)}>★ {s.average_rating}</Badge>
                </div>
              </Card>
            ))}
          </div>
        )
      )}
    </div>
  );
}
