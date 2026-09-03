"use client";
/**
 * Reviews & Service Quality — canonical customer_reviews/review_replies/
 * review_flags system (Sprint 24), joined to real service_jobs/technicians/
 * complaints via GET /v1/tenant/home-services/reviews. No second review
 * engine or quality score -- see hs_quality_service.py.
 *
 * Reply/moderation-request mutations call the EXISTING, already-secured
 * /v1/provider/reviews/{id}/reply and /flag endpoints.
 *
 * Redesign notes — this page previously exposed only 2 of the 9 filters the
 * endpoint supports, paged nothing (a hard limit of 10 with no way to reach
 * review 11), and dropped most of the detail payload on the floor. Every
 * filter below maps 1:1 to a verified query parameter, and the detail panel
 * now renders the whole contract, including the review_events timeline and
 * the moderation reason.
 */
import React, { useCallback, useEffect, useMemo, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  RefreshCw, Search, Star, MessageSquare, TrendingDown, Flag, X, ExternalLink,
  ShieldAlert, CheckCircle2, Info, Download, ChevronLeft, ChevronRight,
  AlertTriangle, FileText, Clock, Eye, EyeOff, SlidersHorizontal,
} from "lucide-react";
import {
  hsReviewsApi, ServiceOSError,
  type HsReviewListItem, type HsReviewDetail, type HsReviewsListResponse,
} from "../../../../lib/api";
import { Skeleton, Btn, Badge, KpiGrid, SummaryCard, Pagination } from "../../../../components/shared/ui";

const MODERATION_REASONS = [
  { value: "abusive_language", label: "Abusive language" },
  { value: "personal_information_exposed", label: "Personal information exposed" },
  { value: "irrelevant_content", label: "Irrelevant content" },
  { value: "spam", label: "Spam" },
  { value: "conflict_of_interest", label: "Conflict of interest" },
  { value: "not_based_on_job", label: "Review not based on the linked job" },
  { value: "prohibited_content", label: "Prohibited content" },
  { value: "legal_safety_concern", label: "Legal/safety concern" },
];
// The backend's ReviewFlagRequest only accepts these literal reason_code
// values -- moderation UI options above map to the closest real code rather
// than sending an unsupported string the API would reject.
const REASON_CODE_MAP: Record<string, string> = {
  abusive_language: "offensive", personal_information_exposed: "other",
  irrelevant_content: "irrelevant", spam: "spam", conflict_of_interest: "other",
  not_based_on_job: "fake", prohibited_content: "offensive", legal_safety_concern: "other",
};

const PAGE_SIZE = 10;

/**
 * Tabs are saved filter presets over the SAME endpoint — each one maps to
 * query parameters that were verified against the live API, so a tab can
 * never show a count it cannot then filter to.
 */
type TabId = "all" | "unanswered" | "low" | "complaints" | "flagged";
const TABS: { id: TabId; label: string; countKey?: keyof NonNullable<HsReviewsListResponse["summary"]> }[] = [
  { id: "all",        label: "All reviews", countKey: "reviews" },
  { id: "unanswered", label: "Needs reply", countKey: "unanswered" },
  { id: "low",        label: "Low ratings", countKey: "low_ratings" },
  { id: "complaints", label: "With complaints" },
  { id: "flagged",    label: "Moderation",  countKey: "flagged" },
];

function tabParams(tab: TabId) {
  switch (tab) {
    case "unanswered": return { reply_status: "unanswered" };
    // <= 2, matching how the Low ratings KPI is counted server-side. An exact
    // rating=2 match here would silently exclude every 1-star review.
    case "low":        return { rating_max: 2 };
    case "complaints": return { complaint_linked: true };
    case "flagged":    return { moderation_status: "open" };
    default:           return {};
  }
}

