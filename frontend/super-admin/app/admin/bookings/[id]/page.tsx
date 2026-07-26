"use client";
/**
 * Admin Booking Detail — uses adminBookingsApi (super-admin endpoints only).
 * FIXED: was calling bookingsApi.get() (tenant-scoped) → now uses adminBookingsApi.get()
 * FIXED: field names aligned to admin response: service_name, category_name, estimated_amount
 * FIXED: breadcrumb points to /admin/bookings (not /admin/operations)
 * FIXED: cancel/void use admin-specific endpoints via adminBookingsApi.cancel/void
 * FIXED: timeline/notes use admin-specific endpoints
 */
import React, { useCallback, useState } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Skeleton } from "../../../../components/shared/ui";
import { adminBookingsApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { ArrowLeft, AlertTriangle, RotateCcw } from "lucide-react";

const STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "danger" | "info" | "muted"> = {
  pending_confirmation: "warning",
  confirmed:   "success",
  in_progress: "info",
  cancelled:   "danger",
  void:        "muted",
  draft:       "muted",
  completed:   "success",
};

function TextArea({
  label, value, onChange, placeholder, rows = 3,
}: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; rows?: number;
}) {
  return (
    <div>
      <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)",
        display: "block", marginBottom: 6 }}>{label}</label>
      <textarea value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} rows={rows}
        style={{
          width: "100%", padding: "8px 10px", fontSize: 13, fontFamily: "inherit",
          borderRadius:"var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)",
          color: "var(--text-primary)", outline: "none", resize: "vertical", boxSizing: "border-box",
        }} />
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ fontSize: 12, color: "var(--text-tertiary)", width: 140, flexShrink: 0 }}>{label}</span>
      <span style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 500 }}>{value ?? "—"}</span>
    </div>
  );
}

