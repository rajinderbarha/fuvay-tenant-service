"use client";
import { useState } from "react";
import { PageShell, PageHeader, Section, Card, Button } from "@serviceos/design-system";

/** Platform configuration layout pattern — section cards with current
 * value, last-changed-by/when, change history, validation, unsaved-change
 * protection, read-only mode. PRODUCT_DECISION_REQUIRED whether any of
 * these settings get a real write path in this phase. */
const SETTINGS = [
  { id: "s1", label: "Default Commission Rate", value: "10.0%", changedBy: "root", changedAt: "2026-06-01T00:00:00Z" },
  { id: "s2", label: "Default Storage Quota (Starter)", value: "20 GB", changedBy: "priya.s", changedAt: "2026-05-12T00:00:00Z" },
];

export default function PlatformSettingsShowcase() {
  const [dirty, setDirty] = useState(false);
  const [readOnly] = useState(false);
  return (
    <PageShell>
      <PageHeader title="Platform Configuration" description="PRODUCT_DECISION_REQUIRED — pattern only, no write path wired." />
      {dirty && (
        <div role="status" style={{ padding: "0.75rem", border: "1px solid var(--warning-border)", background: "var(--warning-bg)", borderRadius: "var(--radius-md)" }}>
          You have unsaved changes. Navigating away will discard them (design-only guard; no real persistence).
        </div>
      )}
      {SETTINGS.map((s) => (
        <Section key={s.id} title={s.label}>
          <Card>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 600 }}>{s.value}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Last changed by {s.changedBy} on {s.changedAt}</div>
              </div>
              <Button size="sm" disabled={readOnly} onClick={() => setDirty(true)}>Edit</Button>
            </div>
          </Card>
        </Section>
      ))}
    </PageShell>
  );
}
