import Link from "next/link";
import { PageShell, PageHeader, Card } from "@serviceos/design-system";

/**
 * DESIGN PHASE UX-02 dev-only showcase index.
 * Not linked from production nav-config.ts. Do not add a production route
 * pointing here.
 */
const ROUTES = [
  { href: "/dev/ux-02/dashboard", label: "Role Dashboard (all 5 canonical roles)" },
  { href: "/dev/ux-02/tenants", label: "Tenant List" },
  { href: "/dev/ux-02/tenants/tn_2201", label: "Tenant 360" },
  { href: "/dev/ux-02/verification", label: "Verification Review Workspace" },
  { href: "/dev/ux-02/compliance", label: "Compliance Case List" },
  { href: "/dev/ux-02/compliance/cc_501", label: "Compliance Case Detail" },
  { href: "/dev/ux-02/security", label: "Security Observations" },
  { href: "/dev/ux-02/audit", label: "Audit Explorer" },
  { href: "/dev/ux-02/finance", label: "Finance Presentation" },
  { href: "/dev/ux-02/settings", label: "Platform Configuration Pattern" },
  { href: "/dev/ux-02/states", label: "States gallery (loading/empty/error/read-only/restricted/long-text)" },
];

export default function Ux02ShowcaseIndex() {
  return (
    <PageShell>
      <PageHeader title="UX-02 Dev Showcase" description="Dev-only. Not linked from production navigation. Fixture data only." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
        {ROUTES.map((r) => (
          <Card key={r.href}><Link href={r.href}>{r.label}</Link></Card>
        ))}
      </div>
    </PageShell>
  );
}
