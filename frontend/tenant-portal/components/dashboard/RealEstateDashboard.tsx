"use client";
import React, { useCallback } from "react";
import { StatCard, Card, Skeleton } from "../shared/ui";
import { categoryDashboardApi } from "../../lib/api";
import { MonetizationStatusWidget } from "./MonetizationStatusWidget";
import { OnboardingWidget } from "./OnboardingWidget";
import { MarketingLaunchWidget } from "./MarketingLaunchWidget";
import { useApi } from "../../hooks/useApi";
import { Users2, TrendingUp, CalendarDays, Bell, MapPin, FileText } from "lucide-react";

export function RealEstateDashboard() {
  const summary = useApi(useCallback(() => categoryDashboardApi.getRealEstateSummary(), []));
  const d = (summary.data ?? {}) as Record<string, unknown>;

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:22 }}>
      <OnboardingWidget/>
      <MonetizationStatusWidget/>
      <MarketingLaunchWidget/>
      {/* Header banner */}
      <div style={{ background:"linear-gradient(135deg, #059669 0%, #0284c7 100%)",
        borderRadius:16, padding:"20px 28px", color:"white" }}>
        <p style={{ fontSize:11, fontWeight:700, letterSpacing:"0.1em", textTransform:"uppercase",
          margin:"0 0 4px", opacity:0.7 }}>Real Estate Dashboard</p>
        <h1 style={{ fontSize:20, fontWeight:800, margin:0 }}>
          Leads, Properties & Deals
        </h1>
        <p style={{ fontSize:12, margin:"4px 0 0", opacity:0.8 }} suppressHydrationWarning>
          {new Date().toLocaleDateString("en-IN",{weekday:"long",day:"numeric",month:"long"})}
        </p>
      </div>

      {/* KPI Row */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(180px,1fr))", gap:14 }}>
        {summary.loading ? [...Array(6)].map((_,i) => <Skeleton key={i} height={100} style={{ borderRadius:14 }}/>) : (<>
          <StatCard icon={<TrendingUp/>} label="New Leads"
            value={Number(d.new_leads ?? 0)} accent="#059669"/>
          <StatCard icon={<TrendingUp/>} label="Active Leads"
            value={Number(d.active_leads ?? 0)} accent="#0284c7"/>
          <StatCard icon={<FileText/>} label="Property Inquiries"
            value={Number(d.property_inquiries ?? 0)} accent="#7c3aed"/>
          <StatCard icon={<Users2/>} label="Agent Assignments"
            value={Number(d.agent_assignments ?? 0)} accent="#d97706"/>
          <StatCard icon={<Bell/>} label="Follow-ups Due"
            value={Number(d.followups_due ?? 0)} accent="#dc2626"/>
          <StatCard icon={<CalendarDays/>} label="Site Visits"
            value={Number(d.site_visits ?? 0)} accent="#2563eb"/>
        </>)}
      </div>

      {/* Deal Pipeline */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        <Card>
          <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 16px" }}>
            Deal Pipeline
          </p>
          {summary.loading ? <Skeleton height={120}/> : (
            <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
              {(["new", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"] as const).map(stage => {
                const count = ((d.pipeline ?? {}) as Record<string, number>)[stage] ?? 0;
                const colors: Record<string, string> = {
                  new:"#2563eb", qualified:"#7c3aed", proposal:"#d97706",
                  negotiation:"#059669", closed_won:"#16a34a", closed_lost:"#dc2626"
                };
                const label = stage.replace("_", " ").replace(/\b\w/g, c => c.toUpperCase());
                return (
                  <div key={stage} style={{ display:"flex", alignItems:"center", gap:10 }}>
                    <span style={{ fontSize:11, color:"var(--text-secondary)", minWidth:90 }}>{label}</span>
                    <div style={{ flex:1, height:6, background:"var(--surface-sunken)", borderRadius:3, overflow:"hidden" }}>
                      <div style={{ height:"100%", borderRadius:3,
                        background: colors[stage] ?? "#94a3b8",
                        width: `${Math.min(100, count * 10)}%` }}/>
                    </div>
                    <span style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)", minWidth:20, textAlign:"right" }}>
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
        <Card>
          <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 16px" }}>
            Recent Properties
          </p>
          {summary.loading ? <Skeleton height={120}/> : (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {((d.recent_properties ?? []) as Array<{ title: string; city: string; type: string; price?: number }>)
                .slice(0, 4).map((p, i) => (
                <div key={i} style={{ display:"flex", gap:10, alignItems:"flex-start",
                  padding:"8px 0", borderBottom:"1px solid var(--border)" }}>
                  <MapPin size={12} style={{ color:"#059669", flexShrink:0, marginTop:1 }}/>
                  <div style={{ flex:1, minWidth:0 }}>
                    <p style={{ fontSize:13, fontWeight:500, color:"var(--text-primary)", margin:0,
                      whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{p.title}</p>
                    <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>{p.city} · {p.type}</p>
                  </div>
                </div>
              ))}
              {((d.recent_properties ?? []) as unknown[]).length === 0 && (
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No properties yet</p>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
