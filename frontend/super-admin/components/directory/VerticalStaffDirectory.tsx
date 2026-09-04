"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../layout/AdminLayout";
import { Card, Badge, Btn } from "../shared/ui";
import { verticalDirectoryApi, hsReviewApi } from "../../lib/api";
import { useApi, useAction } from "../../hooks/useApi";
import { Lock, FileText, ShieldCheck, Search, Download } from "lucide-react";

// VERTICAL-DIRECTORY-FRAMEWORK: Staff domain. Reused as-is by every
// Business Vertical (Home Services, Coaching, Food, Real Estate, ...) --
// the vertical is resolved from trusted route/navigation configuration
// (never a client-editable selector inside this page). Staff creation is
// provider-owned (tenant portal) -- this page never offers "Add Staff".
// Availability/workload are read from the backend's canonical derivation
// (ServiceJob-based) -- no second state machine lives in this component.

type Row = Record<string, unknown>;

const VERIFICATION_FILTERS = ["not_started", "in_review", "changes_requested", "verified", "rejected", "expired"];
const ASSIGNMENT_FILTERS = ["pending", "active", "restricted", "suspended", "deactivated"];

function verificationVariant(v: string): "success" | "warning" | "danger" | "muted" {
  if (v === "verified") return "success";
  if (v === "rejected" || v === "expired") return "danger";
  if (v === "in_review" || v === "changes_requested") return "warning";
  return "muted";
}
function assignmentVariant(v: string): "success" | "warning" | "danger" | "muted" {
  if (v === "active") return "success";
  if (v === "suspended" || v === "deactivated") return "danger";
  if (v === "restricted" || v === "pending") return "warning";
  return "muted";
}
function availabilityVariant(v: string): "success" | "warning" | "danger" | "muted" {
  if (v === "available") return "success";
  if (v === "on_job" || v === "assigned") return "warning";
  if (v === "unavailable" || v === "offline") return "muted";
  return "muted";
}

