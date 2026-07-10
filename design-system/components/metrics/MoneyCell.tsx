"use client";
import React from "react";
export interface MoneyCellProps { amount: number; currency?: string; negative?: boolean; bold?: boolean; size?: "sm"|"md"|"lg"; colorize?: boolean; }
export function MoneyCell({ amount, currency = "₹", negative, bold, size = "md", colorize = false }: MoneyCellProps) {
  const isNeg = negative ?? amount < 0;
  const abs   = Math.abs(amount);
  const fmt   = abs >= 100000 ? `${currency}${(abs/100000).toFixed(1)}L` : abs >= 1000 ? `${currency}${(abs/1000).toFixed(1)}K` : `${currency}${abs.toLocaleString("en-IN")}`;
  const S: Record<string,React.CSSProperties> = { sm:{fontSize:"var(--text-sm)"}, md:{fontSize:"var(--text-base)"}, lg:{fontSize:"var(--text-lg)"} };
  const color = !colorize ? "inherit" : isNeg ? "var(--color-danger-text)" : "var(--color-success-text)";
  return (
    <span style={{ color, fontWeight: bold ? "var(--font-bold)" : "var(--font-medium)",
      fontVariantNumeric:"tabular-nums", ...S[size] }}>
      {isNeg ? "-" : ""}{fmt}
    </span>
  );
}
