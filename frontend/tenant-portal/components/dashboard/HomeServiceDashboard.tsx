"use client";
import React, { useCallback } from "react";
import { StatCard, Card, Skeleton, Badge, JobStatusBadge, HealthMeter } from "../shared/ui";
import { analyticsApi, jobsApi, financeApi, reviewsApi, bookingsApi, staffApi } from "../../lib/api";
import { MonetizationStatusWidget } from "./MonetizationStatusWidget";
import { OnboardingWidget } from "./OnboardingWidget";
import { MarketingLaunchWidget } from "./MarketingLaunchWidget";
import { useApi } from "../../hooks/useApi";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Wrench, CalendarDays, Wallet, BarChart3, Users2, Star } from "lucide-react";

const fmt = (n: number | null | undefined) => `₹${(n ?? 0).toLocaleString("en-IN")}`;

export function HomeServiceDashboard() {
  const jobs     = useApi(useCallback(() => jobsApi.list({ limit:"8" }), []));
  const sla      = useApi(useCallback(() => jobsApi.slaAlerts(), []));
  const wallet   = useApi(useCallback(() => financeApi.wallet(), []));
  const reviews  = useApi(useCallback(() => reviewsApi.getAggregate(), []));
  const bookings = useApi(useCallback(() => bookingsApi.list({ status:"pending_confirmation", limit:"5" }), []));
  const staffList = useApi(useCallback(() => staffApi.list(), []));
  const commissions = useApi(useCallback(() => financeApi.commissionHistory(1), []));
  const revenue  = useApi(useCallback(() => analyticsApi.dailyMetric("commission_collected", 7), []));

  const kpis = jobs.loading || bookings.loading || staffList.loading || commissions.loading;
  const w = wallet.data;
  const r = reviews.data;
  const lowBalance = (w?.available ?? 0) < 2000;
  const staffActive = (staffList.data?.users ?? []).filter((s: { is_active: boolean }) => s.is_active).length;
  const revenueChartData = (revenue.data?.data ?? []).map((d: { date: string; value: unknown }) => ({
    date: d.date, value: Number(d.value) || 0,
  }));

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:22 }}>
      {/* Onboarding widget — shown until onboarding is complete */}
      <OnboardingWidget/>
      {/* Monetization status */}
      <MonetizationStatusWidget/>
      {/* Marketing launch */}
      <MarketingLaunchWidget/>
      {/* KPI Row */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(180px,1fr))", gap:14 }}>
        {kpis ? [...Array(6)].map((_,i) => <Skeleton key={i} height={100} style={{ borderRadius:14 }}/>) : (<>
          <StatCard icon={<Wrench/>} label="Active Jobs"
            value={(jobs.data?.jobs ?? []).filter((j: { status: string }) => j.status === "in_progress").length}
            trend="up" accent="var(--brand)"/>
          <StatCard icon={<CalendarDays/>} label="Pending Bookings"
            value={(bookings.data?.bookings ?? []).length} accent="#7c3aed"/>
          <StatCard icon={<Users2/>} label="Active Staff"
            value={staffActive} accent="#059669"/>
          <StatCard icon={<Wallet/>} label="Wallet"
            value={fmt(w?.available)} accent={lowBalance ? "#dc2626" : "#059669"}
            alert={lowBalance}/>
          <StatCard icon={<Star/>} label="Avg Rating"
            value={r?.avg_composite ? r.avg_composite.toFixed(1) : "—"} accent="#d97706"/>
          <StatCard icon={<BarChart3/>} label="SLA Alerts"
            value={(sla.data ?? []).length} accent="#dc2626"/>
        </>)}
      </div>

      {/* Revenue Chart */}
      <Card>
        <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 16px" }}>
          Revenue — Last 7 Days
        </p>
        {revenue.loading ? <Skeleton height={180}/> : (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={revenueChartData}>
              <defs>
                <linearGradient id="rv" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--brand)" stopOpacity={0.25}/>
                  <stop offset="95%" stopColor="var(--brand)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/>
              <XAxis dataKey="date" tick={{ fontSize:11 }} stroke="var(--border)"/>
              <YAxis tick={{ fontSize:11 }} stroke="var(--border)" tickFormatter={v => `₹${(v/1000).toFixed(0)}k`}/>
              <Tooltip formatter={(v: number) => [`₹${v.toLocaleString("en-IN")}`, "Revenue"]}/>
              <Area dataKey="value" stroke="var(--brand)" fill="url(#rv)" strokeWidth={2}/>
            </AreaChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* Recent Jobs */}
      <Card padding={0}>
        <div style={{ padding:"14px 18px", borderBottom:"1px solid var(--border)" }}>
          <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>Recent Jobs</p>
        </div>
        {jobs.loading ? (
          <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
            {[...Array(5)].map((_,i) => <Skeleton key={i} height={44}/>)}
          </div>
        ) : (jobs.data?.jobs ?? []).slice(0, 8).map((job: { id: string; job_number: string; status: string; customer_name?: string; service_type?: string; assigned_staff?: string; job_value?: number }) => (
          <div key={job.id} style={{ display:"flex", alignItems:"center", gap:12,
            padding:"11px 18px", borderBottom:"1px solid var(--border)" }}>
            <JobStatusBadge status={job.status}/>
            <div style={{ flex:1, minWidth:0 }}>
              <p style={{ fontSize:13, fontWeight:500, color:"var(--text-primary)", margin:0,
                whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>
                {job.job_number} — {job.customer_name ?? "Customer"}
              </p>
              <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                {job.service_type} · {job.assigned_staff ?? "Unassigned"}
              </p>
            </div>
            {job.job_value != null && (
              <span style={{ fontSize:12, color:"var(--text-secondary)" }}>{fmt(job.job_value)}</span>
            )}
          </div>
        ))}
      </Card>
    </div>
  );
}
