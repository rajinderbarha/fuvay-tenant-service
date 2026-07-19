"use client";
import type React from "react";
import { PageShell } from "@serviceos/design-system";
import { Card, Section, StatusBadge } from "@serviceos/design-system";
import { EnterpriseDetailPage } from "../../../../../components/ux02/patterns/EnterpriseDetailPage";
import { FIXTURE_TENANTS, FIXTURE_COMPLIANCE_CASES, FIXTURE_AUDIT_ENTRIES } from "../../../../../lib/ux02/fixtures";

/** Tenant 360 — 15 sections per spec, sticky nav desktop / select on mobile. */
export default function Tenant360Showcase({ params }: { params: { id: string } }) {
  const tenant = FIXTURE_TENANTS.find((t) => t.id === params.id) ?? FIXTURE_TENANTS[0];
  const cases = FIXTURE_COMPLIANCE_CASES.filter((c) => c.tenantId === tenant.id);
  const audit = FIXTURE_AUDIT_ENTRIES.filter((a) => a.tenantId === tenant.id);

  const kv = (label: string, value: React.ReactNode) => (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "0.375rem 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ color: "var(--text-secondary)" }}>{label}</span><span>{value}</span>
    </div>
  );

  const sections = [
    { id: "overview", label: "Overview", content: <Card><Section title="Overview">{kv("Legal Name", tenant.legalName)}{kv("Vertical", tenant.vertical)}{kv("Status", <StatusBadge status={tenant.status} />)}{kv("Created", tenant.createdAt)}</Section></Card> },
    { id: "owner", label: "Owner & Contacts", content: <Card><Section title="Owner">{kv("Name", tenant.ownerName)}{kv("Email", tenant.ownerEmail)}</Section></Card> },
    { id: "plan", label: "Plan & Package", content: <Card><Section title="Plan">{kv("Package", tenant.planPackage)}{kv("Package Credit Balance", `$${tenant.packageCreditBalance.toLocaleString()}`)}{kv("Commission Rate", `${(tenant.commissionRateBps / 100).toFixed(2)}%`)}</Section></Card> },
    { id: "deposit", label: "Security Deposit", content: <Card><Section title="Security Deposit">{kv("Amount held", `$${tenant.securityDepositAmount.toLocaleString()}`)}<p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>Separate from package credit; not payable to platform for ordinary job payments.</p></Section></Card> },
    { id: "storage", label: "Storage", content: <Card><Section title="Storage Quota">{kv("Used / Quota", `${tenant.storageUsedGb} / ${tenant.storageQuotaGb} GB`)}</Section></Card> },
    { id: "staff", label: "Staff", content: <Card><Section title="Staff">{kv("Staff Count", tenant.staffCount)}</Section></Card> },
    { id: "serviceability", label: "Serviceability", content: <Card><Section title="Serviceability">{kv("Region", `${tenant.city}, ${tenant.region}`)}</Section></Card> },
    { id: "bookings", label: "Bookings", content: <Card><Section title="Bookings">MOCK_DESIGN_ONLY — booking summary widget placeholder.</Section></Card> },
    { id: "invoices", label: "Invoices", content: <Card><Section title="Invoices">MOCK_DESIGN_ONLY — invoice list placeholder.</Section></Card> },
    { id: "complaints", label: "Complaints", content: <Card><Section title="Complaints">{kv("Open Complaints", tenant.openComplaints)}</Section></Card> },
    { id: "compliance", label: "Compliance Cases", content: <Card><Section title="Compliance Cases">{cases.length === 0 ? "None" : cases.map(c => <div key={c.id}>{c.title} — <StatusBadge status={c.status} /></div>)}</Section></Card> },
    { id: "verification", label: "Verification", content: <Card><Section title="Verification">MOCK_DESIGN_ONLY — link to Verification Review workspace.</Section></Card> },
    { id: "reviews", label: "Reviews & Ratings", content: <Card><Section title="Reviews">MOCK_DESIGN_ONLY placeholder.</Section></Card> },
    { id: "notifications", label: "Notifications", content: <Card><Section title="Notifications">MOCK_DESIGN_ONLY placeholder.</Section></Card> },
    { id: "audit", label: "Audit Trail", content: <Card><Section title="Audit Trail">{audit.length === 0 ? "No entries in fixture set" : audit.map(a => <div key={a.id}>{a.timestamp} · {a.action} · {a.result}</div>)}</Section></Card> },
  ];

  return (
    <PageShell>
      <EnterpriseDetailPage title={tenant.displayName} subtitle={tenant.legalName} readiness="MOCK_DESIGN_ONLY" sections={sections} />
    </PageShell>
  );
}
