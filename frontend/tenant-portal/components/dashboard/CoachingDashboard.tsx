"use client";
import React, { useCallback } from "react";
import { StatCard, Card, Skeleton } from "../shared/ui";
import { categoryDashboardApi } from "../../lib/api";
import { MonetizationStatusWidget } from "./MonetizationStatusWidget";
import { OnboardingWidget } from "./OnboardingWidget";
import { MarketingLaunchWidget } from "./MarketingLaunchWidget";
import { useApi } from "../../hooks/useApi";
import { CalendarCheck, Users2, TrendingUp, Wallet, Star, Bell } from "lucide-react";

const fmt = (n: number | null | undefined) => `₹${(n ?? 0).toLocaleString("en-IN")}`;

export function CoachingDashboard() {
  const summary = useApi(useCallback(() => categoryDashboardApi.getCoachingSummary(), []));
  const d = (summary.data ?? {}) as Record<string, unknown>;

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:22 }}>
      <OnboardingWidget/>
      <MonetizationStatusWidget/>
      <MarketingLaunchWidget/>
      {/* Header banner */}
      <div style={{ background:"linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)",
        borderRadius:16, padding:"20px 28px", color:"white" }}>
        <p style={{ fontSize:11, fontWeight:700, letterSpacing:"0.1em", textTransform:"uppercase",
          margin:"0 0 4px", opacity:0.7 }}>Coaching Center Dashboard</p>
        <h1 style={{ fontSize:20, fontWeight:800, margin:0 }}>
          Appointments & Student Growth
        </h1>
        <p style={{ fontSize:12, margin:"4px 0 0", opacity:0.8 }} suppressHydrationWarning>
          {new Date().toLocaleDateString("en-IN",{weekday:"long",day:"numeric",month:"long"})}
        </p>
      </div>

      {/* KPI Row */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(180px,1fr))", gap:14 }}>
        {summary.loading ? [...Array(6)].map((_,i) => <Skeleton key={i} height={100} style={{ borderRadius:14 }}/>) : (<>
          <StatCard icon={<CalendarCheck/>} label="Today's Appointments"
            value={Number(d.today_appointments ?? 0)} accent="#7c3aed"/>
          <StatCard icon={<CalendarCheck/>} label="Demo Class Bookings"
            value={Number(d.demo_class_bookings ?? 0)} accent="#4f46e5"/>
          <StatCard icon={<Users2/>} label="New Student Leads"
            value={Number(d.new_student_leads ?? 0)} accent="var(--success)"/>
          <StatCard icon={<Bell/>} label="Pending Follow-ups"
            value={Number(d.pending_followups ?? 0)} accent="var(--warning)"/>
          <StatCard icon={<Wallet/>} label="Payments This Month"
            value={fmt(d.payments_this_month as number)} accent="var(--success)"/>
          <StatCard icon={<Star/>} label="Avg Rating"
            value={d.average_rating != null ? Number(d.average_rating).toFixed(1) : "—"} accent="var(--warning)"/>
        </>)}
      </div>

      {/* Conversion funnel */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        <Card>
          <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 16px" }}>
            Lead Conversion Rate
          </p>
          {summary.loading ? <Skeleton height={80}/> : (
            <div style={{ display:"flex", alignItems:"center", gap:16 }}>
              <div style={{ width:80, height:80, borderRadius:"50%",
                background:`conic-gradient(#7c3aed ${Number(d.conversion_rate ?? 0)}%, var(--surface-sunken) 0)`,
                display:"flex", alignItems:"center", justifyContent:"center" }}>
                <div style={{ width:60, height:60, borderRadius:"50%", background:"var(--card-bg)",
                  display:"flex", alignItems:"center", justifyContent:"center" }}>
                  <span style={{ fontSize:16, fontWeight:700, color:"#7c3aed" }}>
                    {Number(d.conversion_rate ?? 0)}%
                  </span>
                </div>
              </div>
              <div>
                <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
                  {Number(d.new_student_leads ?? 0)} leads → {Number(d.conversions ?? 0)} conversions
                </p>
                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"4px 0 0" }}>This month</p>
              </div>
            </div>
          )}
        </Card>
        <Card>
          <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 16px" }}>
            Course Inquiries
          </p>
          {summary.loading ? <Skeleton height={80}/> : (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {((d.course_inquiries_by_course ?? []) as Array<{ course: string; count: number }>).slice(0, 4).map(c => (
                <div key={c.course} style={{ display:"flex", justifyContent:"space-between",
                  alignItems:"center", padding:"8px 0", borderBottom:"1px solid var(--border)" }}>
                  <span style={{ fontSize:13, color:"var(--text-primary)" }}>{c.course}</span>
                  <span style={{ fontSize:12, fontWeight:600, color:"#7c3aed" }}>{c.count}</span>
                </div>
              ))}
              {((d.course_inquiries_by_course ?? []) as unknown[]).length === 0 && (
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No data yet</p>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
