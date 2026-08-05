"use client";
/** Home Services Customer Relationships — detail panel with tabs, matching
 * the reference design's structure. Per the customer-privacy policy, there
 * is deliberately NO "Providers Used" tab and NO "Addresses" tab -- those
 * are exactly the cross-tenant / permanent-address-book surfaces removed
 * by this task. Contact is never shown raw; only the alias and a
 * disclosure that contact is protected. */
import React, { useCallback, useState } from "react";
import { X, Lock, ClipboardList, CheckCircle2, XCircle, Wrench, Star, ShieldAlert, Wallet } from "lucide-react";
import { Card, Badge, Skeleton } from "../shared/ui";
import { hsCustomersApi, type HsCustomerDetail } from "../../lib/api";
import { useApi } from "../../hooks/useApi";

/** These tab feeds are backend-shaped list payloads that this panel renders
 * field-by-field. Naming the envelope explicitly keeps `ListTab`'s generic
 * from collapsing to `unknown`, which is what made every row field below an
 * error. See lib/api-tenant-workspaces.ts for why the client itself is
 * permissive and where the durable fix (schema tests) belongs. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FeedRow = any;
type Feed = { items: FeedRow[]; total?: number };

const TABS = ["Overview", "Services Used", "Jobs", "Payments", "Complaints", "Reviews", "Activity"] as const;
type Tab = typeof TABS[number];

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function CustomerDetailPanel({ customerId, onClose }: { customerId: string; onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("Overview");

  const detail = useApi(useCallback(() => hsCustomersApi.detail(customerId), [customerId]));
  const jobs = useApi<Feed>(useCallback(() => hsCustomersApi.jobs<Feed>(customerId), [customerId]));
  const complaints = useApi<Feed>(useCallback(() => hsCustomersApi.complaints<Feed>(customerId), [customerId]));
  const payments = useApi<Feed>(useCallback(() => hsCustomersApi.payments<Feed>(customerId), [customerId]));
  const reviews = useApi<Feed>(useCallback(() => hsCustomersApi.reviews<Feed>(customerId), [customerId]));
  const activity = useApi<Feed>(useCallback(() => hsCustomersApi.activity<Feed>(customerId), [customerId]));

  const d: HsCustomerDetail | null = detail.data;

  return (
    <Card padding={0} style={{ width: 420, flexShrink: 0, position: "sticky", top: 24 }}>
      <div style={{ padding: 20, maxHeight: 760, overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 44, height: 44, borderRadius: "50%", background: "var(--accent-muted)",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15, fontWeight: 700, color: "var(--accent)" }}>
              {d ? d.alias.replace("Customer ", "").slice(0, 2) : "…"}
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>{d?.alias ?? "Loading…"}</h3>
              <div style={{ display: "flex", gap: 6 }}>
                {d && <Badge variant={d.is_active ? "success" : "muted"} size="sm">{d.is_active ? "Active" : "Inactive"}</Badge>}
                {d && d.repeat_status === "repeat" && <Badge variant="info" size="sm">Repeat customer</Badge>}
              </div>
            </div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}>
            <X size={16}/>
          </button>
        </div>

        <div style={{ display: "flex", gap: 6, padding: "8px 10px", borderRadius: 8, background: "var(--surface-sunken)",
          border: "1px solid var(--border)", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 16 }}>
          <Lock size={12} style={{ flexShrink: 0, marginTop: 1 }}/>
          <span>Customer contact is protected by ServiceOS and available only during authorized job activity.</span>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--border)", marginBottom: 16, overflowX: "auto" }}>
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "8px 10px", background: "none", border: "none", cursor: "pointer", whiteSpace: "nowrap",
              fontSize: 12, fontWeight: tab === t ? 700 : 500,
              color: tab === t ? "var(--brand)" : "var(--text-tertiary)",
              borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
            }}>
              {t}
            </button>
          ))}
        </div>

        {detail.loading ? <Skeleton height={300}/> : !d ? (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Could not load this relationship.</p>
        ) : tab === "Overview" ? (
          <OverviewTab d={d} activity={activity.data?.items ?? []} activityLoading={activity.loading}/>
        ) : tab === "Services Used" ? (
          <ServicesUsedTab d={d}/>
        ) : tab === "Jobs" ? (
          <ListTab loading={jobs.loading} items={jobs.data?.items ?? []} empty="No jobs yet."
            render={j => (
              <div key={j.job_id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>{j.job_number}</span>
                  <Badge variant={j.status === "completed" ? "success" : j.status === "cancelled" ? "danger" : "info"} size="sm">{j.status}</Badge>
                </div>
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                  {j.master_service_name ?? "Service"} · {fmtDate(j.scheduled_date)}
                </p>
              </div>
            )}/>
        ) : tab === "Payments" ? (
          <ListTab loading={payments.loading} items={payments.data?.items ?? []} empty="No payment records yet."
            footer="Paid directly to the provider. ServiceOS records confirmation only."
            render={p => (
              <div key={p.payment_id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>₹{Number(p.collected_amount).toLocaleString("en-IN")}</span>
                  <Badge variant={p.customer_confirmed ? "success" : "warning"} size="sm">{p.customer_confirmed ? "Confirmed" : "Pending"}</Badge>
                </div>
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{p.payment_mode} · {fmtDate(p.created_at)}</p>
              </div>
            )}/>
        ) : tab === "Complaints" ? (
          <ListTab loading={complaints.loading} items={complaints.data?.items ?? []} empty="No complaints on record."
            render={c => (
              <div key={c.complaint_id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>{c.complaint_number}</span>
                  <Badge variant={c.status === "resolved" || c.status === "closed" ? "success" : "warning"} size="sm">{c.status}</Badge>
                </div>
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{c.title} · {fmtDate(c.created_at)}</p>
              </div>
            )}/>
        ) : tab === "Reviews" ? (
          <ListTab loading={reviews.loading} items={reviews.data?.items ?? []} empty="No reviews yet."
            render={r => (
              <div key={r.review_id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Star size={13} style={{ color: "var(--warning-text)" }}/>
                  <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>{r.overall_rating} / 5</span>
                </div>
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{fmtDate(r.created_at)}</p>
              </div>
            )}/>
        ) : (
          <ListTab loading={activity.loading} items={activity.data?.items ?? []} empty="No activity recorded yet."
            render={a => (
              <div key={`${a.source_system}-${a.source_record_id}-${a.timestamp}`} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: "0 0 2px" }}>{a.description}</p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{fmtDate(a.timestamp)} · {a.actor}</p>
              </div>
            )}/>
        )}
      </div>
    </Card>
  );
}

function OverviewTab({ d, activity, activityLoading }: {
  d: HsCustomerDetail; activity: { description: string; timestamp: string | null }[]; activityLoading: boolean;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
        <StatBox icon={<ClipboardList size={14}/>} label="Total jobs" value={d.completed_jobs + d.cancelled_jobs}/>
        <StatBox icon={<CheckCircle2 size={14}/>} label="Completed" value={d.completed_jobs} tone="success"/>
        <StatBox icon={<XCircle size={14}/>} label="Cancelled" value={d.cancelled_jobs} tone="danger"/>
      </div>

      <Section title="Recent activity">
        {activityLoading ? <Skeleton height={80}/> : activity.length === 0 ? (
          <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No activity recorded yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {activity.slice(0, 4).map((a, i) => (
              <div key={i} style={{ display: "flex", gap: 8 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--brand)", marginTop: 5, flexShrink: 0 }}/>
                <div>
                  <p style={{ fontSize: 12, color: "var(--text-primary)", margin: 0 }}>{a.description}</p>
                  <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: 0 }}>{fmtDate(a.timestamp)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Services used">
        {d.services_used_by_master_service.length === 0 ? (
          <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No completed services yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {d.services_used_by_master_service.map(s => (
              <div key={s.offering_id} style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                <span style={{ color: "var(--text-primary)" }}>{s.master_service_name ?? "Service"}</span>
                <span style={{ color: "var(--text-tertiary)" }}>{s.completed_jobs}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Payment behaviour">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <Wallet size={14} style={{ color: "var(--success-text)" }}/>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>₹{Number(d.confirmed_job_value).toLocaleString("en-IN")}</span>
          <span style={{ fontSize: 11.5, color: "var(--text-tertiary)" }}>confirmed lifetime</span>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
          {d.payment_reliability === "not_implemented" || d.payment_reliability === "insufficient_data"
            ? "Payment-reliability scoring isn't available yet — not enough confirmed jobs, or no canonical model exists for it."
            : d.payment_reliability}
        </p>
      </Section>

      {d.open_complaints > 0 && (
        <div style={{ display: "flex", gap: 8, padding: "10px 12px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
          <ShieldAlert size={14} style={{ color: "var(--danger-text)", flexShrink: 0, marginTop: 1 }}/>
          <span style={{ fontSize: 12, color: "var(--danger-text)" }}>{d.open_complaints} open complaint{d.open_complaints > 1 ? "s" : ""} for this relationship.</span>
        </div>
      )}
    </div>
  );
}

function ServicesUsedTab({ d }: { d: HsCustomerDetail }) {
  return (
    <div>
      {d.services_used_by_master_service.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No completed services yet.</p>
      ) : d.services_used_by_master_service.map(s => (
        <div key={s.offering_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
          <Wrench size={14} style={{ color: "var(--text-tertiary)" }}/>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{s.master_service_name ?? "Service"}</p>
          </div>
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{s.completed_jobs} job{s.completed_jobs === 1 ? "" : "s"}</span>
        </div>
      ))}
    </div>
  );
}

function ListTab<T>({ items, loading, empty, render, footer }: {
  items: T[]; loading: boolean; empty: string; render: (item: T) => React.ReactNode; footer?: string;
}) {
  if (loading) return <Skeleton height={200}/>;
  if (items.length === 0) return <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>{empty}</p>;
  return (
    <div>
      {items.map(render)}
      {footer && <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10 }}>{footer}</p>}
    </div>
  );
}

function StatBox({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: number; tone?: "success" | "danger" }) {
  const color = tone === "success" ? "var(--success-text)" : tone === "danger" ? "var(--danger-text)" : "var(--text-primary)";
  return (
    <div style={{ padding: "10px 12px", borderRadius: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, color: "var(--text-tertiary)" }}>{icon}<span style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.03em" }}>{label}</span></div>
      <p style={{ fontSize: 20, fontWeight: 800, color, margin: 0 }}>{value}</p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", margin: "0 0 8px" }}>{title}</p>
      {children}
    </div>
  );
}