function Stars({ rating, size = 13 }: { rating: number; size?: number }) {
  return (
    <span style={{ display: "inline-flex", gap: 1 }} aria-label={`${rating} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map(i => (
        <Star key={i} size={size} fill={i <= rating ? "var(--warning-text)" : "none"} color={i <= rating ? "var(--warning-text)" : "var(--border)"}/>
      ))}
    </span>
  );
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function ReviewsQualityPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [tab, setTab]                 = useState<TabId>((searchParams.get("tab") as TabId) || "all");
  const [rating, setRating]           = useState<number | undefined>(searchParams.get("rating") ? Number(searchParams.get("rating")) : undefined);
  const [technicianId, setTechnician] = useState(searchParams.get("technician_id") ?? "");
  const [offeringId, setOffering]     = useState(searchParams.get("offering_id") ?? "");
  const [dateFrom, setDateFrom]       = useState(searchParams.get("date_from") ?? "");
  const [dateTo, setDateTo]           = useState(searchParams.get("date_to") ?? "");
  const [searchInput, setSearchInput] = useState(searchParams.get("search") ?? "");
  const [search, setSearch]           = useState(searchParams.get("search") ?? "");
  const [page, setPage]               = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedId, setSelectedId]   = useState<string | null>(searchParams.get("review_id"));

  const [data, setData]       = useState<HsReviewsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  /** Everything the queue is currently filtered by, in endpoint terms. */
  const activeParams = useMemo(() => ({
    ...tabParams(tab),
    rating,
    technician_id: technicianId || undefined,
    offering_id: offeringId || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    search: search || undefined,
  }), [tab, rating, technicianId, offeringId, dateFrom, dateTo, search]);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    hsReviewsApi.list({ ...activeParams, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then(setData)
      .catch((e: unknown) => setError(e instanceof ServiceOSError ? e.message : "We couldn't load reviews."))
      .finally(() => setLoading(false));
  }, [activeParams, page]);

  useEffect(() => { load(); }, [load]);

  // Any filter change invalidates the current page number -- staying on page 4
  // of a result set that now has one page shows a confusing empty queue.
  useEffect(() => { setPage(0); }, [tab, rating, technicianId, offeringId, dateFrom, dateTo, search]);

  useEffect(() => {
    const qs = new URLSearchParams();
    if (tab !== "all") qs.set("tab", tab);
    if (rating) qs.set("rating", String(rating));
    if (technicianId) qs.set("technician_id", technicianId);
    if (offeringId) qs.set("offering_id", offeringId);
    if (dateFrom) qs.set("date_from", dateFrom);
    if (dateTo) qs.set("date_to", dateTo);
    if (search) qs.set("search", search);
    if (selectedId) qs.set("review_id", selectedId);
    router.replace(`/home-services/reviews${qs.toString() ? `?${qs}` : ""}`, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, rating, technicianId, offeringId, dateFrom, dateTo, search, selectedId]);

  const [exporting, setExporting] = useState(false);
  const handleExport = async () => {
    setExporting(true);
    try {
      // Re-fetch the full filtered set page by page (backend caps limit at
      // 100 per request) rather than just the current page's rows -- only
      // masked fields are included, matching the shape already in the queue.
      const all: HsReviewListItem[] = [];
      let offset = 0;
      for (;;) {
        const page_ = await hsReviewsApi.list({ ...activeParams, limit: 100, offset });
        all.push(...page_.reviews);
        offset += page_.reviews.length;
        if (page_.reviews.length < 100 || all.length >= page_.total) break;
      }
      const header = ["Review #", "Customer", "Rating", "Job #", "Service", "Technician", "Reply status", "Publication", "Complaint linked", "Moderation status", "Date"];
      const rows = all.map(r => [
        r.review_number, r.customer_alias, String(r.rating), r.job_number, r.service_name,
        r.technician_name ?? "", r.reply_status, r.review_status, r.complaint_linked ? "yes" : "no",
        r.moderation_status ?? "", fmtDate(r.created_at),
      ]);
      const csv = [header, ...rows].map(row => row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `reviews-export-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const failed  = new Set(data?.failed_modules ?? []);
  const kpis    = data?.summary;
  const options = data?.available_filters;
  const total   = data?.total ?? 0;
  const pages   = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const extraFilterCount =
    (rating ? 1 : 0) + (technicianId ? 1 : 0) + (offeringId ? 1 : 0) +
    (dateFrom ? 1 : 0) + (dateTo ? 1 : 0);
  const anyFilter = extraFilterCount > 0 || Boolean(search) || tab !== "all";

  const clearAll = () => {
    setTab("all"); setRating(undefined); setTechnician(""); setOffering("");
    setDateFrom(""); setDateTo(""); setSearch(""); setSearchInput("");
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap", marginBottom: 20 }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 4px", textTransform: "uppercase" }}>Customers</p>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px" }}>Reviews &amp; Service Quality</h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>Respond to customer feedback and improve service quality with job-linked evidence.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="secondary" size="sm" icon={<Download size={13}/>} loading={exporting} disabled={total === 0} onClick={handleExport}>Export</Btn>
          <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={load}>Refresh</Btn>
        </div>
      </div>

      {/* ── KPI tiles ─────────────────────────────────────────────────── */}
      {loading && !data ? (
        <KpiGrid minCardWidth={160} style={{ marginBottom: 20 }}>
          {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} height={80}/>)}
        </KpiGrid>
      ) : (
        <KpiGrid minCardWidth={160} style={{ marginBottom: 20 }}>
          <KpiTile icon={<MessageSquare size={18}/>} label="Reviews" value={kpis?.reviews ?? "—"} color="var(--text-primary)"
            onClick={() => setTab("all")} active={tab === "all"}/>
          <KpiTile icon={<Star size={18}/>} label="Average rating" value={kpis?.average_rating ?? "—"} color="var(--warning-text)"/>
          <KpiTile icon={<CheckCircle2 size={18}/>} label="Response rate" value={kpis ? `${kpis.response_rate}%` : "—"} color="var(--success-text)"/>
          <KpiTile icon={<TrendingDown size={18}/>} label="Low ratings" value={kpis?.low_ratings ?? "—"} color="var(--danger-text)"
            onClick={() => setTab(tab === "low" ? "all" : "low")} active={tab === "low"}/>
          <KpiTile icon={<MessageSquare size={18}/>} label="Unanswered" value={kpis?.unanswered ?? "—"} color="var(--warning-text)"
            onClick={() => setTab(tab === "unanswered" ? "all" : "unanswered")} active={tab === "unanswered"}/>
          {/* Previously inert: the tile showed a flagged count with nothing to
              click through to. It now drives the same moderation tab. */}
          <KpiTile icon={<Flag size={18}/>} label="Flagged" value={kpis?.flagged ?? "—"} color="var(--danger-text)"
            onClick={() => setTab(tab === "flagged" ? "all" : "flagged")} active={tab === "flagged"}/>
        </KpiGrid>
      )}

      {/* ── Analytics band ────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 16, marginBottom: 20 }} className="rq-analytics-grid">
        <style>{`@media (max-width: 1100px) { .rq-analytics-grid { grid-template-columns: 1fr !important; } }`}</style>

        <Panel title="Rating trend">
          {failed.has("rating_trend") ? <ModuleUnavailable onRetry={load}/> : !data?.rating_trend.length ? (
            <Empty text="Not enough data in this period yet."/>
          ) : (
            <RatingTrendChart points={data.rating_trend}/>
          )}
        </Panel>

        <Panel title="Rating distribution">
          {failed.has("rating_distribution") ? <ModuleUnavailable onRetry={load}/> : !kpis?.reviews ? (
            <Empty text="No reviews yet."/>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(data?.rating_distribution ?? []).map(d => (
                <button
                  key={d.stars}
                  onClick={() => { setTab("all"); setRating(rating === d.stars ? undefined : d.stars); }}
                  title={`${d.count} review${d.count === 1 ? "" : "s"} — click to filter`}
                  style={{
                    display: "flex", alignItems: "center", gap: 8, background: "none", padding: "2px 4px",
                    border: "1px solid " + (rating === d.stars ? "var(--brand)" : "transparent"),
                    borderRadius: 6, cursor: "pointer", fontFamily: "inherit", width: "100%",
                  }}
                >
                  <span style={{ fontSize: 12, color: "var(--text-secondary)", width: 46, flexShrink: 0, textAlign: "left" }}>{d.stars} stars</span>
                  <div style={{ flex: 1, height: 8, background: "var(--surface-sunken)", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{ width: `${d.percent}%`, height: "100%", background: d.stars >= 4 ? "var(--success-text)" : d.stars === 3 ? "var(--warning-text)" : "var(--danger-text)" }}/>
                  </div>
                  <span style={{ fontSize: 12, color: "var(--text-tertiary)", width: 32, textAlign: "right", flexShrink: 0 }}>{d.percent}%</span>
                </button>
              ))}
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "8px 0 0" }}>Based on {kpis?.reviews ?? 0} reviews</p>
            </div>
          )}
        </Panel>

        <Panel title="Quality signals" hint="Calculated from real completed jobs and complaints in this period.">
          {failed.has("quality_signals") ? <ModuleUnavailable onRetry={load}/> : !data?.quality_signals || data.quality_signals.sample_size === 0 ? (
            <Empty text="Not enough completed jobs yet."/>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <QualitySignalRow label="SLA met" value={data.quality_signals.sla_met_percent}/>
              <QualitySignalRow label="Rework rate" value={data.quality_signals.rework_rate_percent} invert/>
              <QualitySignalRow label="Complaint after completion" value={data.quality_signals.complaint_after_completion_percent} invert/>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>Sample: {data.quality_signals.sample_size} completed jobs</p>
            </div>
          )}
        </Panel>
      </div>

      {/* ── Queue + detail split ──────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: selectedId ? "1.3fr 1fr" : "1fr", gap: 16, alignItems: "start" }} className="rq-split-grid">
        <style>{`@media (max-width: 1200px) { .rq-split-grid { grid-template-columns: 1fr !important; } }`}</style>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, overflow: "hidden" }}>
          {/* Tabs */}
          <div role="tablist" aria-label="Review queues" style={{ display: "flex", gap: 2, padding: "10px 12px 0", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
            {TABS.map(t => {
              const count = t.countKey && kpis ? kpis[t.countKey] : undefined;
              const isActive = tab === t.id;
              return (
                <button
                  key={t.id} role="tab" aria-selected={isActive}
                  onClick={() => setTab(t.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: 6, padding: "9px 13px",
                    background: "none", border: "none", cursor: "pointer", fontFamily: "inherit",
                    fontSize: 13, fontWeight: isActive ? 700 : 500,
                    color: isActive ? "var(--brand)" : "var(--text-secondary)",
                    borderBottom: `2px solid ${isActive ? "var(--brand)" : "transparent"}`,
                    marginBottom: -1,
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
                placeholder="Search review text, review # or job #…"
                aria-label="Search reviews"
                value={searchInput}
                onChange={e => setSearchInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") setSearch(searchInput); }}
                onBlur={() => setSearch(searchInput)}
                style={{ width: "100%", height: 34, padding: "0 12px 0 32px", fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", color: "var(--text-primary)", outline: "none", fontFamily: "inherit", boxSizing: "border-box" }}
              />
            </div>
            <button
              onClick={() => setShowFilters(v => !v)}
              aria-expanded={showFilters}
              style={{
                display: "flex", alignItems: "center", gap: 6, height: 34, padding: "0 12px", fontSize: 13,
                background: showFilters ? "var(--accent-muted)" : "var(--surface-sunken)",
                border: `1px solid ${extraFilterCount ? "var(--brand)" : "var(--border)"}`,
                borderRadius: "var(--radius-lg)", color: extraFilterCount ? "var(--brand)" : "var(--text-secondary)",
                cursor: "pointer", fontFamily: "inherit", fontWeight: 500,
              }}
            >
              <SlidersHorizontal size={13}/>Filters
              {extraFilterCount > 0 && (
                <span style={{ fontSize: 11, fontWeight: 700, padding: "1px 5px", borderRadius: 999, background: "var(--brand)", color: "#fff" }}>{extraFilterCount}</span>
              )}
            </button>
            {anyFilter && (
              <button onClick={clearAll} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: 12, fontFamily: "inherit", textDecoration: "underline" }}>
                Clear all
              </button>
            )}
          </div>

          {/* Advanced filters — every control maps to a real query parameter */}
          {showFilters && (
            <div style={{ padding: 12, borderBottom: "1px solid var(--border)", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, background: "var(--surface-sunken)" }}>
              <FilterField label="Rating">
                <select value={rating ?? ""} onChange={e => setRating(e.target.value ? Number(e.target.value) : undefined)} style={selectStyle}>
                  <option value="">All ratings</option>
                  {[5, 4, 3, 2, 1].map(r => <option key={r} value={r}>{r} stars</option>)}
                </select>
              </FilterField>
              <FilterField label="Service">
                <select value={offeringId} onChange={e => setOffering(e.target.value)} style={selectStyle}>
                  <option value="">All services</option>
                  {(options?.services ?? []).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </FilterField>
              <FilterField label="Technician">
                <select value={technicianId} onChange={e => setTechnician(e.target.value)} style={selectStyle}>
                  <option value="">All technicians</option>
                  {(options?.technicians ?? []).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </FilterField>
              <FilterField label="From date">
                <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={selectStyle}/>
              </FilterField>
              <FilterField label="To date">
                <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={selectStyle}/>
              </FilterField>
            </div>
          )}

          {/* Queue */}
          {loading ? (
            <div style={{ padding: 20 }}>{[1, 2, 3].map(i => <Skeleton key={i} height={50} style={{ marginBottom: 8 }}/>)}</div>
          ) : error ? (
            <div style={{ textAlign: "center", padding: "32px 16px" }}>
              <p style={{ fontSize: 14, color: "var(--text-primary)", margin: "0 0 12px" }}>{error}</p>
              <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={load}>Retry</Btn>
            </div>
          ) : failed.has("reviews") ? (
            <div style={{ padding: "32px 16px" }}><ModuleUnavailable onRetry={load}/></div>
          ) : !data || data.reviews.length === 0 ? (
            <div style={{ textAlign: "center", padding: "48px 16px" }}>
              <MessageSquare size={28} color="var(--text-tertiary)" style={{ marginBottom: 10 }}/>
              <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 10px" }}>
                {anyFilter ? "No reviews match your filters." : "No reviews yet. They appear here once customers rate a completed job."}
              </p>
              {anyFilter && <Btn variant="secondary" size="sm" onClick={clearAll}>Clear filters</Btn>}
            </div>
          ) : (
            <div>
              {data.reviews.map(rv => (
                <button key={rv.review_id} onClick={() => setSelectedId(rv.review_id)} style={{
                  display: "block", width: "100%", textAlign: "left", padding: "14px 16px",
                  borderBottom: "1px solid var(--border)", background: selectedId === rv.review_id ? "var(--surface-sunken)" : "none",
                  border: "none", borderLeft: selectedId === rv.review_id ? "3px solid var(--brand)" : "3px solid transparent",
                  cursor: "pointer", fontFamily: "inherit",
                }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4, gap: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Stars rating={rv.rating}/>
                      <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{rv.customer_alias}</span>
                    </div>
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{fmtDate(rv.created_at)}</span>
                  </div>
                  <p style={{ fontSize: 13, color: "var(--text-primary)", margin: "0 0 6px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {rv.review_excerpt || <span style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>Rating only — no written feedback</span>}
                  </p>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                    <Badge variant="muted" size="sm">{rv.job_number}</Badge>
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{rv.service_name}{rv.technician_name ? ` · ${rv.technician_name}` : ""}</span>
                    <Badge variant={rv.reply_status === "answered" ? "success" : "warning"} size="sm">{rv.reply_status}</Badge>
                    <PublicationBadge status={rv.review_status}/>
                    {rv.complaint_linked && <Badge variant="danger" size="sm">complaint</Badge>}
                    {rv.moderation_status && <Badge variant="warning" size="sm">moderation: {rv.moderation_status}</Badge>}
                  </div>
                </button>
              ))}

              {/* Pagination — the queue was previously capped at the first 10
                  rows with no way to reach anything past them. */}
              <Pagination page={page + 1} pageSize={PAGE_SIZE} total={total} pageCount={pages}
                onPage={target => setPage(target - 1)} itemLabel="reviews" alwaysShow />
            </div>
          )}
        </div>

        {selectedId && <ReviewDetailPanel reviewId={selectedId} onClose={() => setSelectedId(null)} onChanged={load}/>}
      </div>
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  height: 34, padding: "0 10px", fontSize: 13, background: "var(--surface)", border: "1px solid var(--border)",
  borderRadius: "var(--radius-lg)", color: "var(--text-primary)", fontFamily: "inherit", width: "100%", boxSizing: "border-box",
};

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "block" }}>
      <span style={{ display: "block", fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 4 }}>{label}</span>
      {children}
    </label>
  );
}

function Panel({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, padding: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 6 }}>
        {title}
        {hint && <span title={hint}><Info size={13} color="var(--text-tertiary)"/></span>}
      </h3>
      {children}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>{text}</p>;
}

/**
 * A review is only visible to customers once approved. With no review policy
 * row configured, every review stays `pending`, so surfacing this is the only
 * way a provider can tell that their feedback is not yet public.
 */
function PublicationBadge({ status }: { status: string }) {
  if (!status || status === "approved") {
    return <Badge variant="success" size="sm">published</Badge>;
  }
  const variant = status === "pending" ? "warning" : "danger";
  return (
    <span title={status === "pending" ? "Awaiting Fuvay moderation before it is shown publicly." : undefined}>
      <Badge variant={variant} size="sm">{status}</Badge>
    </span>
  );
}

function KpiTile({ icon, label, value, color, onClick, active }: { icon: React.ReactNode; label: string; value: string | number; color: string; onClick?: () => void; active?: boolean }) {
  return <SummaryCard label={label} value={value} icon={icon} accent={color}
    onClick={onClick} active={active}/>;
}

function QualitySignalRow({ label, value, invert }: { label: string; value: number | null; invert?: boolean }) {
  if (value === null) return null;
  const good = invert ? value < 10 : value >= 90;
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 700, color: good ? "var(--success-text)" : "var(--warning-text)" }}>{value}%</span>
    </div>
  );
}

function RatingTrendChart({ points }: { points: { date: string; average_rating: number; review_count: number }[] }) {
  const w = 480, h = 140, pad = 20;
  const xs = points.map((_, i) => pad + (i / Math.max(points.length - 1, 1)) * (w - pad * 2));
  const ys = points.map(p => h - pad - ((p.average_rating - 1) / 4) * (h - pad * 2));
  const path = xs.map((x, i) => `${i === 0 ? "M" : "L"}${x},${ys[i]}`).join(" ");
  const current = points[points.length - 1];
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Daily average</span>
        <span style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)" }}>{current?.average_rating.toFixed(1)}</span>
      </div>
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: "block" }} role="img" aria-label="Daily average rating trend">
        <path d={path} fill="none" stroke="var(--brand)" strokeWidth={2}/>
        {xs.map((x, i) => (
          <circle key={i} cx={x} cy={ys[i]} r={2.5} fill="var(--brand)">
            <title>{`${points[i].date}: ${points[i].average_rating} avg (${points[i].review_count} review${points[i].review_count === 1 ? "" : "s"})`}</title>
          </circle>
        ))}
      </svg>
    </div>
  );
}

function ModuleUnavailable({ onRetry }: { onRetry: () => void }) {
  return (
    <div style={{ textAlign: "center", padding: "16px 0" }}>
      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 8px" }}>This section is temporarily unavailable.</p>
      <Btn variant="secondary" size="sm" icon={<RefreshCw size={11}/>} onClick={onRetry}>Retry</Btn>
    </div>
  );
}

function ReviewDetailPanel({ reviewId, onClose, onChanged }: { reviewId: string; onClose: () => void; onChanged: () => void }) {
  const router = useRouter();
  const [detail, setDetail] = useState<HsReviewDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [replyText, setReplyText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showModeration, setShowModeration] = useState(false);
  const [modReason, setModReason] = useState(MODERATION_REASONS[0].value);
  const [modExplanation, setModExplanation] = useState("");
  const [showActivity, setShowActivity] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    hsReviewsApi.get(reviewId)
      .then(setDetail)
      .catch(() => setError("We couldn't load this review."))
      .finally(() => setLoading(false));
  }, [reviewId]);

  useEffect(() => { load(); }, [load]);

  const handlePublishReply = async () => {
    if (!replyText.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await hsReviewsApi.reply(reviewId, replyText.trim());
      setReplyText("");
      load();
      onChanged();
    } catch (e) {
      setSubmitError(e instanceof ServiceOSError ? e.message : "Could not publish reply.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRequestModeration = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await hsReviewsApi.requestModeration(reviewId, REASON_CODE_MAP[modReason] ?? "other", modExplanation || undefined);
      setShowModeration(false);
      setModExplanation("");
      load();
      onChanged();
    } catch (e) {
      setSubmitError(e instanceof ServiceOSError ? e.message : "Could not submit moderation request.");
    } finally {
      setSubmitting(false);
    }
  };

  // Server decides what is allowed; the panel no longer infers it locally.
  const canReply    = detail?.available_actions.includes("REPLY") ?? false;
  const canModerate = detail?.available_actions.includes("REQUEST_MODERATION") ?? false;

  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, padding: 20, position: "sticky", top: 20, maxHeight: "calc(100vh - 40px)", overflowY: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          {detail && <Stars rating={detail.rating} size={15}/>}
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{detail?.review_number}</p>
        </div>
        <button onClick={onClose} aria-label="Close review detail" style={{ width: 28, height: 28, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
          <X size={14}/>
        </button>
      </div>

      {loading ? (
        <>{[1, 2, 3].map(i => <Skeleton key={i} height={36} style={{ marginBottom: 10 }}/>)}</>
      ) : error || !detail ? (
        <div>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", marginBottom: 10 }}>{error}</p>
          <Btn variant="secondary" size="sm" icon={<RefreshCw size={12}/>} onClick={load}>Retry</Btn>
        </div>
      ) : (
        <>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
            <PublicationBadge status={detail.review_status}/>
            {detail.job.status && <Badge variant="muted" size="sm">job: {String(detail.job.status).replace(/_/g, " ")}</Badge>}
          </div>

          <div style={{ padding: 14, borderRadius: 10, background: "var(--surface-sunken)", marginBottom: 16 }}>
            {detail.title && <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>{detail.title}</p>}
            <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0, lineHeight: 1.5 }}>
              {detail.review_text || <span style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>Rating only — the customer left no written feedback.</span>}
            </p>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "8px 0 0" }}>{detail.customer_alias} · {fmtDateTime(detail.created_at)}</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14, fontSize: 12 }}>
            <DetailField label="Service" value={detail.job.service_name}/>
            <DetailField label="Technician" value={detail.technician?.name ?? "Unassigned"}/>
            <DetailField label="Location" value={[detail.job.city, detail.job.zipcode].filter(Boolean).join(" · ") || "—"}/>
            <DetailField label="Invoice" value={detail.invoice ? `${detail.invoice.invoice_number}${detail.invoice.payment_status ? ` (${detail.invoice.payment_status})` : ""}` : "Not invoiced"}/>
          </div>

          <LinkRow icon={<ExternalLink size={13} color="var(--text-tertiary)"/>} onClick={() => router.push(`/jobs/${detail.job.job_id}`)}>
            <span style={{ fontSize: 12, color: "var(--text-primary)" }}>Open job {detail.job.job_number}</span>
          </LinkRow>

          {detail.complaint && (
            <LinkRow
              danger
              icon={<ExternalLink size={13} color="var(--danger-text)"/>}
              onClick={() => router.push(`/home-services/complaints/${detail.complaint!.complaint_id}`)}
            >
              <span style={{ fontSize: 12, color: "var(--danger-text)", fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                <AlertTriangle size={12}/>
                Complaint {detail.complaint.complaint_number} ({detail.complaint.status}
                {detail.complaint.severity ? ` · ${detail.complaint.severity}` : ""})
              </span>
            </LinkRow>
          )}

          <div style={{ height: 6 }}/>

          {/* Reply */}
          {detail.reply ? (
            <div style={{ padding: 14, borderRadius: 10, background: "var(--accent-muted)", marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6, gap: 8 }}>
                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--brand)", margin: 0 }}>Your reply</p>
                <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{fmtDate(detail.reply.created_at)}</span>
              </div>
              <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0 }}>{detail.reply.reply_text}</p>
              {detail.reply.status && detail.reply.status !== "approved" && (
                <p style={{ fontSize: 11, color: "var(--warning-text)", margin: "8px 0 0", display: "flex", alignItems: "center", gap: 4 }}>
                  <Clock size={11}/> Reply status: {detail.reply.status} — not shown publicly yet.
                </p>
              )}
            </div>
          ) : canReply ? (
            <div style={{ marginBottom: 16 }}>
              <label htmlFor="rq-reply" style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Your public reply</label>
              <textarea
                id="rq-reply"
                value={replyText} onChange={e => setReplyText(e.target.value.slice(0, 1000))}
                placeholder="Acknowledge the feedback, explain corrective action, and keep all communication within Fuvay…"
                rows={4}
                style={{ width: "100%", padding: 10, fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--text-primary)", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }}
              />
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{replyText.length} / 1000 characters — keep all communication, revisit and rebooking activity within Fuvay.</p>
              {submitError && <p role="alert" style={{ fontSize: 12, color: "var(--danger-text)", margin: "6px 0 0" }}>{submitError}</p>}
              <Btn variant="primary" size="sm" loading={submitting} disabled={!replyText.trim()} onClick={handlePublishReply} style={{ marginTop: 8 }}>Publish reply</Btn>
            </div>
          ) : null}

          {/* Moderation */}
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
            {detail.moderation ? (
              <div style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius: 10, padding: 12 }}>
                <p style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "var(--warning-text)", margin: "0 0 6px" }}>
                  <ShieldAlert size={13}/> Moderation requested — {detail.moderation.status}
                </p>
                {detail.moderation.reason_code && (
                  <p style={{ fontSize: 11.5, color: "var(--text-secondary)", margin: "0 0 3px" }}>Reason: {detail.moderation.reason_code.replace(/_/g, " ")}</p>
                )}
                {detail.moderation.reason_text && (
                  <p style={{ fontSize: 11.5, color: "var(--text-secondary)", margin: "0 0 3px" }}>{detail.moderation.reason_text}</p>
                )}
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
                  Raised {fmtDate(detail.moderation.created_at)} — only Fuvay Admin can action it.
                </p>
              </div>
            ) : showModeration ? (
              <div>
                <label htmlFor="rq-reason" style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Reason</label>
                <select id="rq-reason" value={modReason} onChange={e => setModReason(e.target.value)} style={{ ...selectStyle, marginBottom: 8 }}>
                  {MODERATION_REASONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
                <textarea
                  value={modExplanation} onChange={e => setModExplanation(e.target.value)}
                  placeholder="Explain why this review should be moderated…" rows={3}
                  style={{ width: "100%", padding: 10, fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--text-primary)", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box", marginBottom: 8 }}
                />
                {submitError && <p role="alert" style={{ fontSize: 12, color: "var(--danger-text)", margin: "0 0 6px" }}>{submitError}</p>}
                <div style={{ display: "flex", gap: 8 }}>
                  <Btn variant="secondary" size="sm" loading={submitting} onClick={handleRequestModeration}>Submit request</Btn>
                  <Btn variant="secondary" size="sm" onClick={() => setShowModeration(false)}>Cancel</Btn>
                </div>
              </div>
            ) : canModerate ? (
              <button onClick={() => setShowModeration(true)} style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", color: "var(--text-secondary)", fontSize: 12, cursor: "pointer", padding: 0, fontFamily: "inherit" }}>
                <Flag size={13}/> Request platform moderation
              </button>
            ) : null}
          </div>

          {/* Activity timeline — review_events was returned by the API but
              never rendered, so the audit trail was invisible. */}
          {detail.activity.length > 0 && (
            <div style={{ borderTop: "1px solid var(--border)", marginTop: 14, paddingTop: 14 }}>
              <button
                onClick={() => setShowActivity(v => !v)}
                aria-expanded={showActivity}
                style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", color: "var(--text-secondary)", fontSize: 12, fontWeight: 600, cursor: "pointer", padding: 0, fontFamily: "inherit" }}
              >
                {showActivity ? <EyeOff size={13}/> : <Eye size={13}/>}
                Activity ({detail.activity.length})
              </button>
              {showActivity && (
                <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                  {detail.activity.map((ev, i) => (
                    <li key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                      <FileText size={12} style={{ color: "var(--text-tertiary)", marginTop: 2, flexShrink: 0 }}/>
                      <div>
                        <p style={{ fontSize: 12, color: "var(--text-primary)", margin: 0 }}>
                          {ev.event_type.replace(/_/g, " ")}
                          {ev.actor_type ? <span style={{ color: "var(--text-tertiary)" }}> · {ev.actor_type}</span> : null}
                        </p>
                        {ev.reason && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "1px 0 0" }}>{ev.reason}</p>}
                        <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "1px 0 0" }}>{fmtDateTime(ev.occurred_at)}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function LinkRow({ children, icon, onClick, danger }: { children: React.ReactNode; icon: React.ReactNode; onClick: () => void; danger?: boolean }) {
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%",
      padding: "10px 12px", borderRadius: 10,
      background: danger ? "var(--danger-bg)" : "var(--surface-sunken)",
      border: `1px solid ${danger ? "var(--danger-border)" : "var(--border)"}`,
      marginBottom: 10, cursor: "pointer", fontFamily: "inherit", textAlign: "left",
    }}>
      {children}
      {icon}
    </button>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>{label}</p>
      <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{value}</p>
    </div>
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
export default function ReviewsQualityPage() {
  return (
    <Suspense fallback={null}>
      <ReviewsQualityPageInner />
    </Suspense>
  );
}
