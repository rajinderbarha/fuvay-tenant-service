"use client";
import { useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Badge, Btn } from "../../../../../components/shared/ui";
import { catalogApi } from "../../../../../lib/api";
import { useApi } from "../../../../../hooks/useApi";
import type { PricingRule } from "../../../../../lib/api";

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display:"flex", gap:12, padding:"10px 0", borderBottom:"1px solid var(--border)" }}>
      <span style={{ fontSize:12, color:"var(--text-tertiary)", minWidth:180, fontWeight:500 }}>{label}</span>
      <div style={{ fontSize:13, color:"var(--text-primary)", flex:1 }}>{children}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card padding={16}>
      <h3 style={{ margin:"0 0 12px", fontSize:14, fontWeight:700 }}>{title}</h3>
      {children}
    </Card>
  );
}

export default function TierDetailPage() {
  const { tier_id } = useParams<{ tier_id: string }>();
  const router = useRouter();
  const detail = useApi(useCallback(() => catalogApi.getTierDetail(tier_id), [tier_id]));

  const d = detail.data;

  return (
    <AdminLayout activeNav="pricing-tiers">
      <SectionHeader title="Pricing Tier Detail" subtitle="Overview, mapped locations, pricing rules, and audit history for this tier."/>
      <div style={{ padding:"0 28px 32px", display:"flex", flexDirection:"column", gap:16 }}>
        <Btn variant="ghost" size="sm" onClick={() => router.push("/admin/pricing-tiers")}>
          <ArrowLeft size={13}/> Back to Pricing Tiers
        </Btn>

        {detail.loading && <Card padding={16}>Loading…</Card>}
        {detail.error && <Card padding={16}><p style={{ color:"var(--danger-text)" }}>{detail.error}</p></Card>}

        {d && (
          <>
            <Section title="Overview">
              <InfoRow label="Name">{d.tier.name}</InfoRow>
              <InfoRow label="Code">{d.tier.code}</InfoRow>
              <InfoRow label="Type"><span style={{ textTransform:"capitalize" }}>{d.tier.tier_type.replace(/_/g," ")}</span></InfoRow>
              <InfoRow label="Multiplier">×{d.tier.base_multiplier}</InfoRow>
              <InfoRow label="Platform Fee">{d.tier.platform_fee_percent}%</InfoRow>
              <InfoRow label="Default SLA">{d.tier.default_sla_minutes} min</InfoRow>
              <InfoRow label="Status">
                <Badge variant={d.tier.is_active ? "success" : "muted"}>{d.tier.is_active ? "Active" : "Inactive"}</Badge>
              </InfoRow>
              {d.tier.description && <InfoRow label="Description">{d.tier.description}</InfoRow>}
            </Section>

            <Section title={`Mapped Cities (${d.mapped_cities.length})`}>
              {d.mapped_cities.length === 0 ? (
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No cities mapped to this tier yet.</p>
              ) : (
                <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                  {d.mapped_cities.map(c => <Badge key={c} variant="info">{c}</Badge>)}
                </div>
              )}
            </Section>

            <Section title={`Mapped Zipcodes (${d.mapped_zipcodes.length})`}>
              {d.mapped_zipcodes.length === 0 ? (
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No zipcodes mapped to this tier yet.</p>
              ) : (
                <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                  {d.mapped_zipcodes.map(z => <Badge key={z} variant="muted">{z}</Badge>)}
                </div>
              )}
            </Section>

            <Section title={`Zones (${d.zones.length})`}>
              {d.zones.length === 0 ? (
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No zones mapped to this tier yet.</p>
              ) : (
                <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                  {d.zones.map(z => <Badge key={z} variant="muted">{z}</Badge>)}
                </div>
              )}
            </Section>

            <Section title={`Pricing Rules Using This Tier (${d.pricing_rules.length})`}>
              {d.pricing_rules.length === 0 ? (
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No pricing rules reference this tier yet.</p>
              ) : (
                <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
                  <thead>
                    <tr style={{ borderBottom:"1px solid var(--border)" }}>
                      {["Rule","Pricing Model","Price","Priority","Status"].map(h => (
                        <th key={h} style={{ textAlign:"left", padding:"6px 8px", fontSize:11, color:"var(--text-tertiary)", textTransform:"uppercase" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {d.pricing_rules.map((r: PricingRule) => (
                      <tr key={r.rule_id} style={{ borderBottom:"1px solid var(--border)" }}>
                        <td style={{ padding:"8px" }}>{r.rule_name || r.rule_code || r.rule_id}</td>
                        <td style={{ padding:"8px" }}>{r.pricing_model}</td>
                        <td style={{ padding:"8px" }}>₹{r.base_price.toLocaleString("en-IN")}</td>
                        <td style={{ padding:"8px" }}>{r.priority}</td>
                        <td style={{ padding:"8px" }}>
                          <Badge variant={r.is_active ? "success" : "muted"}>{r.is_active ? "Active" : "Inactive"}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Section>

            <div id="audit">
              <Section title={`Audit Logs (${d.audit_log.length})`}>
                {d.audit_log.length === 0 ? (
                  <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No audit history yet.</p>
                ) : (
                  <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                    {d.audit_log.map(a => (
                      <div key={a.id} style={{ fontSize:12, padding:"8px 0", borderBottom:"1px solid var(--border)" }}>
                        <strong style={{ textTransform:"capitalize" }}>{a.action}</strong>
                        {a.actor_role && <span style={{ color:"var(--text-tertiary)" }}> · {a.actor_role}</span>}
                        {a.created_at && <span style={{ color:"var(--text-tertiary)" }}> · {new Date(a.created_at).toLocaleString()}</span>}
                        {a.change_summary && <p style={{ margin:"4px 0 0", color:"var(--text-secondary)" }}>{a.change_summary}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </Section>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
