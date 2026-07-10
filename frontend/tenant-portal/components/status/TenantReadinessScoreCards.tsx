"use client";
import React from "react";
import Link from "next/link";
import { Card } from "../shared/ui";
import { TenantStatusBadge, type StatusVariant } from "./TenantStatusBadge";

export interface ScoreCard {
  id: string;
  label: string;
  value: string;
  variant: StatusVariant;
  reason: string;
  ctaLabel?: string;
  ctaRoute?: string;
}

export function TenantReadinessScoreCards({ cards }: { cards: ScoreCard[] }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
      {cards.map(c => (
        <Card key={c.id} padding={18}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-tertiary)", margin: 0 }}>
              {c.label}
            </p>
            <TenantStatusBadge label={c.variant === "success" ? "Ready" : c.variant === "danger" ? "Blocked" : c.variant === "warning" ? "Attention" : "Info"} variant={c.variant}/>
          </div>
          <p style={{ fontSize: 26, fontWeight: 800, margin: "0 0 6px" }}>{c.value}</p>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, minHeight: 32 }}>{c.reason}</p>
          {c.ctaLabel && c.ctaRoute && (
            <Link href={c.ctaRoute} style={{ fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none", marginTop: 10, display: "inline-block" }}>
              {c.ctaLabel} →
            </Link>
          )}
        </Card>
      ))}
    </div>
  );
}
