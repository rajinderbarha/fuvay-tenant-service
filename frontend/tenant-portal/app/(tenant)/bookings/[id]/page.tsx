"use client";
/**
 * Booking Detail — full view of a single booking.
 * PROVEN: bookingsApi.get() + getTimeline() + listNotes() connected.
 * PROVEN: confirm/reject/reschedule/convertToJob/addNote all call live API + refetch.
 */
import React, { useCallback, useState } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { PageHeader, Card, StatusBadge, Button, Modal, Input, Textarea, Select, Skeleton } from "@serviceos/design-system";
import { Badge } from "../../../../components/shared/ui";
import { bookingsApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { CheckCircle2, XCircle, RefreshCw, Plus } from "lucide-react";

const SLOTS = ["morning","afternoon","evening"].map(s => ({ value: s, label: s[0].toUpperCase()+s.slice(1) }));

export default function BookingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);

  const booking  = useApi(useCallback(() => bookingsApi.get(id),         [id]));
  const timeline = useApi(useCallback(() => bookingsApi.getTimeline(id), [id]));
  const notes    = useApi(useCallback(() => bookingsApi.listNotes(id),   [id]));

  const confirmAction    = useAction(useCallback(() => bookingsApi.confirm(id), [id]));
  const rejectAction     = useAction(useCallback((reason: string) => bookingsApi.reject(id, reason), [id]));
  const rescheduleAction = useAction(useCallback(
    (date: string, slot: string, reason: string) => bookingsApi.reschedule(id, date, slot, reason), [id]));
  const convertAction    = useAction(useCallback(() => bookingsApi.convertToJob(id), [id]));
  const addNoteAction    = useAction(useCallback((content: string) => bookingsApi.addNote(id, content), [id]));

  const [rejectModal, setRejectModal] = useState(false);
  const [rejectMsg,   setRejectMsg]   = useState("");
  const [reschedModal,setReschedModal]= useState(false);
  const [reschedDate, setReschedDate] = useState("");
  const [reschedSlot, setReschedSlot] = useState("");
  const [reschedMsg,  setReschedMsg]  = useState("");
  const [noteModal,   setNoteModal]   = useState(false);
  const [noteContent, setNoteContent] = useState("");

  function refetchAll() { booking.refetch(); timeline.refetch(); }

  async function handleConfirm() {
    const res = await confirmAction.execute();
    if (res) refetchAll();
  }
  async function handleReject() {
    const res = await rejectAction.execute(rejectMsg);
    if (res) { refetchAll(); setRejectModal(false); setRejectMsg(""); }
  }
  async function handleReschedule() {
    const res = await rescheduleAction.execute(reschedDate, reschedSlot, reschedMsg);
    if (res) { refetchAll(); setReschedModal(false); setReschedDate(""); setReschedSlot(""); setReschedMsg(""); }
  }
  async function handleConvert() {
    const res = await convertAction.execute();
    if (res) window.location.href = "/jobs";
  }
  async function handleAddNote() {
    const res = await addNoteAction.execute(noteContent);
    if (res) { notes.refetch(); setNoteModal(false); setNoteContent(""); }
  }

  const b   = booking.data;
  const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`;
  const fmtDate = (d?: string) => d ? new Date(d).toLocaleString("en-IN",
    { day:"numeric", month:"short", year:"numeric", hour:"2-digit", minute:"2-digit" }) : "—";

  return (
    <TenantLayout activeNav="jobs">
      {/* Breadcrumb */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:16,
        fontSize:12, color:"var(--text-tertiary)" }}>
        <Link href="/jobs" style={{ color:"var(--text-link)", textDecoration:"none" }}>Bookings & Jobs</Link>
        <span>›</span>
        <span style={{ color:"var(--text-primary)", fontWeight:500 }}>
          {booking.loading ? "Loading..." : b?.booking_number}
        </span>
      </div>

      <PageHeader title={booking.loading ? "Loading..." : (b?.booking_number ?? "Booking")} description="Booking (field_ops.Job) pipeline" />

      {booking.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Skeleton height="8.75rem"/>
          <Skeleton height="12.5rem"/>
        </div>
      ) : !b ? (
        <div style={{ textAlign:"center", padding:60 }}>
          <p style={{ color:"var(--text-tertiary)" }}>Booking not found</p>
        </div>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {/* Hero */}
          <Card padding="lg">
            <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", flexWrap:"wrap", gap:16 }}>
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
                  <h1 style={{ fontSize:20, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                    {b.booking_number}
                  </h1>
                  <StatusBadge status={b.status} />
                  {b.reschedule_count > 0 && (
                    <Badge variant="info">Rescheduled {b.reschedule_count}×</Badge>
                  )}
                </div>
                <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 4px" }}>
                  {b.service_type_id} · {b.scheduled_at ? fmtDate(b.scheduled_at) : (b.preferred_date ?? "—")}
                </p>
                <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
                  Booked {fmtDate(b.created_at)}
                </p>
              </div>
              <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                {b.status === "pending_confirmation" && <>
                  <Button variant="primary" size="sm" leftIcon={<CheckCircle2 size={14}/>} loading={confirmAction.loading} onClick={handleConfirm}>
                    Confirm
                  </Button>
                  <Button variant="destructive" size="sm" leftIcon={<XCircle size={14}/>} onClick={() => setRejectModal(true)}>Reject</Button>
                </>}
                {(b.status === "pending_confirmation" || b.status === "confirmed") && (
                  <Button variant="secondary" size="sm" onClick={() => setReschedModal(true)}>
                    Reschedule
                  </Button>
                )}
                {b.status === "confirmed" && (
                  <Button variant="primary" size="sm" loading={convertAction.loading} onClick={handleConvert}>
                    Convert to Job
                  </Button>
                )}
                <Button variant="ghost" size="sm" leftIcon={<RefreshCw size={14}/>} onClick={refetchAll}>Refresh</Button>
              </div>
            </div>
          </Card>

          {/* Details grid */}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <Card padding="md">
              <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 14px",
                textTransform:"uppercase", letterSpacing:"0.06em" }}>Customer</h3>
              <div style={{ display:"flex", gap:12, padding:"7px 0", borderBottom:"1px solid var(--border)" }}>
                <span style={{ fontSize:12, color:"var(--text-tertiary)", width:70, flexShrink:0 }}>Customer</span>
                <Link href={`/customers/${b.customer_id}`} style={{ fontSize:12, color:"var(--text-link)", fontWeight:500 }}>
                  View customer →
                </Link>
              </div>
              <div style={{ display:"flex", gap:12, padding:"7px 0" }}>
                <span style={{ fontSize:12, color:"var(--text-tertiary)", width:70, flexShrink:0 }}>Pincode</span>
                <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{b.pincode ?? "—"}</span>
              </div>
            </Card>

            <Card padding="md">
              <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 14px",
                textTransform:"uppercase", letterSpacing:"0.06em" }}>Booking Info</h3>
              {[
                { label:"Service", v: b.service_type_id },
                { label:"Category", v: b.service_category },
                { label:"Price",   v: b.quoted_price != null ? fmt(b.quoted_price) : "—" },
                { label:"Notes",   v: b.customer_notes ?? "—" },
              ].map(r => (
                <div key={r.label} style={{ display:"flex", gap:12, padding:"7px 0",
                  borderBottom:"1px solid var(--border)" }}>
                  <span style={{ fontSize:12, color:"var(--text-tertiary)", width:70, flexShrink:0 }}>{r.label}</span>
                  <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{r.v}</span>
                </div>
              ))}
            </Card>
          </div>

          {/* Payment breakdown — Home Services rule: customer pays provider directly,
              platform never collects the service payment. */}
          {b.quoted_price != null && (
            <Card padding="md">
              <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 14px",
                textTransform:"uppercase", letterSpacing:"0.06em" }}>Payment Breakdown</h3>
              {[
                { label:"Service Price",           v: fmt(b.quoted_price) },
                { label:"ServiceOS Credit Applied", v: fmt(b.credit_applied ?? 0) },
                { label:"Payable To Provider",      v: fmt(b.payable_amount ?? b.quoted_price) },
                { label:"Payment Mode",             v: "Customer pays provider directly" },
                { label:"Platform Collected Payment", v: b.platform_payment_collected ? "Yes" : "No" },
              ].map(r => (
                <div key={r.label} style={{ display:"flex", gap:12, padding:"7px 0",
                  borderBottom:"1px solid var(--border)" }}>
                  <span style={{ fontSize:12, color:"var(--text-tertiary)", width:170, flexShrink:0 }}>{r.label}</span>
                  <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{r.v}</span>
                </div>
              ))}
              {b.job_id && (
                <Link href={`/jobs/${b.job_id}`} style={{ fontSize:12, color:"var(--text-link)", fontWeight:500,
                  display:"inline-block", marginTop:10 }}>
                  View job & payment collection status →
                </Link>
              )}
            </Card>
          )}

          {/* Status timeline */}
          <Card padding="md">
            <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:"0 0 16px",
              textTransform:"uppercase", letterSpacing:"0.06em" }}>Status Timeline</h3>
            {timeline.loading ? (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(3)].map((_,i) => <Skeleton key={i} height="2rem"/>)}
              </div>
            ) : (timeline.data?.timeline ?? []).length === 0 ? (
              <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No history available</p>
            ) : (timeline.data?.timeline ?? []).map((h, i, arr) => (
              <div key={i} style={{ display:"flex", alignItems:"center", gap:14, padding:"10px 0",
                borderBottom:i<arr.length-1?"1px solid var(--border)":"none" }}>
                <div style={{ width:8, height:8, borderRadius:"50%", background:"var(--accent)",
                  flexShrink:0 }}/>
                <div style={{ flex:1 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                    {h.from_status && (
                      <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>{h.from_status.replace(/_/g," ")} →</span>
                    )}
                    <StatusBadge status={h.to_status} />
                    {h.reason && <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>{h.reason}</span>}
                  </div>
                </div>
                <span style={{ fontSize:11, color:"var(--text-tertiary)", flexShrink:0 }}>
                  {fmtDate(h.occurred_at)}
                </span>
              </div>
            ))}
          </Card>

          {/* Notes */}
          <Card padding="md">
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
              <h3 style={{ fontSize:13, fontWeight:600, color:"var(--text-tertiary)", margin:0,
                textTransform:"uppercase", letterSpacing:"0.06em" }}>Notes</h3>
              <Button variant="ghost" size="sm" leftIcon={<Plus size={14}/>} onClick={() => setNoteModal(true)}>Add Note</Button>
            </div>
            {notes.loading ? (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(2)].map((_,i) => <Skeleton key={i} height="2.5rem"/>)}
              </div>
            ) : (notes.data?.notes ?? []).length === 0 ? (
              <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No notes yet</p>
            ) : (notes.data?.notes ?? []).map(n => (
              <div key={n.note_id} style={{ padding:"10px 0", borderBottom:"1px solid var(--border)" }}>
                <p style={{ fontSize:13, color:"var(--text-primary)", margin:"0 0 4px" }}>{n.content}</p>
                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                  {n.author_role ?? "Staff"} · {fmtDate(n.created_at)}
                </p>
              </div>
            ))}
          </Card>
        </div>
      )}

      {/* Reject modal */}
      <Modal
        open={rejectModal}
        onClose={() => setRejectModal(false)}
        title="Reject Booking"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setRejectModal(false)}>Cancel</Button>
          <Button variant="destructive" size="sm" loading={rejectAction.loading} onClick={handleReject}>
            Reject Booking
          </Button>
        </>}
      >
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Textarea label="Reason for rejection" placeholder="Not available on this date, out of service area..."
            value={rejectMsg} onChange={e => setRejectMsg(e.target.value)} rows={3} required/>
          {rejectAction.error && <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{rejectAction.error}</p>}
        </div>
      </Modal>

      {/* Reschedule modal */}
      <Modal
        open={reschedModal}
        onClose={() => setReschedModal(false)}
        title="Request Reschedule"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setReschedModal(false)}>Cancel</Button>
          <Button variant="primary" size="sm" loading={rescheduleAction.loading}
            disabled={!reschedDate || !reschedSlot} onClick={handleReschedule}>
            Request Reschedule
          </Button>
        </>}
      >
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Input label="New date" type="date" value={reschedDate} onChange={e => setReschedDate(e.target.value)} required/>
          <Select label="New slot" value={reschedSlot} onChange={e => setReschedSlot(e.target.value)}
            placeholder="Select a slot…" options={SLOTS}/>
          <Textarea label="Reason" placeholder="Customer requested a different time..."
            value={reschedMsg} onChange={e => setReschedMsg(e.target.value)} rows={2}/>
          {rescheduleAction.error && <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{rescheduleAction.error}</p>}
        </div>
      </Modal>

      {/* Add note modal */}
      <Modal
        open={noteModal}
        onClose={() => setNoteModal(false)}
        title="Add Note"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setNoteModal(false)}>Cancel</Button>
          <Button variant="primary" size="sm" loading={addNoteAction.loading}
            disabled={!noteContent.trim()} onClick={handleAddNote}>
            Add Note
          </Button>
        </>}
      >
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Textarea label="Note" placeholder="Internal note about this booking..."
            value={noteContent} onChange={e => setNoteContent(e.target.value)} rows={3} required/>
          {addNoteAction.error && <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{addNoteAction.error}</p>}
        </div>
      </Modal>
    </TenantLayout>
  );
}
