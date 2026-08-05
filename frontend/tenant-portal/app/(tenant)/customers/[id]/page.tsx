"use client";
/**
 * Home Services Customer 360 — real directory (see ../page.tsx header for
 * the wrong-backend bug this replaces). Tabs match the real backend
 * surface one-for-one: Overview, Services Used, Jobs, Payments,
 * Complaints, Reviews, Activity & Audit.
 *
 * Deliberately NO "Providers Used" or "Addresses" tab: the tenant-facing
 * router (app/engines/tenant_engine/hs_tenant_customer_router.py) excludes
 * both by documented customer-privacy policy -- those are permanent-
 * directory / cross-tenant surfaces, not something a single tenant should
 * see about a customer. Building them here would mean either fabricating
 * data or bypassing a real privacy boundary; neither is acceptable.
 */
import React, { useCallback, useState } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, Skeleton } from "@serviceos/design-system";
import { Badge } from "../../../../components/shared/ui";
import { hsCustomersApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import {
  ClipboardList, XCircle, Wrench, IndianRupee, Calendar, Clock,
  MessageSquare, Star, ShieldCheck, TrendingUp,
} from "lucide-react";

const TABS = ["Overview", "Services Used", "Jobs", "Payments", "Complaints", "Reviews", "Activity & Audit"] as const;
type Tab = typeof TABS[number];

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" });
}
function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}
function typeLabel(status: string | undefined): { label: string; variant: "success" | "info" | "muted" } {
  if (status === "repeat") return { label: "Repeat customer", variant: "success" };
  if (status === "one_time") return { label: "One-time customer", variant: "info" };
  return { label: "New customer", variant: "muted" };
}

