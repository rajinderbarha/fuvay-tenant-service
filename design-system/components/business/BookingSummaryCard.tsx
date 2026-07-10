"use client";
import React from "react";
export interface BookingSummaryCardProps { bookingNumber:string; customerName:string; customerPhone?:string; serviceType:string; scheduledAt:string; status:string; price:number; currency?:string; staffAssigned?:string; notes?:string; onConfirm?:()=>void; onReject?:()=>void; loading?:boolean; }
export function BookingSummaryCard({ bookingNumber, customerName, customerPhone, serviceType, scheduledAt, status, price, currency="₹", staffAssigned, notes, onConfirm, onReject, loading }: BookingSummaryCardProps) {
  const fmt = (n:number) => `${currency}${n.toLocaleString("en-IN")}`;
  const statusBg: Record<string,string> = {
    pending_confirmation:"var(--color-warning-bg)", confirmed:"var(--color-success-bg)",
    cancelled:"var(--color-danger-bg)", converted:"var(--color-info-bg)"
  };
  const statusText: Record<string,string> = {
    pending_confirmation:"var(--color-warning-text)", confirmed:"var(--color-success-text)",
    cancelled:"var(--color-danger-text)", converted:"var(--color-info-text)"
  };
  const date = new Date(scheduledAt);
  return (
    <div style={{ background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
      borderRadius:"var(--radius-xl)", overflow:"hidden", boxShadow:"var(--shadow-sm)" }}>
      <div style={{ padding:"16px 20px", borderBottom:"1px solid var(--color-border)",
        background: statusBg[status]??"var(--color-surface-sunken)" }}>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div>
            <p style={{ fontSize:"var(--text-base)", fontWeight:"var(--font-semibold)",
              color:"var(--color-text-primary)", margin:"0 0 3px" }}>{bookingNumber}</p>
            <span style={{ fontSize:"var(--text-xs)", padding:"2px 8px", borderRadius:"var(--radius-full)",
              fontWeight:"var(--font-bold)", background: statusBg[status]??"var(--color-surface-sunken)",
              color: statusText[status]??"var(--color-text-secondary)",
              border:"1px solid var(--color-border)" }}>
              {status.replace(/_/g," ").toUpperCase()}
            </span>
          </div>
          <p style={{ fontSize:"var(--text-2xl)", fontWeight:"var(--font-extrabold)",
            color:"var(--color-brand-500)", margin:0 }}>{fmt(price)}</p>
        </div>
      </div>
      <div style={{ padding:"16px 20px" }}>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginBottom:12 }}>
          {[
            { label:"Customer",  v: customerName },
            { label:"Phone",     v: customerPhone??"-" },
            { label:"Service",   v: serviceType },
            { label:"Date",      v: date.toLocaleString("en-IN",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}) },
            { label:"Staff",     v: staffAssigned??"-" },
          ].map(row=>(
            <div key={row.label}>
              <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)", margin:"0 0 2px",
                textTransform:"uppercase", letterSpacing:"0.05em" }}>{row.label}</p>
              <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)",
                color:"var(--color-text-primary)", margin:0 }}>{row.v}</p>
            </div>
          ))}
        </div>
        {notes && <div style={{ padding:"8px 12px", borderRadius:"var(--radius-sm)",
          background:"var(--color-surface-sunken)", fontSize:"var(--text-sm)",
          color:"var(--color-text-secondary)", marginTop:8 }}>
          Note: {notes}
        </div>}
        {(onConfirm||onReject) && (
          <div style={{ display:"flex", gap:8, marginTop:14 }}>
            {onReject && <button onClick={onReject} disabled={loading}
              style={{ flex:1, padding:"8px", borderRadius:"var(--radius-md)",
                border:"1px solid var(--color-danger-border)", background:"var(--color-danger-bg)",
                color:"var(--color-danger-text)", cursor:"pointer",
                fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)", fontWeight:"var(--font-semibold)" }}>
              ✕ Reject
            </button>}
            {onConfirm && <button onClick={onConfirm} disabled={loading}
              style={{ flex:2, padding:"8px", borderRadius:"var(--radius-md)", border:"none",
                background:"var(--color-brand-500)", color:"white", cursor:"pointer",
                fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)", fontWeight:"var(--font-semibold)",
                opacity:loading?0.6:1 }}>
              ✓ Confirm Booking
            </button>}
          </div>
        )}
      </div>
    </div>
  );
}
