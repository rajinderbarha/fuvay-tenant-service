"use client";
import React, { useState } from "react";
import Link from "next/link";
import { Card, Btn, EmptyState, Skeleton } from "../shared/ui";
import { TenantStatusBadge } from "./TenantStatusBadge";
import { ChevronDown, ChevronUp, Wrench, Zap } from "lucide-react";
import { safeText, safeCurrency, safeStatus, safeDate, type RequiredAction } from "../../lib/status-format";
import type { EnabledOffering, OfferingBookableStatus } from "../../lib/api";

// ── Offering Bookability ──────────────────────────────────────────────────

export interface OfferingRow {
  id: string;
  name: string;
  status: string;
  brandCoverage: string;
  typeCoverage: string;
  isBookable: boolean;
  blockers: string[];
}

export function TenantOfferingBookabilityPanel({ offerings, statuses, loading }: {
  offerings: EnabledOffering[]; statuses: OfferingBookableStatus[]; loading: boolean;
}) {
  const statusByOffering = new Map(statuses.map(s => [s.provider_enabled_offering_id, s]));
  const bookableCount = offerings.filter(o => statusByOffering.get(o.provider_enabled_offering_id)?.is_bookable).length;

  return (
    <Card padding={0}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
        <div>
          <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Offering Bookability</p>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0", maxWidth: 560 }}>
            Each service offering must pass catalog, coverage, service area, staff, pricing, availability, and finance checks before it can receive bookings.
          </p>
        </div>
        <Link href="/provider/offerings" style={{ fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none", whiteSpace: "nowrap" }}>
          Manage Offerings →
        </Link>
      </div>

      {loading ? (
        <div style={{ padding: 20 }}><Skeleton height={100}/></div>
      ) : offerings.length === 0 ? (
        <EmptyState
          icon={<Zap/>}
          title="No offerings enabled yet"
          description="Add at least one Home Services offering from the platform catalog to become discoverable."
          action={
            <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
              <Link href="/provider/offerings"><Btn size="sm" variant="primary">Enable Offering</Btn></Link>
              <Link href="/provider/offerings"><Btn size="sm" variant="secondary">View Catalog</Btn></Link>
            </div>
          }
        />
      ) : (
        <>
          <div style={{ padding: "10px 20px", fontSize: 12, color: "var(--text-secondary)", borderBottom: "1px solid var(--border)" }}>
            {bookableCount} of {offerings.length} offerings are bookable
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                  {["Offering", "Type Coverage", "Brand Coverage", "Bookable Status", "Blocking Reasons", "Actions"].map(h => (
                    <th key={h} style={{ padding: "8px 14px", textAlign: "left", fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {offerings.map(o => {
                  const st = statusByOffering.get(o.provider_enabled_offering_id);
                  const isBookable = st?.is_bookable ?? false;
                  const blockers = st?.blockers ?? [];
                  return (
                    <tr key={o.provider_enabled_offering_id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 14px", fontWeight: 600 }}>{safeText(o.provider_display_name || o.offering_name)}</td>
                      <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>
                        {o.supported_type_ids && o.supported_type_ids.length > 0 ? `${o.supported_type_ids.length} type(s)` : "Not configured"}
                      </td>
                      <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>
                        {o.supported_brand_ids && o.supported_brand_ids.length > 0 ? `${o.supported_brand_ids.length} brand(s)` : "Not configured"}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <TenantStatusBadge label={isBookable ? "Bookable" : "Blocked"} variant={isBookable ? "success" : "danger"}/>
                      </td>
                      <td style={{ padding: "10px 14px", color: "#dc2626", maxWidth: 240 }}>
                        {blockers.length === 0 ? <span style={{ color: "var(--text-tertiary)" }}>—</span> : blockers.map(b => b.message).join("; ")}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <Link href={`/provider/offerings`} style={{ fontSize: 11, fontWeight: 700, color: "var(--brand)", textDecoration: "none" }}>
                          View Offering
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Card>
  );
}

// ── Setup Readiness Checklist ──────────────────────────────────────────────

export interface ChecklistItem {
  key: string;
  label: string;
  status: "completed" | "blocked" | "warning" | "pending";
  reason: string;
  cta: string;
  ctaRoute: string;
  ruleKey: string;
}

export function TenantSetupStatusChecklist({ items, lastCheckedAt }: { items: ChecklistItem[]; lastCheckedAt: string | null }) {
  const STATUS_VARIANT = { completed: "success", blocked: "danger", warning: "warning", pending: "info" } as const;
  return (
    <Card padding={0}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
        <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Setup Readiness Checklist</p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>
          Backend-computed from your live account data — not a manual checklist.
        </p>
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {items.map(item => (
          <div key={item.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, padding: "12px 20px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                <TenantStatusBadge label={item.status === "completed" ? "Completed" : item.status === "blocked" ? "Blocked" : item.status === "warning" ? "Warning" : "Pending"} variant={STATUS_VARIANT[item.status]}/>
                <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{item.label}</p>
              </div>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>{item.reason}</p>
              <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "2px 0 0", fontFamily: "monospace" }}>
                Rule: {item.ruleKey} · Last checked: {safeDate(lastCheckedAt)}
              </p>
            </div>
            {item.status !== "completed" && (
              <Link href={item.ctaRoute} style={{ fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none", whiteSpace: "nowrap", flexShrink: 0 }}>
                {item.cta}
              </Link>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Finance Readiness ──────────────────────────────────────────────────────

export function TenantFinanceReadinessPanel(props: {
  packageName: string; packageStatus: string; packageMessage: string;
  creditBalance: number; includedCredits: number;
  depositRequired: number; depositPaid: number; depositStatus: string;
  financeReady: boolean;
}) {
  return (
    <Card padding={0}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Finance Readiness</p>
        <TenantStatusBadge label={props.financeReady ? "Ready" : "Blocked"} variant={props.financeReady ? "success" : "danger"}/>
      </div>
      <div style={{ padding: 20, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 18 }}>
        <div>
          <p style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>Package Status</p>
          <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{safeText(props.packageName, "No package selected")}</p>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>{safeStatus(props.packageStatus)} — {props.packageMessage}</p>
        </div>
        <div>
          <p style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>Usage Credit Balance</p>
          <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{props.creditBalance.toLocaleString("en-IN")} credits</p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
            Included with package: {props.includedCredits.toLocaleString("en-IN")} credits. Usage credits are internal platform credits, not cash, and are not withdrawable.
          </p>
        </div>
        <div>
          <p style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>Security Deposit</p>
          <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{safeCurrency(props.depositRequired)} — {safeStatus(props.depositStatus)}</p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
            {safeCurrency(props.depositPaid)} paid so far. Separate from your usage credit balance; cannot be self-marked as received.
          </p>
        </div>
        <div>
          <p style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>Completed Job Deduction</p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Usage credits are deducted from your balance after each completed job, per the pricing configured for that service. This happens at job completion, not during setup.
          </p>
        </div>
      </div>
    </Card>
  );
}

// ── Operational Readiness ──────────────────────────────────────────────────

export function TenantOperationalReadinessPanel({ rows }: {
  rows: { label: string; status: string; count: string; blockingReason: string | null; ctaLabel: string; ctaRoute: string }[];
}) {
  return (
    <Card padding={0}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
        <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Operational Readiness</p>
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {rows.map(r => (
          <div key={r.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "12px 20px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{r.label}</p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>
                {r.count}{r.blockingReason ? ` — ${r.blockingReason}` : ""}
              </p>
            </div>
            <TenantStatusBadge label={safeStatus(r.status)} variant={r.status === "ready" ? "success" : r.status === "missing" ? "danger" : "warning"}/>
            <Link href={r.ctaRoute} style={{ fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none", whiteSpace: "nowrap" }}>
              {r.ctaLabel}
            </Link>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Visibility Rules Explanation ───────────────────────────────────────────

const RULES = [
  "Tenant approved",
  "Package active",
  "Usage credits available",
  "Security deposit received or waived",
  "At least one active service area",
  "At least one active offering",
  "Coverage configured",
  "At least one active technician",
  "Pricing valid",
  "Availability configured",
  "Documents submitted/verified according to policy",
];

export function TenantVisibilityRulesPanel() {
  const [open, setOpen] = useState(false);
  return (
    <Card padding={0}>
      <button onClick={() => setOpen(o => !o)} style={{
        width: "100%", padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center",
        background: "transparent", border: "none", cursor: "pointer", textAlign: "left",
      }}>
        <div>
          <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>How bookability is calculated</p>
          {!open && (
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>
              Your business becomes bookable when approval, package, usage credits, security deposit, service areas, offerings, coverage, active technicians, pricing, availability, and required documents satisfy platform rules.
            </p>
          )}
        </div>
        {open ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}
      </button>
      {open && (
        <div style={{ padding: "0 20px 20px" }}>
          <ol style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 6 }}>
            {RULES.map(r => (
              <li key={r} style={{ fontSize: 13, color: "var(--text-secondary)" }}>{r}</li>
            ))}
          </ol>
        </div>
      )}
    </Card>
  );
}

// ── Recent Status Activity ─────────────────────────────────────────────────

export interface ActivityRow {
  event: string;
  result: string;
  actor: string;
  requestId: string | null;
  createdAt: string;
}

export function TenantStatusActivityTimeline({ rows, loading }: { rows: ActivityRow[]; loading: boolean }) {
  return (
    <Card padding={0}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
        <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Recent Status Activity</p>
      </div>
      {loading ? (
        <div style={{ padding: 20 }}><Skeleton height={80}/></div>
      ) : rows.length === 0 ? (
        <EmptyState icon={<Wrench/>} title="No status activity yet." description="Status recalculations and setup changes will appear here."/>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                {["Event", "Actor", "Request ID", "Created At"].map(h => (
                  <th key={h} style={{ padding: "8px 14px", textAlign: "left", fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "8px 14px", fontFamily: "monospace" }}>{r.event}</td>
                  <td style={{ padding: "8px 14px" }}>{safeText(r.actor)}</td>
                  <td style={{ padding: "8px 14px", fontFamily: "monospace", color: "var(--text-tertiary)" }}>{safeText(r.requestId)}</td>
                  <td style={{ padding: "8px 14px", color: "var(--text-tertiary)" }}>{safeDate(r.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
