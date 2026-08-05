"use client";

// DEV-ONLY route: not linked from any nav. Accessible directly at
// /dev/design-system for reviewing the @serviceos/design-system component
// library in both themes. Do not add this to lib/nav-config.ts.

import React, { useState } from "react";
import {
  Button,
  StatusBadge,
  Input,
  Textarea,
  Select,
  Card,
  Modal,
  Drawer,
  Tooltip,
  Alert,
  Skeleton,
  Spinner,
  EmptyState,
  ErrorState,
  PermissionDeniedState,
  PageShell,
  PageHeader,
  Section,
  DataTable,
  useTheme,
  ThemeProvider,
  pushToast,
} from "@serviceos/design-system";

const fixtureBookings = [
  { id: "BK-1042", customer: "Rhea Kapoor", service: "AC Deep Clean", status: "scheduled", amount: 1499 },
  { id: "BK-1041", customer: "Vikram Shah", service: "Plumbing Repair", status: "completed", amount: 899 },
  { id: "BK-1039", customer: "Anita Desai", service: "Home Painting", status: "pending", amount: 12500 },
  { id: "BK-1035", customer: "Farhan Ali", service: "Pest Control", status: "cancelled", amount: 699 },
  { id: "BK-1030", customer: "Meera Nair", service: "Electrician Visit", status: "in_progress", amount: 349 },
];

const fixtureTenants = [
  { name: "UrbanFix Services", plan: "Enterprise", status: "active" },
  { name: "QuickCare Home", plan: "Growth", status: "suspended" },
  { name: "TrustHands Co-op", plan: "Starter", status: "pending" },
];

