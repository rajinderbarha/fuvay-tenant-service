"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout }      from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader } from "../../../../components/shared/ui";
import {
  providersAdminApi, adminOnboardingProvidersApi,
  type NewRequestsProvider, type NewRequestsSummary,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { Search, Bell, ArrowRight, RefreshCw } from "lucide-react";

const VERTICAL_LABEL: Record<string, string> = {
  home_services: "Home Services", salon: "Salon", coaching: "Coaching",
  real_estate: "Real Estate", restaurant: "Restaurant", automotive: "Automotive",
  professional_services: "Professional Services", pharmacy: "Pharmacy",
  hardware: "Hardware", repair_services: "Repair Services",
  cleaning_services: "Cleaning Services", laundry: "Laundry",
  marketplace_products: "Marketplace", other: "Other",
};

const PKG_STATUS_LABEL: Record<string, string> = {
  selected: "Package Selected", paid_pending_approval: "Paid — Awaiting Approval",
  active: "Active", pending_review: "Pending", rejected: "Rejected",
};

function ProfileBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "#16a34a" : pct >= 60 ? "#d97706" : "#dc2626";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ flex: 1, height: 6, background: "var(--border)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4 }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color, minWidth: 32 }}>{pct}%</span>
    </div>
  );
}

function SummaryCard({ label, value, color, loading }: { label: string; value?: number; color: string; loading: boolean }) {
  return (
    <div style={{
      background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 10,
      padding: "14px 16px", borderLeft: `3px solid ${color}`, flex: 1, minWidth: 140,
    }}>
      <div style={{ fontSize: 24, fontWeight: 700, color, fontVariantNumeric: "tabular-nums" }}>
        {loading ? "…" : (value ?? 0)}
      </div>
      <div style={{ fontSize: 11, color: "var(--muted-text)", marginTop: 3 }}>{label}</div>
    </div>
  );
}

