"use client";
import React, { useState, useCallback, useEffect, useRef } from "react";
import { AdminLayout }  from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Select, SectionHeader, Input, Skeleton, Modal } from "../../../components/shared/ui";
import { Search, Star, MessageSquare, Flag, AlertTriangle,
         ThumbsUp, ThumbsDown, Minus, RefreshCw, Download, Filter, X } from "lucide-react";
import { adminReviewApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { CustomerReviewRecord, ReviewSummary, ReviewListMeta } from "../../../lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────
interface Filters {
  q: string; status: string; record_type: string; rating: string;
  has_reply: string; sort_by: string; sort_dir: string;
}
const DEFAULT: Filters = {
  q: "", status: "", record_type: "", rating: "",
  has_reply: "", sort_by: "created_at", sort_dir: "desc",
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function Stars({ n }: { n: number }) {
  const color = n >= 4 ? "var(--success)" : n === 3 ? "var(--warning)" : "#ef4444";
  return (
    <span style={{ display:"flex", alignItems:"center", gap:2 }}>
      {[1,2,3,4,5].map(i => (
        <Star key={i} size={11} fill={i <= n ? color : "none"}
          stroke={i <= n ? color : "var(--border)"} strokeWidth={1.5}/>
      ))}
      <span style={{ fontSize:12, fontWeight:700, color, marginLeft:3 }}>{n}</span>
    </span>
  );
}

function SentimentBadge({ s }: { s: string | undefined }) {
  if (!s) return <span style={{ color:"var(--text-tertiary)", fontSize:12 }}>—</span>;
  const cfg: Record<string,{icon: React.ElementType; color: string; bg: string}> = {
    positive: { icon: ThumbsUp,   color:"var(--success)", bg:"#dcfce7" },
    neutral:  { icon: Minus,      color:"#78716c", bg:"#f5f5f4" },
    negative: { icon: ThumbsDown, color:"var(--danger)", bg:"#fee2e2" },
  };
  const { icon: Icon, color, bg } = cfg[s] ?? cfg.neutral;
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:4, padding:"2px 8px",
      borderRadius:20, background:bg, fontSize:11, fontWeight:600, color }}>
      <Icon size={10}/>{s}
    </span>
  );
}

function StatusBadge({ s }: { s: string }) {
  const map: Record<string,[string,string]> = {
    approved:  ["var(--success)","#dcfce7"],
    pending:   ["#92400e","#fef3c7"],
    flagged:   ["var(--danger)","#fee2e2"],
    hidden:    ["#78716c","#f5f5f4"],
    rejected:  ["var(--danger)","#fee2e2"],
    deleted:   ["var(--danger)","#fee2e2"],
  };
  const [color, bg] = map[s] ?? ["#78716c","#f5f5f4"];
  return (
    <span style={{ padding:"2px 8px", borderRadius:20, fontSize:11, fontWeight:600,
      background:bg, color, textTransform:"capitalize" }}>
      {s.replace(/_/g," ")}
    </span>
  );
}

