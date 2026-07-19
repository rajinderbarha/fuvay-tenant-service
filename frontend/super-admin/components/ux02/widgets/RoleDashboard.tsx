"use client";
import React from "react";
import { Card, Section, StatusBadge } from "@serviceos/design-system";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip as RTooltip } from "recharts";
import type { CanonicalAdminRole } from "../../../lib/ux02/types";
import { FIXTURE_TENANTS, FIXTURE_COMPLIANCE_CASES, FIXTURE_SECURITY_OBSERVATIONS, FIXTURE_PLATFORM_NOTICES } from "../../../lib/ux02/fixtures";

/**
 * One role-sensitive dashboard composition (not five separate dashboards).
 * Widget visibility/emphasis is configured per canonical role. Nav/dashboard
 * visibility is a UX convenience, never a real authorization boundary.
 */
const activityData = [
  { day: "Mon", value: 32 }, { day: "Tue", value: 41 }, { day: "Wed", value: 28 },
  { day: "Thu", value: 55 }, { day: "Fri", value: 47 }, { day: "Sat", value: 19 }, { day: "Sun", value: 24 },
];

export function RoleDashboard({ role }: { role: CanonicalAdminRole }) {
  const showFinance = role === "super_admin" || role === "admin_finance";
  const showSecurity = role === "super_admin" || role === "admin_security";
  const showOps = role !== "admin_readonly" || true; // read-only still sees the read view

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <Section title="Platform Snapshot">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "1rem" }}>
          <Card><div style={{ fontSize: "1.75rem", fontWeight: 700 }}>{FIXTURE_TENANTS.length}</div><div style={{ color: "var(--text-secondary)" }}>Active Tenants</div></Card>
          <Card><div style={{ fontSize: "1.75rem", fontWeight: 700 }}>{FIXTURE_COMPLIANCE_CASES.filter(c => c.status !== "resolved").length}</div><div style={{ color: "var(--text-secondary)" }}>Open Compliance Cases</div></Card>
          {showSecurity && <Card><div style={{ fontSize: "1.75rem", fontWeight: 700 }}>{FIXTURE_SECURITY_OBSERVATIONS.length}</div><div style={{ color: "var(--text-secondary)" }}>Security Observations</div></Card>}
          {showFinance && <Card><div style={{ fontSize: "1.75rem", fontWeight: 700 }}>${FIXTURE_TENANTS.reduce((s, t) => s + t.packageCreditBalance, 0).toLocaleString()}</div><div style={{ color: "var(--text-secondary)" }}>Package Credit (all tenants)</div></Card>}
        </div>
      </Section>

      <Section title="Action Center">
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {FIXTURE_TENANTS.filter(t => t.status === "pending_verification").map(t => (
            <Card key={t.id}><div style={{ display: "flex", justifyContent: "space-between" }}><span>{t.displayName} awaiting verification</span><StatusBadge status="pending" /></div></Card>
          ))}
        </div>
      </Section>

      {showOps && (
        <Section title="Activity (last 7 days)">
          <Card>
            <div style={{ width: "100%", height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={activityData}>
                  <XAxis dataKey="day" stroke="var(--text-secondary)" />
                  <YAxis stroke="var(--text-secondary)" />
                  <RTooltip />
                  <Bar dataKey="value" fill="var(--brand)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Section>
      )}

      {showSecurity && (
        <Section title="Risk Overview">
          {FIXTURE_SECURITY_OBSERVATIONS.map(o => (
            <Card key={o.id}><div style={{ display: "flex", justifyContent: "space-between" }}><span>{o.title}</span><StatusBadge status={o.status} /></div></Card>
          ))}
        </Section>
      )}

      <Section title="System Notices">
        {FIXTURE_PLATFORM_NOTICES.map(n => (
          <Card key={n.id}><strong>{n.title}</strong><p style={{ margin: "0.25rem 0 0", color: "var(--text-secondary)" }}>{n.body}</p></Card>
        ))}
      </Section>
    </div>
  );
}
