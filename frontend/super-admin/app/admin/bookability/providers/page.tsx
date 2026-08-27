"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Select, Skeleton, KpiGrid, SummaryCard, Pagination } from "../../../../components/shared/ui";
import { RefreshCw, AlertCircle, CheckCircle2, XCircle, ChevronRight, Zap, Eye, EyeOff } from "lucide-react";
import {
  adminBookabilityApi, categoryRuntimeApi,
  type ProviderVisibilityStatus, type BookabilitySummary, type ServiceCategory,
} from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { useAction } from "../../../../hooks/useApi";
import { usePermissions } from "../../../../hooks/usePermissions";
import Link from "next/link";
import { PageHeader } from "@serviceos/design-system";

const PAGE_SIZE = 25;

const BOOKABLE_OPTIONS = [
  { value: "", label: "All Bookability" },
  { value: "true", label: "Bookable" },
  { value: "false", label: "Not Bookable" },
];

const VISIBLE_OPTIONS = [
  { value: "", label: "All Visibility" },
  { value: "true", label: "Visible" },
  { value: "false", label: "Hidden" },
];

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <Badge variant={ok ? "success" : "warning"} size="sm">
      {ok ? <CheckCircle2 size={10} style={{ display: "inline", marginRight: 3 }} /> : null}
      {label}
    </Badge>
  );
}