function SummaryCard({ label, value, icon: Icon, color, active, onClick }: {
  label: string; value: number | string | undefined; icon: React.ElementType;
  color: string; active?: boolean; onClick?: () => void;
}) {
  return (
    <div onClick={onClick} style={{
      background:"var(--surface)", border:`1.5px solid ${active ? color : "var(--border)"}`,
      borderRadius:"var(--radius-lg)", padding:"14px 18px", cursor:onClick ? "pointer":"default",
      display:"flex", alignItems:"center", gap:12, transition:"all 0.12s", flex:1, minWidth:130,
      boxShadow: active ? `0 0 0 3px ${color}22` : "none",
    }}>
      <div style={{ width:38, height:38, borderRadius:9, background:`${color}18`,
        display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
        <Icon size={16} color={color}/>
      </div>
      <div>
        <div style={{ fontSize:20, fontWeight:700, color:"var(--text-primary)", lineHeight:1 }}>
          {value ?? "—"}
        </div>
        <div style={{ fontSize:11, color:"var(--text-tertiary)", marginTop:3,
          fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>{label}</div>
      </div>
    </div>
  );
}

function Chip({ label, active, color="#6366f1", onClick }: {
  label: string; active: boolean; color?: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick} style={{
      padding:"5px 12px", borderRadius:20, fontSize:12, fontWeight:600, border:"none",
      cursor:"pointer", transition:"all 0.12s",
      background:active ? color : "var(--surface-sunken)",
      color:active ? "#fff" : "var(--text-secondary)",
    }}>{label}</button>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function AdminReviewsPage() {
  const [filters, setFilters]       = useState<Filters>(DEFAULT);
  const [page, setPage]             = useState(1);
  const [showAdv, setShowAdv]       = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [moderateRow, setModerateRow] = useState<CustomerReviewRecord | null>(null);
  const [moderateAction, setModerateAction] = useState<"approve"|"reject"|"hide">("approve");
  const [moderateReason, setModerateReason] = useState("");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const listParams = {
    q:           filters.q      || undefined,
    status:      filters.status || undefined,
    record_type: filters.record_type || undefined,
    rating:      filters.rating || undefined,
    has_reply:   filters.has_reply || undefined,
    sort_by:     filters.sort_by,
    sort_dir:    filters.sort_dir,
    page:        String(page),
    page_size:   "25",
  };

  const summary = useApi(useCallback(() => adminReviewApi.summary(), []));
  const reviews = useApi(useCallback(() => adminReviewApi.list(listParams), [
    filters.q, filters.status, filters.record_type, filters.rating,
    filters.has_reply, filters.sort_by, filters.sort_dir, page,
  ]));

  const approveAction = useAction(useCallback((id: string) => adminReviewApi.approve(id), []));
  const rejectAction  = useAction(useCallback((id: string, r: string) => adminReviewApi.reject(id, r), []));
  const hideAction    = useAction(useCallback((id: string, r: string) => adminReviewApi.hide(id, r), []));

  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = setInterval(() => { reviews.refetch(); summary.refetch(); }, 30000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [autoRefresh]);

  function setF<K extends keyof Filters>(k: K, v: Filters[K]) {
    setFilters(f => ({ ...f, [k]: v }));
    setPage(1);
  }
  function clearAll() { setFilters(DEFAULT); setPage(1); }

  const hasActive = filters.q || filters.status || filters.record_type
    || filters.rating || filters.has_reply;

  const sum: ReviewSummary | null = summary.data ?? null;
  const items: CustomerReviewRecord[] = reviews.data?.items ?? [];
  const meta: ReviewListMeta | null = reviews.data?.meta ?? null;

  async function handleModerate() {
    if (!moderateRow) return;
    let res = null;
    if (moderateAction === "approve") res = await approveAction.execute(moderateRow.id);
    else if (moderateAction === "reject") res = await rejectAction.execute(moderateRow.id, moderateReason);
    else res = await hideAction.execute(moderateRow.id, moderateReason);
    if (res) {
      setModerateRow(null); setModerateReason("");
      reviews.refetch(); summary.refetch();
    }
  }

  function handleExport() {
    if (!items.length) return;
    const headers = ["Review#","Rating","Sentiment","Status","Customer","Tenant","Type","Has Reply","Created"];
    const rows = items.map(r => [
      r.review_number ?? "", r.overall_rating, r.sentiment ?? "", r.status,
      r.customer_name ?? r.customer_id, r.tenant_name ?? r.tenant_id,
      r.record_type, r.has_reply ? "Yes":"No", r.created_at ?? "",
    ]);
    const csv = [headers,...rows].map(r => r.map(c => `"${String(c).replace(/"/g,'""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type:"text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = `reviews-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  }

  const moderateLoading = approveAction.loading || rejectAction.loading || hideAction.loading;
  const moderateError   = approveAction.error   || rejectAction.error   || hideAction.error;

  return (
    <AdminLayout activeNav="reviews">
      <SectionHeader
        title="Reviews"
        subtitle="Platform-wide customer review monitoring and moderation"
        actions={<>
          <Chip label={autoRefresh ? "Auto ✓":"Auto-refresh"} active={autoRefresh}
            onClick={() => setAutoRefresh(v => !v)}/>
          <Btn variant="secondary" size="sm" onClick={() => { reviews.refetch(); summary.refetch(); }}>
            <RefreshCw size={13}/> Refresh
          </Btn>
          <Btn variant="secondary" size="sm" onClick={handleExport} disabled={!items.length}>
            <Download size={13}/> Export
          </Btn>
        </>}
      />

      {/* ── Summary Cards ─────────────────────────────────────────────────── */}
      {summary.loading ? (
        <div style={{ display:"flex", gap:12, flexWrap:"wrap", marginBottom:20 }}>
          {[...Array(6)].map((_,i) => <Skeleton key={i} height={74} style={{ flex:1, minWidth:130, borderRadius:"var(--radius-lg)" }}/>)}
        </div>
      ) : (
        <div style={{ display:"flex", gap:12, flexWrap:"wrap", marginBottom:20 }}>
          <SummaryCard label="Total Reviews" value={sum?.total} icon={Star} color="#6366f1"/>
          <SummaryCard label="Avg Rating" value={sum?.avg_rating ? `${sum.avg_rating} ★` : "—"}
            icon={Star} color="var(--success)"/>
          <SummaryCard label="Low Rating (1–2★)" value={sum?.low_rating} icon={ThumbsDown} color="#ef4444"
            active={filters.rating === "2"} onClick={() => setF("rating", filters.rating === "2" ? "" : "2")}/>
          <SummaryCard label="Unreplied" value={sum?.unreplied} icon={MessageSquare} color="var(--warning)"
            active={filters.has_reply === "false"} onClick={() => setF("has_reply", filters.has_reply === "false" ? "" : "false")}/>
          <SummaryCard label="Flagged" value={sum?.flagged} icon={Flag} color="var(--danger)"
            active={filters.status === "flagged"} onClick={() => setF("status", filters.status === "flagged" ? "" : "flagged")}/>
          <SummaryCard label="Pending" value={sum?.pending_moderation} icon={AlertTriangle} color="var(--warning)"
            active={filters.status === "pending"} onClick={() => setF("status", filters.status === "pending" ? "" : "pending")}/>
        </div>
      )}

      {/* ── Filter Bar ────────────────────────────────────────────────────── */}
      <Card padding={14} style={{ marginBottom:16 }}>
        {/* Quick chips */}
        <div style={{ display:"flex", gap:8, marginBottom:12, flexWrap:"wrap" }}>
          <Chip label="1 Star"   active={filters.rating==="1"} color="#ef4444" onClick={() => setF("rating", filters.rating==="1"?"":"1")}/>
          <Chip label="2 Star"   active={filters.rating==="2"} color="#f97316" onClick={() => setF("rating", filters.rating==="2"?"":"2")}/>
          <Chip label="Negative" active={filters.rating==="2"&&!filters.status} color="#ef4444"
            onClick={() => { setF("rating","2"); setF("status",""); }}/>
          <Chip label="Unreplied" active={filters.has_reply==="false"} color="var(--warning)"
            onClick={() => setF("has_reply", filters.has_reply==="false"?"":"false")}/>
          <Chip label="Flagged"  active={filters.status==="flagged"} color="var(--danger)"
            onClick={() => setF("status", filters.status==="flagged"?"":"flagged")}/>
          <Chip label="Pending"  active={filters.status==="pending"} color="#92400e"
            onClick={() => setF("status", filters.status==="pending"?"":"pending")}/>
          {hasActive && (
            <button onClick={clearAll} style={{
              padding:"5px 10px", borderRadius:20, fontSize:12, fontWeight:600, border:"none",
              cursor:"pointer", background:"var(--danger-bg)", color:"var(--danger-text)",
              display:"flex", alignItems:"center", gap:4 }}>
              <X size={11}/> Clear all
            </button>
          )}
        </div>
        {/* Main toolbar */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr auto auto auto auto", gap:10, alignItems:"end" }}>
          <Input placeholder="Search review text, customer, tenant, booking #…"
            value={filters.q} onChange={v => setF("q", v)} icon={<Search size={14}/>}/>
          <Select label="" value={filters.status} onChange={v => setF("status", v)}
            placeholder="All statuses" options={[
              { value:"pending",  label:"Pending"  },
              { value:"approved", label:"Approved" },
              { value:"flagged",  label:"Flagged"  },
              { value:"hidden",   label:"Hidden"   },
              { value:"rejected", label:"Rejected" },
            ]}/>
          <Select label="" value={filters.rating} onChange={v => setF("rating", v)}
            placeholder="All ratings" options={[
              { value:"5", label:"5 ★" }, { value:"4", label:"4 ★" },
              { value:"3", label:"3 ★" }, { value:"2", label:"2 ★" },
              { value:"1", label:"1 ★" },
            ]}/>
          <Btn variant={showAdv?"primary":"secondary"} size="sm" onClick={() => setShowAdv(v => !v)}>
            <Filter size={13}/> {showAdv?"Hide":"Filters"}
          </Btn>
          <Select label="" value={`${filters.sort_by}:${filters.sort_dir}`}
            onChange={v => { const [by,dir]=v.split(":"); setF("sort_by",by); setF("sort_dir",dir); }}
            placeholder="Sort" options={[
              { value:"created_at:desc",     label:"Newest first"    },
              { value:"created_at:asc",      label:"Oldest first"    },
              { value:"overall_rating:asc",  label:"Lowest rating"   },
              { value:"overall_rating:desc", label:"Highest rating"  },
              { value:"submitted_at:desc",   label:"Recently submitted" },
            ]}/>
        </div>
        {/* Advanced */}
        {showAdv && (
          <div style={{ marginTop:14, paddingTop:14, borderTop:"1px solid var(--border)",
            display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10 }}>
            <Select label="Record Type" value={filters.record_type} onChange={v => setF("record_type", v)}
              placeholder="All types" options={[
                { value:"service_job",          label:"Service Job"          },
                { value:"service_booking",      label:"Service Booking"      },
                { value:"coaching_appointment", label:"Coaching Appointment" },
                { value:"real_estate_lead",     label:"Real Estate Lead"     },
              ]}/>
            <Select label="Reply Status" value={filters.has_reply} onChange={v => setF("has_reply", v)}
              placeholder="Any" options={[
                { value:"true",  label:"Has Reply"    },
                { value:"false", label:"No Reply Yet" },
              ]}/>
          </div>
        )}
      </Card>

      {/* ── Error State ───────────────────────────────────────────────────── */}
      {reviews.error && (
        <div style={{ padding:"14px 18px", borderRadius:10, background:"var(--danger-bg)",
          border:"1px solid var(--danger-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--danger-text)", margin:"0 0 8px", fontWeight:600 }}>
            Could not load reviews
          </p>
          <p style={{ fontSize:12, color:"var(--danger-text)", margin:"0 0 10px", opacity:0.8 }}>
            {reviews.error}
          </p>
          <Btn variant="secondary" size="sm" onClick={() => reviews.refetch()}>Retry</Btn>
        </div>
      )}

      {/* ── Table ─────────────────────────────────────────────────────────── */}
      <Card padding={0} style={{ overflow:"hidden" }}>
        <div style={{ overflowX:"auto" }}>
          <table style={{ width:"100%", borderCollapse:"collapse", minWidth:1000 }}>
            <thead>
              <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                {["Rating","Review","Customer","Tenant","Type","Status","Sentiment","Reply","Created",""].map(h => (
                  <th key={h} style={{ padding:"10px 14px", textAlign:"left", fontSize:11,
                    fontWeight:700, color:"var(--text-tertiary)",
                    letterSpacing:"0.06em", textTransform:"uppercase", whiteSpace:"nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {reviews.loading ? (
                [...Array(8)].map((_,i) => (
                  <tr key={i}><td colSpan={10} style={{ padding:"10px 14px" }}><Skeleton height={18}/></td></tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ padding:"60px 20px", textAlign:"center" }}>
                    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:12 }}>
                      <Star size={36} style={{ opacity:0.15 }}/>
                      <p style={{ fontSize:14, color:"var(--text-tertiary)", margin:0, fontWeight:500 }}>
                        {hasActive ? "No reviews match your filters"
                          : "No reviews yet — they appear after completed bookings"}
                      </p>
                      {hasActive && <Btn variant="secondary" size="sm" onClick={clearAll}>Clear filters</Btn>}
                    </div>
                  </td>
                </tr>
              ) : items.map((rv, i) => (
                <ReviewRow key={rv.id} rv={rv} index={i} total={items.length}
                  onView={() => window.location.href = `/admin/reviews/${rv.id}`}
                  onModerate={(action) => { setModerateRow(rv); setModerateAction(action); setModerateReason(""); }}/>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!reviews.loading && meta && (
          <div style={{ padding:"12px 16px", borderTop:"1px solid var(--border)",
            display:"flex", alignItems:"center", justifyContent:"space-between" }}>
            <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>
              {meta.total.toLocaleString()} total · showing page {meta.page} of {meta.total_pages}
            </span>
            <div style={{ display:"flex", gap:8 }}>
              <Btn variant="secondary" size="sm" disabled={!meta.has_previous} onClick={() => setPage(p=>p-1)}>← Prev</Btn>
              <span style={{ fontSize:12, color:"var(--text-secondary)", padding:"0 8px", display:"flex", alignItems:"center" }}>
                {page}
              </span>
              <Btn variant="secondary" size="sm" disabled={!meta.has_next} onClick={() => setPage(p=>p+1)}>Next →</Btn>
            </div>
          </div>
        )}
      </Card>

      {/* ── Moderation Modal ──────────────────────────────────────────────── */}
      <Modal open={!!moderateRow} onClose={() => setModerateRow(null)}
        title={moderateAction === "approve" ? "Approve Review" : moderateAction === "reject" ? "Reject Review" : "Hide Review"}>
        {moderateRow && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ padding:"10px 14px", borderRadius:"var(--radius-md)", background:"var(--surface-sunken)",
              border:"1px solid var(--border)" }}>
              <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 2px" }}>
                {moderateRow.review_number} — {moderateRow.review_title ?? "Untitled Review"}
              </p>
              <div style={{ display:"flex", alignItems:"center", gap:8, marginTop:4 }}>
                <Stars n={moderateRow.overall_rating}/>
                <StatusBadge s={moderateRow.status}/>
              </div>
              {moderateRow.review_text && (
                <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"6px 0 0",
                  display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical", overflow:"hidden" }}>
                  {moderateRow.review_text}
                </p>
              )}
            </div>
            {moderateAction !== "approve" && (
              <div>
                <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)",
                  display:"block", marginBottom:6 }}>
                  Reason {moderateAction === "reject" ? "for Rejection" : "for Hiding"}
                </label>
                <textarea value={moderateReason} onChange={e => setModerateReason(e.target.value)}
                  placeholder={moderateAction === "reject" ? "Policy violation reason…" : "Why is this being hidden?"}
                  rows={3} style={{ width:"100%", padding:"8px 10px", fontSize:13, fontFamily:"inherit",
                    borderRadius:"var(--radius-md)", border:"1px solid var(--border)", background:"var(--surface)",
                    color:"var(--text-primary)", outline:"none", resize:"vertical", boxSizing:"border-box" }}/>
              </div>
            )}
            {moderateError && <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{moderateError}</p>}
            <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
              <Btn variant="secondary" size="sm" onClick={() => setModerateRow(null)}>Cancel</Btn>
              <Btn variant={moderateAction==="approve"?"primary":"danger"} size="sm"
                loading={moderateLoading} onClick={handleModerate}>
                {moderateAction === "approve" ? "Approve" : moderateAction === "reject" ? "Reject" : "Hide"}
              </Btn>
            </div>
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}

// ── ReviewRow (hooks at top level) ─────────────────────────────────────────────
function ReviewRow({ rv, index, total, onView, onModerate }: {
  rv: CustomerReviewRecord; index: number; total: number;
  onView: () => void;
  onModerate: (action: "approve"|"reject"|"hide") => void;
}) {
  const [hov, setHov] = React.useState(false);
  const isFlagged  = rv.status === "flagged";
  const isPending  = rv.status === "pending";
  const isLowRating = rv.overall_rating <= 2;
  const rowBg = isFlagged ? "var(--danger-bg)" : isPending ? "var(--warning-bg)" : "transparent";
  return (
    <tr
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      onClick={onView}
      style={{ borderBottom:index<total-1?"1px solid var(--border)":"none",
        background:hov?"var(--surface-sunken)":rowBg, cursor:"pointer", transition:"background 0.1s" }}>
      <td style={{ padding:"11px 14px", whiteSpace:"nowrap" }}>
        <Stars n={rv.overall_rating}/>
      </td>
      <td style={{ padding:"11px 14px", maxWidth:200 }}>
        <p style={{ fontSize:12, fontWeight:600, color:isLowRating?"var(--danger-text)":"var(--text-primary)",
          margin:"0 0 2px", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
          {rv.review_title || "No title"}
        </p>
        <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0,
          overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
          {rv.review_text ? rv.review_text.slice(0,60) + (rv.review_text.length>60?"…":"") : ""}
        </p>
        {rv.review_number && (
          <span style={{ fontSize:10, color:"var(--text-tertiary)", fontFamily:"monospace" }}>
            {rv.review_number}
          </span>
        )}
      </td>
      <td style={{ padding:"11px 14px", fontSize:12, color:"var(--text-secondary)", maxWidth:120 }}>
        <span style={{ display:"block", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
          {rv.customer_name || "—"}
        </span>
      </td>
      <td style={{ padding:"11px 14px", fontSize:12, color:"var(--text-secondary)", maxWidth:120 }}>
        <span style={{ display:"block", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
          {rv.tenant_name || "—"}
        </span>
      </td>
      <td style={{ padding:"11px 14px" }}>
        <span style={{ fontSize:11, fontWeight:500, color:"var(--text-tertiary)",
          background:"var(--surface-sunken)", padding:"2px 7px", borderRadius:5 }}>
          {rv.record_type?.replace(/_/g," ") || "—"}
        </span>
      </td>
      <td style={{ padding:"11px 14px" }}>
        <StatusBadge s={rv.status}/>
      </td>
      <td style={{ padding:"11px 14px" }}>
        <SentimentBadge s={rv.sentiment}/>
      </td>
      <td style={{ padding:"11px 14px" }}>
        {rv.has_reply ? (
          <span style={{ fontSize:11, fontWeight:600, color:"var(--success)",
            display:"flex", alignItems:"center", gap:4 }}>
            <MessageSquare size={11}/> Replied
          </span>
        ) : (
          <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>No reply</span>
        )}
      </td>
      <td style={{ padding:"11px 14px", fontSize:12, color:"var(--text-tertiary)", whiteSpace:"nowrap" }}>
        {rv.created_at ? rv.created_at.slice(0,10) : "—"}
      </td>
      <td style={{ padding:"11px 14px" }} onClick={e => e.stopPropagation()}>
        <div style={{ display:"flex", gap:5 }}>
          <Btn variant="ghost" size="sm" onClick={onView}>View</Btn>
          {rv.status === "pending" && (
            <Btn variant="primary" size="sm" onClick={() => onModerate("approve")}>Approve</Btn>
          )}
          {rv.status !== "rejected" && rv.status !== "deleted" && rv.status !== "hidden" && (
            <Btn variant="danger" size="sm" onClick={() => onModerate("hide")}>Hide</Btn>
          )}
        </div>
      </td>
    </tr>
  );
}