export default function CustomerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const [tab, setTab] = useState<Tab>("Overview");

  const detail = useApi(useCallback(() => hsCustomersApi.detail(id), [id]), [id]);
  const jobs = useApi(useCallback(() => hsCustomersApi.jobs(id), [id]), [id]);
  const complaints = useApi(useCallback(() => hsCustomersApi.complaints(id), [id]), [id]);
  const payments = useApi(useCallback(() => hsCustomersApi.payments(id), [id]), [id]);
  const reviews = useApi(useCallback(() => hsCustomersApi.reviews(id), [id]), [id]);
  const activity = useApi(useCallback(() => hsCustomersApi.activity(id), [id]), [id]);

  const c = detail.data;
  const jobRows: Array<Record<string, unknown>> = Array.isArray(jobs.data?.items) ? jobs.data.items : [];
  const complaintRows: Array<Record<string, unknown>> = Array.isArray(complaints.data?.items) ? complaints.data.items : [];
  const paymentRows: Array<Record<string, unknown>> = Array.isArray(payments.data?.items) ? payments.data.items : [];
  const reviewRows: Array<Record<string, unknown>> = Array.isArray(reviews.data?.items) ? reviews.data.items : [];
  const activityRows: Array<Record<string, unknown>> = Array.isArray(activity.data?.items) ? activity.data.items : [];
  const servicesUsed: Array<Record<string, unknown>> = Array.isArray(c?.services_used_by_master_service) ? c.services_used_by_master_service : [];

  const nextBooking = jobRows
    .filter(j => j?.scheduled_date && new Date(String(j.scheduled_date)) >= new Date(new Date().toDateString())
      && j?.status !== "completed" && j?.status !== "cancelled")
    .sort((a, b) => String(a.scheduled_date).localeCompare(String(b.scheduled_date)))[0];

  const confirmedPayments = paymentRows.filter(p => p.customer_confirmed).length;
  const pendingPayments = paymentRows.length - confirmedPayments;
  const avgRating = reviewRows.length
    ? reviewRows.reduce((sum, r) => sum + Number(r.overall_rating ?? 0), 0) / reviewRows.length
    : null;

  const type = typeLabel(c?.repeat_status as string | undefined);

  return (
    <TenantLayout activeNav="customers">
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, fontSize: 12, color: "var(--text-tertiary)" }}>
        <Link href="/customers" style={{ color: "var(--brand)", textDecoration: "none" }}>Customers</Link>
        <span>›</span>
        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{c?.alias ?? "Loading…"}</span>
      </div>

      {detail.loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Skeleton height={100} radius="14px" />
          <Skeleton height={300} radius="14px" />
        </div>
      ) : !c ? (
        <Card><p style={{ textAlign: "center", color: "var(--text-tertiary)", padding: 24 }}>Customer not found.</p></Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Header */}
          <Card padding="lg">
            <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
              <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--accent-muted)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, fontWeight: 700, color: "var(--accent)", flexShrink: 0 }}>
                {String(c.alias ?? "C").replace("Customer ", "").slice(0, 1).toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{String(c.alias)}</h1>
                  <Badge variant={c.is_active ? "success" : "muted"}>{c.is_active ? "Active" : "Inactive"}</Badge>
                  <Badge variant={type.variant}>{type.label}</Badge>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
                  Customer since {fmtDate(c.first_booking_at as string)} · Last activity {fmtDate(c.last_activity_at as string)}
                </p>
              </div>
            </div>
          </Card>

          {/* Tabs */}
          <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)}
                style={{
                  padding: "9px 14px", border: "none", borderBottom: `2px solid ${tab === t ? "var(--brand)" : "transparent"}`,
                  background: "transparent", cursor: "pointer", fontFamily: "inherit",
                  fontSize: 13, fontWeight: tab === t ? 700 : 500,
                  color: tab === t ? "var(--brand)" : "var(--text-secondary)",
                }}>{t}</button>
            ))}
          </div>

          {tab === "Overview" && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14 }}>
                {[
                  { icon: <ClipboardList size={18} />, label: "Completed jobs", value: Number(c.completed_jobs ?? 0) },
                  { icon: <XCircle size={18} />, label: "Cancelled jobs", value: Number(c.cancelled_jobs ?? 0) },
                  { icon: <Wrench size={18} />, label: "Services used", value: servicesUsed.length },
                  { icon: <IndianRupee size={18} />, label: "Confirmed job value", value: `₹${Number(c.confirmed_job_value ?? 0).toLocaleString("en-IN")}` },
                ].map(s => (
                  <Card key={s.label} style={{ padding: "14px 16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 34, height: 34, borderRadius: "var(--radius-md)", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "var(--accent-muted)", color: "var(--brand)" }}>{s.icon}</div>
                      <div>
                        <p style={{ fontSize: 17, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>{s.value}</p>
                        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{s.label}</p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }} className="cust-grid">
                <style>{`@media (max-width: 900px) { .cust-grid { grid-template-columns: 1fr !important; } }`}</style>
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <Card>
                    <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 }}>
                      <Clock size={15} color="var(--brand)" /> Recent activity
                    </h3>
                    {activity.loading ? <Skeleton height={80} /> : activityRows.length === 0 ? (
                      <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No activity yet.</p>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                        {activityRows.slice(0, 6).map((a, i) => (
                          <div key={i} style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                            <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{String(a.description ?? a.event_type)}</span>
                            <span style={{ fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{fmtDate(a.timestamp as string)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>

                  <Card>
                    <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 }}>
                      <Wrench size={15} color="var(--brand)" /> Services used ({servicesUsed.length})
                    </h3>
                    {servicesUsed.length === 0 ? (
                      <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No completed services yet.</p>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {servicesUsed.map((sv, i) => (
                          <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "6px 0", borderBottom: i < servicesUsed.length - 1 ? "1px solid var(--border)" : "none" }}>
                            <span style={{ color: "var(--text-primary)" }}>{String(sv.master_service_name ?? sv.name ?? "Service")}</span>
                            <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>{String(sv.count ?? sv.jobs_count ?? "")}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  {nextBooking && (
                    <Card>
                      <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 8 }}>
                        <Calendar size={15} color="var(--brand)" /> Next booking
                      </h3>
                      <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 2px" }}>{String(nextBooking.job_number)}</p>
                      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 8px" }}>{String(nextBooking.master_service_name)} · {fmtDate(nextBooking.scheduled_date as string)}</p>
                      <Link href={`/home-services/bookings-jobs?job=${nextBooking.job_id}`} style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>View job</Link>
                    </Card>
                  )}

                  <Card>
                    <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px", display: "flex", alignItems: "center", gap: 8 }}>
                      <TrendingUp size={15} color="var(--brand)" /> Payment behaviour
                    </h3>
                    {payments.loading ? <Skeleton height={40} /> : (
                      <>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10, marginBottom: 8 }}>
                          <div><p style={{ fontSize: 18, fontWeight: 800, color: "var(--success-text)", margin: 0 }}>{confirmedPayments}</p><p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: 0 }}>Confirmed</p></div>
                          <div><p style={{ fontSize: 18, fontWeight: 800, color: "var(--warning-text)", margin: 0 }}>{pendingPayments}</p><p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: 0 }}>Pending confirmation</p></div>
                        </div>
                        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{String(payments.data?.note ?? "")}</p>
                      </>
                    )}
                  </Card>

                  <Card>
                    <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px", display: "flex", alignItems: "center", gap: 8 }}>
                      <MessageSquare size={15} color="var(--brand)" /> Complaint summary
                    </h3>
                    <div style={{ display: "flex", gap: 18 }}>
                      <div><p style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>{complaints.data?.total ?? 0}</p><p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: 0 }}>Lifetime</p></div>
                      <div><p style={{ fontSize: 18, fontWeight: 800, color: Number(c.open_complaints ?? 0) > 0 ? "var(--danger-text)" : "var(--text-primary)", margin: 0 }}>{Number(c.open_complaints ?? 0)}</p><p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: 0 }}>Open</p></div>
                    </div>
                  </Card>

                  <Card>
                    <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px", display: "flex", alignItems: "center", gap: 8 }}>
                      <Star size={15} color="var(--brand)" /> Review summary
                    </h3>
                    <div style={{ display: "flex", gap: 18 }}>
                      <div><p style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>{avgRating === null ? "—" : avgRating.toFixed(1)}</p><p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: 0 }}>Average rating</p></div>
                      <div><p style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>{reviews.data?.total ?? 0}</p><p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: 0 }}>Reviews</p></div>
                    </div>
                  </Card>

                  <Card>
                    <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 8 }}>
                      <ShieldCheck size={15} color="var(--brand)" /> Privacy & consent
                    </h3>
                    <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0, lineHeight: 1.5 }}>
                      This is a tenant-scoped view only. Customer identity, addresses and cross-tenant history are never shown here by policy.
                    </p>
                  </Card>
                </div>
              </div>
            </>
          )}

          {tab === "Services Used" && (
            <Card padding="none">
              {servicesUsed.length === 0 ? (
                <p style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, margin: 0 }}>No completed services yet.</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                      <th style={{ textAlign: "left", padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>Service</th>
                      <th style={{ textAlign: "left", padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>Jobs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {servicesUsed.map((sv, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "10px 16px", fontSize: 13, color: "var(--text-primary)" }}>{String(sv.master_service_name ?? sv.name ?? "Service")}</td>
                        <td style={{ padding: "10px 16px", fontSize: 13, color: "var(--text-secondary)" }}>{String(sv.count ?? sv.jobs_count ?? "—")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          )}

          {tab === "Jobs" && (
            <Card padding="none">
              {jobs.loading ? <div style={{ padding: 20 }}><Skeleton height={60} /></div> : jobRows.length === 0 ? (
                <p style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, margin: 0 }}>No jobs found for this customer.</p>
              ) : jobRows.map((j, i) => (
                <div key={String(j.job_id)} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "12px 20px", borderBottom: i < jobRows.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{String(j.job_number)} · {String(j.master_service_name)}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{fmtDate(j.scheduled_date as string)}</p>
                  </div>
                  <Badge variant={j.status === "completed" ? "success" : j.status === "cancelled" ? "danger" : "muted"} size="sm">{String(j.status).replace(/_/g, " ")}</Badge>
                </div>
              ))}
            </Card>
          )}

          {tab === "Payments" && (
            <Card padding="none">
              {paymentRows.length > 0 && (
                <div style={{ padding: "10px 20px", fontSize: 12, color: "var(--text-tertiary)", borderBottom: "1px solid var(--border)" }}>{String(payments.data?.note ?? "")}</div>
              )}
              {payments.loading ? <div style={{ padding: 20 }}><Skeleton height={60} /></div> : paymentRows.length === 0 ? (
                <p style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, margin: 0 }}>No payment records yet.</p>
              ) : paymentRows.map((p, i) => (
                <div key={String(p.payment_id)} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "12px 20px", borderBottom: i < paymentRows.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>₹{Number(p.collected_amount ?? 0).toLocaleString("en-IN")} · {String(p.payment_mode ?? "—")}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{fmtDate(p.created_at as string)}</p>
                  </div>
                  <Badge variant={p.customer_confirmed ? "success" : "warning"} size="sm">{p.customer_confirmed ? "Confirmed" : "Pending confirmation"}</Badge>
                </div>
              ))}
            </Card>
          )}

          {tab === "Complaints" && (
            <Card padding="none">
              {complaints.loading ? <div style={{ padding: 20 }}><Skeleton height={60} /></div> : complaintRows.length === 0 ? (
                <p style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, margin: 0 }}>No complaints from this customer.</p>
              ) : complaintRows.map((cm, i) => (
                <div key={String(cm.complaint_id)} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "12px 20px", borderBottom: i < complaintRows.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{String(cm.complaint_number)} · {String(cm.title)}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{fmtDate(cm.created_at as string)}</p>
                  </div>
                  <Badge variant={cm.status === "resolved" || cm.status === "closed" ? "success" : "warning"} size="sm">{String(cm.status).replace(/_/g, " ")}</Badge>
                </div>
              ))}
            </Card>
          )}

          {tab === "Reviews" && (
            <Card padding="none">
              {reviews.loading ? <div style={{ padding: 20 }}><Skeleton height={60} /></div> : reviewRows.length === 0 ? (
                <p style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, margin: 0 }}>No reviews from this customer yet.</p>
              ) : reviewRows.map((r, i) => (
                <div key={String(r.review_id)} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "12px 20px", borderBottom: i < reviewRows.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Star size={14} color="var(--warning-text)" />
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{String(r.overall_rating)} / 5</span>
                  </div>
                  <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{fmtDate(r.created_at as string)}</span>
                </div>
              ))}
            </Card>
          )}

          {tab === "Activity & Audit" && (
            <Card padding="none">
              {activity.loading ? <div style={{ padding: 20 }}><Skeleton height={60} /></div> : activityRows.length === 0 ? (
                <p style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, margin: 0 }}>No activity yet.</p>
              ) : activityRows.map((a, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "10px 20px", borderBottom: i < activityRows.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{String(a.description ?? a.event_type)}</span>
                  <span style={{ fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{fmtDateTime(a.timestamp as string)}</span>
                </div>
              ))}
            </Card>
          )}
        </div>
      )}
    </TenantLayout>
  );
}
