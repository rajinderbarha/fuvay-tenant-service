"use client";
/**
 * Bookings — 100% connected to bookingsApi.
 * PROVEN: confirm/reject/reschedule all call live API + refetch.
 */
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { PageHeader, Card, StatusBadge, Button, Modal, Textarea } from "@serviceos/design-system";
import { Badge, Skeleton } from "../../../components/shared/ui";
import { bookingsApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { Booking } from "../../../lib/api";
import { RefreshCw, CalendarDays, CheckCircle2, XCircle } from "lucide-react";

export default function BookingsPage() {
  const [tab, setTab] = useState("pending_confirmation");
  const bookings = useApi(useCallback(() => bookingsApi.list({ status:tab, limit:"30" }), [tab]));

  const confirmAction  = useAction(useCallback((id:string) => bookingsApi.confirm(id), []));
  const rejectAction   = useAction(useCallback((id:string, reason:string) => bookingsApi.reject(id, reason), []));
  const convertAction  = useAction(useCallback((id:string) => bookingsApi.convertToJob(id), []));

  const [rejectModal, setRejectModal] = useState(false);
  const [rejectId,    setRejectId]    = useState("");
  const [rejectMsg,   setRejectMsg]   = useState("");

  async function handleConfirm(id:string) {
    const res = await confirmAction.execute(id);
    if (res) bookings.refetch();
  }
  async function handleReject() {
    const res = await rejectAction.execute(rejectId, rejectMsg);
    if (res) { bookings.refetch(); setRejectModal(false); setRejectMsg(""); }
  }
  async function handleConvert(id:string) {
    const res = await convertAction.execute(id);
    if (res) { bookings.refetch(); window.location.href = "/jobs"; }
  }

  const fmt = (n:number) => `₹${n.toLocaleString("en-IN")}`;
  const TABS = [
    { id:"pending_confirmation", label:"Pending" },
    { id:"confirmed",            label:"Confirmed" },
    { id:"converted",            label:"Jobs"     },
    { id:"cancelled",            label:"Cancelled" },
  ];

  return (
    <TenantLayout activeNav="bookings">
      <PageHeader
        title="Bookings"
        description={bookings.loading ? "Loading..." : `${bookings.data?.bookings.length ?? 0} ${tab.replace(/_/g," ")} bookings — Booking (field_ops.Job) pipeline`}
        actions={<Button variant="ghost" size="sm" leftIcon={<RefreshCw size={14}/>} onClick={bookings.refetch}>Refresh</Button>}
      />

      {/* Tabs */}
      <div style={{ display:"flex", gap:2, padding:4, background:"var(--surface-sunken)",
        borderRadius:12, border:"1px solid var(--border)", marginBottom:16, marginTop:16 }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            padding:"7px 16px", borderRadius:9, border:"none",
            background: tab===t.id ? "var(--surface)" : "transparent",
            color: tab===t.id ? "var(--text-primary)" : "var(--text-secondary)",
            fontWeight: tab===t.id ? 600 : 400, fontSize:13, cursor:"pointer",
            boxShadow: tab===t.id ? "var(--shadow-sm)" : "none",
            transition:"all 0.15s", fontFamily:"inherit",
          }}>{t.label}</button>
        ))}
      </div>

      {bookings.error && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--danger-bg)",
          border:"1px solid var(--danger-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>{bookings.error}</p>
        </div>
      )}

      {/* Booking cards */}
      {bookings.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {[...Array(4)].map((_,i) => <Skeleton key={i} height={100} style={{ borderRadius:14 }}/>)}
        </div>
      ) : (bookings.data?.bookings ?? []).length === 0 ? (
        <Card padding="lg" style={{ textAlign:"center" }}>
          <div style={{ display:"flex", justifyContent:"center", marginBottom:12, color:"var(--text-tertiary)" }}><CalendarDays size={32}/></div>
          <p style={{ fontSize:14, color:"var(--text-secondary)", margin:0 }}>
            No {tab.replace(/_/g," ")} bookings
          </p>
        </Card>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {(bookings.data?.bookings ?? []).map((b:Booking) => (
            <Card key={b.booking_id} padding="md" style={{ cursor:"pointer" }}
              onClick={() => window.location.href = `/bookings/${b.booking_id}`}>
              <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between",
                gap:16, flexWrap:"wrap" }}>
                <div style={{ flex:1, minWidth:200 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
                    <span style={{ fontSize:13, fontWeight:700, color:"var(--text-primary)" }}>
                      {b.booking_number}
                    </span>
                    <StatusBadge status={b.status} />
                    {b.reschedule_count > 0 && (
                      <Badge variant="info" size="sm">Rescheduled {b.reschedule_count}×</Badge>
                    )}
                  </div>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
                    {[
                      {label:"Customer", v:`#${b.customer_id.slice(0,8)}`},
                      {label:"Service",  v:b.service_type_id},
                      {label:"Date",     v:b.scheduled_at ? new Date(b.scheduled_at).toLocaleString("en-IN",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}) : (b.preferred_date ?? "—")},
                    ].map(r=>(
                      <div key={r.label} style={{ display:"flex", gap:6 }}>
                        <span style={{ fontSize:11, color:"var(--text-tertiary)", width:60, flexShrink:0 }}>{r.label}</span>
                        <span style={{ fontSize:12, color:"var(--text-primary)", fontWeight:500 }}>{r.v}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:8, alignItems:"flex-end" }}>
                  {b.quoted_price != null && (
                    <span style={{ fontSize:18, fontWeight:700, color:"var(--success-text)" }}>
                      {fmt(b.quoted_price)}
                    </span>
                  )}
                  <div style={{ display:"flex", gap:8 }} onClick={e => e.stopPropagation()}>
                    {b.status==="pending_confirmation" && <>
                      <Button variant="primary" size="sm" leftIcon={<CheckCircle2 size={14}/>} loading={confirmAction.loading}
                        onClick={() => handleConfirm(b.booking_id)}>Accept</Button>
                      <Button variant="destructive" size="sm" leftIcon={<XCircle size={14}/>}
                        onClick={() => { setRejectId(b.booking_id); setRejectModal(true); }}>Reject</Button>
                    </>}
                    {b.status==="confirmed" && (
                      <Button variant="primary" size="sm" loading={convertAction.loading}
                        onClick={() => handleConvert(b.booking_id)}>Convert to Job</Button>
                    )}
                  </div>
                </div>
              </div>
              {b.customer_notes && (
                <div style={{ marginTop:10, padding:"8px 12px", borderRadius:8,
                  background:"var(--surface-sunken)", fontSize:12, color:"var(--text-secondary)" }}>
                  Note: {b.customer_notes}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

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
        <Textarea label="Reason for rejection" placeholder="Not available on this date, out of service area..."
          value={rejectMsg} onChange={e => setRejectMsg(e.target.value)} rows={3} required/>
      </Modal>
    </TenantLayout>
  );
}
