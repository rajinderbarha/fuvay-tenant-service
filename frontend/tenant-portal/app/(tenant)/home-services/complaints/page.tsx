"use client";
/**
 * Complaints & Resolution Center — tenant-scoped queue + case workspace over
 * the canonical `app.engines.complaints` state machine. No second complaint
 * engine and no invented status field.
 *
 * Redesign notes — the queue previously exposed 4 of the 6 filters the
 * endpoint supports, had no tabs, and never paged (a fixed first 20 with no
 * way to reach case 21). Every control below maps 1:1 to a query parameter
 * verified against the live API. Case actions are deliberately limited to what
 * the tenant can actually do (reply, propose resolution) — complaint status is
 * admin-mediated in this engine and there is no tenant transition endpoint, so
 * the workspace explains that rather than rendering buttons that cannot work.
 */
import React, { useCallback, useMemo, useState, Suspense } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { RefreshCw, Search, SlidersHorizontal, ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import { Skeleton, Btn } from "../../../../components/shared/ui";
import { ComplaintKpis } from "../../../../components/complaints/ComplaintKpis";
import { ComplaintQueueList } from "../../../../components/complaints/ComplaintQueueList";
import { ComplaintCaseDetail, type ComplaintTab } from "../../../../components/complaints/ComplaintCaseDetail";
import { tenantComplaintsApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

const PAGE_SIZE = 20;

/**
 * Tabs are saved filter presets over the same endpoint. `open` is a special
 * server-side value meaning "any non-final status", so the Open tab matches
 * the Open KPI exactly instead of approximating it.
 */
type QueueTab = "open" | "at_risk" | "breached" | "escalated" | "critical" | "all";
const TABS: { id: QueueTab; label: string; countKey?: keyof ComplaintSummaryShape }[] = [
  { id: "open",      label: "Open",       countKey: "open" },
  { id: "at_risk",   label: "At risk",    countKey: "at_risk" },
  { id: "breached",  label: "SLA breached", countKey: "breached" },
  { id: "escalated", label: "Escalated",  countKey: "escalated" },
  { id: "critical",  label: "Critical",   countKey: "critical" },
  { id: "all",       label: "All cases",  countKey: "total" },
];
interface ComplaintSummaryShape {
  total: number; open: number; at_risk: number; breached: number;
  escalated: number; critical: number; awaiting_response: number; resolved_this_month: number;
}

function tabParams(tab: QueueTab): { status?: string; sla_state?: string; severity?: string } {
  switch (tab) {
    case "open":      return { status: "open" };
    case "at_risk":   return { sla_state: "at_risk" };
    case "breached":  return { sla_state: "breached" };
    case "escalated": return { sla_state: "escalated" };
    case "critical":  return { severity: "critical" };
    default:          return {};
  }
}

function ComplaintsPageInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const selectedId = searchParams.get("complaint");
  const tab = (searchParams.get("tab") as ComplaintTab) || "overview";
  const queueTab = (searchParams.get("queue") as QueueTab) || "open";
  const search = searchParams.get("q") ?? "";
  const status = searchParams.get("status") ?? "";
  const severity = searchParams.get("severity") ?? "";
  const slaState = searchParams.get("sla") ?? "";
  const serviceId = searchParams.get("service") ?? "";
  const complaintType = searchParams.get("type") ?? "";
  const page = Number(searchParams.get("page") ?? "0");

  const [searchInput, setSearchInput] = useState(search);
  const [showFilters, setShowFilters] = useState(false);

  const updateParams = useCallback((patch: Record<string, string | null>) => {
    const params = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (v) params.set(k, v); else params.delete(k);
    }
    // Any filter change invalidates the page cursor — staying on page 3 of a
    // result set that now has one page shows a confusing empty queue.
    if (!("page" in patch)) params.delete("page");
    router.replace(`${pathname}?${params.toString()}`);
  }, [router, pathname, searchParams]);

  // Explicit dropdown filters win over the tab preset, so choosing e.g.
  // severity=high inside the "At risk" tab does not silently fight it.
  const activeParams = useMemo(() => {
    const preset = tabParams(queueTab);
    return {
      ...preset,
      ...(status ? { status } : {}),
      ...(severity ? { severity } : {}),
      ...(slaState ? { sla_state: slaState } : {}),
      search: search || undefined,
      service_id: serviceId || undefined,
      complaint_type: complaintType || undefined,
    };
  }, [queueTab, status, severity, slaState, search, serviceId, complaintType]);

  const queue = useApi(useCallback(
    () => tenantComplaintsApi.list({ ...activeParams, limit: PAGE_SIZE, cursor: page * PAGE_SIZE }),
    [activeParams, page],
  ));

  const summary = queue.data?.summary;
  const options = queue.data?.available_filters;
  const total = queue.data?.pagination?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const extraFilters =
    (status ? 1 : 0) + (severity ? 1 : 0) + (slaState ? 1 : 0) +
    (serviceId ? 1 : 0) + (complaintType ? 1 : 0);
  const anyFilter = extraFilters > 0 || Boolean(search) || queueTab !== "open";

  function clearAll() {
    router.replace(pathname);
    setSearchInput("");
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, color: "var(--brand)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>Customers</p>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px" }}>Complaints &amp; Resolution Center</h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
            Resolve customer issues with complete job context, clear ownership and SLA control.
          </p>
        </div>
        <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={() => queue.refetch()}>Refresh</Btn>
      </div>

      {queue.loading && !queue.data ? <Skeleton height={100}/> : summary && <ComplaintKpis summary={summary}/>}

      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
        <div style={{
          flex: 1, minWidth: 0, background: "var(--surface)",
          border: "1px solid var(--border)", borderRadius: 16, overflow: "hidden",
        }}>
          {/* Queue tabs */}
          <div role="tablist" aria-label="Complaint queues" style={{ display: "flex", gap: 2, padding: "10px 12px 0", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
            {TABS.map(t => {
              const count = t.countKey && summary ? summary[t.countKey] : undefined;
              const isActive = queueTab === t.id;
              return (
                <button
                  key={t.id} role="tab" aria-selected={isActive}
                  onClick={() => updateParams({ queue: t.id === "open" ? null : t.id })}
                  style={{
                    display: "flex", alignItems: "center", gap: 6, padding: "9px 13px",
                    background: "none", border: "none", cursor: "pointer", fontFamily: "inherit",
                    fontSize: 13, fontWeight: isActive ? 700 : 500,
                    color: isActive ? "var(--brand)" : "var(--text-secondary)",
                    borderBottom: `2px solid ${isActive ? "var(--brand)" : "transparent"}`,
                    marginBottom: -1, whiteSpace: "nowrap",
                  }}
                >
                  {t.label}
                  {typeof count === "number" && (
                    <span style={{
                      fontSize: 11, fontWeight: 700, padding: "1px 6px", borderRadius: 999,
                      background: isActive ? "var(--accent-muted)" : "var(--surface-sunken)",
                      color: isActive ? "var(--brand)" : "var(--text-tertiary)",
                    }}>{count}</span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Search + filter toggle */}
          <div style={{ padding: 12, borderBottom: "1px solid var(--border)", display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
              <Search size={14} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
              <input
                placeholder="Search complaint #, title or description…"
                aria-label="Search complaints"
                value={searchInput}
                onChange={e => setSearchInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") updateParams({ q: searchInput || null }); }}
                onBlur={() => { if (searchInput !== search) updateParams({ q: searchInput || null }); }}
                style={{
                  width: "100%", height: 34, padding: "0 12px 0 32px", fontSize: 13,
                  background: "var(--surface-sunken)", border: "1px solid var(--border)",
                  borderRadius: "var(--radius-lg)", color: "var(--text-primary)", outline: "none",
                  fontFamily: "inherit", boxSizing: "border-box",
                }}
              />
            </div>
            <button
              onClick={() => setShowFilters(v => !v)}
              aria-expanded={showFilters}
              style={{
                display: "flex", alignItems: "center", gap: 6, height: 34, padding: "0 12px", fontSize: 13,
                background: showFilters ? "var(--accent-muted)" : "var(--surface-sunken)",
                border: `1px solid ${extraFilters ? "var(--brand)" : "var(--border)"}`,
                borderRadius: "var(--radius-lg)", color: extraFilters ? "var(--brand)" : "var(--text-secondary)",
                cursor: "pointer", fontFamily: "inherit", fontWeight: 500,
              }}
            >
              <SlidersHorizontal size={13}/>Filters
              {extraFilters > 0 && (
                <span style={{ fontSize: 11, fontWeight: 700, padding: "1px 5px", borderRadius: 999, background: "var(--brand)", color: "#fff" }}>{extraFilters}</span>
              )}
            </button>
            {anyFilter && (
              <button onClick={clearAll} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: 12, fontFamily: "inherit", textDecoration: "underline" }}>
                Clear all
              </button>
            )}
          </div>

          {showFilters && (
            <div style={{ padding: 12, borderBottom: "1px solid var(--border)", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, background: "var(--surface-sunken)" }}>
              <FilterField label="Status">
                <select value={status} onChange={e => updateParams({ status: e.target.value || null })} style={selectStyle}>
                  <option value="">All statuses</option>
                  {(options?.status ?? []).map(s => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                </select>
              </FilterField>
              <FilterField label="Severity">
                <select value={severity} onChange={e => updateParams({ severity: e.target.value || null })} style={selectStyle}>
                  <option value="">All severities</option>
                  {(options?.severity ?? []).map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </FilterField>
              <FilterField label="SLA">
                <select value={slaState} onChange={e => updateParams({ sla: e.target.value || null })} style={selectStyle}>
                  <option value="">All SLA states</option>
                  {(options?.sla_state ?? []).map(s => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                </select>
              </FilterField>
              {/* Both of these map to query params the endpoint already
                  supported but that had no control in the UI. */}
              <FilterField label="Service">
                <select value={serviceId} onChange={e => updateParams({ service: e.target.value || null })} style={selectStyle}>
                  <option value="">All services</option>
                  {(options?.services ?? []).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </FilterField>
              <FilterField label="Issue type">
                <select value={complaintType} onChange={e => updateParams({ type: e.target.value || null })} style={selectStyle}>
                  <option value="">All issue types</option>
                  {(options?.complaint_type ?? []).map(s => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                </select>
              </FilterField>
            </div>
          )}

          {/* Queue */}
          {queue.loading ? (
            <div style={{ padding: 16 }}><Skeleton height={400}/></div>
          ) : queue.error ? (
            <div style={{ textAlign: "center", padding: "32px 16px" }}>
              <p style={{ fontSize: 14, color: "var(--text-primary)", margin: "0 0 12px" }}>{queue.error}</p>
              <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={() => queue.refetch()}>Retry</Btn>
            </div>
          ) : (queue.data?.complaints ?? []).length === 0 ? (
            <div style={{ textAlign: "center", padding: "48px 16px" }}>
              <Inbox size={28} color="var(--text-tertiary)" style={{ marginBottom: 10 }}/>
              <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 10px" }}>
                {anyFilter ? "No complaints match your filters." : "No open complaints. Cases appear here when a customer reports an issue."}
              </p>
              {anyFilter && <Btn variant="secondary" size="sm" onClick={clearAll}>Clear filters</Btn>}
            </div>
          ) : (
            <>
              <ComplaintQueueList
                items={queue.data?.complaints ?? []}
                selectedId={selectedId}
                onSelect={id => updateParams({ complaint: id, tab: "overview", page: String(page) })}
              />
              {/* Pagination — the queue was capped at the first 20 cases with
                  no way to reach anything past them. */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", gap: 10, flexWrap: "wrap", borderTop: "1px solid var(--border)" }}>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                  Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total} cases
                </p>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Btn variant="secondary" size="sm" icon={<ChevronLeft size={13}/>} disabled={page === 0}
                    onClick={() => updateParams({ page: String(Math.max(0, page - 1)) })}>Previous</Btn>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Page {page + 1} of {pages}</span>
                  <Btn variant="secondary" size="sm" disabled={page + 1 >= pages}
                    onClick={() => updateParams({ page: String(page + 1) })}>
                    Next <ChevronRight size={13} style={{ marginLeft: 4 }}/>
                  </Btn>
                </div>
              </div>
            </>
          )}
        </div>

        {selectedId && (
          <ComplaintCaseDetail
            complaintId={selectedId}
            tab={tab}
            onTabChange={t => updateParams({ tab: t, page: String(page) })}
          />
        )}
      </div>
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  height: 34, padding: "0 10px", fontSize: 13, background: "var(--surface)",
  border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
  color: "var(--text-primary)", fontFamily: "inherit", width: "100%", boxSizing: "border-box",
};

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "block" }}>
      <span style={{ display: "block", fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 4 }}>{label}</span>
      {children}
    </label>
  );
}

/**
 * Real build failure fixed here: this page calls `useSearchParams()`, which
 * Next.js requires to sit inside a Suspense boundary. Without one, static
 * prerendering threw "useSearchParams() should be wrapped in a suspense
 * boundary" and FAILED THE WHOLE PRODUCTION BUILD.
 *
 * The boundary is scoped to the page rather than the layout so the rest of
 * the tenant shell keeps prerendering normally.
 */
export default function ComplaintsPage() {
  return (
    <Suspense fallback={null}>
      <ComplaintsPageInner />
    </Suspense>
  );
}
