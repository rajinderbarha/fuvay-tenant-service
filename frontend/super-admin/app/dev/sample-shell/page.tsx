"use client";

// DEV-ONLY sample screen demonstrating shell+nav+header+status+table+states
// composed purely from @serviceos/design-system primitives. Not linked from
// nav-config.ts; illustrative only, does not replace the real super-admin
// dashboard pages.

import React from "react";
import { PageShell, PageHeader, Section, Card, StatusBadge, DataTable, Button } from "@serviceos/design-system";
import { ShieldCheck } from "lucide-react";

const complianceRequests = [
  { id: "CR-501", tenant: "UrbanFix Services", type: "Background check", status: "pending" },
  { id: "CR-497", tenant: "QuickCare Home", type: "Insurance renewal", status: "approved" },
  { id: "CR-492", tenant: "TrustHands Co-op", type: "License upload", status: "rejected" },
];

export default function SampleSuperAdminShell() {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <aside style={{ width: "15rem", background: "var(--sidebar-bg)", color: "var(--sidebar-text)", padding: "1.5rem 1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--sidebar-text-active)", marginBottom: "1.5rem" }}>
          <ShieldCheck size={20} />
          <strong>ServiceOS Admin</strong>
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          {["Overview", "Tenants", "Compliance", "Billing"].map((item, i) => (
            <div
              key={item}
              style={{
                padding: "0.5rem 0.75rem",
                borderRadius: "var(--radius-md)",
                background: i === 2 ? "var(--sidebar-active)" : "transparent",
                color: i === 2 ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
              }}
            >
              {item}
            </div>
          ))}
        </nav>
      </aside>
      <main style={{ flex: 1 }}>
        <PageShell>
          <PageHeader
            title="Compliance Requests"
            description="Sample shell screen built from shared design-system primitives."
            actions={<Button variant="secondary">Export CSV</Button>}
          />
          <Section title="Open requests">
            <Card padding="none">
              <DataTable
                rowKey={(r) => r.id}
                rows={complianceRequests}
                columns={[
                  { key: "id", header: "Request", accessor: (r) => r.id },
                  { key: "tenant", header: "Tenant", accessor: (r) => r.tenant, sortable: true },
                  { key: "type", header: "Type", accessor: (r) => r.type },
                  { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
                ]}
              />
            </Card>
          </Section>
        </PageShell>
      </main>
    </div>
  );
}
