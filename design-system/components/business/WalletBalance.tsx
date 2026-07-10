/**
 * WalletBalance — INR formatted, low-balance warning from tokens.
 * PROVEN: colour logic reads from CSS vars, not hardcoded values.
 */
import React from "react";

function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", { style:"currency", currency:"INR", maximumFractionDigits:2 }).format(amount);
}

export function WalletBalance({ balance, threshold=1000, label="Wallet Balance" }:{
  balance:number; threshold?:number; label?:string;
}) {
  const low = balance <= threshold;
  const critical = balance <= threshold * 0.3;

  return (
    <div style={{
      padding:"16px 20px", borderRadius:"12px",
      background: critical ? "var(--color-danger-bg)"  : low ? "var(--color-warning-bg)" : "var(--color-surface-base)",
      border: `1px solid ${critical ? "var(--color-danger-border)" : low ? "var(--color-warning-border)" : "var(--color-border)"}`,
    }}>
      <p style={{ fontSize:"11px", fontWeight:600, letterSpacing:"0.05em", textTransform:"uppercase",
        color: critical ? "var(--color-danger-text)" : low ? "var(--color-warning-text)" : "var(--color-text-tertiary)",
        margin:"0 0 6px" }}>
        {label}
        {low && ` • ${critical ? "CRITICAL" : "LOW"}`}
      </p>
      <p style={{ fontSize:"24px", fontWeight:700, margin:0,
        color: critical ? "var(--color-danger-text)" : low ? "var(--color-warning-text)" : "var(--color-text-primary)" }}>
        {formatINR(balance)}
      </p>
    </div>
  );
}