export default function NewBusinessRequestsPage() {
  const [q, setQ]               = useState("");
  const [vertical, setVertical] = useState("");
  const [city, setCity]         = useState("");
  const [hasPkg, setHasPkg]     = useState<"" | "true" | "false">("");
  const [page, setPage]         = useState(1);
  const PAGE_SIZE = 50;

  const summaryFetch = useApi(useCallback(() => providersAdminApi.newRequestsSummary(), []));
  const listFetch    = useApi(useCallback(
    () => providersAdminApi.newRequests({
      q: q || undefined, vertical_type: vertical || undefined,
      city: city || undefined,
      has_package: hasPkg === "" ? undefined : hasPkg === "true",
      page, page_size: PAGE_SIZE,
    }),
    [q, vertical, city, hasPkg, page]
  ));

  const summary: NewRequestsSummary | null =
    (summaryFetch.data as { data?: NewRequestsSummary } | null)?.data ??
    (summaryFetch.data as NewRequestsSummary | null);

  const listData =
    (listFetch.data as { data?: { providers: NewRequestsProvider[]; total: number } } | null)?.data ??
    (listFetch.data as { providers: NewRequestsProvider[]; total: number } | null);

  const providers: NewRequestsProvider[] = listData?.providers ?? [];
  const total = listData?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

  const [reminderLoading, setReminderLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  async function sendReminder(tenantId: string, name: string) {
    setReminderLoading(tenantId);
    try {
      await adminOnboardingProvidersApi.sendReminder(tenantId);
      notify(`Reminder sent to "${name}".`);
    } catch { notify("Failed to send reminder.", false); }
    finally { setReminderLoading(null); }
  }

  return (
    <AdminLayout activeNav="tenants">
      <div style={{ padding: "24px 28px", maxWidth: 1280, margin: "0 auto" }}>
        <SectionHeader
          title="New Business Requests"
          subtitle="Providers who registered but haven't submitted for review yet."
        />

        {toast && (
          <div style={{
            padding: "10px 16px", borderRadius: 10, marginBottom: 12,
            background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
            border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
            color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13,
          }}>
            {toast.ok ? "✓" : "✗"} {toast.msg}
          </div>
        )}

        {/* Summary Cards */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20 }}>
          <SummaryCard label="Total New Requests"    value={summary?.total}                color="var(--primary)"  loading={summaryFetch.loading} />
          <SummaryCard label="With Package"          value={summary?.with_package}         color="#16a34a"         loading={summaryFetch.loading} />
          <SummaryCard label="Without Package"       value={summary?.without_package}      color="#dc2626"         loading={summaryFetch.loading} />
          <SummaryCard label="Package Selected"      value={summary?.package_selected}     color="#d97706"         loading={summaryFetch.loading} />
          <SummaryCard label="Profile ≥ 80%"         value={summary?.profile_near_complete} color="#0891b2"        loading={summaryFetch.loading} />
        </div>

        {/* Filters */}
        <Card padding={14} style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ flex: 2, minWidth: 200, position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--muted-text)" }} />
              <input
                value={q} onChange={e => { setQ(e.target.value); setPage(1); }}
                placeholder="Search by name, email, phone…"
                style={{
                  width: "100%", padding: "8px 10px 8px 32px", borderRadius: 8,
                  border: "1px solid var(--border)", background: "var(--bg)",
                  color: "var(--text-primary)", fontSize: 13, outline: "none", boxSizing: "border-box",
                }}
              />
            </div>
            <select value={vertical} onChange={e => { setVertical(e.target.value); setPage(1); }}
              style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}>
              <option value="">All Verticals</option>
              {Object.entries(VERTICAL_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <select value={hasPkg} onChange={e => { setHasPkg(e.target.value as "" | "true" | "false"); setPage(1); }}
              style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}>
              <option value="">Package: All</option>
              <option value="true">Has Package</option>
              <option value="false">No Package</option>
            </select>
            <input
              value={city} onChange={e => { setCity(e.target.value); setPage(1); }}
              placeholder="Filter by city…"
              style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, width: 160 }}
            />
            <Btn variant="ghost" size="sm" onClick={() => listFetch.refetch()}>
              <RefreshCw size={13} />
            </Btn>
          </div>
        </Card>

        {/* Table */}
        <Card padding={0} style={{ overflow: "hidden" }}>
          {listFetch.error ? (
            <div style={{ padding: 32, textAlign: "center", color: "var(--danger-text)", fontSize: 14 }}>
              Failed to load: {listFetch.error}
              <Btn variant="secondary" size="sm" onClick={() => listFetch.refetch()} style={{ marginLeft: 12 }}>Retry</Btn>
            </div>
          ) : listFetch.loading ? (
            <div style={{ padding: 40, textAlign: "center", color: "var(--muted-text)", fontSize: 13 }}>Loading…</div>
          ) : providers.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center" }}>
              <p style={{ color: "var(--muted-text)", fontSize: 14, marginBottom: 12 }}>No new business requests found.</p>
              {(q || vertical || city || hasPkg) && (
                <Btn variant="ghost" size="sm" onClick={() => { setQ(""); setVertical(""); setCity(""); setHasPkg(""); }}>
                  Clear Filters
                </Btn>
              )}
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid var(--border)", background: "var(--card-bg)" }}>
                    {["Business", "Owner", "Vertical", "Location", "Profile", "Package", "Joined", "Actions"].map(h => (
                      <th key={h} style={{
                        padding: "10px 14px", textAlign: "left", fontSize: 11, fontWeight: 700,
                        color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.04em", whiteSpace: "nowrap",
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {providers.map((p, i) => (
                    <tr key={p.tenant_id} style={{
                      borderBottom: "1px solid var(--border)",
                      background: i % 2 === 0 ? "transparent" : "var(--row-alt-bg, rgba(0,0,0,0.015))",
                    }}>
                      <td style={{ padding: "10px 14px" }}>
                        <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                          {p.business_name ?? p.tenant_name ?? "—"}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--muted-text)", fontFamily: "monospace" }}>
                          {p.tenant_id.slice(0, 8)}…
                        </div>
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <div>{p.owner_name ?? "—"}</div>
                        <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{p.owner_email ?? p.owner_phone ?? ""}</div>
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        {p.vertical_type
                          ? <Badge variant="info" size="sm">{VERTICAL_LABEL[p.vertical_type] ?? p.vertical_type}</Badge>
                          : <span style={{ color: "var(--muted-text)" }}>—</span>}
                      </td>
                      <td style={{ padding: "10px 14px", color: "var(--text-secondary)", fontSize: 12 }}>
                        {[p.city, p.state].filter(Boolean).join(", ") || "—"}
                      </td>
                      <td style={{ padding: "10px 14px", minWidth: 140 }}>
                        <ProfileBar pct={p.profile_completion_percentage} />
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        {p.package_status
                          ? <Badge
                              variant={p.package_status === "selected" || p.package_status === "paid_pending_approval" ? "warning" : "success"}
                              size="sm">
                              {PKG_STATUS_LABEL[p.package_status] ?? p.package_status}
                            </Badge>
                          : <span style={{ color: "var(--muted-text)", fontSize: 12 }}>No package</span>}
                        {p.package_name && (
                          <div style={{ fontSize: 11, color: "var(--muted-text)", marginTop: 2 }}>{p.package_name}</div>
                        )}
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 12, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                        {p.created_at ? new Date(p.created_at).toLocaleDateString("en-IN") : "—"}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <div style={{ display: "flex", gap: 6 }}>
                          <Btn variant="primary" size="sm"
                            onClick={() => window.location.href = `/admin/tenants/${p.tenant_id}?tab=onboarding`}>
                            Review <ArrowRight size={12} style={{ marginLeft: 2 }} />
                          </Btn>
                          <Btn variant="ghost" size="sm"
                            loading={reminderLoading === p.tenant_id}
                            onClick={() => sendReminder(p.tenant_id, p.business_name ?? p.tenant_name ?? p.tenant_id)}>
                            <Bell size={13} />
                          </Btn>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginTop: 16 }}>
            <Btn variant="secondary" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
              Prev
            </Btn>
            <span style={{ fontSize: 13, color: "var(--muted-text)" }}>
              Page {page} of {totalPages} ({total} total)
            </span>
            <Btn variant="secondary" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
              Next
            </Btn>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
