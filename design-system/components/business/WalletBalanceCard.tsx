"use client";
import React from "react";
export interface WalletBalanceCardProps { balance:number; reserved:number; available:number; currency?:string; last_topup_at?:string; low_threshold?:number; onTopup?:()=>void; }
export function WalletBalanceCard({ balance, reserved, available, currency="₹", last_topup_at, low_threshold=2000, onTopup }: WalletBalanceCardProps) {
  const fmt = (n:number) => `${currency}${n.toLocaleString("en-IN")}`;
  const low = available < low_threshold;
  const pct = Math.min(100,(available/Math.max(balance,1))*100);
  return (
    <div style={{ background: low?"var(--color-danger-bg)":"var(--color-surface-base)",
      border:`1px solid ${low?"var(--color-danger-border)":"var(--color-border)"}`,
      borderRadius:"var(--radius-lg)", padding:"20px", boxShadow:"var(--shadow-sm)" }}>
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom:14 }}>
        <div>
          <p style={{ fontSize:"var(--text-xs)", fontWeight:"var(--font-bold)", textTransform:"uppercase",
            letterSpacing:"0.06em", color: low?"var(--color-danger-text)":"var(--color-text-tertiary)",
            margin:"0 0 6px" }}>💳 Credit Wallet{low?" · LOW BALANCE":""}</p>
          <p style={{ fontSize:"var(--text-5xl)", fontWeight:"var(--font-extrabold)",
            color: low?"var(--color-danger-text)":"var(--color-text-primary)",
            margin:0, lineHeight:1, letterSpacing:"-0.03em" }}>{fmt(balance)}</p>
          <p style={{ fontSize:"var(--text-sm)", color: low?"var(--color-danger-text)":"var(--color-text-tertiary)",
            margin:"6px 0 0", opacity:0.85 }}>
            {fmt(available)} available · {fmt(reserved)} reserved
          </p>
        </div>
        {onTopup && (
          <button onClick={onTopup}
            style={{ padding:"7px 14px", borderRadius:"var(--radius-md)", border:"none",
              background:"var(--color-brand-500)", color:"white", cursor:"pointer",
              fontSize:"var(--text-sm)", fontFamily:"var(--font-sans)",
              fontWeight:"var(--font-semibold)", flexShrink:0 }}>
            Top Up
          </button>
        )}
      </div>
      <div style={{ height:8, background:"var(--color-border)", borderRadius:"var(--radius-full)", overflow:"hidden", marginBottom:10 }}>
        <div style={{ height:"100%", width:`${pct}%`,
          background: low?"var(--color-danger)":"var(--color-success)",
          borderRadius:"var(--radius-full)", transition:"width 0.5s ease" }}/>
      </div>
      {last_topup_at && (
        <p style={{ fontSize:"var(--text-xs)", color: low?"var(--color-danger-text)":"var(--color-text-tertiary)",
          margin:0, opacity:0.8 }}>
          Last top-up: {new Date(last_topup_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}
        </p>
      )}
    </div>
  );
}
