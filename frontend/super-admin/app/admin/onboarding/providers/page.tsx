"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Skeleton } from "../../../../components/shared/ui";
import {
  Search, RefreshCw, ChevronRight, ClipboardList, CheckCircle,
  XCircle, AlertTriangle, MessageSquare, Users, X,
} from "lucide-react";
import {
  adminOnboardingProvidersApi, categoryRuntimeApi,
  type AdminOnboardingProviderListItem,
  type OnboardingProviderSummary,
  type ServiceCategory,
} from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import Link from "next/link";

const PAGE_SIZE = 25;

const REVIEW_STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "not_submitted",     label: "Not Submitted" },
  { value: "pending_review",    label: "Pending Review" },
  { value: "changes_requested", label: "Changes Requested" },
  { value: "rejected",          label: "Rejected" },
];

const VERTICAL_OPTIONS = [
  { value: "", label: "All Verticals" },
  { value: "home_services",        label: "Home Services" },
  { value: "coaching",             label: "Coaching" },
  { value: "real_estate",          label: "Real Estate" },
  { value: "salon",                label: "Salon" },
  { value: "restaurant",           label: "Restaurant" },
  { value: "automotive",           label: "Automotive" },
  { value: "professional_services",label: "Professional Services" },
];

// ── Sub-components ──────────────────────────────────────────────────────────

function SummaryCard({
  label, count, color, active, onClick,
}: { label: string; count: number; color: string; active?: boolean; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: "1 1 160px", minWidth: 140, padding: "14px 16px",
        background: active ? color + "15" : "var(--surface)",
        border: `1.5px solid ${active ? color : "var(--border)"}`,
        borderRadius: 10, cursor: onClick ? "pointer" : "default",
        textAlign: "left", transition: "all 0.15s",
      }}
    >
      <p style={{ fontSize: 22, fontWeight: 700, color, margin: 0, lineHeight: 1 }}>{count}</p>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 0", fontWeight: 500 }}>{label}</p>
    </button>
  );
}

function ReviewBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; variant: "success" | "danger" | "warning" | "muted" | "info" }> = {
    approved:          { label: "Approved",          variant: "success" },
    rejected:          { label: "Rejected",           variant: "danger"  },
    pending_review:    { label: "Pending Review",     variant: "info"    },
    changes_requested: { label: "Changes Requested",  variant: "warning" },
    not_submitted:     { label: "Not Submitted",      variant: "muted"   },
  };
  const cfg = map[status] ?? { label: status, variant: "muted" as const };
  return <Badge variant={cfg.variant} size="sm">{cfg.label}</Badge>;
}

function ReadinessBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string }> = {
    approved:         { label: "Approved",       color: "#059669" },
    ready_for_review: { label: "Ready",          color: "#2563eb" },
    ready_to_submit:  { label: "Ready to Submit",color: "#7c3aed" },
    needs_changes:    { label: "Needs Changes",  color: "#d97706" },
    rejected:         { label: "Rejected",       color: "#dc2626" },
    incomplete:       { label: "Incomplete",     color: "#6b7280" },
  };
  const cfg = map[status] ?? { label: status, color: "#6b7280" };
  return (
    <span style={{ fontSize: 11, fontWeight: 600, color: cfg.color, padding: "2px 8px",
      background: cfg.color + "15", borderRadius: 20, border: `1px solid ${cfg.color}30`,
      whiteSpace: "nowrap" }}>
      {cfg.label}
    </span>
  );
}

function ProgressBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "#059669" : pct >= 40 ? "#d97706" : "#2563eb";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7, minWidth: 90 }}>
      <div style={{ flex: 1, height: 5, background: "var(--surface-sunken)",
        borderRadius: 3, border: "1px solid var(--border)", overflow: "hidden" }}>
        <div style={{ height: "100%", borderRadius: 3, background: color,
          width: `${Math.max(0, Math.min(100, pct))}%`, transition: "width 0.3s" }}/>
      </div>
      <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-primary)", minWidth: 28, textAlign: "right" }}>
        {pct}%
      </span>
    </div>
  );
}

// ── Modal: Reject ───────────────────────────────────────────────────────────

