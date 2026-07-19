"use client";
import { useState } from "react";
import { PageShell, PageHeader, Section, Card, StatusBadge } from "@serviceos/design-system";
import { FIXTURE_AUDIT_ENTRIES } from "../../../../lib/ux02/fixtures";

/** Audit Explorer — redacted JSON viewer, no real secrets in fixtures. */
export default function AuditExplorerShowcase() {
  const [expanded, setExpanded] = useState<string | null>(null);
  return (
    <PageShell>
      <PageHeader title="Audit Explorer" description="MOCK_DESIGN_ONLY — audit coverage across engines is partial; see backend-contract-dependencies.md." />
      <Section>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {FIXTURE_AUDIT_ENTRIES.map((a) => (
            <Card key={a.id}>
              <div style={{ display: "flex", justifyContent: "space-between", cursor: "pointer" }} onClick={() => setExpanded(expanded === a.id ? null : a.id)}>
                <span>{a.timestamp} · {a.actor} ({a.role}) · {a.action} on {a.resource}</span>
                <StatusBadge status={a.result} />
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                Tenant: {a.tenantId ?? "—"} · IP/Device: {a.ipDevice} · Correlation: {a.correlationId} · Risk: {a.risk}
              </div>
              {expanded === a.id && (
                <pre style={{ background: "var(--bg-muted)", padding: "0.75rem", borderRadius: "var(--radius-md)", overflowX: "auto", fontSize: "0.75rem" }}>
                  {JSON.stringify(a.detailsRedacted, null, 2)}
                </pre>
              )}
            </Card>
          ))}
        </div>
      </Section>
    </PageShell>
  );
}
