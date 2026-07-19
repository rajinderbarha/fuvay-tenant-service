"use client";
import { useState } from "react";
import { PageShell, PageHeader, Card, Alert } from "@serviceos/design-system";

export default function Settings() {
  const [dirty, setDirty] = useState(false);
  return (
    <PageShell>
      <PageHeader title="Business Settings" description="Details/hours/booking prefs/notifications/service defaults/locale/branding/security/team defaults." />
      {dirty && <Alert tone="warning" title="Unsaved changes">You have unsaved changes on this page.</Alert>}
      <Card title="Business Hours">
        <label>
          <input type="checkbox" onChange={() => setDirty(true)} /> Open Sundays
        </label>
      </Card>
      <Card title="Booking Preferences (read-only — permission restricted)">
        <p style={{ color: "var(--text-secondary)" }}>Only tenant_owner can edit this section.</p>
      </Card>
      {dirty && (
        <div style={{ position: "sticky", bottom: 0, padding: "0.75rem", background: "var(--surface)", borderTop: "1px solid var(--border)", display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
          <button onClick={() => setDirty(false)}>Discard</button>
          <button onClick={() => setDirty(false)}>Save Changes</button>
        </div>
      )}
    </PageShell>
  );
}