function RejectModal({
  tenant, onClose, onDone,
}: { tenant: AdminOnboardingProviderListItem; onClose: () => void; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function submit() {
    if (!reason.trim()) { setErr("Reason is required"); return; }
    setLoading(true); setErr("");
    try {
      await adminOnboardingProvidersApi.reject(tenant.tenant_id, reason.trim());
      onDone();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to reject");
    } finally { setLoading(false); }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 9999,
      display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "var(--surface)", borderRadius: 12, width: 440, padding: 24,
        boxShadow: "0 20px 60px rgba(0,0,0,0.3)", border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#dc2626", margin: 0 }}>Reject Provider</h3>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "3px 0 0" }}>
              {tenant.business_name ?? tenant.tenant_name}
            </p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer",
            color: "var(--text-tertiary)", padding: 2 }}><X size={16}/></button>
        </div>
        <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: 6 }}>
          Rejection Reason *
        </label>
        <textarea value={reason} onChange={e => setReason(e.target.value)}
          placeholder="Explain why this provider is being rejected…"
          rows={4}
          style={{ width: "100%", padding: "10px 12px", borderRadius: 8, fontSize: 13,
            border: "1.5px solid var(--border)", background: "var(--surface-sunken)",
            color: "var(--text-primary)", resize: "vertical", boxSizing: "border-box", outline: "none" }}/>
        {err && <p style={{ fontSize: 12, color: "#dc2626", margin: "8px 0 0" }}>{err}</p>}
        <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
          <Btn size="sm" variant="secondary" onClick={onClose} disabled={loading}>Cancel</Btn>
          <Btn size="sm" variant="danger" onClick={submit} disabled={loading || !reason.trim()}>
            {loading ? "Rejecting…" : "Reject Provider"}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Request Changes ──────────────────────────────────────────────────

function RequestChangesModal({
  tenant, onClose, onDone,
}: { tenant: AdminOnboardingProviderListItem; onClose: () => void; onDone: () => void }) {
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function submit() {
    setLoading(true); setErr("");
    try {
      await adminOnboardingProvidersApi.requestChanges(tenant.tenant_id, notes.trim());
      onDone();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to request changes");
    } finally { setLoading(false); }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 9999,
      display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "var(--surface)", borderRadius: 12, width: 440, padding: 24,
        boxShadow: "0 20px 60px rgba(0,0,0,0.3)", border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "#d97706", margin: 0 }}>Request Changes</h3>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "3px 0 0" }}>
              {tenant.business_name ?? tenant.tenant_name}
            </p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer",
            color: "var(--text-tertiary)", padding: 2 }}><X size={16}/></button>
        </div>
        <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: 6 }}>
          Notes for Provider (optional)
        </label>
        <textarea value={notes} onChange={e => setNotes(e.target.value)}
          placeholder="Describe what changes are needed…"
          rows={4}
          style={{ width: "100%", padding: "10px 12px", borderRadius: 8, fontSize: 13,
            border: "1.5px solid var(--border)", background: "var(--surface-sunken)",
            color: "var(--text-primary)", resize: "vertical", boxSizing: "border-box", outline: "none" }}/>
        {err && <p style={{ fontSize: 12, color: "#dc2626", margin: "8px 0 0" }}>{err}</p>}
        <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
          <Btn size="sm" variant="secondary" onClick={onClose} disabled={loading}>Cancel</Btn>
          <Btn size="sm" variant="warning" onClick={submit} disabled={loading}>
            {loading ? "Sending…" : "Request Changes"}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Approve Confirm ──────────────────────────────────────────────────

