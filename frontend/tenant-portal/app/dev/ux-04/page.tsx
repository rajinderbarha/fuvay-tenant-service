/**
 * DESIGN PHASE UX-04 — dev-only showcase index. NOT linked from production
 * nav. Lists every example route built in this phase. This phase built a
 * pragmatic-depth subset of the full 27-example target — see
 * docs/design/ux-04-tenant-operations/development-showcase-inventory.csv
 * for the complete list including deferred routes and why.
 */
import Link from "next/link";

const EXAMPLES: { href: string; label: string }[] = [
  { href: "/dev/ux-04/command-center", label: "Operations Command Center (role-sensitive action queue)" },
  { href: "/dev/ux-04/booking-list", label: "Booking + Job List (pipeline-aware, combined view)" },
  { href: "/dev/ux-04/job-detail", label: "Job Detail Workspace (ServiceJob — status/quote/checklist/parts/credit/comms)" },
  { href: "/dev/ux-04/assignment-workspace", label: "Assignment / Dispatch Workspace" },
  { href: "/dev/ux-04/parts-approval", label: "Parts Request Approval (ServiceJob-only, provider-side)" },
];

export default function Ux04ShowcaseIndex() {
  return (
    <div style={{ padding: "2rem", maxWidth: "56rem", margin: "0 auto" }}>
      <h1>UX-04 Tenant Operations — Dev Showcase</h1>
      <p style={{ color: "#666" }}>
        Dev-only routes. Not linked from production nav. Built on UX-03&apos;s foundation
        (types/fixtures/patterns) — see docs/design/ux-04-tenant-operations for the full
        specification set and honest scope notes.
      </p>
      <ul>
        {EXAMPLES.map((e) => (
          <li key={e.href}>
            <Link href={e.href}>{e.label}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
