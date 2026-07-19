/**
 * DESIGN PHASE UX-03 — dev-only showcase index. NOT linked from production
 * nav. Lists every example route built in this phase.
 */
import Link from "next/link";

const EXAMPLES: { href: string; label: string }[] = [
  { href: "/dev/ux-03/dashboard-pre-approval", label: "Dashboard — Pre-Approval" },
  { href: "/dev/ux-03/dashboard-approved", label: "Dashboard — Approved Business" },
  { href: "/dev/ux-03/setup-wizard", label: "First-Time Setup Wizard" },
  { href: "/dev/ux-03/profile-under-review", label: "Business Profile — Under Review" },
  { href: "/dev/ux-03/profile-changes-requested", label: "Business Profile — Changes Requested" },
  { href: "/dev/ux-03/team-list", label: "Team Members — List" },
  { href: "/dev/ux-03/team-staff-detail", label: "Team Member Detail — Staff" },
  { href: "/dev/ux-03/team-technician-detail", label: "Team Member Detail — Technician" },
  { href: "/dev/ux-03/permission-editor", label: "StaffPermission Editor" },
  { href: "/dev/ux-03/booking-list", label: "Booking List (field_ops.Job pipeline)" },
  { href: "/dev/ux-03/job-list", label: "Job List (ServiceJob pipeline)" },
  { href: "/dev/ux-03/job-detail", label: "Job Detail" },
  { href: "/dev/ux-03/dispatch-workspace", label: "Assignment / Dispatch Workspace" },
  { href: "/dev/ux-03/parts-approval", label: "Parts Request Approval (ServiceJob-only)" },
  { href: "/dev/ux-03/package-credits", label: "Package / Credits / Commission" },
  { href: "/dev/ux-03/finance-history", label: "Finance History" },
  { href: "/dev/ux-03/security-deposit", label: "Security Deposit" },
  { href: "/dev/ux-03/pricing", label: "Pricing Management" },
  { href: "/dev/ux-03/service-areas", label: "Service Areas" },
  { href: "/dev/ux-03/customers-complaints", label: "Customers & Complaints" },
  { href: "/dev/ux-03/compliance", label: "Compliance" },
  { href: "/dev/ux-03/media", label: "Media Management" },
  { href: "/dev/ux-03/settings", label: "Business Settings (save-bar pattern)" },
  { href: "/dev/ux-03/audit-activity", label: "Audit / Activity (tenant-scoped)" },
  { href: "/dev/ux-03/read-only-restricted", label: "Read-Only / Restricted States" },
];

export default function Ux03ShowcaseIndex() {
  return (
    <div style={{ padding: "2rem", maxWidth: "56rem", margin: "0 auto" }}>
      <h1>UX-03 Tenant Portal — Dev Showcase</h1>
      <p style={{ color: "#666" }}>
        Dev-only routes. Not linked from production nav. Every page here uses
        fixture data from lib/ux03/fixtures.ts (MOCK_DESIGN_ONLY / READ_ONLY_READY
        per readiness-state-registry.csv) — no real API calls.
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