function DesignSystemShowcaseInner() {
  const { resolvedTheme, toggle } = useTheme();
  const [modalOpen, setModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [longText] = useState(
    "Compliance review requested for tenant UrbanFix Services regarding a background-check document that expired ninety days ago and has not yet been re-submitted by the provider despite two reminder notifications."
  );

  return (
    <PageShell>
      <PageHeader
        title="Design System Showcase (dev only)"
        description="Not part of the product nav — for reviewing components in light/dark, default/hover/disabled/error/loading/long-text states."
        actions={
          <Button variant="secondary" onClick={toggle}>
            Switch to {resolvedTheme === "dark" ? "light" : "dark"}
          </Button>
        }
      />

      <Section title="Buttons">
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="tertiary">Tertiary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="link">Link action</Button>
          <Button variant="primary" loading>
            Saving
          </Button>
          <Button variant="primary" disabled>
            Disabled
          </Button>
        </div>
      </Section>

      <Section title="Status registry">
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          {["active", "pending", "approved", "rejected", "cancelled", "in_progress", "expired", "totally_unknown_status"].map((s) => (
            <StatusBadge key={s} status={s} />
          ))}
        </div>
      </Section>

      <Section title="Form fields">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
          <Input label="Tenant name" required placeholder="UrbanFix Services" />
          <Input label="Contact email" status="error" message="Enter a valid email address" defaultValue="not-an-email" />
          <Input label="Storage quota (GB)" status="success" message="Looks good" defaultValue="50" disabled={false} />
          <Select label="Compliance tier" options={[{ value: "t1", label: "Tier 1" }, { value: "t2", label: "Tier 2" }]} placeholder="Choose a tier" />
          <Textarea label="Rejection reason" description="Shown to the provider" message={longText} status="warning" />
        </div>
      </Section>

      <Section title="Cards, alerts, tooltips">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
          <Card title="Compliance request" actions={<Tooltip label="View full history"><Button variant="icon" aria-label="View history">i</Button></Tooltip>}>
            <p className="ds-text-body">{longText}</p>
          </Card>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <Alert tone="success" title="Package activated">Storage quota applied for tenant.</Alert>
            <Alert tone="warning" title="Approaching quota">85% of storage used this cycle.</Alert>
            <Alert tone="danger" title="Payment failed" onDismiss={() => {}}>Retry the transaction or contact billing.</Alert>
            <Button onClick={() => pushToast({ tone: "success", title: "Toast fired", description: "This auto-dismisses in 4s." })}>
              Fire a toast
            </Button>
          </div>
        </div>
      </Section>

      <Section title="Loading & skeletons">
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <Spinner />
          <Skeleton width="10rem" height="1rem" />
          <Skeleton width="6rem" height="2rem" radius="var(--radius-md)" />
        </div>
      </Section>

      <Section title="Modal & drawer">
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Button onClick={() => setModalOpen(true)}>Open modal</Button>
          <Button variant="secondary" onClick={() => setDrawerOpen(true)}>
            Open drawer
          </Button>
        </div>
        <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Reject compliance request" footer={<><Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button><Button variant="destructive">Reject</Button></>}>
          <p className="ds-text-body">{longText}</p>
        </Modal>
        <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Tenant detail">
          <p className="ds-text-body">UrbanFix Services — Enterprise plan, 12 active technicians.</p>
        </Drawer>
      </Section>

      <Section title="State views">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
          <Card padding="none">
            <EmptyState title="No bookings yet" description="Bookings will appear here once created." primaryAction={<Button>Create booking</Button>} />
          </Card>
          <Card padding="none">
            <ErrorState title="Couldn't load tenants" description="The tenant service returned a 500 error." primaryAction={<Button variant="secondary">Retry</Button>} />
          </Card>
          <Card padding="none">
            <PermissionDeniedState title="Access restricted" description="You need the compliance.review permission to view this page." />
          </Card>
        </div>
      </Section>

      <Section title="DataTable">
        <DataTable
          rowKey={(r) => r.id}
          rows={fixtureBookings}
          columns={[
            { key: "id", header: "Booking", accessor: (r) => r.id, sortable: true },
            { key: "customer", header: "Customer", accessor: (r) => r.customer, sortable: true },
            { key: "service", header: "Service", accessor: (r) => r.service },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
            { key: "amount", header: "Amount", align: "right", accessor: (r) => r.amount, sortable: true, render: (r) => `₹${r.amount.toLocaleString("en-IN")}` },
          ]}
          mobileCard={(r) => (
            <Card>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{r.customer}</strong>
                <StatusBadge status={r.status} />
              </div>
              <div className="ds-text-body-compact">{r.service} — ₹{r.amount.toLocaleString("en-IN")}</div>
            </Card>
          )}
        />
      </Section>

      <Section title="DataTable — loading / empty / error">
        <div style={{ display: "grid", gap: "1rem" }}>
          <DataTable rowKey={(r: any) => r.id} rows={[]} loading columns={[{ key: "a", header: "A" }]} />
          <DataTable rowKey={(r: any) => r.id} rows={[]} columns={[{ key: "a", header: "A" }]} emptyTitle="No tenants match this filter" />
          <DataTable rowKey={(r: any) => r.id} rows={[]} error="Request timed out" columns={[{ key: "a", header: "A" }]} />
        </div>
      </Section>

      <Section title="Reference fixture: tenants">
        <ul>
          {fixtureTenants.map((t) => (
            <li key={t.name} style={{ display: "flex", gap: "0.5rem", alignItems: "center", padding: "0.25rem 0" }}>
              {t.name} — {t.plan} <StatusBadge status={t.status} variant="dot" />
            </li>
          ))}
        </ul>
      </Section>
    </PageShell>
  );
}


/**
 * Real build failure fixed here: this dev-only showcase renders
 * `@serviceos/design-system` components that call that package's OWN
 * `useTheme`, which throws outside its `ThemeProvider`. The app's root
 * layout deliberately does NOT mount that provider (it uses this app's own
 * `hooks/useTheme` with a different localStorage key -- see the comment in
 * app/layout.tsx), so prerendering this page crashed with "useTheme must be
 * used within a ThemeProvider" and FAILED THE WHOLE PRODUCTION BUILD.
 *
 * Scoping the provider to this one dev route fixes the build without
 * touching app-wide theming, which was changed deliberately.
 */
export default function DesignSystemShowcase() {
  return (
    <ThemeProvider>
      <DesignSystemShowcaseInner />
    </ThemeProvider>
  );
}