function ApproveModal({
  tenant, onClose, onDone,
}: { tenant: AdminOnboardingProviderListItem; onClose: () => void; onDone: () => void }) {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function submit() {
    setLoading(true); setErr("");
    try {
      await adminOnboardingProvidersApi.approve(tenant.tenant_id);
      onDone();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to approve");
    } finally { setLoading(false); }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 9999,
      display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "var(--surface)", borderRadius: 12, width: 400, padding: 24,
        boxShadow: "0 20px 60px rgba(0,0,0,0.3)", border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Approve Provider</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer",
            color: "var(--text-tertiary)", padding: 2 }}><X size={16}/></button>
        </div>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px" }}>
          Approve <strong>{tenant.business_name ?? tenant.tenant_name}</strong>? This will activate their account and start their package if selected.
        </p>
        {(tenant.profile_completion_percentage ?? 0) < 100 && (
          <div style={{ padding: "10px 12px", borderRadius: 8, background: "#fef3c7", border: "1px solid #fde68a",
            color: "#92400e", fontSize: 12, marginBottom: 12 }}>
            ⚠ Profile is only {tenant.profile_completion_percentage ?? 0}% complete. Approval will be blocked by the server until it reaches 100%.
          </div>
        )}
        {err && <p style={{ fontSize: 12, color: "#dc2626", margin: "0 0 12px" }}>{err}</p>}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Btn size="sm" variant="secondary" onClick={onClose} disabled={loading}>Cancel</Btn>
          <Btn size="sm" variant="primary" onClick={submit} disabled={loading}>
            {loading ? "Approving…" : "Approve"}
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function OnboardingProvidersPage() {
  const [search,       setSearch]       = useState("");
  const [categoryId,   setCategoryId]   = useState("");
  const [verticalType, setVerticalType] = useState("");
  const [reviewStatus, setReviewStatus] = useState("");
  const [city,         setCity]         = useState("");
  const [page,         setPage]         = useState(1);

  type ModalState =
    | { type: "approve"; tenant: AdminOnboardingProviderListItem }
    | { type: "reject";  tenant: AdminOnboardingProviderListItem }
    | { type: "changes"; tenant: AdminOnboardingProviderListItem }
    | null;
  const [modal, setModal] = useState<ModalState>(null);

  function resetPage() { setPage(1); }

  const categories = useApi(
    useCallback(() => categoryRuntimeApi.listCategories({ is_active: true }), [])
  );

  const providers = useApi(
    useCallback(
      () => adminOnboardingProvidersApi.list({
        q:            search        || undefined,
        category_id:  categoryId    || undefined,
        vertical_type: verticalType || undefined,
        review_status: reviewStatus || undefined,
        city:          city         || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [search, categoryId, verticalType, reviewStatus, city, page]
    ),
    [search, categoryId, verticalType, reviewStatus, city, page]
  );

  const total      = providers.data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const rows: AdminOnboardingProviderListItem[] = providers.data?.providers ?? [];
  const summary: OnboardingProviderSummary | undefined = providers.data?.summary;

  function closeModal() { setModal(null); }
  function actionDone() { setModal(null); providers.refetch(); }

  const categoryOptions = [
    { value: "", label: "All Categories" },
    ...(categories.data?.categories ?? []).map(
      (c: ServiceCategory) => ({ value: c.category_id, label: c.name })
    ),
  ];

  return (
    <AdminLayout>
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              Provider Onboarding Queue
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
              Providers awaiting review, approval, or action — not yet fully active
            </p>
          </div>
          <Btn size="sm" variant="secondary" onClick={() => providers.refetch()}>
            <RefreshCw size={13}/> Refresh
          </Btn>
        </div>

        {/* Summary Cards */}
        {summary && (
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <SummaryCard label="Total in Queue" count={summary.total}
              color="var(--brand)" active={!reviewStatus}
              onClick={() => { setReviewStatus(""); resetPage(); }}/>
            <SummaryCard label="Pending Review" count={summary.pending_review}
              color="#2563eb" active={reviewStatus === "pending_review"}
              onClick={() => { setReviewStatus("pending_review"); resetPage(); }}/>
            <SummaryCard label="Not Submitted" count={summary.not_submitted}
              color="#6b7280" active={reviewStatus === "not_submitted"}
              onClick={() => { setReviewStatus("not_submitted"); resetPage(); }}/>
            <SummaryCard label="Changes Requested" count={summary.changes_requested}
              color="#d97706" active={reviewStatus === "changes_requested"}
              onClick={() => { setReviewStatus("changes_requested"); resetPage(); }}/>
            <SummaryCard label="Rejected" count={summary.rejected}
              color="#dc2626" active={reviewStatus === "rejected"}
              onClick={() => { setReviewStatus("rejected"); resetPage(); }}/>
          </div>
        )}
        {!summary && providers.loading && (
          <div style={{ display: "flex", gap: 10 }}>
            {[...Array(5)].map((_, i) => <Skeleton key={i} height={62} style={{ flex: "1 1 140px" }}/>)}
          </div>
        )}

        {/* Filters */}
        <Card padding={14}>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr", gap: 10 }}>
            <div style={{ position: "relative" }}>
              <Search size={13} style={{ position: "absolute", left: 10, top: "50%",
                transform: "translateY(-50%)", color: "var(--text-tertiary)", pointerEvents: "none" }}/>
              <input value={search}
                onChange={e => { setSearch(e.target.value); resetPage(); }}
                placeholder="Search business name, email…"
                style={{ width: "100%", paddingLeft: 32, paddingRight: 10, height: 34, borderRadius: 8, fontSize: 13,
                  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
                  outline: "none", boxSizing: "border-box" }}/>
            </div>

            <select value={reviewStatus} onChange={e => { setReviewStatus(e.target.value); resetPage(); }}
              style={{ height: 34, borderRadius: 8, fontSize: 13, border: "1px solid var(--border)",
                background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px", outline: "none" }}>
              {REVIEW_STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>

            <select value={verticalType} onChange={e => { setVerticalType(e.target.value); resetPage(); }}
              style={{ height: 34, borderRadius: 8, fontSize: 13, border: "1px solid var(--border)",
                background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px", outline: "none" }}>
              {VERTICAL_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>

            <select value={categoryId} onChange={e => { setCategoryId(e.target.value); resetPage(); }}
              style={{ height: 34, borderRadius: 8, fontSize: 13, border: "1px solid var(--border)",
                background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px", outline: "none" }}>
              {categoryOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>

            <input value={city} onChange={e => { setCity(e.target.value); resetPage(); }}
              placeholder="City…"
              style={{ height: 34, borderRadius: 8, fontSize: 13, border: "1px solid var(--border)",
                background: "var(--surface)", color: "var(--text-primary)", padding: "0 10px", outline: "none" }}/>
          </div>
        </Card>

        {/* Table */}
        <Card padding={0}>
          {providers.loading ? (
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
              {[...Array(6)].map((_, i) => <Skeleton key={i} height={48}/>)}
            </div>
          ) : providers.error ? (
            <div style={{ textAlign: "center", padding: "48px 0" }}>
              <AlertTriangle size={28} style={{ color: "#dc2626", display: "block", margin: "0 auto 12px" }}/>
              <p style={{ fontSize: 14, fontWeight: 600, color: "#dc2626", margin: "0 0 6px" }}>
                Failed to load onboarding queue
              </p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 16px" }}>
                {providers.error}
              </p>
              <Btn size="sm" variant="primary" onClick={() => providers.refetch()}>Retry</Btn>
            </div>
          ) : rows.length === 0 ? (
            <div style={{ textAlign: "center", padding: "64px 0", color: "var(--text-tertiary)" }}>
              <ClipboardList size={36} style={{ display: "block", margin: "0 auto 14px", opacity: 0.35 }}/>
              <p style={{ fontSize: 15, fontWeight: 600, margin: "0 0 6px", color: "var(--text-primary)" }}>
                No providers in queue
              </p>
              <p style={{ fontSize: 13, margin: 0 }}>
                {reviewStatus || search || city ? "Try adjusting the filters." : "All providers are fully approved and active."}
              </p>
            </div>
          ) : (
            <>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                      {["Provider", "Owner", "Vertical / Category", "Location", "Profile %", "Review Status", "Readiness", "Package", "Registered", "Actions"].map(h => (
                        <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 10, fontWeight: 700,
                          color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em",
                          whiteSpace: "nowrap" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((p, i) => (
                      <tr key={p.tenant_id}
                        style={{ borderBottom: i < rows.length - 1 ? "1px solid var(--border)" : "none",
                          transition: "background 0.12s" }}
                        onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                        onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>

                        {/* Provider */}
                        <td style={{ padding: "11px 14px" }}>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                            {p.business_name ?? p.tenant_name ?? "—"}
                          </p>
                          <p style={{ fontSize: 10, fontFamily: "monospace", color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                            {p.tenant_id.slice(0, 8)}…
                          </p>
                        </td>

                        {/* Owner */}
                        <td style={{ padding: "11px 14px" }}>
                          {p.owner_name ? (
                            <p style={{ fontSize: 12, color: "var(--text-primary)", margin: 0 }}>{p.owner_name}</p>
                          ) : null}
                          {p.owner_email ? (
                            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "1px 0 0" }}>{p.owner_email}</p>
                          ) : (
                            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>—</span>
                          )}
                        </td>

                        {/* Vertical / Category */}
                        <td style={{ padding: "11px 14px" }}>
                          {p.vertical_type && (
                            <p style={{ fontSize: 12, color: "var(--text-primary)", margin: 0,
                              textTransform: "capitalize" }}>{p.vertical_type.replace(/_/g, " ")}</p>
                          )}
                          {p.category_name && (
                            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "1px 0 0" }}>
                              {p.category_name}
                            </p>
                          )}
                          {!p.vertical_type && !p.category_name && (
                            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>—</span>
                          )}
                        </td>

                        {/* Location */}
                        <td style={{ padding: "11px 14px", fontSize: 12, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                          {[p.city, p.state].filter(Boolean).join(", ") || "—"}
                        </td>

                        {/* Profile % */}
                        <td style={{ padding: "11px 14px", minWidth: 110 }}>
                          <ProgressBar pct={p.profile_completion_percentage}/>
                        </td>

                        {/* Review Status */}
                        <td style={{ padding: "11px 14px" }}>
                          <ReviewBadge status={p.review_status}/>
                        </td>

                        {/* Readiness */}
                        <td style={{ padding: "11px 14px" }}>
                          <ReadinessBadge status={p.readiness_status}/>
                        </td>

                        {/* Package */}
                        <td style={{ padding: "11px 14px" }}>
                          {p.selected_package_name ? (
                            <div>
                              <p style={{ fontSize: 12, color: "var(--text-primary)", margin: 0 }}>{p.selected_package_name}</p>
                              {p.package_status && (
                                <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "1px 0 0",
                                  textTransform: "capitalize" }}>{p.package_status.replace(/_/g, " ")}</p>
                              )}
                            </div>
                          ) : (
                            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No package</span>
                          )}
                        </td>

                        {/* Registered */}
                        <td style={{ padding: "11px 14px", fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                          {p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}
                        </td>

                        {/* Actions */}
                        <td style={{ padding: "11px 14px" }}>
                          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "nowrap" }}>
                            <Link href={`/admin/tenants/${p.tenant_id}`}
                              title="View tenant detail"
                              style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11,
                                color: "var(--brand)", textDecoration: "none", fontWeight: 500,
                                padding: "4px 8px", borderRadius: 6, background: "var(--brand)10",
                                border: "1px solid var(--brand)30", whiteSpace: "nowrap" }}>
                              <Users size={11}/> View
                            </Link>

                            {p.review_status !== "approved" && p.review_status !== "rejected" && (() => {
                              const profileComplete = (p.profile_completion_percentage ?? 0) >= 100;
                              return (
                                <button
                                  title={profileComplete ? "Approve provider" : `Profile only ${p.profile_completion_percentage ?? 0}% complete — must be 100% to approve`}
                                  onClick={() => { if (profileComplete) setModal({ type: "approve", tenant: p }); }}
                                  disabled={!profileComplete}
                                  style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11,
                                    color: profileComplete ? "#059669" : "#9ca3af",
                                    background: profileComplete ? "#05966910" : "#9ca3af15",
                                    border: `1px solid ${profileComplete ? "#05966930" : "#9ca3af40"}`,
                                    borderRadius: 6, padding: "4px 8px",
                                    cursor: profileComplete ? "pointer" : "not-allowed",
                                    fontWeight: 500, opacity: profileComplete ? 1 : 0.7 }}>
                                  <CheckCircle size={11}/> Approve
                                </button>
                              );
                            })()}

                            {p.review_status !== "rejected" && (
                              <button
                                title="Request changes"
                                onClick={() => setModal({ type: "changes", tenant: p })}
                                style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11,
                                  color: "#d97706", background: "#d9770610", border: "1px solid #d9770630",
                                  borderRadius: 6, padding: "4px 8px", cursor: "pointer", fontWeight: 500 }}>
                                <MessageSquare size={11}/> Changes
                              </button>
                            )}

                            {p.review_status !== "rejected" && (
                              <button
                                title="Reject provider"
                                onClick={() => setModal({ type: "reject", tenant: p })}
                                style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11,
                                  color: "#dc2626", background: "#dc262610", border: "1px solid #dc262630",
                                  borderRadius: 6, padding: "4px 8px", cursor: "pointer", fontWeight: 500 }}>
                                <XCircle size={11}/> Reject
                              </button>
                            )}

                            {p.review_status === "approved" && (
                              <span style={{ fontSize: 11, color: "#059669", fontWeight: 600 }}>Active</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                    Page {page} of {totalPages} · {total} total
                  </span>
                  <div style={{ display: "flex", gap: 6 }}>
                    <Btn size="sm" variant="secondary" disabled={page <= 1}
                      onClick={() => setPage(p => Math.max(1, p - 1))}>Previous</Btn>
                    <Btn size="sm" variant="secondary" disabled={page >= totalPages}
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}>Next</Btn>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      </div>

      {/* Modals */}
      {modal?.type === "approve" && (
        <ApproveModal tenant={modal.tenant} onClose={closeModal} onDone={actionDone}/>
      )}
      {modal?.type === "reject" && (
        <RejectModal tenant={modal.tenant} onClose={closeModal} onDone={actionDone}/>
      )}
      {modal?.type === "changes" && (
        <RequestChangesModal tenant={modal.tenant} onClose={closeModal} onDone={actionDone}/>
      )}
    </AdminLayout>
  );
}
