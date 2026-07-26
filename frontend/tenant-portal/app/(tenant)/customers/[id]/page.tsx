"use client";
/**
 * Customer Detail — full profile: contact, health signals, risk flags, job history.
 * PROVEN: customersApi.get() + customersApi.getHealth() + customersApi.jobs() connected.
 */
import React, { useCallback } from "react";
import Link from "next/link";
import { TenantLayout }       from "../../../../components/layout/TenantLayout";
import { Card, Skeleton, HealthMeter, JobStatusBadge, Badge } from "../../../../components/shared/ui";
import { customersApi }       from "../../../../lib/api";
import { useApi }             from "../../../../hooks/useApi";
import { Phone, Mail, AlertTriangle, ClipboardList, Wallet, CalendarDays, Tag } from "lucide-react";

const HEALTH_BAND_META: Record<string, { label:string; bg:string; text:string; border:string }> = {
  platinum: { label:"Platinum", bg:"var(--warning-bg)",  text:"var(--warning-text)",  border:"var(--warning-border)"  },
  gold:     { label:"Gold",     bg:"var(--warning-bg)",  text:"var(--warning-text)",  border:"var(--warning-border)"  },
  silver:   { label:"Silver",   bg:"var(--surface-sunken)", text:"var(--text-tertiary)", border:"var(--border)"       },
  bronze:   { label:"Bronze",   bg:"var(--surface-sunken)", text:"var(--text-secondary)", border:"var(--border)"      },
  at_risk:  { label:"At Risk",  bg:"var(--warning-bg)",  text:"var(--warning-text)",  border:"var(--warning-border)"  },
  critical: { label:"Critical", bg:"var(--danger-bg)",   text:"var(--danger-text)",   border:"var(--danger-border)"   },
};

