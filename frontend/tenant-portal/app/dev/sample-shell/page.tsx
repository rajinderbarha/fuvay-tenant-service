"use client";

// DEV-ONLY sample screen demonstrating shell+nav+header+status+table+states
// composed purely from @serviceos/design-system primitives. Not linked from
// nav-config.ts; illustrative only, does not replace real tenant-portal pages.

import React from "react";
import { PageShell, PageHeader, Section, Card, StatusBadge, DataTable, Button } from "@serviceos/design-system";
import { Wrench } from "lucide-react";

const jobs = [
  { id: "JOB-2201", technician: "Ravi Kumar", service: "AC Deep Clean", status: "scheduled" },
  { id: "JOB-2198", technician: "Sana Iqbal", service: "Plumbing Repair", status: "completed" },
  { id: "JOB-2190", technician: "Unassigned", service: "Electrician Visit", status: "pending" },
];

export default function SampleTenantShell() {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <aside style={{ width: "15rem", background: "var(--sidebar-bg)", color: "var(--sidebar-text)", padding: "1.5rem 1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--sidebar-text-active)", marginBottom: "1.5rem" }}>
          <Wrench size={20} />
          <strong>UrbanFix Services</strong>
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          {["Dashboard", "Jobs", "Staff", "Invoices"].map((item, i) => (
            <div
              key={item}
              style={{
                padding: "0.5rem 0.75rem",
                borderRadius: "var(--radius-md)",
                background: i === 1 ? "var(--sidebar-active)" : "transparent",
                color: i === 1 ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
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
            title="Service Jobs"
            description="Sample shell screen built from shared design-system primitives."
            actions={<Button variant="primary">Assign job</Button>}
          />
          <Section title="Today's jobs">
            <Card padding="none">
              <DataTable
                rowKey={(r) => r.id}
                rows={jobs}
                columns={[
                  { key: "id", header: "Job", accessor: (r) => r.id },
                  { key: "technician", header: "Technician", accessor: (r) => r.technician, sortable: true },
                  { key: "service", header: "Service", accessor: (r) => r.service },
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
