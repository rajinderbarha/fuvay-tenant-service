"use client";
/**
 * Staff Detail — full 360° staff member view.
 * PROVEN: staffApi.get() + staffApi.getPerformance() + serviceJobsApi.list() connected.
 * PROVEN: updateSchedule calls staffApi.updateSchedule() + refetches.
 * FINAL-L5-02B: migrated "Recent Jobs" off legacy jobsApi (/v1/jobs) onto
 * serviceJobsApi (/v1/provider/my-records/jobs, canonical service_jobs).
 */
import React, { useCallback, useState, useEffect } from "react";
import { TenantLayout }                  from "../../../../components/layout/TenantLayout";
import { Card, Btn, Skeleton, Badge, JobStatusBadge, Modal, SectionHeader, EditBtn } from "../../../../components/shared/ui";
import { staffApi, serviceJobsApi, authApi }    from "../../../../lib/api";
import { trustBadgesApi }                from "../../../../lib/api";
import { TrustBadges }                    from "../../../../components/TrustBadges";
import { useApi, useAction }             from "../../../../hooks/useApi";
import type { WorkingHours, StaffSecurityStatus, StaffLoginEvent } from "../../../../lib/api";
import { CalendarDays } from "lucide-react";

const DAYS = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"] as const;
const DAY_LABEL: Record<string,string> = {
  monday:"Mon", tuesday:"Tue", wednesday:"Wed", thursday:"Thu",
  friday:"Fri", saturday:"Sat", sunday:"Sun",
};

