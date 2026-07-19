"use client";
import { PageShell, PageHeader, Section, Card } from "@serviceos/design-system";
import { FIXTURE_TENANTS } from "../../../../lib/ux02/fixtures";

/**
 * Finance presentation — respects the canonical rule: platform package
 * credit is not the same as ordinary on-site job payments. Commission is
 * deducted from tenant credit; security deposit is separate; there is no
 * payout/withdrawal UI here because ServiceOS does not process ordinary
 * job payments on tenants' behalf.
 */
export default function FinancePresentationShowcase() {
  const totalCredit = FIXTURE_TENANTS.reduce((s, t) => s + t.packageCreditBalance, 0);
  const totalDeposit = FIXTURE_TENANTS.reduce((s, t) => s + t.securityDepositAmount, 0);
  return (
    <PageShell>
      <PageHeader title="Finance Summary" description="MOCK_DESIGN_ONLY — platform package credit / commission / deposit presentation. No payout or withdrawal UI (ordinary job payments are not processed by the platform)." />
      <Section title="Platform Package Credit">
        <Card><div style={{ fontSize: "1.5rem", fontWeight: 700 }}>${totalCredit.toLocaleString()}</div><p style={{ color: "var(--text-secondary)" }}>Sum of all tenants' package credit balances — NOT ordinary job-payment revenue.</p></Card>
      </Section>
      <Section title="Security Deposits Held">
        <Card><div style={{ fontSize: "1.5rem", fontWeight: 700 }}>${totalDeposit.toLocaleString()}</div><p style={{ color: "var(--text-secondary)" }}>Held separately from package credit; not commission-eligible.</p></Card>
      </Section>
      <Section title="Commission (deducted from tenant package credit)">
        {FIXTURE_TENANTS.map((t) => (
          <Card key={t.id}><div style={{ display: "flex", justifyContent: "space-between" }}><span>{t.displayName}</span><span>{(t.commissionRateBps / 100).toFixed(2)}%</span></div></Card>
        ))}
      </Section>
    </PageShell>
  );
}