export default function CustomerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);

  const customer = useApi(useCallback(() => customersApi.get(id),         [id]));
  const health   = useApi(useCallback(() => customersApi.getHealth(id),   [id]));
  const jobs     = useApi(useCallback(() => customersApi.jobs(id, 15),    [id]));

  const c  = customer.data;
  const h  = health.data;
  const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`;
  const bandMeta = HEALTH_BAND_META[c?.health_band ?? "silver"];

  return (
    <TenantLayout activeNav="customers">
      {/* Breadcrumb */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:20,
        fontSize:12, color:"var(--text-tertiary)" }}>
        <Link href="/customers" style={{ color:"var(--text-link)", textDecoration:"none" }}>Customers</Link>
        <span>›</span>
        <span style={{ color:"var(--text-primary)", fontWeight:500 }}>
          {c?.name ?? "Loading…"}
        </span>
      </div>

      {customer.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Skeleton height={160} style={{ borderRadius:14 }} />
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <Skeleton height={220} style={{ borderRadius:14 }} />
            <Skeleton height={220} style={{ borderRadius:14 }} />
          </div>
          <Skeleton height={300} style={{ borderRadius:14 }} />
        </div>
      ) : c && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

          {/* ── Profile header ── */}
          <Card padding={24}>
            <div style={{ display:"flex", alignItems:"flex-start", gap:16, flexWrap:"wrap" }}>
              <div style={{ width:56, height:56, borderRadius:"50%",
                background:"var(--accent-muted)", display:"flex", alignItems:"center",
                justifyContent:"center", fontSize:22, fontWeight:700,
                color:"var(--accent)", flexShrink:0 }}>
                {c.name[0].toUpperCase()}
              </div>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ display:"flex", alignItems:"center", gap:10, flexWrap:"wrap", marginBottom:5 }}>
                  <h1 style={{ fontSize:22, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                    {c.name}
                  </h1>
                  <span style={{ fontSize:12, padding:"3px 9px", borderRadius:99, fontWeight:700,
                    background:bandMeta.bg, color:bandMeta.text, border:`1px solid ${bandMeta.border}` }}>
                    {bandMeta.label}
                  </span>
                </div>
                {/* Contact info */}
                <div style={{ display:"flex", gap:16, flexWrap:"wrap", marginBottom:14 }}>
                  {c.phone && (
                    <a href={`tel:${c.phone}`}
                      style={{ fontSize:13, color:"var(--text-link)", textDecoration:"none",
                        display:"flex", alignItems:"center", gap:5 }}>
                      <Phone size={13}/> {c.phone}
                    </a>
                  )}
                  {c.email && (
                    <a href={`mailto:${c.email}`}
                      style={{ fontSize:13, color:"var(--text-link)", textDecoration:"none",
                        display:"flex", alignItems:"center", gap:5 }}>
                      <Mail size={13}/> {c.email}
                    </a>
                  )}
                  <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>
                    Customer since {new Date(c.created_at).toLocaleDateString("en-IN",
                      { month:"short", year:"numeric" })}
                  </span>
                </div>
                {/* KPI chips */}
                <div style={{ display:"flex", gap:10, flexWrap:"wrap" }}>
                  {[
                    { label:"Total Jobs",  v: String(c.total_jobs),    color:"var(--text-primary)"  },
                    { label:"Total Spend", v: fmt(c.total_spend),       color:"var(--success-text)" },
                    { label:"LTV Band",    v: c.ltv_band ?? "—",        color:"var(--accent)"       },
                    { label:"Health",      v: String(c.health_score),   color:bandMeta.text         },
                  ].map(m => (
                    <div key={m.label} style={{ padding:"8px 14px", borderRadius:10,
                      background:"var(--surface-sunken)", border:"1px solid var(--border)" }}>
                      <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:"0 0 2px",
                        textTransform:"uppercase", letterSpacing:"0.05em" }}>{m.label}</p>
                      <p style={{ fontSize:15, fontWeight:700, color:m.color, margin:0 }}>{m.v}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>

            {/* ── Health score breakdown ── */}
            <Card padding={20}>
              <h3 style={{ fontSize:15, fontWeight:600, color:"var(--text-primary)", margin:"0 0 14px" }}>
                Health Analysis
              </h3>
              {health.loading ? (
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {[...Array(4)].map((_,i) => <Skeleton key={i} height={36} />)}
                </div>
              ) : h ? (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  {/* Overall bar */}
                  <div style={{ marginBottom:6 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
                      <span style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)" }}>
                        Overall Health
                      </span>
                      <span style={{ fontSize:14, fontWeight:800, color:bandMeta.text }}>
                        {c.health_score} · {bandMeta.label}
                      </span>
                    </div>
                    <HealthMeter score={c.health_score} />
                  </div>

                  {/* Signal bars */}
                  {Object.entries(h.signals).map(([key, val]) => {
                    const pct = Math.min(100, Math.max(0, Number(val)));
                    const barColor = pct >= 70 ? "var(--success)" : pct >= 40 ? "var(--warning)" : "var(--danger)";
                    return (
                      <div key={key}>
                        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:3 }}>
                          <span style={{ fontSize:12, color:"var(--text-secondary)", textTransform:"capitalize" }}>
                            {key.replace(/_/g," ")}
                          </span>
                          <span style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)" }}>
                            {pct.toFixed(0)}
                          </span>
                        </div>
                        <div style={{ height:5, background:"var(--border)", borderRadius:99, overflow:"hidden" }}>
                          <div style={{ height:"100%", width:`${pct}%`, background:barColor, borderRadius:99 }} />
                        </div>
                      </div>
                    );
                  })}

                  {/* Risk flags */}
                  {h.risk_flags.length > 0 && (
                    <div style={{ marginTop:8, padding:"10px 12px", borderRadius:8,
                      background:"var(--danger-bg)", border:"1px solid var(--danger-border)" }}>
                      <p style={{ fontSize:11, fontWeight:700, color:"var(--danger-text)",
                        textTransform:"uppercase", letterSpacing:"0.05em", margin:"0 0 6px",
                        display:"flex", alignItems:"center", gap:5 }}>
                        <AlertTriangle size={12}/> Risk Flags
                      </p>
                      {h.risk_flags.map(flag => (
                        <p key={flag} style={{ fontSize:12, color:"var(--danger-text)",
                          margin:"0 0 2px" }}>
                          · {flag.replace(/_/g," ")}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <p style={{ fontSize:13, color:"var(--text-tertiary)", textAlign:"center", padding:"20px 0" }}>
                  Health data unavailable
                </p>
              )}
            </Card>

            {/* ── Summary stats ── */}
            <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
              {[
                { icon:<ClipboardList/>, label:"Total Jobs",      v:String(c.total_jobs),     sub:"lifetime"     },
                { icon:<Wallet/>,        label:"Total Spend",     v:fmt(c.total_spend),        sub:"lifetime"     },
                { icon:<CalendarDays/>,  label:"Last Job",        v:c.last_job_at
                    ? new Date(c.last_job_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})
                    : "Never",                                                       sub:"most recent"  },
                { icon:<Tag/>,           label:"LTV Band",       v:c.ltv_band ?? "Not set",  sub:"lifetime value"},
              ].map(stat => (
                <Card key={stat.label} padding={16}>
                  <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                    <span style={{ display:"flex", color:"var(--text-tertiary)" }}>{React.isValidElement(stat.icon) ? React.cloneElement(stat.icon as React.ReactElement<{size?:number}>, {size:24}) : stat.icon}</span>
                    <div>
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 2px",
                        textTransform:"uppercase", letterSpacing:"0.05em" }}>
                        {stat.label}
                      </p>
                      <p style={{ fontSize:17, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                        {stat.v}
                      </p>
                      <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:0 }}>{stat.sub}</p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* ── Job history ── */}
          <Card padding={0}>
            <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)",
              display:"flex", alignItems:"center", justifyContent:"space-between" }}>
              <h3 style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                Job History
              </h3>
              <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>
                Last {jobs.data?.jobs.length ?? 0} jobs
              </span>
            </div>
            {jobs.loading ? (
              <div style={{ padding:"12px 20px", display:"flex", flexDirection:"column", gap:6 }}>
                {[...Array(4)].map((_,i) => <Skeleton key={i} height={48} />)}
              </div>
            ) : (jobs.data?.jobs ?? []).length === 0 ? (
              <p style={{ padding:"32px 20px", textAlign:"center",
                color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
                No jobs found for this customer
              </p>
            ) : (jobs.data?.jobs ?? []).map((j, i, arr) => (
              <div key={j.id}
                style={{ display:"flex", alignItems:"center", gap:12, padding:"11px 20px",
                  borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none",
                  cursor:"pointer" }}
                onClick={() => window.location.href = `/jobs/${j.id}`}
                onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.background="var(--surface-sunken)"}
                onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.background="transparent"}>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)",
                    margin:"0 0 2px" }}>
                    {j.job_number} · {j.service_type}
                  </p>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                    {j.city} · {new Date(j.created_at).toLocaleDateString("en-IN",
                      { day:"numeric", month:"short", year:"numeric" })}
                  </p>
                </div>
                <JobStatusBadge status={j.status} />
                {j.job_value != null && (
                  <span style={{ fontSize:13, fontWeight:700, color:"var(--success-text)",
                    whiteSpace:"nowrap" }}>
                    {fmt(j.job_value)}
                  </span>
                )}
              </div>
            ))}
          </Card>

        </div>
      )}
    </TenantLayout>
  );
}
