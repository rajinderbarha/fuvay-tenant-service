"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import {
  Card, Badge, Btn, StatCard, SectionHeader, Skeleton,
} from "../../../components/shared/ui";
import {
  dsApi,
  type PricingRecommendation, type StaffRanking, type HighValueCustomer,
  type BusinessPerformance,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  Activity, TrendingUp, Wallet, Trophy, Star, RefreshCw, CheckCircle2, BarChart3,
  Briefcase,
} from "lucide-react";

type Tab = "performance" | "churn" | "demand" | "pricing" | "staff" | "customers";
const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "performance", label: "Performance",   icon: <Briefcase size={14}/> },
  { id: "churn",       label: "Health & Churn",icon: <Activity size={14}/> },
  { id: "demand",      label: "Demand Forecast",icon: <TrendingUp size={14}/> },
  { id: "pricing",     label: "Pricing",       icon: <Wallet size={14}/> },
  { id: "staff",       label: "Staff Rankings",icon: <Trophy size={14}/> },
  { id: "customers",   label: "Top Customers", icon: <Star size={14}/> },
];

export default function InsightsPage() {
  const [tab, setTab] = useState<Tab>("performance");
  const [toast, setToast] = useState("");
  const [perfDays, setPerfDays] = useState(30);
  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  // Data — lazy per tab but cheap enough to load eagerly for snapshot row
  const perf      = useApi(useCallback(() => dsApi.getBusinessPerformance(perfDays), [perfDays]));
  const churn      = useApi(useCallback(() => dsApi.getChurnScore(), []));
  const factors    = useApi(useCallback(() => dsApi.getChurnFactors(), []));
  const forecast   = useApi(useCallback(() => dsApi.demandForecast(), []));
  const pricing    = useApi(useCallback(() => dsApi.pricingRecommendations(), []));
  const rankings   = useApi(useCallback(() => dsApi.staffRankings(), []));
  const highValue  = useApi(useCallback(() => dsApi.highValueCustomers(20), []));

  const recompute  = useAction(useCallback(() => dsApi.recomputeDemand(), []));
  const applyPrice = useAction(useCallback((serviceTypeId: string, targetPrice: number) =>
    dsApi.applyPricingRecommendation(serviceTypeId, targetPrice), []));

  async function handleRecompute() {
    const res = await recompute.execute();
    if (res) { forecast.refetch(); notify("Demand forecast recomputed."); }
  }
  async function handleApply(rec: PricingRecommendation) {
    await applyPrice.execute(rec.service_type_id, rec.benchmark_price);
    notify(`Price update for ${rec.service_type_id} applied.`);
  }

  const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`;
  const c = churn.data;
  const f = forecast.data;

  const BAND_COLOR = (b: string) => b === "critical" ? "danger" : b === "high" ? "warning" : b === "medium" ? "info" : "success";

  return (
    <TenantLayout activeNav="insights">
      <SectionHeader
        title="Insights"
        subtitle="AI-driven churn risk, demand forecasts, pricing and staff performance"
        icon={<BarChart3/>}
        actions={<Btn variant="secondary" size="sm" icon={<RefreshCw size={14}/>} onClick={() => { churn.refetch(); forecast.refetch(); }}>Refresh</Btn>}
      />

      {toast && (
        <div style={{ padding:"10px 16px", background:"var(--success-bg)", border:"1px solid var(--success-border)",
          borderRadius:10, color:"var(--success-text)", fontSize:13, marginBottom:16, display:"flex", gap:8, alignItems:"center" }}>
          <CheckCircle2 size={14}/> {toast}
        </div>
      )}

      {/* Snapshot row */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(170px,1fr))", gap:14, marginBottom:20 }}>
        {(churn.loading || forecast.loading) ? (
          [...Array(4)].map((_,i) => <Skeleton key={i} height={100} style={{ borderRadius:14 }}/>)
        ) : <>
          <StatCard label="Churn Risk" value={c ? `${c.churn_score.toFixed(0)}` : "—"} icon={<Activity/>}
            trend={c && c.churn_band === "low" ? "up" : "down"} alert={c?.churn_band === "high" || c?.churn_band === "critical"}/>
          <StatCard label="14-Day Demand" value={f?.total_predicted ?? "—"} icon={<TrendingUp/>} trend="neutral"/>
          <StatCard label="Pricing Opportunities" value={(pricing.data?.recommendations ?? []).filter(r=>r.action!=="hold").length} icon={<Wallet/>} trend="neutral"/>
          <StatCard label="Top Performer Score" value={rankings.data?.rankings[0]?.composite_score?.toFixed(0) ?? "—"} icon={<Trophy/>} trend="up"/>
        </>}
      </div>

      {/* Tabs */}
      <div style={{ display:"flex", gap:2, borderBottom:"2px solid var(--border)", marginBottom:20, overflowX:"auto" }}>
        {TABS.map(tb => (
          <button key={tb.id} onClick={() => setTab(tb.id)}
            style={{ padding:"10px 16px", border:"none", background:"none", cursor:"pointer",
              fontSize:13, fontWeight: tab === tb.id ? 700 : 500,
              color: tab === tb.id ? "var(--brand)" : "var(--text-secondary)",
              borderBottom: tab === tb.id ? "2px solid var(--brand)" : "2px solid transparent",
              marginBottom:-2, whiteSpace:"nowrap", display:"flex", gap:6, alignItems:"center" }}>
            {tb.icon} {tb.label}
          </button>
        ))}
      </div>

      {/* ── Performance (Phase 13) ── */}
      {tab === "performance" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {/* Period selector */}
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <span style={{ fontSize:12, color:"var(--text-secondary)" }}>Period:</span>
            {[7, 30, 90].map(d => (
              <button key={d} onClick={() => setPerfDays(d)}
                style={{ padding:"4px 12px", borderRadius:20, border:"1px solid var(--border)",
                  background: perfDays === d ? "var(--brand)" : "var(--surface)",
                  color: perfDays === d ? "#fff" : "var(--text-primary)", fontSize:12, cursor:"pointer" }}>
                {d}d
              </button>
            ))}
            <Btn size="sm" variant="ghost" icon={<RefreshCw size={12}/>} onClick={() => perf.refetch()}>Refresh</Btn>
          </div>

          {perf.loading ? (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(170px,1fr))", gap:12 }}>
              {[...Array(6)].map((_,i) => <Skeleton key={i} height={90} style={{ borderRadius:14 }}/>)}
            </div>
          ) : perf.data ? (() => {
            const p: BusinessPerformance = perf.data;
            const pct = (n: number|null) => n == null ? "—" : `${(n*100).toFixed(1)}%`;
            const rev = (n: number) => `₹${n.toLocaleString("en-IN")}`;
            const JOB_TYPE_LABELS: Record<string,string> = { repair:"Repair", service:"Service", consultation:"Consultation" };
            return (
              <>
                {/* Stat cards row */}
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(160px,1fr))", gap:12 }}>
                  <StatCard label="Total Jobs" value={p.total_jobs} icon={<Briefcase/>} trend="neutral"/>
                  <StatCard label="Consultation Conv." value={pct(p.consultation_conversion_rate)} icon={<TrendingUp/>}
                    trend={p.consultation_conversion_rate != null && p.consultation_conversion_rate > 0.5 ? "up" : "neutral"}/>
                  <StatCard label="Repeat Booking Rate" value={pct(p.repeat_booking_rate)} icon={<Star/>}
                    trend={p.repeat_booking_rate != null && p.repeat_booking_rate > 0.3 ? "up" : "neutral"}/>
                  <StatCard label="SLA Breaches" value={p.sla_breaches} icon={<Activity/>}
                    trend={p.sla_breaches > 0 ? "down" : "up"} alert={p.sla_breaches > 0}/>
                  <StatCard label="SLA Breach Rate" value={pct(p.sla_breach_rate)} icon={<Activity/>}
                    trend={p.sla_breach_rate != null && p.sla_breach_rate < 0.05 ? "up" : "down"}/>
                  <StatCard label="Rework / Fail Rate" value={pct(p.rework_quality_failure_rate)} icon={<BarChart3/>}
                    trend={p.rework_quality_failure_rate != null && p.rework_quality_failure_rate < 0.1 ? "up" : "down"}
                    alert={p.rework_quality_failure_rate != null && p.rework_quality_failure_rate > 0.1}/>
                </div>

                {/* Jobs by type + Avg revenue by type */}
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
                  <Card padding={20}>
                    <h3 style={{ fontSize:14, fontWeight:600, margin:"0 0 14px" }}>Jobs by Type</h3>
                    {Object.keys(JOB_TYPE_LABELS).map(jt => {
                      const count = p.jobs_by_type[jt] ?? 0;
                      const total = p.total_jobs || 1;
                      return (
                        <div key={jt} style={{ marginBottom:12 }}>
                          <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                            <span style={{ fontSize:12, color:"var(--text-secondary)" }}>{JOB_TYPE_LABELS[jt]}</span>
                            <span style={{ fontSize:12, fontWeight:700 }}>{count}</span>
                          </div>
                          <div style={{ height:6, background:"var(--border)", borderRadius:999, overflow:"hidden" }}>
                            <div style={{ height:"100%", width:`${Math.round(count/total*100)}%`, background:"var(--brand)", borderRadius:999 }}/>
                          </div>
                        </div>
                      );
                    })}
                  </Card>

                  <Card padding={20}>
                    <h3 style={{ fontSize:14, fontWeight:600, margin:"0 0 14px" }}>Avg Revenue by Job Type</h3>
                    {Object.keys(JOB_TYPE_LABELS).map(jt => {
                      const avgRev = p.avg_revenue_by_type[jt];
                      return (
                        <div key={jt} style={{ display:"flex", justifyContent:"space-between",
                          padding:"8px 0", borderBottom:"1px solid var(--border)" }}>
                          <span style={{ fontSize:13, color:"var(--text-secondary)" }}>{JOB_TYPE_LABELS[jt]}</span>
                          <span style={{ fontSize:13, fontWeight:700, color: avgRev ? "var(--success-text)" : "var(--text-tertiary)" }}>
                            {avgRev != null ? rev(avgRev) : "—"}
                          </span>
                        </div>
                      );
                    })}
                  </Card>
                </div>

                {/* Top staff */}
                {p.top_staff.length > 0 && (
                  <Card padding={0}>
                    <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)" }}>
                      <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Top Staff (by Score)</h3>
                    </div>
                    {p.top_staff.slice(0,8).map((s, i) => (
                      <div key={s.staff_id} style={{ display:"flex", alignItems:"center", gap:14,
                        padding:"10px 20px", borderBottom: i < p.top_staff.length - 1 ? "1px solid var(--border)" : "none" }}>
                        <div style={{ width:26, height:26, borderRadius:"50%", flexShrink:0,
                          background: i < 3 ? "var(--warning-bg)" : "var(--surface-sunken)",
                          display:"flex", alignItems:"center", justifyContent:"center", fontSize:11, fontWeight:700,
                          color: i < 3 ? "var(--warning-text)" : "var(--text-secondary)" }}>
                          #{i+1}
                        </div>
                        <div style={{ flex:1, minWidth:0 }}>
                          <p style={{ fontSize:13, fontWeight:600, margin:0 }}>{s.name}</p>
                          <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                            {s.jobs_completed} jobs
                            {s.avg_rating != null ? ` · ${s.avg_rating.toFixed(1)}★` : ""}
                          </p>
                        </div>
                        <span style={{ fontSize:16, fontWeight:800,
                          color: s.score != null && s.score >= 80 ? "var(--success-text)" : s.score != null && s.score >= 60 ? "var(--warning-text)" : "var(--danger-text)" }}>
                          {s.score != null ? s.score.toFixed(0) : "—"}
                        </span>
                      </div>
                    ))}
                  </Card>
                )}

                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                  Generated {new Date(p.generated_at).toLocaleString()} · Last {p.period_days} days
                </p>
              </>
            );
          })() : (
            <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>No performance data available.</p>
          )}
        </div>
      )}

      {/* ── Health & Churn ── */}
      {tab === "churn" && (
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
          <Card padding={24}>
            <h3 style={{ fontSize:15, fontWeight:600, margin:"0 0 16px" }}>Churn Risk Score</h3>
            {churn.loading ? <Skeleton height={100}/> : c ? (
              <>
                <div style={{ display:"flex", alignItems:"center", gap:16, marginBottom:16 }}>
                  <p style={{ fontSize:42, fontWeight:800, margin:0,
                    color: c.churn_band === "critical" || c.churn_band === "high" ? "var(--danger-text)" : "var(--success-text)" }}>
                    {c.churn_score.toFixed(0)}
                  </p>
                  <div>
                    <Badge variant={BAND_COLOR(c.churn_band) as "danger"}>{c.churn_band} risk</Badge>
                    {c.score_delta != null && (
                      <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"4px 0 0" }}>
                        {c.score_delta > 0 ? "↑" : "↓"} {Math.abs(c.score_delta)} since last check
                      </p>
                    )}
                  </div>
                </div>
                <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>{c.interpretation}</p>
                {c.observation_mode && (
                  <div style={{ marginTop:12, padding:"8px 12px", borderRadius:"var(--radius-md)", background:"var(--info-bg)", border:"1px solid var(--info-border)" }}>
                    <p style={{ fontSize:11, color:"var(--info-text)", margin:0, display:"flex", alignItems:"center", gap:6 }}>
                      <BarChart3 size={12}/> Platform-wide benchmark — personalises as your job history grows.
                    </p>
                  </div>
                )}
              </>
            ) : <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>No churn data yet</p>}
          </Card>

          <Card padding={24}>
            <h3 style={{ fontSize:15, fontWeight:600, margin:"0 0 16px" }}>Contributing Factors</h3>
            {factors.loading ? (
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                {[...Array(3)].map((_,i) => <Skeleton key={i} height={40}/>)}
              </div>
            ) : factors.data ? (
              <>
                {factors.data.contributing_factors.map((f, i) => (
                  <div key={i} style={{ marginBottom:12 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                      <span style={{ fontSize:12, color:"var(--text-secondary)", textTransform:"capitalize" }}>
                        {f.signal.replace(/_/g," ")}
                      </span>
                      <span style={{ fontSize:12, fontWeight:700, color:"var(--text-primary)" }}>
                        {f.contribution.toFixed(1)} pts
                      </span>
                    </div>
                    <div style={{ height:6, background:"var(--border)", borderRadius:999, overflow:"hidden" }}>
                      <div style={{ height:"100%", width:`${Math.min(100, f.value)}%`, background:"var(--brand)", borderRadius:999 }}/>
                    </div>
                  </div>
                ))}
                <h4 style={{ fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                  color:"var(--text-tertiary)", margin:"16px 0 10px" }}>Recommended Actions</h4>
                <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                  {factors.data.recommended_actions.map((a, i) => (
                    <div key={i} style={{ display:"flex", alignItems:"center", gap:8, padding:"8px 12px",
                      background:"var(--surface-sunken)", borderRadius:"var(--radius-md)" }}>
                      <Badge variant={a.priority === "urgent" || a.priority === "high" ? "danger" : "muted"} size="sm">
                        {a.priority}
                      </Badge>
                      <span style={{ fontSize:12, color:"var(--text-primary)" }}>{a.action.replace(/_/g," ")}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>No factor data</p>}
          </Card>
        </div>
      )}

      {/* ── Demand Forecast ── */}
      {tab === "demand" && (
        <Card padding={24}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:20 }}>
            <h3 style={{ fontSize:15, fontWeight:600, margin:0 }}>14-Day Demand Forecast</h3>
            <Btn size="sm" variant="secondary" icon={<RefreshCw size={14}/>} loading={recompute.loading} onClick={handleRecompute}>
              Recompute
            </Btn>
          </div>
          {forecast.loading ? <Skeleton height={120}/> : f ? (
            <>
              <div style={{ display:"flex", gap:24, marginBottom:20 }}>
                <div>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px" }}>Total Predicted Jobs</p>
                  <p style={{ fontSize:32, fontWeight:800, color:"var(--brand)", margin:0 }}>{f.total_predicted}</p>
                </div>
                <div>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px" }}>Peak Day</p>
                  <p style={{ fontSize:20, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{f.peak_day}</p>
                </div>
                <div>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px" }}>Model</p>
                  <p style={{ fontSize:14, fontWeight:600, color:"var(--text-secondary)", margin:0 }}>{f.model_version}</p>
                </div>
              </div>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>{f.interpretation}</p>
              <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"8px 0 0" }}>
                Computed {new Date(f.computed_at).toLocaleString()}
              </p>
            </>
          ) : <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>No forecast available yet</p>}
        </Card>
      )}

      {/* ── Pricing ── */}
      {tab === "pricing" && (
        <Card padding={0}>
          <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)" }}>
            <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Pricing Recommendations vs Platform Benchmark</h3>
          </div>
          {pricing.loading ? (
            <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(4)].map((_,i) => <Skeleton key={i} height={56}/>)}
            </div>
          ) : (pricing.data?.recommendations ?? []).length === 0 ? (
            <p style={{ padding:"32px 20px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
              No pricing recommendations available — set up your service prices first.
            </p>
          ) : (pricing.data?.recommendations ?? []).map((rec: PricingRecommendation, i: number) => (
            <div key={rec.service_type_id} style={{ display:"flex", alignItems:"center", gap:14, padding:"14px 20px",
              borderBottom: i < (pricing.data?.recommendations.length ?? 0) - 1 ? "1px solid var(--border)" : "none" }}>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:3 }}>
                  <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{rec.service_type_id}</p>
                  <Badge variant={rec.action === "increase" ? "success" : rec.action === "decrease" ? "warning" : "muted"} size="sm">
                    {rec.action}
                  </Badge>
                </div>
                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                  Current {fmt(rec.current_price)} · Benchmark {fmt(rec.benchmark_price)} · Gap {rec.gap_pct}%
                </p>
              </div>
              {rec.action !== "hold" && (
                <Btn size="xs" variant="secondary" loading={applyPrice.loading} onClick={() => handleApply(rec)}>
                  Apply {fmt(rec.benchmark_price)}
                </Btn>
              )}
            </div>
          ))}
        </Card>
      )}

      {/* ── Staff Rankings ── */}
      {tab === "staff" && (
        <Card padding={0}>
          <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)" }}>
            <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Staff Performance Rankings</h3>
          </div>
          {rankings.loading ? (
            <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(5)].map((_,i) => <Skeleton key={i} height={48}/>)}
            </div>
          ) : (rankings.data?.rankings ?? []).length === 0 ? (
            <p style={{ padding:"32px 20px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
              No staff performance data yet
            </p>
          ) : (rankings.data?.rankings ?? []).map((s: StaffRanking, i: number) => (
            <div key={s.staff_id}
              onClick={() => window.location.href = `/staff/${s.staff_id}`}
              style={{ display:"flex", alignItems:"center", gap:14, padding:"12px 20px", cursor:"pointer",
                borderBottom: i < (rankings.data?.rankings.length ?? 0) - 1 ? "1px solid var(--border)" : "none" }}>
              <div style={{ width:28, height:28, borderRadius:"50%", flexShrink:0,
                background: s.rank <= 3 ? "var(--warning-bg)" : "var(--surface-sunken)",
                display:"flex", alignItems:"center", justifyContent:"center", fontSize:12, fontWeight:700,
                color: s.rank <= 3 ? "var(--warning-text)" : "var(--text-secondary)" }}>
                #{s.rank}
              </div>
              <div style={{ flex:1, minWidth:0 }}>
                <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0, fontFamily:"monospace" }}>
                  {s.staff_id.slice(0,8)}
                </p>
                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                  {s.jobs_completed} jobs · {s.avg_rating.toFixed(1)}★ · {s.sla_adherence}% SLA
                </p>
              </div>
              <span style={{ fontSize:18, fontWeight:800,
                color: s.composite_score >= 80 ? "var(--success-text)" : s.composite_score >= 60 ? "var(--warning-text)" : "var(--danger-text)" }}>
                {s.composite_score.toFixed(0)}
              </span>
            </div>
          ))}
        </Card>
      )}

      {/* ── Top Customers (LTV) ── */}
      {tab === "customers" && (
        <Card padding={0}>
          <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)" }}>
            <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>High-Value Customers by Predicted LTV</h3>
          </div>
          {highValue.loading ? (
            <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(6)].map((_,i) => <Skeleton key={i} height={48}/>)}
            </div>
          ) : (highValue.data?.high_value_customers ?? []).length === 0 ? (
            <p style={{ padding:"32px 20px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
              No customer LTV data yet
            </p>
          ) : (highValue.data?.high_value_customers ?? []).map((cust: HighValueCustomer, i: number) => (
            <div key={cust.customer_id}
              onClick={() => window.location.href = `/customers/${cust.customer_id}`}
              style={{ display:"flex", alignItems:"center", gap:14, padding:"12px 20px", cursor:"pointer",
                borderBottom: i < (highValue.data?.high_value_customers.length ?? 0) - 1 ? "1px solid var(--border)" : "none" }}>
              <div style={{ flex:1, minWidth:0 }}>
                <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0, fontFamily:"monospace" }}>
                  {cust.customer_id.slice(0,8)}
                </p>
                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                  {cust.booking_frequency.toFixed(1)} bookings/mo · {(cust.churn_probability*100).toFixed(0)}% churn risk
                </p>
              </div>
              <Badge variant={cust.ltv_band === "high" ? "success" : cust.ltv_band === "medium" ? "info" : "muted"} size="sm">
                {cust.ltv_band}
              </Badge>
              <span style={{ fontSize:15, fontWeight:700, color:"var(--success-text)", minWidth:80, textAlign:"right" }}>
                {fmt(cust.predicted_ltv)}
              </span>
            </div>
          ))}
        </Card>
      )}
    </TenantLayout>
  );
}
