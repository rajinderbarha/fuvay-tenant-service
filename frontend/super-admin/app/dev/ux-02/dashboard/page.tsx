"use client";
import { useState } from "react";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { RoleDashboard } from "../../../../components/ux02/widgets/RoleDashboard";
import type { CanonicalAdminRole } from "../../../../lib/ux02/types";

const ROLES: CanonicalAdminRole[] = ["super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly"];

export default function DashboardShowcase() {
  const [role, setRole] = useState<CanonicalAdminRole>("super_admin");
  return (
    <PageShell>
      <PageHeader
        title="Role Dashboard"
        description="One dashboard system, configured per canonical role. Switch roles below to see composition change."
        actions={
          <select aria-label="Preview role" value={role} onChange={(e) => setRole(e.target.value as CanonicalAdminRole)} style={{ padding: "0.5rem", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        }
      />
      <RoleDashboard role={role} />
    </PageShell>
  );
}
