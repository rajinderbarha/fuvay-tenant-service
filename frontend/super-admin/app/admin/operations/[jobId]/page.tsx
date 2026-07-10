"use client";
/**
 * Job Detail (Super Admin) — full 360° job view with admin-level controls.
 * PROVEN: jobsApi.get() + jobsApi.history() connected.
 * PROVEN: overrideStatus, forceClose, reassign all call API + refetch.
 * PROVEN: no mock data, no inline fetch.
 */
import React, { useCallback, useState } from "react";
import { AdminLayout }   from "../../../../components/layout/AdminLayout";
import { Card, Badge, JobStatusBadge, Btn, Select, Input,
         SectionHeader, Skeleton, Modal } from "../../../../components/shared/ui";
import { Users, Settings2, XCircle } from "lucide-react";
import { jobsApi, staffApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import type { StaffMember } from "../../../../lib/api";

// Admin-visible status transitions (superset of tenant transitions)
const ADMIN_TRANSITIONS: Record<string, string[]> = {
  pending_assignment: ["assigned","cancelled"],
  assigned:           ["accepted","cancelled"],
  accepted:           ["en_route","cancelled"],
  en_route:           ["arrived","cancelled"],
  arrived:            ["in_progress","cancelled"],
  in_progress:        ["parts_required","quality_check","completed","cancelled"],
  parts_required:     ["parts_sourced","cancelled"],
  parts_sourced:      ["resumed","cancelled"],
  resumed:            ["quality_check","completed","cancelled"],
  quality_check:      ["completed","in_progress","cancelled"],
  completed:          ["invoiced","closed"],
  invoiced:           ["payment_pending","closed"],
  payment_pending:    ["paid","disputed","closed"],
  paid:               ["closed"],
  disputed:           ["resolved","cancelled"],
  resolved:           ["closed"],
};

const STATUS_VARIANT: Record<string, "danger"|"success"|"secondary"> = {
  cancelled: "danger",
  closed:    "danger",
  completed: "success",
  resolved:  "success",
};

export default function JobDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = React.use(params);

  const [overrideOpen,  setOverrideOpen]  = useState(false);
  const [forceCloseOpen,setForceCloseOpen]= useState(false);
  const [reassignOpen,  setReassignOpen]  = useState(false);
  const [newStatus,     setNewStatus]     = useState("");
  const [adminNote,     setAdminNote]     = useState("");
  const [selectedStaff, setSelectedStaff] = useState("");

  // ── Live API ──────────────────────────────────────────────────────────────
  const job     = useApi(useCallback(() => jobsApi.get(jobId),     [jobId]));
  const history = useApi(useCallback(() => jobsApi.history(jobId), [jobId]));

  const tenantId = job.data?.tenant_id ?? "";
  const staffList = useApi(
    useCallback(() => tenantId ? staffApi.listByTenant(tenantId) : Promise.resolve({ staff:[], total:0 }),
    [tenantId])
  );

  const overrideAction  = useAction(useCallback((s: string, n: string) =>
    jobsApi.overrideStatus(jobId, s, n), [jobId]));
  const forceCloseAction= useAction(useCallback((n: string) =>
    jobsApi.forceClose(jobId, n), [jobId]));
  const reassignAction  = useAction(useCallback((sId: string, n: string) =>
    jobsApi.reassign(jobId, sId, n), [jobId]));

  function refetchAll() { job.refetch(); history.refetch(); }

  async function handleOverride() {
    if (!newStatus) return;
    const res = await overrideAction.execute(newStatus, adminNote.trim());
    if (res) { setOverrideOpen(false); setNewStatus(""); setAdminNote(""); refetchAll(); }
  }

  async function handleForceClose() {
    if (!adminNote.trim()) return;
    const res = await forceCloseAction.execute(adminNote.trim());
    if (res) { setForceCloseOpen(false); setAdminNote(""); refetchAll(); }
  }

  async function handleReassign() {
    if (!selectedStaff) return;
    const res = await reassignAction.execute(selectedStaff, adminNote.trim());
    if (res) { setReassignOpen(false); setSelectedStaff(""); setAdminNote(""); refetchAll(); }
  }

  const j = job.data;
  const allowed = j ? (ADMIN_TRANSITIONS[j.status] ?? []) : [];
  const fmtDate = (d: string) => new Date(d).toLocaleString("en-IN",{
    day:"numeric", month:"short", year:"numeric", hour:"2-digit", minute:"2-digit"
  });
  const activeStaff: StaffMember[] = (staffList.data?.staff ?? []).filter(s => s.status === "active");

  return (
    <AdminLayout activeNav="operations">
      {/* Breadcrumb */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:20,
        fontSize:12, color:"var(--text-tertiary)" }}>
        <a href="/admin/operations" style={{ color:"var(--text-link)", textDecoration:"none" }}>Operations</a>
        <span>›</span>
        <span style={{ color:"var(--text-primary)", fontWeight:600 }}>
          {j?.job_number ?? "Loading…"}
        </span>
      </div>

      {job.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {[...Array(4)].map((_,i) => <Skeleton key={i} height={90} style={{ borderRadius:14 }}/>)}
        </div>
      ) : j && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

          {/* ── Header ────────────────────────────────────────────────────── */}
          <Card padding={24}>
            <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between",
              gap:16, flexWrap:"wrap" }}>
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:6 }}>
                  <h1 style={{ fontSize:22, fontWeight:800, color:"var(--text-primary)", margin:0 }}>
                    {j.job_number}
                  </h1>
                  <JobStatusBadge status={j.status}/>
                  {j.commission_amount != null && (
                    <span style={{ fontSize:13, fontWeight:700, color:"var(--success-text)",
                      padding:"2px 8px", borderRadius:6, background:"var(--success-bg)" }}>
                      ₹{j.commission_amount.toLocaleString("en-IN")} usage credit deduction
                    </span>
                  )}
                </div>
                <p style={{ fontSize:15, fontWeight:600, color:"var(--text-primary)", margin:"0 0 3px" }}>
                  {j.service_type} · {j.city}
                </p>
                <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
                  Created {fmtDate(j.created_at)} · Updated {fmtDate(j.updated_at)}
                </p>
              </div>
              {/* Admin action buttons */}
              <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                <Btn variant="secondary" size="sm" icon={<Users size={14}/>} onClick={() => { setReassignOpen(true); setAdminNote(""); setSelectedStaff(""); }}>
                  Reassign Staff
                </Btn>
                <Btn variant="secondary" size="sm" icon={<Settings2 size={14}/>} onClick={() => { setOverrideOpen(true); setNewStatus(""); setAdminNote(""); }}>
                  Override Status
                </Btn>
                {!["closed","cancelled","completed"].includes(j.status) && (
                  <Btn variant="danger" size="sm" icon={<XCircle size={14}/>} onClick={() => { setForceCloseOpen(true); setAdminNote(""); }}>
                    Force Close
                  </Btn>
                )}
                <Btn variant="ghost" size="sm" onClick={refetchAll}>↻</Btn>
              </div>
            </div>

            {/* SLA bar */}
            {j.sla_minutes != null && j.minutes_in_status != null && (
              <div style={{ marginTop:14 }}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
                  <span style={{ fontSize:12, color:"var(--text-secondary)" }}>SLA Progress</span>
                  <span style={{ fontSize:12, fontWeight:700,
                    color: j.minutes_in_status > j.sla_minutes
                      ? "var(--danger-text)" : j.minutes_in_status > j.sla_minutes * 0.75
                      ? "var(--warning-text)" : "var(--success-text)" }}>
                    {j.minutes_in_status}m / {j.sla_minutes}m
                    {j.minutes_in_status > j.sla_minutes && ` — ${j.minutes_in_status - j.sla_minutes}m OVERDUE ⚠`}
                  </span>
                </div>
                <div style={{ height:8, background:"var(--border)", borderRadius:99, overflow:"hidden" }}>
                  <div style={{ height:"100%",
                    width:`${Math.min(100,(j.minutes_in_status/j.sla_minutes)*100)}%`,
                    background: j.minutes_in_status > j.sla_minutes ? "var(--danger)"
                      : j.minutes_in_status > j.sla_minutes * 0.75 ? "var(--warning)" : "var(--success)",
                    borderRadius:99, transition:"width 0.4s" }}/>
                </div>
              </div>
            )}
          </Card>

          {/* ── Payment / Credit / Deduction Record ─────────────────────────── */}
          {j.quoted_price != null && (
            <Card padding={20}>
              <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)",
                textTransform:"uppercase", letterSpacing:"0.07em", margin:"0 0 12px" }}>
                Payment / Credit / Deduction Record
              </p>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:14 }}>
                {[
                  { label:"Quoted Price",              v: `₹${j.quoted_price.toLocaleString("en-IN")}` },
                  { label:"Customer Credit Applied",    v: `₹${(j.customer_credit_applied ?? 0).toLocaleString("en-IN")}` },
                  { label:"Payable To Provider",        v: `₹${(j.payable_to_provider ?? j.quoted_price).toLocaleString("en-IN")}` },
                  { label:"Payment Collection Mode",    v: "Customer pays provider directly" },
                  { label:"Payment Recorded",           v: j.payment_recorded ? "Yes" : "No" },
                  { label:"Amount Collected",           v: j.amount_collected != null ? `₹${j.amount_collected.toLocaleString("en-IN")}` : "—" },
                  { label:"Completed Job Deduction",    v: j.commission_amount != null ? `₹${j.commission_amount.toLocaleString("en-IN")}` : "—" },
                ].map(r => (
                  <div key={r.label}>
                    <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 2px" }}>{r.label}</p>
                    <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{r.v}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            {/* ── Tenant + Customer ────────────────────────────────────────── */}
            <Card padding={20} style={{ display:"flex", flexDirection:"column", gap:12 }}>
              <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)",
                textTransform:"uppercase", letterSpacing:"0.07em", margin:0 }}>Tenant</p>
              <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                <div style={{ width:36, height:36, borderRadius:10, background:"var(--accent-muted)",
                  display:"flex", alignItems:"center", justifyContent:"center",
                  fontWeight:700, fontSize:15, color:"var(--accent)" }}>
                  {(j.tenant_name ?? "T")[0]}
                </div>
                <div>
                  <p style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                    {j.tenant_name ?? "—"}
                  </p>
                  <a href={`/admin/tenants/${j.tenant_id}`}
                    style={{ fontSize:11, color:"var(--text-link)" }}>View tenant →</a>
                </div>
              </div>
              <div style={{ borderTop:"1px solid var(--border)", paddingTop:12 }}>
                <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)",
                  textTransform:"uppercase", letterSpacing:"0.07em", margin:"0 0 8px" }}>Customer</p>
                <p style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:"0 0 3px" }}>
                  {j.customer_name ?? "—"}
                </p>
              </div>
            </Card>

            {/* ── Staff ─────────────────────────────────────────────────────── */}
            <Card padding={20} style={{ display:"flex", flexDirection:"column", gap:12 }}>
              <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)",
                textTransform:"uppercase", letterSpacing:"0.07em", margin:0 }}>Assigned Staff</p>
              {j.assigned_staff ? (
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <div style={{ width:36, height:36, borderRadius:"50%", background:"var(--brand)",
                    display:"flex", alignItems:"center", justifyContent:"center",
                    fontWeight:700, fontSize:14, color:"white" }}>
                    {j.assigned_staff[0]}
                  </div>
                  <div>
                    <p style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                      {j.assigned_staff}
                    </p>
                    <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>Field Technician</p>
                  </div>
                </div>
              ) : (
                <div style={{ padding:"16px", borderRadius:8, background:"var(--warning-bg)",
                  border:"1px solid var(--warning-border)", textAlign:"center" }}>
                  <p style={{ fontSize:13, color:"var(--warning-text)", margin:"0 0 8px" }}>
                    ⚠ No staff assigned
                  </p>
                  <Btn variant="secondary" size="xs"
                    onClick={() => { setReassignOpen(true); setAdminNote(""); setSelectedStaff(""); }}>
                    Assign Staff
                  </Btn>
                </div>
              )}
            </Card>
          </div>

          {/* ── Job History Timeline ─────────────────────────────────────────── */}
          <Card padding={20}>
            <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)",
              textTransform:"uppercase", letterSpacing:"0.07em", margin:"0 0 16px" }}>
              Job History
            </p>
            {history.loading ? (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(4)].map((_,i) => <Skeleton key={i} height={40}/>)}
              </div>
            ) : (history.data?.history ?? []).length === 0 ? (
              <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No history available</p>
            ) : (
              <div style={{ display:"flex", flexDirection:"column" }}>
                {(history.data?.history ?? []).map((h, i, arr) => (
                  <div key={i} style={{ display:"flex", gap:14, alignItems:"flex-start",
                    paddingBottom: i < arr.length-1 ? 16 : 0 }}>
                    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", flexShrink:0 }}>
                      <div style={{ width:10, height:10, borderRadius:"50%",
                        background: i===0 ? "var(--accent)" : "var(--border)", marginTop:4 }}/>
                      {i < arr.length-1 && (
                        <div style={{ width:2, flex:1, background:"var(--border)", marginTop:4, minHeight:20 }}/>
                      )}
                    </div>
                    <div style={{ flex:1 }}>
                      <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                        <JobStatusBadge status={h.status}/>
                        {h.changed_by && (
                          <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>
                            by {h.changed_by}
                          </span>
                        )}
                      </div>
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"4px 0 0" }}>
                        {fmtDate(h.changed_at)}
                      </p>
                      {h.notes && (
                        <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"4px 0 0",
                          fontStyle:"italic" }}>
                          "{h.notes}"
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ── Override Status Modal ──────────────────────────────────────────── */}
      <Modal open={overrideOpen} onClose={() => setOverrideOpen(false)} title="Override Job Status">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <div style={{ padding:"10px 14px", borderRadius:8, background:"var(--warning-bg)",
            border:"1px solid var(--warning-border)" }}>
            <p style={{ fontSize:13, color:"var(--warning-text)", margin:0 }}>
              ⚠ Admin override bypasses normal flow. All changes are audit-logged.
            </p>
          </div>
          <Select label="New Status *" value={newStatus} onChange={setNewStatus}
            placeholder="Select target status…"
            options={allowed.map(s => ({ value:s, label:s.replace(/_/g," ") }))}/>
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)",
              display:"block", marginBottom:6 }}>Admin Note *</label>
            <textarea value={adminNote} onChange={e => setAdminNote(e.target.value)}
              placeholder="Reason for override (required for audit log)…"
              rows={3}
              style={{ width:"100%", padding:"8px 10px", fontSize:13, fontFamily:"inherit",
                borderRadius:8, border:"1px solid var(--border)", background:"var(--surface)",
                color:"var(--text-primary)", outline:"none", resize:"vertical",
                boxSizing:"border-box" as const }}/>
          </div>
          {overrideAction.error && (
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{overrideAction.error}</p>
          )}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setOverrideOpen(false)}>Cancel</Btn>
            <Btn variant="primary"   size="sm"
              loading={overrideAction.loading}
              disabled={!newStatus || !adminNote.trim()}
              onClick={handleOverride}>
              Apply Override
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Force Close Modal ──────────────────────────────────────────────── */}
      <Modal open={forceCloseOpen} onClose={() => setForceCloseOpen(false)} title="Force Close Job">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <div style={{ padding:"10px 14px", borderRadius:8, background:"var(--danger-bg)",
            border:"1px solid var(--danger-border)" }}>
            <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>
              This will immediately close the job regardless of current status.
              The tenant and customer will be notified.
            </p>
          </div>
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)",
              display:"block", marginBottom:6 }}>Reason *</label>
            <textarea value={adminNote} onChange={e => setAdminNote(e.target.value)}
              placeholder="Reason for force close (required)…"
              rows={4}
              style={{ width:"100%", padding:"8px 10px", fontSize:13, fontFamily:"inherit",
                borderRadius:8, border:"1px solid var(--border)", background:"var(--surface)",
                color:"var(--text-primary)", outline:"none", resize:"vertical",
                boxSizing:"border-box" as const }}/>
          </div>
          {forceCloseAction.error && (
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{forceCloseAction.error}</p>
          )}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setForceCloseOpen(false)}>Cancel</Btn>
            <Btn variant="danger"    size="sm"
              loading={forceCloseAction.loading}
              disabled={!adminNote.trim()}
              onClick={handleForceClose}>
              Force Close Job
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Reassign Staff Modal ───────────────────────────────────────────── */}
      <Modal open={reassignOpen} onClose={() => setReassignOpen(false)} title="Reassign Staff">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)",
              display:"block", marginBottom:6 }}>Assign to Staff *</label>
            {staffList.loading ? <Skeleton height={38}/> : (
              <select value={selectedStaff} onChange={e => setSelectedStaff(e.target.value)}
                style={{ width:"100%", height:38, padding:"0 10px", fontSize:13, fontFamily:"inherit",
                  borderRadius:8, border:"1px solid var(--border)", background:"var(--surface)",
                  color:"var(--text-primary)", outline:"none" }}>
                <option value="">Select staff member…</option>
                {activeStaff.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.full_name}
                    {s.rating != null ? ` ★${s.rating.toFixed(1)}` : ""}
                    {s.specialisations.length > 0 ? ` · ${s.specialisations[0]}` : ""}
                    {s.jobs_today != null ? ` · ${s.jobs_today} jobs today` : ""}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)",
              display:"block", marginBottom:6 }}>Reason</label>
            <textarea value={adminNote} onChange={e => setAdminNote(e.target.value)}
              placeholder="Reason for reassignment (optional)…"
              rows={3}
              style={{ width:"100%", padding:"8px 10px", fontSize:13, fontFamily:"inherit",
                borderRadius:8, border:"1px solid var(--border)", background:"var(--surface)",
                color:"var(--text-primary)", outline:"none", resize:"vertical",
                boxSizing:"border-box" as const }}/>
          </div>
          {reassignAction.error && (
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{reassignAction.error}</p>
          )}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setReassignOpen(false)}>Cancel</Btn>
            <Btn variant="primary"   size="sm"
              loading={reassignAction.loading}
              disabled={!selectedStaff}
              onClick={handleReassign}>
              Reassign
            </Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