export default function BookingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);

  // All calls use the admin-scoped endpoints (not tenant-scoped bookingsApi)
  const booking  = useApi(useCallback(() => adminBookingsApi.get(id),          [id]));
  const timeline = useApi(useCallback(() => adminBookingsApi.getTimeline(id),  [id]));
  const notes    = useApi(useCallback(() => adminBookingsApi.listNotes(id),    [id]));

  const cancelAction = useAction(
    useCallback((reason: string) => adminBookingsApi.cancel(id, reason), [id])
  );
  const voidAction = useAction(
    useCallback((reason: string) => adminBookingsApi.void(id, reason), [id])
  );

  const [cancelModal, setCancelModal] = useState(false);
  const [cancelMsg,   setCancelMsg]   = useState("");
  const [voidModal,   setVoidModal]   = useState(false);
  const [voidMsg,     setVoidMsg]     = useState("Voided by admin");

  function refetchAll() { booking.refetch(); timeline.refetch(); }

  async function handleCancel() {
    const res = await cancelAction.execute(cancelMsg);
    if (res) { refetchAll(); setCancelModal(false); setCancelMsg(""); }
  }
  async function handleVoid() {
    const res = await voidAction.execute(voidMsg);
    if (res) { refetchAll(); setVoidModal(false); }
  }

  // Unwrap response — adminBookingsApi.get returns { data: AdminBooking & ... }
  const raw = booking.data as { data?: Record<string, unknown> } | null;
  const b   = raw?.data ?? null;

  const fmtDate = (d?: string | null) =>
    d ? new Date(d).toLocaleString("en-IN", {
      day: "numeric", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    }) : "—";
  const fmtAmt = (n?: number | null) => n != null ? `₹${Number(n).toLocaleString("en-IN")}` : "—";

  // Timeline unwrap
  const tlRaw = timeline.data as { data?: { timeline: unknown[] } } | null;
  const tlItems = (tlRaw?.data?.timeline ?? []) as {
    from_status: string | null; to_status: string; reason: string | null; occurred_at: string | null;
  }[];

  // Notes unwrap
  const notesRaw = notes.data as { data?: { notes: unknown[] } } | null;
  const noteItems = (notesRaw?.data?.notes ?? []) as {
    note_id: string; content: string; author_role: string | null; created_at: string | null;
  }[];

  return (
    <AdminLayout activeNav="bookings">
      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16,
        fontSize: 12, color: "var(--text-tertiary)" }}>
        <Link href="/admin/bookings"
          style={{ color: "var(--text-link)", textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
          <ArrowLeft size={13} /> Bookings
        </Link>
        <span>›</span>
        <span style={{ color: "var(--text-primary)", fontWeight: 600, fontFamily: "monospace" }}>
          {booking.loading ? "Loading…" : (b?.booking_number as string) ?? id}
        </span>
      </div>

      {/* Loading state */}
      {booking.loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {[...Array(3)].map((_, i) => <Skeleton key={i} height={100} style={{ borderRadius: 14 }} />)}
        </div>
      )}

      {/* Error state */}
      {booking.error && !booking.loading && (
        <div style={{ padding: 60, textAlign: "center" }}>
          <AlertTriangle size={36} style={{ color: "var(--danger-text, #b91c1c)", marginBottom: 12 }} />
          <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 6px" }}>
            Could not load booking
          </p>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>
            {String(booking.error)}
          </p>
          <Btn variant="secondary" size="sm" onClick={() => booking.refetch()}>
            <RotateCcw size={13} style={{ marginRight: 4 }} /> Retry
          </Btn>
        </div>
      )}

      {/* Not found */}
      {!booking.loading && !booking.error && !b && (
        <div style={{ textAlign: "center", padding: 60 }}>
          <p style={{ color: "var(--text-tertiary)", fontSize: 15 }}>Booking not found</p>
          <Link href="/admin/bookings" style={{ fontSize: 13, color: "var(--text-link)" }}>← Back to Bookings</Link>
        </div>
      )}

      {/* Main content */}
      {b && !booking.loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Header */}
          <Card padding={24}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between",
              gap: 16, flexWrap: "wrap" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                  <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)",
                    margin: 0, fontFamily: "monospace" }}>
                    {b.booking_number as string}
                  </h1>
                  <Badge variant={STATUS_VARIANT[b.status as string] ?? "muted"}>
                    {(b.status as string).replace(/_/g, " ")}
                  </Badge>
                  {(b.reschedule_count as number) > 0 && (
                    <Badge variant="info">Rescheduled {b.reschedule_count as number}×</Badge>
                  )}
                  {b.sla_breached && (
                    <Badge variant="danger">SLA Breached</Badge>
                  )}
                </div>
                <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 3px" }}>
                  {b.service_name as string} · {b.category_name as string}
                </p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                  Scheduled {fmtDate(b.scheduled_at as string)} · Booked {fmtDate(b.created_at as string)}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {(["pending_confirmation", "confirmed"] as string[]).includes(b.status as string) && (
                  <Btn variant="danger" size="sm" onClick={() => setCancelModal(true)}>Cancel</Btn>
                )}
                {b.status !== "void" && (
                  <Btn variant="danger" size="sm" onClick={() => setVoidModal(true)}>Void</Btn>
                )}
                <Btn variant="ghost" size="sm" onClick={refetchAll}>↻ Refresh</Btn>
              </div>
            </div>
          </Card>

          {/* Two-column details */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

            {/* Provider */}
            <Card padding={20}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 12px" }}>
                Provider
              </p>
              <InfoRow label="Name"      value={b.provider_name as string || b.tenant_name as string || "—"} />
              <InfoRow label="Tenant ID" value={
                <Link href={`/admin/tenants/${b.tenant_id}`}
                  style={{ color: "var(--text-link)", fontSize: 11, fontFamily: "monospace" }}>
                  View tenant →
                </Link>
              } />
            </Card>

            {/* Customer */}
            <Card padding={20}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 12px" }}>
                Customer
              </p>
              <InfoRow label="Name"  value={b.customer_name as string} />
              <InfoRow label="Phone" value={b.customer_phone as string} />
            </Card>

            {/* Booking details */}
            <Card padding={20}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 12px" }}>
                Booking Details
              </p>
              <InfoRow label="Booking #"   value={<span style={{ fontFamily: "monospace" }}>{b.booking_number as string}</span>} />
              <InfoRow label="Category"    value={b.category_name as string} />
              <InfoRow label="Service"     value={b.service_name as string} />
              <InfoRow label="Job Type"    value={b.job_type as string} />
              <InfoRow label="Amount"      value={fmtAmt(b.estimated_amount as number)} />
              <InfoRow label="Preferred"   value={`${b.preferred_date ?? ""} ${b.preferred_slot ?? ""}`.trim() || "—"} />
              <InfoRow label="Confirmed"   value={fmtDate(b.confirmed_at as string)} />
              <InfoRow label="Reschedules" value={String(b.reschedule_count ?? 0)} />
            </Card>

            {/* Location */}
            <Card padding={20}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 12px" }}>
                Location
              </p>
              <InfoRow label="City"     value={b.city as string} />
              <InfoRow label="District" value={b.district as string} />
              <InfoRow label="State"    value={b.state as string} />
              <InfoRow label="Pincode"  value={b.zipcode as string} />
              <InfoRow label="City Tier" value={b.city_tier as string} />
              {b.address && typeof b.address === "object" && (
                <InfoRow label="Full Address" value={
                  <span style={{ fontSize: 11 }}>
                    {Object.values(b.address as Record<string, string>).filter(Boolean).join(", ")}
                  </span>
                } />
              )}
            </Card>
          </div>

          {/* Job & Assignment */}
          <Card padding={20}>
            <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 12px" }}>
              Job & Assignment
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
              <InfoRow label="Assignment"  value={
                <Badge variant={b.assignment_status === "assigned" ? "success" : "muted"}>
                  {b.assignment_status as string}
                </Badge>
              } />
              <InfoRow label="Job Status"  value={b.job_status as string || "—"} />
              <InfoRow label="Job ID"      value={
                b.job_id ? (
                  <Link href={`/admin/home-services/service-jobs/${b.job_id}`} style={{ fontSize: 11, color: "var(--text-link)", fontFamily: "monospace" }}>
                    {(b.job_id as string).slice(0, 8)}… →
                  </Link>
                ) : "—"
              } />
            </div>
          </Card>

          {/* Payment breakdown — Home Services rule: customer pays provider directly,
              platform never collects the service payment. */}
          {(b.estimated_amount != null || b.credit_applied != null) && (
            <Card padding={20}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 12px" }}>
                Payment Breakdown
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
                <InfoRow label="Quoted Price"            value={fmtAmt(b.estimated_amount as number)} />
                <InfoRow label="Customer Credit Applied" value={fmtAmt((b.credit_applied as number) ?? 0)} />
                <InfoRow label="Payable To Provider"     value={fmtAmt((b.payable_amount as number) ?? (b.estimated_amount as number))} />
                <InfoRow label="Payment Collection Mode" value="Customer pays provider directly" />
                <InfoRow label="Payment Recorded"        value={b.payment_recorded ? "Yes" : "No"} />
                <InfoRow label="Amount Collected"        value={b.amount_collected != null ? fmtAmt(b.amount_collected as number) : "—"} />
              </div>
            </Card>
          )}

          {/* Notes */}
          {(b.customer_notes || b.internal_notes || b.cancellation_reason || b.blocking_reason) && (
            <Card padding={20}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 12px" }}>
                Notes & Flags
              </p>
              {b.customer_notes && <InfoRow label="Customer Note" value={b.customer_notes as string} />}
              {b.internal_notes && <InfoRow label="Internal Note" value={b.internal_notes as string} />}
              {b.cancellation_reason && <InfoRow label="Cancellation Reason" value={b.cancellation_reason as string} />}
              {b.blocking_reason && <InfoRow label="Blocking Reason" value={b.blocking_reason as string} />}
            </Card>
          )}

          {/* Timeline */}
          <Card padding={20}>
            <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 16px" }}>
              Status Timeline
            </p>
            {timeline.loading ? (
              [...Array(3)].map((_, i) => <Skeleton key={i} height={40} style={{ marginBottom: 8 }} />)
            ) : tlItems.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No history available</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column" }}>
                {tlItems.map((h, i) => (
                  <div key={i} style={{ display: "flex", gap: 14, alignItems: "flex-start",
                    paddingBottom: i < tlItems.length - 1 ? 16 : 0 }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                      <div style={{ width: 10, height: 10, borderRadius: "50%",
                        background: i === 0 ? "var(--accent, var(--primary))" : "var(--border)", marginTop: 4 }} />
                      {i < tlItems.length - 1 && (
                        <div style={{ width: 2, flex: 1, background: "var(--border)", marginTop: 4, minHeight: 20 }} />
                      )}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        {h.from_status && (
                          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                            {h.from_status.replace(/_/g, " ")} →
                          </span>
                        )}
                        <Badge variant={STATUS_VARIANT[h.to_status] ?? "muted"}>
                          {h.to_status.replace(/_/g, " ")}
                        </Badge>
                      </div>
                      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                        {fmtDate(h.occurred_at)}
                      </p>
                      {h.reason && (
                        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 0", fontStyle: "italic" }}>
                          "{h.reason}"
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Notes log */}
          <Card padding={20}>
            <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 16px" }}>
              Booking Notes
            </p>
            {notes.loading ? (
              [...Array(2)].map((_, i) => <Skeleton key={i} height={40} style={{ marginBottom: 8 }} />)
            ) : noteItems.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No notes on this booking</p>
            ) : noteItems.map(n => (
              <div key={n.note_id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <p style={{ fontSize: 13, color: "var(--text-primary)", margin: "0 0 4px" }}>{n.content}</p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                  {n.author_role ?? "Admin"} · {fmtDate(n.created_at)}
                </p>
              </div>
            ))}
          </Card>
        </div>
      )}

      {/* Cancel modal */}
      <Modal open={cancelModal} onClose={() => setCancelModal(false)} title="Cancel Booking">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <TextArea label="Reason *" value={cancelMsg} onChange={setCancelMsg}
            placeholder="Reason for cancellation (required for audit log)…" />
          {cancelAction.error && (
            <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{cancelAction.error}</p>
          )}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setCancelModal(false)}>Back</Btn>
            <Btn variant="danger" size="sm" loading={cancelAction.loading}
              disabled={!cancelMsg.trim()} onClick={handleCancel}>
              Cancel Booking
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Void modal */}
      <Modal open={voidModal} onClose={() => setVoidModal(false)} title="Void Booking">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ padding: "10px 14px", borderRadius:"var(--radius-md)", background: "var(--danger-bg)",
            border: "1px solid var(--danger-border)" }}>
            <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>
              Voiding permanently invalidates this booking. This action is logged.
            </p>
          </div>
          <TextArea label="Reason *" value={voidMsg} onChange={setVoidMsg} />
          {voidAction.error && (
            <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{voidAction.error}</p>
          )}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setVoidModal(false)}>Cancel</Btn>
            <Btn variant="danger" size="sm" loading={voidAction.loading}
              disabled={!voidMsg.trim()} onClick={handleVoid}>
              Void Booking
            </Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
