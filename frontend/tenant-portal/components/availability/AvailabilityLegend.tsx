"use client";
import React from "react";

function Swatch({ color, border, label }: { color: string; border: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--text-secondary)" }}>
      <span style={{ width: 12, height: 12, borderRadius: 4, background: color, border: `1px solid ${border}`, display: "inline-block" }}/>
      {label}
    </div>
  );
}

export function AvailabilityLegend() {
  return (
    <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginTop: 16, padding: "0 4px" }}>
      <Swatch color="var(--success-bg)" border="var(--success-border)" label="Available"/>
      <Swatch color="var(--info-bg)" border="var(--info-border)" label="Assigned"/>
      <Swatch color="var(--surface-sunken)" border="var(--border)" label="Break / Off"/>
      <Swatch color="var(--danger-bg)" border="var(--danger-border)" label="Conflict"/>
    </div>
  );
}