export default function BookabilityProvidersPage() {
  const perm = usePermissions();
  const [isBookable, setIsBookable] = useState("");
  const [isVisible,  setIsVisible]  = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [search,     setSearch]     = useState("");
  const [page,       setPage]       = useState(1);

  const categories = useApi(useCallback(() => categoryRuntimeApi.listCategories({ is_active: true }), []));
  const summary    = useApi(useCallback(() => adminBookabilityApi.getSummary(), []));

  const params = {
    is_bookable:  isBookable === "" ? undefined : isBookable === "true",
    is_visible:   isVisible  === "" ? undefined : isVisible  === "true",
    category_id:  categoryId || undefined,
    search:       search     || undefined,
    page,
    page_size:    PAGE_SIZE,
  };

  const providers = useApi(
    useCallback(
      () => adminBookabilityApi.listProviders(params),
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [isBookable, isVisible, categoryId, search, page]
    )
  );

  const bulkRefreshAction = useAction(
    useCallback(() => adminBookabilityApi.bulkRefresh(), [])
  );

  // MODULE-L5-43: the real /v1/admin/bookability/providers response is
  // {providers, total} -- there is no count/page/page_size on it (the
  // backend also has no page/search param support; it only accepts limit).
  const total      = providers.data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const rows: ProviderVisibilityStatus[] = providers.data?.providers ?? [];
  const sum: BookabilitySummary | null = summary.data ?? null;

  const categoryOptions = [
    { value: "", label: "All Categories" },
    ...(categories.data?.categories ?? []).map(
      (c: ServiceCategory) => ({ value: c.category_id, label: c.name })
    ),
  ];

  function resetPage() { setPage(1); }

  return (
    <AdminLayout>
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Header */}
        <PageHeader
          title="Provider Bookability"
          description="Monitor and manage provider visibility and bookability status."
          eyebrow="Operations"
          actions={<div style={{ display: "flex", gap: "var(--layout-control-gap)", flexWrap: "wrap" }}>
            <Btn size="sm" variant="secondary" onClick={() => providers.refetch()}>
              <RefreshCw size={13} /> Refresh
            </Btn>
            {/* FINAL-L5-05P: bulk-refresh is a platform-wide bookability
                mutation -- gated by role, not page-read permission alone. */}
            {perm.role === "super_admin" && (
              <Btn
                size="sm"
                variant="primary"
                onClick={() => bulkRefreshAction.execute().then(() => { providers.refetch(); summary.refetch(); })}
                disabled={bulkRefreshAction.loading}
              >
                <Zap size={13} />
                {bulkRefreshAction.loading ? "Re-evaluating…" : "Bulk Re-evaluate"}
              </Btn>
            )}
          </div>}
        />

        {/* Summary stats */}
        {sum && (
          <KpiGrid>
            {[
              { label: "Total", value: sum.total_providers },
              { label: "Bookable", value: sum.bookable, tone: "success" as const },
              { label: "Not Bookable", value: sum.not_bookable, tone: "danger" as const },
              { label: "Visible", value: sum.visible, tone: "info" as const },
              { label: "With Overrides", value: sum.with_overrides, tone: "warning" as const },
            ].map(s => (
              <SummaryCard key={s.label} label={s.label} value={s.value} tone={s.tone} />
            ))}
          </KpiGrid>
        )}

        {/* Filters */}
        <Card padding={14}>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", gap: 10 }}>
            <div style={{ position: "relative" }}>
              <input
                value={search}
                onChange={e => { setSearch(e.target.value); resetPage(); }}
                placeholder="Search by name, city…"
                style={{ width: "100%", paddingLeft: 12, paddingRight: 10, height: 34, borderRadius:"var(--radius-md)",
                  fontSize: 13, border: "1px solid var(--border)", background: "var(--surface)",
                  color: "var(--text-primary)", outline: "none", boxSizing: "border-box" }}
              />
            </div>
            <Select value={categoryId} onChange={v => { setCategoryId(v); resetPage(); }} options={categoryOptions} placeholder="All Categories" />
            <Select value={isBookable} onChange={v => { setIsBookable(v); resetPage(); }} options={BOOKABLE_OPTIONS} placeholder="All Bookability" />
            <Select value={isVisible}  onChange={v => { setIsVisible(v);  resetPage(); }} options={VISIBLE_OPTIONS}  placeholder="All Visibility" />
          </div>
        </Card>

        {/* Table */}
        <Card padding={0}>
          {providers.loading ? (
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
              {[...Array(6)].map((_, i) => <Skeleton key={i} height={44} />)}
            </div>
          ) : providers.error ? (
            <div style={{ textAlign: "center", padding: "40px 0" }}>
              <AlertCircle size={28} style={{ color: "var(--danger)", display: "block", margin: "0 auto 10px" }} />
              <p style={{ fontSize: 13, color: "var(--danger)", margin: "0 0 12px" }}>{providers.error}</p>
              <Btn size="sm" variant="primary" onClick={() => providers.refetch()}>Retry</Btn>
            </div>
          ) : rows.length === 0 ? (
            <div style={{ textAlign: "center", padding: "56px 0", color: "var(--text-tertiary)" }}>
              <Zap size={32} style={{ display: "block", margin: "0 auto 12px", opacity: 0.4 }} />
              <p style={{ fontSize: 14, fontWeight: 500, margin: "0 0 4px" }}>No providers found</p>
              <p style={{ fontSize: 12, margin: 0 }}>Try adjusting your filters.</p>
            </div>
          ) : (
            <>
              <div style={{ overflowX: "auto" }}>
                <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                      {["Provider", "City", "Visible", "Bookable", "Visibility Blockers", "Bookability Blockers", "Last Evaluated", ""].map(h => (
                        <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 10, fontWeight: 700,
                          color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", whiteSpace: "nowrap" }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((p, i) => (
                      <tr
                        key={p.tenant_id}
                        style={{ borderBottom: i < rows.length - 1 ? "1px solid var(--border)" : "none", transition: "background 0.15s" }}
                        onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                        onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                      >
                        <td style={{ padding: "10px 14px" }}>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                            {p.business_name ?? "—"}
                          </p>
                          <p style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text-tertiary)", margin: "1px 0 0" }}>
                            {p.tenant_id.slice(0, 8)}…
                          </p>
                        </td>
                        <td style={{ padding: "10px 14px", fontSize: 12, color: "var(--text-secondary)" }}>
                          {p.city ?? "—"}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          <StatusBadge ok={p.is_visible} label={p.is_visible ? "Visible" : "Hidden"} />
                          {p.override_is_visible !== null && (
                            <span style={{ fontSize: 10, color: "var(--warning)", display: "block", marginTop: 2 }}>overridden</span>
                          )}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          <StatusBadge ok={p.is_bookable} label={p.is_bookable ? "Bookable" : "Blocked"} />
                          {p.override_is_bookable !== null && (
                            <span style={{ fontSize: 10, color: "var(--warning)", display: "block", marginTop: 2 }}>overridden</span>
                          )}
                        </td>
                        <td style={{ padding: "10px 14px", maxWidth: 160 }}>
                          {(p.visibility_blockers?.length ?? 0) === 0 ? (
                            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>
                          ) : (
                            <span style={{ fontSize: 11, color: "var(--danger)" }}>
                              {p.visibility_blockers!.length} blocker{p.visibility_blockers!.length > 1 ? "s" : ""}
                            </span>
                          )}
                        </td>
                        <td style={{ padding: "10px 14px", maxWidth: 160 }}>
                          {(p.bookability_blockers?.length ?? 0) === 0 ? (
                            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>
                          ) : (
                            <span style={{ fontSize: 11, color: "var(--danger)" }}>
                              {p.bookability_blockers!.length} blocker{p.bookability_blockers!.length > 1 ? "s" : ""}
                            </span>
                          )}
                        </td>
                        <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                          {p.last_evaluated_at
                            ? new Date(p.last_evaluated_at).toLocaleString()
                            : "Never"}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          <Link
                            href={`/admin/tenants/${p.tenant_id}?tab=bookability`}
                            style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12,
                              color: "var(--brand)", textDecoration: "none", fontWeight: 500 }}
                          >
                            Manage <ChevronRight size={12} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </TableSurface>
              </div>

              <Pagination page={page} pageSize={PAGE_SIZE} total={total} pageCount={totalPages}
                onPage={setPage} itemLabel="providers" />
            </>
          )}
        </Card>
      </div>
    </AdminLayout>
  );
}
