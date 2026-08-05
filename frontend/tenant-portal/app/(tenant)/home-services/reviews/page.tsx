"use client";
/**
 * Reviews & Service Quality — canonical customer_reviews/review_replies/
 * review_flags system (Sprint 24), joined to real service_jobs/technicians/
 * complaints via GET /v1/tenant/home-services/reviews. No second review
 * engine or quality score -- see hs_quality_service.py.
 *
 * Reply/moderation-request mutations call the EXISTING, already-secured
 * /v1/provider/reviews/{id}/reply and /flag endpoints.
 */
import React, { useCallback, useEffect, useMemo, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  RefreshCw, Search, Star, MessageSquare, TrendingDown, HelpCircle, Flag,
  X, ExternalLink, ShieldAlert, CheckCircle2, Info, Download,
} from "lucide-react";
import { hsReviewsApi, ServiceOSError, type HsReviewListItem, type HsReviewDetail } from "../../../../lib/api";
import { Skeleton, Btn, Badge } from "../../../../components/shared/ui";

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

function Stars({ rating }: { rating: number }) {
  return (
    <span style={{ display: "inline-flex", gap: 1 }}>
      {[1, 2, 3, 4, 5].map(i => (
        <Star key={i} size={13} fill={i <= rating ? "var(--warning-text)" : "none"} color={i <= rating ? "var(--warning-text)" : "var(--border)"}/>
      ))}
    </span>
  );
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function ReviewsQualityPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [rating, setRating] = useState<number | undefined>(searchParams.get("rating") ? Number(searchParams.get("rating")) : undefined);
  const [replyStatus, setReplyStatus] = useState(searchParams.get("reply_status") ?? "");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get("review_id"));

  const [data, setData] = useState<{
    reviews: HsReviewListItem[]; total: number; summary: HsReviewsListResponseSummary | null;
    trend: { date: string; average_rating: number; review_count: number }[];
    distribution: { stars: number; count: number; percent: number }[];
    quality: { sla_met_percent: number | null; rework_rate_percent: number | null; complaint_after_completion_percent: number | null; sample_size: number } | null;
    failed: string[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    hsReviewsApi.list({ rating, reply_status: replyStatus || undefined, search: search || undefined, limit: 10 })
      .then(r => setData({
        reviews: r.reviews, total: r.total, summary: r.summary,
        trend: r.rating_trend, distribution: r.rating_distribution, quality: r.quality_signals,
        failed: r.failed_modules,
      }))
      .catch((e: unknown) => setError(e instanceof ServiceOSError ? e.message : "We couldn't load reviews."))
      .finally(() => setLoading(false));
  }, [rating, replyStatus, search]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const qs = new URLSearchParams();
    if (rating) qs.set("rating", String(rating));
    if (replyStatus) qs.set("reply_status", replyStatus);
    if (selectedId) qs.set("review_id", selectedId);
    router.replace(`/home-services/reviews${qs.toString() ? `?${qs}` : ""}`, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rating, replyStatus, selectedId]);

  const [exporting, setExporting] = useState(false);
  const handleExport = async () => {
    setExporting(true);
    try {
      // Re-fetch the full filtered set page by page (backend caps limit at
      // 100 per request) rather than just the current page's 10 rows -- only
      // masked fields are included, matching the shape already in the queue.
      const all: HsReviewListItem[] = [];
      let offset = 0;
      for (;;) {
        const page_ = await hsReviewsApi.list({ rating, reply_status: replyStatus || undefined, search: search || undefined, limit: 100, offset });
        all.push(...page_.reviews);
        offset += page_.reviews.length;
        if (page_.reviews.length < 100 || all.length >= page_.total) break;
      }
      const header = ["Review #", "Customer", "Rating", "Job #", "Service", "Technician", "Reply status", "Complaint linked", "Moderation status", "Date"];
      const rows = all.map(r => [
        r.review_number, r.customer_alias, String(r.rating), r.job_number, r.service_name,
        r.technician_name ?? "", r.reply_status, r.complaint_linked ? "yes" : "no",
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

  const failed = new Set(data?.failed ?? []);
  const kpis = data?.summary;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap", marginBottom: 20 }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 4px", textTransform: "uppercase" }}>Customers</p>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px" }}>Reviews & Service Quality</h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>Respond to customer feedback and improve service quality with job-linked evidence.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="secondary" size="sm" icon={<Download size={13}/>} loading={exporting} onClick={handleExport}>Export</Btn>
          <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={load}>Refresh</Btn>
        </div>
      </div>

      {/* ── KPI tiles ─────────────────────────────────────────────────── */}
      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: 20 }}>
          {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} height={80}/>)}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: 20 }}>
          <KpiTile icon={<MessageSquare size={18}/>} label="Reviews" value={kpis?.reviews ?? "—"} color="var(--text-primary)"/>
          <KpiTile icon={<Star size={18}/>} label="Average rating" value={kpis?.average_rating ?? "—"} color="var(--warning-text)"/>
          <KpiTile icon={<CheckCircle2 size={18}/>} label="Response rate" value={kpis ? `${kpis.response_rate}%` : "—"} color="var(--success-text)"/>
          <KpiTile icon={<TrendingDown size={18}/>} label="Low ratings" value={kpis?.low_ratings ?? "—"} color="var(--danger-text)" onClick={() => setRating(rating === 2 ? undefined : 2)} active={rating === 2}/>
          <KpiTile icon={<HelpCircle size={18}/>} label="Unanswered" value={kpis?.unanswered ?? "—"} color="var(--warning-text)" onClick={() => setReplyStatus(replyStatus === "unanswered" ? "" : "unanswered")} active={replyStatus === "unanswered"}/>
          <KpiTile icon={<Flag size={18}/>} label="Flagged" value={kpis?.flagged ?? "—"} color="var(--danger-text)"/>
        </div>
      )}

      {/* ── Analytics band ────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 16, marginBottom: 20 }} className="rq-analytics-grid">
        <style>{`@media (max-width: 1100px) { .rq-analytics-grid { grid-template-columns: 1fr !important; } }`}</style>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Rating trend</h3>
          {failed.has("rating_trend") ? <ModuleUnavailable onRetry={load}/> : !data?.trend.length ? (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Not enough data in this period yet.</p>
          ) : (
            <RatingTrendChart points={data.trend}/>
          )}
        </div>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Rating distribution</h3>
          {failed.has("rating_distribution") ? <ModuleUnavailable onRetry={load}/> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(data?.distribution ?? []).map(d => (
                <div key={d.stars} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)", width: 46, flexShrink: 0 }}>{d.stars} stars</span>
                  <div style={{ flex: 1, height: 8, background: "var(--surface-sunken)", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{ width: `${d.percent}%`, height: "100%", background: d.stars >= 4 ? "var(--success-text)" : d.stars === 3 ? "var(--warning-text)" : "var(--danger-text)" }}/>
                  </div>
                  <span style={{ fontSize: 12, color: "var(--text-tertiary)", width: 32, textAlign: "right", flexShrink: 0 }}>{d.percent}%</span>
                </div>
              ))}
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "8px 0 0" }}>Based on {kpis?.reviews ?? 0} reviews</p>
            </div>
          )}
        </div>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 6 }}>
            Quality signals <span title="Calculated from real completed jobs and complaints in this period."><Info size={13} color="var(--text-tertiary)"/></span>
          </h3>
          {failed.has("quality_signals") ? <ModuleUnavailable onRetry={load}/> : !data?.quality || data.quality.sample_size === 0 ? (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Not enough completed jobs yet.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <QualitySignalRow label="SLA met" value={data.quality.sla_met_percent}/>
              <QualitySignalRow label="Rework rate" value={data.quality.rework_rate_percent} invert/>
              <QualitySignalRow label="Complaint after completion" value={data.quality.complaint_after_completion_percent} invert/>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>Sample: {data.quality.sample_size} completed jobs</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Queue + detail split ──────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: selectedId ? "1.3fr 1fr" : "1fr", gap: 16, alignItems: "start" }} className="rq-split-grid">
        <style>{`@media (max-width: 1200px) { .rq-split-grid { grid-template-columns: 1fr !important; } }`}</style>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, overflow: "hidden" }}>
          <div style={{ padding: 16, borderBottom: "1px solid var(--border)", display: "flex", gap: 10, flexWrap: "wrap" }}>
            <div style={{ position: "relative", flex: 1, minWidth: 180 }}>
              <Search size={14} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
              <input
                placeholder="Search reviews…"
                value={search} onChange={e => setSearch(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") load(); }}
                style={{ width: "100%", height: 34, padding: "0 12px 0 32px", fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", color: "var(--text-primary)", outline: "none", fontFamily: "inherit" }}
              />
            </div>
            <select value={rating ?? ""} onChange={e => setRating(e.target.value ? Number(e.target.value) : undefined)} style={selectStyle}>
              <option value="">All ratings</option>
              {[5, 4, 3, 2, 1].map(r => <option key={r} value={r}>{r} stars</option>)}
            </select>
            <select value={replyStatus} onChange={e => setReplyStatus(e.target.value)} style={selectStyle}>
              <option value="">All replies</option>
              <option value="answered">Answered</option>
              <option value="unanswered">Unanswered</option>
            </select>
          </div>

          {loading ? (
            <div style={{ padding: 20 }}>{[1, 2, 3].map(i => <Skeleton key={i} height={50} style={{ marginBottom: 8 }}/>)}</div>
          ) : error ? (
            <div style={{ textAlign: "center", padding: "32px 16px" }}>
              <p style={{ fontSize: 14, color: "var(--text-primary)", margin: "0 0 12px" }}>{error}</p>
              <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={load}>Retry</Btn>
            </div>
          ) : !data || data.reviews.length === 0 ? (
            <div style={{ textAlign: "center", padding: "48px 16px" }}>
              <MessageSquare size={28} color="var(--text-tertiary)" style={{ marginBottom: 10 }}/>
              <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>No reviews match your filters.</p>
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
                  <p style={{ fontSize: 13, color: "var(--text-primary)", margin: "0 0 6px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{rv.review_excerpt}</p>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                    <Badge variant="muted" size="sm">{rv.job_number}</Badge>
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{rv.service_name}{rv.technician_name ? ` · ${rv.technician_name}` : ""}</span>
                    <Badge variant={rv.reply_status === "answered" ? "success" : "warning"} size="sm">{rv.reply_status}</Badge>
                    {rv.complaint_linked && <Badge variant="danger" size="sm">complaint</Badge>}
                    {rv.moderation_status && <Badge variant="warning" size="sm">moderation: {rv.moderation_status}</Badge>}
                  </div>
                </button>
              ))}
              <p style={{ padding: "12px 16px", fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Showing {data.reviews.length} of {data.total} reviews</p>
            </div>
          )}
        </div>

        {selectedId && <ReviewDetailPanel reviewId={selectedId} onClose={() => setSelectedId(null)} onChanged={load}/>}
      </div>
    </div>
  );
}

interface HsReviewsListResponseSummary { reviews: number; average_rating: number | null; response_rate: number; low_ratings: number; unanswered: number; flagged: number; }

const selectStyle: React.CSSProperties = {
  height: 34, padding: "0 10px", fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)",
  borderRadius: "var(--radius-lg)", color: "var(--text-primary)", fontFamily: "inherit",
};

function KpiTile({ icon, label, value, color, onClick, active }: { icon: React.ReactNode; label: string; value: string | number; color: string; onClick?: () => void; active?: boolean }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 12, textAlign: "left", padding: "14px 16px",
      background: "var(--surface)", border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
      borderRadius: 14, cursor: onClick ? "pointer" : "default", fontFamily: "inherit", width: "100%", boxSizing: "border-box",
    }}>
      <span style={{ color }}>{icon}</span>
      <div>
        <p style={{ fontSize: 20, fontWeight: 800, color, margin: 0, lineHeight: 1.1 }}>{value}</p>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{label}</p>
      </div>
    </Tag>
  );
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
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: "block" }}>
        <path d={path} fill="none" stroke="var(--brand)" strokeWidth={2}/>
        {xs.map((x, i) => <circle key={i} cx={x} cy={ys[i]} r={2.5} fill="var(--brand)"/>)}
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
  const [modSubmitted, setModSubmitted] = useState(false);

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
      setModSubmitted(true);
      load();
      onChanged();
    } catch (e) {
      setSubmitError(e instanceof ServiceOSError ? e.message : "Could not submit moderation request.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, padding: 20, position: "sticky", top: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          {detail && <Stars rating={detail.rating}/>}
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{detail?.review_number}</p>
        </div>
        <button onClick={onClose} style={{ width: 28, height: 28, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
          <X size={14}/>
        </button>
      </div>

      {loading ? (
        <>{[1, 2, 3].map(i => <Skeleton key={i} height={36} style={{ marginBottom: 10 }}/>)}</>
      ) : error || !detail ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>{error}</p>
      ) : (
        <>
          <div style={{ padding: 14, borderRadius: 10, background: "var(--surface-sunken)", marginBottom: 16 }}>
            <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0, lineHeight: 1.5 }}>{detail.review_text}</p>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "8px 0 0" }}>{detail.customer_alias} · {fmtDate(detail.created_at)}</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16, fontSize: 12 }}>
            <DetailField label="Service" value={detail.job.service_name}/>
            <DetailField label="Technician" value={detail.technician?.name ?? "Unassigned"}/>
          </div>

          <button onClick={() => router.push(`/jobs/${detail.job.job_id}`)} style={{
            display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%",
            padding: "10px 12px", borderRadius: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)",
            marginBottom: 10, cursor: "pointer", fontFamily: "inherit",
          }}>
            <span style={{ fontSize: 12, color: "var(--text-primary)" }}>Open job {detail.job.job_number}</span>
            <ExternalLink size={13} color="var(--text-tertiary)"/>
          </button>

          {detail.complaint && (
            <button onClick={() => router.push(`/complaints?id=${detail.complaint!.complaint_id}`)} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%",
              padding: "10px 12px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
              marginBottom: 16, cursor: "pointer", fontFamily: "inherit",
            }}>
              <span style={{ fontSize: 12, color: "var(--danger-text)", fontWeight: 600 }}>Open complaint {detail.complaint.complaint_number} ({detail.complaint.status})</span>
              <ExternalLink size={13} color="var(--danger-text)"/>
            </button>
          )}

          {detail.reply ? (
            <div style={{ padding: 14, borderRadius: 10, background: "var(--accent-muted)", marginBottom: 16 }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--brand)", margin: "0 0 6px" }}>Your reply</p>
              <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0 }}>{detail.reply.reply_text}</p>
            </div>
          ) : (
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Your public reply</label>
              <textarea
                value={replyText} onChange={e => setReplyText(e.target.value.slice(0, 1000))}
                placeholder="Acknowledge the feedback, explain corrective action, and keep all communication within ServiceOS…"
                rows={4}
                style={{ width: "100%", padding: 10, fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--text-primary)", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }}
              />
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{replyText.length} / 1000 characters — keep all communication, revisit and rebooking activity within ServiceOS.</p>
              {submitError && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "6px 0 0" }}>{submitError}</p>}
              <Btn variant="primary" size="sm" loading={submitting} onClick={handlePublishReply} style={{ marginTop: 8 }}>Publish reply</Btn>
            </div>
          )}

          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
            {detail.moderation ? (
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--warning-text)" }}>
                <ShieldAlert size={14}/> Moderation requested — {detail.moderation.status}
              </div>
            ) : modSubmitted ? (
              <p style={{ fontSize: 12, color: "var(--success-text)" }}>Moderation request submitted. Only ServiceOS Admin can act on it.</p>
            ) : showModeration ? (
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Reason</label>
                <select value={modReason} onChange={e => setModReason(e.target.value)} style={{ ...selectStyle, width: "100%", marginBottom: 8 }}>
                  {MODERATION_REASONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
                <textarea
                  value={modExplanation} onChange={e => setModExplanation(e.target.value)}
                  placeholder="Explain why this review should be moderated…" rows={3}
                  style={{ width: "100%", padding: 10, fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--text-primary)", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box", marginBottom: 8 }}
                />
                <div style={{ display: "flex", gap: 8 }}>
                  <Btn variant="secondary" size="sm" loading={submitting} onClick={handleRequestModeration}>Submit request</Btn>
                  <Btn variant="secondary" size="sm" onClick={() => setShowModeration(false)}>Cancel</Btn>
                </div>
              </div>
            ) : (
              <button onClick={() => setShowModeration(true)} style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", color: "var(--text-secondary)", fontSize: 12, cursor: "pointer", padding: 0 }}>
                <Flag size={13}/> Request platform moderation
              </button>
            )}
          </div>
        </>
      )}
    </div>
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