export function VerticalStaffDirectory({ vertical, verticalLabel }: { vertical: string; verticalLabel: string }) {
  const [search, setSearch] = useState("");
  const [verificationStatus, setVerificationStatus] = useState<string | undefined>(undefined);
  const [assignmentStatus, setAssignmentStatus] = useState<string | undefined>(undefined);
  const [selected, setSelected] = useState<string | null>(null);

  const listApi = useApi(useCallback(
    () => verticalDirectoryApi.listStaff(vertical, {
      search: search || undefined,
      verification_status: verificationStatus, assignment_status: assignmentStatus,
      page_size: 25,
    }),
    [vertical, search, verificationStatus, assignmentStatus]));
  const summaryApi = useApi(useCallback(() => verticalDirectoryApi.staffSummary(vertical), [vertical]));

  const rows = (listApi.data?.items ?? []) as Row[];
  const s = summaryApi.data as Record<string, number> | null;

  async function doExport() {
    const data = await verticalDirectoryApi.exportStaff(vertical);
    const items = data.items;
    if (!items.length) { alert("Nothing to export."); return; }
    const headers = Object.keys(items[0]);
    const csv = [headers.join(","), ...items.map(r => headers.map(h => JSON.stringify(r[h] ?? "")).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${vertical}-staff.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AdminLayout>
      <div style={{ padding: "0 4px" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Operations / {verticalLabel} / Staff</p>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 8 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>{verticalLabel} Staff</h1>
              <Badge variant="muted" size="sm"><Lock size={10} style={{ marginRight: 4, verticalAlign: -1 }}/>{verticalLabel} only</Badge>
            </div>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
              Review staff explicitly assigned to {verticalLabel} work.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="ghost" size="sm" onClick={doExport}><Download size={14} style={{ marginRight: 4 }}/>Export</Btn>
            <Btn variant="ghost" size="sm" onClick={() => setSelected(selected)}><FileText size={14} style={{ marginRight: 4 }}/>View Audit</Btn>
            <Btn variant="primary" size="sm" onClick={() => setVerificationStatus("in_review")}>
              <ShieldCheck size={14} style={{ marginRight: 4 }}/>Review Verifications
            </Btn>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", borderRadius: "var(--radius-lg)",
          background: "var(--info-bg, rgba(59,130,246,0.08))", border: "1px solid var(--info-border, rgba(59,130,246,0.3))", marginBottom: 16 }}>
          <p style={{ fontSize: 12, color: "var(--info-text, #0f6b60)", margin: 0 }}>
            Providers add and manage staff. Platform admins verify identity, capabilities and {verticalLabel} readiness.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: 10, marginBottom: 16 }}>
          {[
            ["Total Staff", s?.total_staff], ["Active", s?.active], ["Pending Verification", s?.pending_verification],
            ["Available", s?.available], ["Assigned", s?.assigned], ["Unavailable", s?.unavailable],
            ["Capability Incomplete", s?.capability_incomplete], ["Suspended", s?.suspended],
          ].map(([label, value]) => (
            <div key={label as string} style={{ padding: "10px 12px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", background: "var(--surface)" }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
                {summaryApi.error ? "—" : (value ?? (summaryApi.loading ? "…" : 0))}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{label}</div>
            </div>
          ))}
        </div>
        {summaryApi.error && (
          <p style={{ fontSize: 11, color: "var(--warning-text)", margin: "-10px 0 16px" }}>
            Summary metrics are temporarily unavailable ({summaryApi.error}) — the directory below is unaffected.
          </p>
        )}

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <div style={{ position: "relative", flex: "1 1 240px", maxWidth: 320 }}>
            <Search size={13} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Name, email, phone or staff ID"
              style={{ width: "100%", padding: "7px 10px 7px 28px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}/>
          </div>
          <select value={verificationStatus ?? ""} onChange={e => setVerificationStatus(e.target.value || undefined)}
            style={{ padding: "7px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}>
            <option value="">All verification</option>
            {VERIFICATION_FILTERS.map(v => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
          </select>
          <select value={assignmentStatus ?? ""} onChange={e => setAssignmentStatus(e.target.value || undefined)}
            style={{ padding: "7px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}>
            <option value="">All statuses</option>
            {ASSIGNMENT_FILTERS.map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>

        <div style={{ display: "flex", gap: 16 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Card style={{ padding: 0 }}>
              {listApi.error ? (
                <div style={{ padding: 24, textAlign: "center" }}>
                  <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{listApi.error}</p>
                  {listApi.requestId && <p style={{ color: "var(--text-tertiary)", fontSize: 11 }}>Request ID: {listApi.requestId}</p>}
                  <Btn variant="ghost" size="sm" onClick={listApi.refetch}>Retry</Btn>
                </div>
              ) : listApi.loading ? (
                <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading staff…</div>
              ) : rows.length === 0 ? (
                <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                  No staff explicitly assigned to {verticalLabel} yet.
                </div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                        {["Staff", "Designation", "Verification", "Availability", "Status", "Updated"].map(h => (
                          <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map(row => (
                        <tr key={row.staff_id as string} onClick={() => setSelected(row.staff_id as string)}
                          style={{ borderBottom: "1px solid var(--border)", cursor: "pointer",
                            background: selected === row.staff_id ? "var(--surface-sunken)" : "transparent" }}>
                          <td style={{ padding: "9px 14px", fontWeight: 600 }}>{row.full_name as string}</td>
                          <td style={{ padding: "9px 14px" }}>{(row.designation as string) ?? "—"}</td>
                          <td style={{ padding: "9px 14px" }}><Badge variant={verificationVariant(row.verification_status as string)} size="sm">{(row.verification_status as string)?.replace(/_/g, " ")}</Badge></td>
                          <td style={{ padding: "9px 14px" }}><Badge variant={availabilityVariant(row.availability_status as string)} size="sm">{(row.availability_status as string)?.replace(/_/g, " ")}</Badge></td>
                          <td style={{ padding: "9px 14px" }}><Badge variant={assignmentVariant(row.assignment_status as string)} size="sm">{row.assignment_status as string}</Badge></td>
                          <td style={{ padding: "9px 14px", color: "var(--text-tertiary)" }}>{row.updated_at ? new Date(row.updated_at as string).toLocaleDateString() : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </TableSurface>
                </div>
              )}
            </Card>
          </div>
          {selected && (
            <div style={{ width: 360, flexShrink: 0 }}>
              <StaffInspector vertical={vertical} verticalLabel={verticalLabel} staffId={selected}
                onClose={() => setSelected(null)}
                onChanged={() => { listApi.refetch(); summaryApi.refetch(); }}/>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}

function StaffInspector({ vertical, verticalLabel, staffId, onClose, onChanged }: {
  vertical: string; verticalLabel: string; staffId: string; onClose: () => void; onChanged: () => void;
}) {
  const [tab, setTab] = useState<"overview" | "capabilities" | "workload" | "performance" | "activity">("overview");
  const [reason, setReason] = useState("");
  const detail = useApi(useCallback(() => verticalDirectoryApi.getStaff(vertical, staffId), [vertical, staffId]));
  const capabilities = useApi(useCallback(() => verticalDirectoryApi.getStaffCapabilities(vertical, staffId), [vertical, staffId]), [tab], { enabled: tab === "capabilities" });
  const workload = useApi(useCallback(() => verticalDirectoryApi.getStaffWorkload(vertical, staffId), [vertical, staffId]), [tab], { enabled: tab === "workload" });
  const performance = useApi(useCallback(() => verticalDirectoryApi.getStaffPerformance(vertical, staffId), [vertical, staffId]), [tab], { enabled: tab === "performance" });
  // REVIEW-CONSOLIDATION: rating data comes from the canonical
  // StaffRatingSummary (customer_reviews engine), not invented here --
  // job-count/completion-rate above is a separate, unrelated projection.
  const reviewSummary = useApi(useCallback(() => hsReviewApi.getStaffReviewSummary(vertical, staffId), [vertical, staffId]), [tab], { enabled: tab === "performance" });
  const activity = useApi(useCallback(() => verticalDirectoryApi.getStaffActivity(vertical, staffId), [vertical, staffId]), [tab], { enabled: tab === "activity" });

  const requestChanges = useAction((r: string) => verticalDirectoryApi.staffRequestChanges(vertical, staffId, r));
  const verify = useAction((r: string) => verticalDirectoryApi.staffVerify(vertical, staffId, r));
  const restrict = useAction((r: string) => verticalDirectoryApi.staffRestrict(vertical, staffId, r));
  const suspend = useAction((r: string) => verticalDirectoryApi.staffSuspend(vertical, staffId, r));
  const reactivate = useAction((r: string) => verticalDirectoryApi.staffReactivate(vertical, staffId, r));

  async function run(action: { execute: (r: string) => Promise<unknown> }) {
    const r = await action.execute(reason);
    if (r) { setReason(""); detail.refetch(); onChanged(); }
  }

  const d = detail.data as Record<string, unknown> | null;

  return (
    <Card style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{d?.full_name as string ?? "…"}</p>
        <Btn variant="ghost" size="sm" onClick={onClose}>Close</Btn>
      </div>
      {d && (
        <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
          <Badge variant={assignmentVariant(d.assignment_status as string)} size="sm">{d.assignment_status as string}</Badge>
          <Badge variant={verificationVariant(d.verification_status as string)} size="sm">{(d.verification_status as string)?.replace(/_/g, " ")}</Badge>
        </div>
      )}
      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 10, overflowX: "auto" }}>
        {(["overview", "capabilities", "workload", "performance", "activity"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding: "6px 8px", fontSize: 11, fontWeight: 600, background: "none", border: "none",
              borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab === t ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer", textTransform: "capitalize" }}>
            {t}
          </button>
        ))}
      </div>

      {tab === "overview" && d && (
        <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 6 }}>
          <Row label="Designation" value={(d.designation as string) ?? "—"}/>
          <Row label="Employee code" value={(d.employee_code as string) ?? "—"}/>
          <Row label="Availability" value={(d.availability_status as string)?.replace(/_/g, " ")}/>
          <Row label="Active jobs" value={String(d.active_jobs ?? 0)}/>
          <Row label="Completed jobs" value={String(d.completed_jobs ?? 0)}/>
          <Row label="Next job" value={(d.next_job_date as string) ?? "—"}/>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>
            Changes here affect only this staff member&apos;s {verticalLabel} assignment.
          </p>
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            <textarea placeholder="Reason (required for restrict/suspend/request changes)" value={reason} onChange={e => setReason(e.target.value)} rows={2}
              style={{ width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 12, boxSizing: "border-box" }}/>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <Btn variant="secondary" size="sm" onClick={() => run(requestChanges)} disabled={requestChanges.loading}>Request Changes</Btn>
              <Btn variant="success" size="sm" onClick={() => run(verify)} disabled={verify.loading}>Verify</Btn>
              <Btn variant="warning" size="sm" onClick={() => run(restrict)} disabled={restrict.loading}>Restrict</Btn>
              <Btn variant="danger" size="sm" onClick={() => run(suspend)} disabled={suspend.loading}>Suspend</Btn>
              <Btn variant="ghost" size="sm" onClick={() => run(reactivate)} disabled={reactivate.loading}>Reactivate</Btn>
            </div>
            {(requestChanges.error || restrict.error || suspend.error) && (
              <p style={{ fontSize: 11, color: "var(--danger-text)" }}>{requestChanges.error || restrict.error || suspend.error}</p>
            )}
          </div>
        </div>
      )}

      {tab === "capabilities" && (
        <div style={{ fontSize: 12 }}>
          {(capabilities.data?.job_types.length ?? 0) === 0 ? (
            <p style={{ color: "var(--text-tertiary)" }}>No job-type capabilities configured yet.</p>
          ) : capabilities.data!.job_types.map((jt, i) => (
            <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
              {(jt as Record<string, unknown>).job_type_name as string} — {(jt as Record<string, unknown>).master_service_name as string ?? "—"}
            </div>
          ))}
        </div>
      )}

      {tab === "workload" && (
        <div style={{ fontSize: 12 }}>
          <p>Active jobs: {workload.data?.capacity_active ?? 0}</p>
          {(workload.data?.active_jobs ?? []).map((j, i) => (
            <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
              {(j as Record<string, unknown>).job_number as string} — {(j as Record<string, unknown>).status as string}
            </div>
          ))}
        </div>
      )}

      {tab === "performance" && performance.data && (
        <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 6 }}>
          <Row label="Completed jobs" value={String(performance.data.completed_jobs)}/>
          <Row label="Completion rate" value={`${performance.data.completion_rate}%`}/>
          <Row label="Cancellation rate" value={`${performance.data.cancellation_rate}%`}/>
          {reviewSummary.data?.summary ? (
            <>
              <Row label="Rating" value={`${(reviewSummary.data.summary as Record<string, unknown>).average_rating}★ (${(reviewSummary.data.summary as Record<string, unknown>).total_reviews} reviews)`}/>
            </>
          ) : reviewSummary.error ? (
            <p style={{ color: "var(--danger-text)" }}>Rating unavailable: {reviewSummary.error}</p>
          ) : (
            <p style={{ color: "var(--text-tertiary)" }}>No reviews yet.</p>
          )}
          {((reviewSummary.data?.recent_reviews as Record<string, unknown>[] | undefined) ?? []).length > 0 && (
            <div style={{ marginTop: 8 }}>
              <p style={{ fontWeight: 700, marginBottom: 4 }}>Recent reviews</p>
              {(reviewSummary.data!.recent_reviews as Record<string, unknown>[]).map(rv => (
                <a key={rv.id as string} href={`/admin/home-services/service-jobs/${rv.job_id}?tab=review`}
                  style={{ display: "block", padding: "4px 0", borderBottom: "1px solid var(--border)", color: "inherit", textDecoration: "none" }}>
                  {String(rv.overall_rating)}★ — {String(rv.review_text ?? "").slice(0, 60) || "No written review"}
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "activity" && (
        <div style={{ fontSize: 12 }}>
          {(activity.data?.items.length ?? 0) === 0 ? (
            <p style={{ color: "var(--text-tertiary)" }}>No recorded activity yet.</p>
          ) : activity.data!.items.map((a, i) => (
            <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
              <p style={{ margin: 0, fontWeight: 600 }}>{(a as Record<string, unknown>).action_type as string}</p>
              <p style={{ margin: 0, color: "var(--text-tertiary)" }}>{(a as Record<string, unknown>).notes as string ?? "—"}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between" }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{value}</span>
    </div>
  );
}