export default function StaffDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);

  const staff       = useApi(useCallback(() => staffApi.get(id),            [id]));
  const performance = useApi(useCallback(() => staffApi.getPerformance(id), [id]));
  const badges      = useApi(useCallback(() => trustBadgesApi.staffBadges(id), [id]));
  const jobs        = useApi(useCallback(() => serviceJobsApi.list({ limit: 20 }), []));

  const [scheduleModal, setScheduleModal] = useState(false);
  const [localHours, setLocalHours]       = useState<WorkingHours>({});

  // Security state
  const [secStatus, setSecStatus]       = useState<StaffSecurityStatus | null>(null);
  const [secHistory, setSecHistory]     = useState<StaffLoginEvent[]>([]);
  const [secLoading, setSecLoading]     = useState(false);
  const [secToast, setSecToast]         = useState("");
  const [secConfirm, setSecConfirm]     = useState<{ title:string; body:string; act:()=>Promise<void> }|null>(null);
  const [secReason, setSecReason]       = useState("");
  const [secActing, setSecActing]       = useState(false);

  const secNotify = (m: string) => { setSecToast(m); setTimeout(()=>setSecToast(""),4000); };

  const loadSecurity = useCallback(async () => {
    setSecLoading(true);
    try {
      const [st, hist] = await Promise.all([
        authApi.getStaffSecurityStatus(id) as Promise<StaffSecurityStatus>,
        authApi.getStaffLoginHistory(id, 20) as Promise<{ events:StaffLoginEvent[]; total:number }>,
      ]);
      setSecStatus(st); setSecHistory(hist.events ?? []);
    } catch { /* ignore — staff may not have auth user */ }
    finally { setSecLoading(false); }
  }, [id]);

  useEffect(() => { loadSecurity(); }, [loadSecurity]);

  async function runSecConfirm() {
    if (!secConfirm) return;
    setSecActing(true);
    try {
      await secConfirm.act();
      setSecConfirm(null); setSecReason("");
      await loadSecurity();
    } catch (e: unknown) {
      secNotify(e instanceof Error ? e.message : "Action failed.");
    } finally { setSecActing(false); }
  }

  const updateSched = useAction(
    useCallback((wh: WorkingHours) => staffApi.updateSchedule(id, wh), [id])
  );

  const s   = staff.data;
  const p   = performance.data;
  const wh  = s?.working_hours ?? {};

  function openSchedule() {
    const init: WorkingHours = {};
    DAYS.forEach(d => {
      init[d] = wh[d] ?? { start: "09:00", end: "18:00", is_working: d !== "sunday" };
    });
    setLocalHours(init); setScheduleModal(true);
  }

  async function saveSchedule() {
    const res = await updateSched.execute(localHours);
    if (res) { staff.refetch(); setScheduleModal(false); }
  }

  const staffJobs = (jobs.data?.items ?? []).filter(j => j.assigned_staff_id === id).slice(0, 10);
  const fmt = (n: number) => `${(n * 100).toFixed(1)}%`;

  const STATUS_COLORS: Record<string, string> = {
    active:      "var(--success-text)",
    on_leave:    "var(--warning-text)",
    inactive:    "var(--text-tertiary)",
    suspended:   "var(--danger-text)",
  };

  return (
    <TenantLayout activeNav="staff">
      {/* Breadcrumb */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:20,
        fontSize:12, color:"var(--text-tertiary)" }}>
        <a href="/staff" style={{ color:"var(--text-link)", textDecoration:"none" }}>Staff</a>
        <span>›</span>
        <span style={{ color:"var(--text-primary)", fontWeight:500 }}>
          {s?.full_name ?? "Loading…"}
        </span>
      </div>

      {staff.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Skeleton height={140} style={{ borderRadius:14 }} />
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <Skeleton height={200} style={{ borderRadius:14 }} />
            <Skeleton height={200} style={{ borderRadius:14 }} />
          </div>
        </div>
      ) : s && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

          {/* ── Profile header ── */}
          <Card padding={24}>
            <div style={{ display:"flex", alignItems:"flex-start", gap:18, flexWrap:"wrap" }}>
              <div style={{ width:64, height:64, borderRadius:"50%",
                background:"var(--brand)", display:"flex", alignItems:"center",
                justifyContent:"center", color:"white", fontSize:24,
                fontWeight:700, flexShrink:0 }}>
                {s.full_name.split(" ").map(n => n[0]).join("").slice(0,2).toUpperCase()}
              </div>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ display:"flex", alignItems:"center", gap:10, flexWrap:"wrap", marginBottom:4 }}>
                  <h1 style={{ fontSize:22, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                    {s.full_name}
                  </h1>
                  <span style={{ fontSize:12, padding:"3px 9px", borderRadius:99, fontWeight:700,
                    background: s.status==="active" ? "var(--success-bg)" : "var(--surface-sunken)",
                    color: STATUS_COLORS[s.status] ?? "var(--text-secondary)",
                    border:`1px solid ${s.status==="active"?"var(--success-border)":"var(--border)"}` }}>
                    {s.status.replace(/_/g," ")}
                  </span>
                </div>
                <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 10px" }}>
                  {s.phone ?? "No phone"} · {s.specialisations.join(" · ") || "No specialisations"}
                </p>
                <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
                  {[
                    { label:"Rating",      v: s.rating     != null ? `★ ${s.rating.toFixed(1)}` : "—"   },
                    { label:"Jobs Today",  v: s.jobs_today != null ? String(s.jobs_today)         : "—"   },
                    { label:"Perf. Score", v: p ? `${p.composite_score.toFixed(1)}/100`           : "…"   },
                    { label:"On-time",     v: p ? `${p.sla_adherence_rate.toFixed(0)}%`            : "…"   },
                  ].map(m => (
                    <div key={m.label} style={{ padding:"8px 14px", borderRadius:10,
                      background:"var(--surface-sunken)", textAlign:"center", minWidth:80 }}>
                      <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:"0 0 3px",
                        textTransform:"uppercase", letterSpacing:"0.06em" }}>{m.label}</p>
                      <p style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{m.v}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ display:"flex", gap:8 }}>
                <Btn variant="secondary" size="sm" icon={<CalendarDays size={14}/>} onClick={openSchedule}>Edit Schedule</Btn>
              </div>
            </div>
          </Card>

          {/* ── Trust badges ── */}
          <Card padding={20}>
            <h3 style={{ fontSize:15, fontWeight:600, color:"var(--text-primary)", margin:"0 0 12px" }}>
              Trust Badges
            </h3>
            <TrustBadges badges={badges.data ?? []} empty="No badges earned yet." />
          </Card>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>

            {/* ── Performance signals ── */}
            <Card padding={20}>
              <h3 style={{ fontSize:15, fontWeight:600, color:"var(--text-primary)", margin:"0 0 16px" }}>
                Performance Breakdown
              </h3>
              {performance.loading ? (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  {[...Array(5)].map((_,i) => <Skeleton key={i} height={36} />)}
                </div>
              ) : p ? (
                <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
                  {/* Composite */}
                  <div style={{ padding:"12px 14px", borderRadius:10,
                    background: p.composite_score >= 80 ? "var(--success-bg)"
                              : p.composite_score >= 60 ? "var(--warning-bg)" : "var(--danger-bg)",
                    border:`1px solid ${p.composite_score>=80?"var(--success-border)":p.composite_score>=60?"var(--warning-border)":"var(--danger-border)"}`,
                    display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                    <span style={{ fontSize:13, fontWeight:600,
                      color: p.composite_score>=80?"var(--success-text)":p.composite_score>=60?"var(--warning-text)":"var(--danger-text)" }}>
                      Composite Score
                    </span>
                    <span style={{ fontSize:20, fontWeight:800,
                      color: p.composite_score>=80?"var(--success-text)":p.composite_score>=60?"var(--warning-text)":"var(--danger-text)" }}>
                      {p.composite_score.toFixed(0)}<span style={{ fontSize:12, opacity:0.7 }}>/100</span>
                    </span>
                  </div>
                  {/* Signal bars */}
                  {Object.entries(p.signal_values).map(([key, val]) => {
                    const pct = Math.min(100, Math.max(0, Number(val)));
                    const barColor = pct >= 75 ? "var(--success)" : pct >= 50 ? "var(--warning)" : "var(--danger)";
                    return (
                      <div key={key}>
                        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                          <span style={{ fontSize:12, color:"var(--text-secondary)", textTransform:"capitalize" }}>
                            {key.replace(/_/g," ")}
                          </span>
                          <span style={{ fontSize:12, fontWeight:700, color:"var(--text-primary)" }}>
                            {pct.toFixed(0)}
                          </span>
                        </div>
                        <div style={{ height:6, background:"var(--border)", borderRadius:99, overflow:"hidden" }}>
                          <div style={{ height:"100%", width:`${pct}%`, background:barColor,
                            borderRadius:99, transition:"width 0.5s ease" }} />
                        </div>
                      </div>
                    );
                  })}
                  {/* Stats row */}
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:8, marginTop:4 }}>
                    {[
                      { label:"Jobs Done",    v: String(p.jobs_completed)                          },
                      { label:"Avg Rating",   v: p.avg_customer_rating.toFixed(1)                  },
                      { label:"Rank",         v: p.rank != null ? `#${p.rank}` : "—"               },
                    ].map(m => (
                      <div key={m.label} style={{ padding:"8px 10px", borderRadius:8,
                        background:"var(--surface-sunken)", textAlign:"center" }}>
                        <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:"0 0 2px",
                          textTransform:"uppercase", letterSpacing:"0.05em" }}>{m.label}</p>
                        <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{m.v}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p style={{ fontSize:13, color:"var(--text-tertiary)", textAlign:"center", padding:"24px 0" }}>
                  Performance data unavailable
                </p>
              )}
            </Card>

            {/* ── Working hours ── */}
            <Card padding={20}>
              <h3 style={{ fontSize:15, fontWeight:600, color:"var(--text-primary)", margin:"0 0 14px" }}>
                Weekly Schedule
              </h3>
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {DAYS.map(day => {
                  const dh = wh[day] ?? { start:"09:00", end:"18:00", is_working: day !== "sunday" };
                  return (
                    <div key={day} style={{ display:"flex", alignItems:"center", gap:10,
                      padding:"8px 12px", borderRadius:8,
                      background: dh.is_working ? "var(--surface-sunken)" : "transparent",
                      border:`1px solid ${dh.is_working?"var(--border)":"transparent"}` }}>
                      <span style={{ width:36, fontSize:12, fontWeight:600,
                        color: dh.is_working ? "var(--text-primary)" : "var(--text-tertiary)" }}>
                        {DAY_LABEL[day]}
                      </span>
                      {dh.is_working ? (
                        <>
                          <div style={{ flex:1, height:6, background:"var(--border)",
                            borderRadius:99, overflow:"hidden" }}>
                            <div style={{ height:"100%",
                              marginLeft:`${(parseInt(dh.start)/24)*100}%`,
                              width:`${((parseInt(dh.end)-parseInt(dh.start))/24)*100}%`,
                              background:"var(--accent)", borderRadius:99 }} />
                          </div>
                          <span style={{ fontSize:11, color:"var(--text-tertiary)", whiteSpace:"nowrap" }}>
                            {dh.start} – {dh.end}
                          </span>
                        </>
                      ) : (
                        <span style={{ fontSize:12, color:"var(--text-tertiary)", fontStyle:"italic" }}>
                          Day off
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
              <div style={{ marginTop:14, textAlign:"right" }}>
                <EditBtn onClick={openSchedule} tooltip="Edit Schedule"/>
              </div>
            </Card>
          </div>

          {/* ── Recent jobs ── */}
          <Card padding={0}>
            <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)",
              display:"flex", alignItems:"center", justifyContent:"space-between" }}>
              <h3 style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                Recent Jobs
              </h3>
              <a href={`/jobs?staff_id=${id}`} style={{ fontSize:12, color:"var(--text-link)",
                textDecoration:"none" }}>
                View all →
              </a>
            </div>
            {jobs.loading ? (
              <div style={{ padding:"12px 20px", display:"flex", flexDirection:"column", gap:6 }}>
                {[...Array(5)].map((_,i) => <Skeleton key={i} height={40} />)}
              </div>
            ) : staffJobs.length === 0 ? (
              <p style={{ padding:"32px 20px", textAlign:"center",
                color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
                No jobs found for this staff member
              </p>
            ) : staffJobs.map((j, i) => (
              <div key={j.id}
                style={{ display:"flex", alignItems:"center", gap:12, padding:"11px 20px",
                  borderBottom: i < staffJobs.length-1 ? "1px solid var(--border)" : "none",
                  cursor:"pointer" }}
                onClick={() => window.location.href = `/jobs/${j.id}`}
                onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.background="var(--surface-sunken)"}
                onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.background="transparent"}>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)",
                    margin:"0 0 2px" }}>
                    {j.job_number}
                  </p>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                    {j.zipcode ?? j.city ?? "—"} · {j.created_at ? new Date(j.created_at).toLocaleDateString("en-IN") : "—"}
                  </p>
                </div>
                <JobStatusBadge status={j.status} />
                {j.completion_data?.collected_amount != null && (
                  <span style={{ fontSize:13, fontWeight:600, color:"var(--success-text)",
                    whiteSpace:"nowrap" }}>
                    ₹{j.completion_data.collected_amount.toLocaleString("en-IN")}
                  </span>
                )}
              </div>
            ))}
          </Card>
        </div>
      )}

      {/* ── Staff Security Section ── */}
      {s && (
        <div style={{ marginTop:8, display:"flex", flexDirection:"column", gap:12 }}>
          <Card padding={20}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
              marginBottom:14, flexWrap:"wrap", gap:8 }}>
              <h3 style={{ fontSize:14, fontWeight:700, margin:0, color:"var(--text-primary)" }}>
                Account Security
              </h3>
              {!secLoading && (
                <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                  {secStatus?.account_status !== "locked" ? (
                    <Btn size="xs" variant="danger" onClick={()=>{
                      setSecReason(""); setSecConfirm({ title:"Lock Staff Account",
                        body:"This will lock the account and revoke all active sessions. The staff member cannot log in.",
                        act: async()=>{ await authApi.lockStaff(id, secReason||"Admin security review", true); secNotify("Account locked."); }
                      });
                    }}>Lock</Btn>
                  ) : (
                    <Btn size="xs" variant="secondary" onClick={()=>{
                      setSecReason(""); setSecConfirm({ title:"Unlock Account",
                        body:"This will allow the staff member to log in again.",
                        act: async()=>{ await authApi.unlockStaff(id, secReason||"Issue resolved"); secNotify("Account unlocked."); }
                      });
                    }}>Unlock</Btn>
                  )}
                  <Btn size="xs" variant="secondary" onClick={()=>{
                    setSecReason(""); setSecConfirm({ title:"Revoke All Sessions",
                      body:"All active sessions for this staff member will be immediately invalidated.",
                      act: async()=>{ await authApi.revokeStaffSessions(id, secReason||"Security reset"); secNotify("Sessions revoked."); }
                    });
                  }}>Revoke Sessions</Btn>
                </div>
              )}
            </div>

            {secToast && (
              <div style={{ padding:"8px 12px", borderRadius:8, background:"var(--success-bg)",
                border:"1px solid var(--success-border)", color:"var(--success-text)", fontSize:12,
                marginBottom:12 }}>{secToast}</div>
            )}

            {secLoading ? (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(3)].map((_,i)=><Skeleton key={i} height={32}/>)}
              </div>
            ) : secStatus ? (
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"0 24px" }}>
                <div>
                  {[
                    { label:"Status", value: <span style={{
                        fontWeight:700,
                        color: secStatus.account_status==="active"?"var(--success-text)":
                               secStatus.account_status==="locked"?"var(--danger-text)":"var(--text-tertiary)"
                      }}>{secStatus.account_status}</span>},
                    { label:"Active Sessions", value: String(secStatus.active_sessions) },
                    { label:"Last Login", value: secStatus.last_login_at ? new Date(secStatus.last_login_at).toLocaleString() : "—" },
                  ].map(r=>(
                    <div key={r.label} style={{ display:"flex", justifyContent:"space-between",
                      padding:"8px 0", borderBottom:"1px solid var(--border)", fontSize:13 }}>
                      <span style={{ fontSize:11, color:"var(--text-tertiary)", textTransform:"uppercase",
                        letterSpacing:"0.05em", fontWeight:500 }}>{r.label}</span>
                      <span style={{ color:"var(--text-primary)" }}>{r.value}</span>
                    </div>
                  ))}
                </div>
                <div>
                  {[
                    { label:"Force PW Change", value: secStatus.password_reset_required ? "Required" : "No" },
                    { label:"Lock Reason", value: secStatus.lock_reason ?? "—" },
                    { label:"Locked Until", value: secStatus.locked_until ? new Date(secStatus.locked_until).toLocaleString() : "—" },
                  ].map(r=>(
                    <div key={r.label} style={{ display:"flex", justifyContent:"space-between",
                      padding:"8px 0", borderBottom:"1px solid var(--border)", fontSize:13 }}>
                      <span style={{ fontSize:11, color:"var(--text-tertiary)", textTransform:"uppercase",
                        letterSpacing:"0.05em", fontWeight:500 }}>{r.label}</span>
                      <span style={{ color:"var(--text-primary)" }}>{r.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>
                Security data unavailable for this staff member.
              </p>
            )}
          </Card>

          {/* Login history mini-table */}
          {secHistory.length > 0 && (
            <Card padding={0}>
              <div style={{ padding:"12px 16px", borderBottom:"1px solid var(--border)" }}>
                <p style={{ margin:0, fontSize:13, fontWeight:700, color:"var(--text-primary)" }}>
                  Recent Login Events
                </p>
              </div>
              <div style={{ overflowX:"auto" }}>
                <table style={{ width:"100%", borderCollapse:"collapse", fontSize:12 }}>
                  <thead>
                    <tr style={{ background:"var(--surface-sunken)" }}>
                      {["Time","Event","IP","Failure"].map(h=>(
                        <th key={h} style={{ padding:"8px 14px", textAlign:"left", fontWeight:600,
                          fontSize:11, color:"var(--text-tertiary)", textTransform:"uppercase",
                          letterSpacing:"0.06em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {secHistory.slice(0,10).map(ev=>(
                      <tr key={ev.event_id} style={{ borderTop:"1px solid var(--border)" }}>
                        <td style={{ padding:"8px 14px", color:"var(--text-secondary)" }}>
                          {new Date(ev.created_at).toLocaleString()}
                        </td>
                        <td style={{ padding:"8px 14px" }}>
                          <span style={{
                            padding:"2px 7px", borderRadius:99, fontSize:11, fontWeight:600,
                            background: ev.event_type==="login_success"?"var(--success-bg)":
                                        ev.event_type==="login_failed"?"var(--danger-bg)":"var(--surface-sunken)",
                            color: ev.event_type==="login_success"?"var(--success-text)":
                                   ev.event_type==="login_failed"?"var(--danger-text)":"var(--text-tertiary)",
                          }}>{ev.event_type.replace(/_/g," ")}</span>
                        </td>
                        <td style={{ padding:"8px 14px", fontFamily:"monospace",
                          color:"var(--text-secondary)" }}>{ev.ip_address ?? "—"}</td>
                        <td style={{ padding:"8px 14px", color:"var(--danger-text)" }}>
                          {ev.failure_reason ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── Security Confirm Modal ── */}
      <Modal open={!!secConfirm} onClose={()=>!secActing&&setSecConfirm(null)}
        title={secConfirm?.title??""} size="sm">
        {secConfirm && (
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            <p style={{ margin:0, fontSize:13, color:"var(--text-secondary)", lineHeight:1.6 }}>
              {secConfirm.body}
            </p>
            <div>
              <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)",
                display:"block", marginBottom:5 }}>Reason (optional)</label>
              <textarea value={secReason} onChange={e=>setSecReason(e.target.value)} rows={2}
                placeholder="Describe why you are taking this action…"
                style={{ width:"100%", padding:"8px 10px", fontSize:13,
                  border:"1px solid var(--border)", borderRadius:8,
                  background:"var(--surface)", color:"var(--text-primary)",
                  fontFamily:"inherit", resize:"vertical", boxSizing:"border-box" as const }}/>
            </div>
            <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
              <Btn variant="ghost" size="sm" onClick={()=>setSecConfirm(null)} disabled={secActing}>
                Cancel
              </Btn>
              <Btn variant="danger" size="sm" onClick={runSecConfirm} loading={secActing}>
                Confirm
              </Btn>
            </div>
          </div>
        )}
      </Modal>

      {/* ── Edit Schedule Modal ── */}
      <Modal open={scheduleModal} onClose={() => setScheduleModal(false)} title="Edit Weekly Schedule">
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {DAYS.map(day => {
            const dh = localHours[day] ?? { start:"09:00", end:"18:00", is_working:true };
            function update(patch: Partial<typeof dh>) {
              setLocalHours(prev => ({ ...prev, [day]: { ...dh, ...patch } }));
            }
            return (
              <div key={day} style={{ display:"flex", alignItems:"center", gap:12,
                padding:"10px 12px", borderRadius:8, background:"var(--surface-sunken)",
                border:"1px solid var(--border)" }}>
                <label style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer",
                  width:80, flexShrink:0 }}>
                  <input type="checkbox" checked={dh.is_working}
                    onChange={e => update({ is_working: e.target.checked })}
                    style={{ width:16, height:16, cursor:"pointer" }} />
                  <span style={{ fontSize:13, fontWeight:600,
                    color: dh.is_working ? "var(--text-primary)" : "var(--text-tertiary)" }}>
                    {DAY_LABEL[day]}
                  </span>
                </label>
                {dh.is_working ? (
                  <div style={{ display:"flex", alignItems:"center", gap:8, flex:1 }}>
                    <input type="time" value={dh.start}
                      onChange={e => update({ start: e.target.value })}
                      style={{ flex:1, height:32, padding:"0 8px", borderRadius:6,
                        border:"1px solid var(--border)", background:"var(--surface-base)",
                        color:"var(--text-primary)", fontSize:13, fontFamily:"inherit", outline:"none" }} />
                    <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>to</span>
                    <input type="time" value={dh.end}
                      onChange={e => update({ end: e.target.value })}
                      style={{ flex:1, height:32, padding:"0 8px", borderRadius:6,
                        border:"1px solid var(--border)", background:"var(--surface-base)",
                        color:"var(--text-primary)", fontSize:13, fontFamily:"inherit", outline:"none" }} />
                  </div>
                ) : (
                  <span style={{ fontSize:12, color:"var(--text-tertiary)", fontStyle:"italic" }}>Day off</span>
                )}
              </div>
            );
          })}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end", marginTop:8 }}>
            <Btn variant="ghost" size="sm" onClick={() => setScheduleModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={updateSched.loading} onClick={saveSchedule}>
              Save Schedule
            </Btn>
          </div>
        </div>
      </Modal>
    </TenantLayout>
  );
}
