"use client";
/**
 * BookingVolumeChart — recharts BarChart for booking counts by period.
 * Stacks confirmed / pending / cancelled bars. CSS-var driven colours.
 */
import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell,
} from "recharts";

export interface BookingVolumePoint {
  period:     string;
  confirmed?: number;
  pending?:   number;
  cancelled?: number;
  total?:     number;
}

export interface BookingVolumeChartProps {
  data:     BookingVolumePoint[];
  stacked?: boolean;
  height?:  number;
  loading?: boolean;
  showTotal?: boolean;
}

const CustomTooltip = ({ active, payload, label }: {
  active?: boolean; payload?: {name:string; value:number; color:string}[]; label?: string;
}) => {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((s, p) => s + (p.value || 0), 0);
  return (
    <div style={{
      background: "var(--color-surface-elevated)", border: "1px solid var(--color-border)",
      borderRadius: "var(--radius-lg)", padding: "12px 14px",
      boxShadow: "var(--shadow-lg)", minWidth: 140,
    }}>
      <p style={{ fontSize: "var(--text-xs)", fontWeight: 700, color: "var(--color-text-tertiary)",
        textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 8px" }}>{label}</p>
      {payload.map(p => (
        <div key={p.name} style={{ display: "flex", justifyContent: "space-between",
          gap: 14, marginBottom: 3 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6,
            fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: p.color, flexShrink: 0 }}/>
            {p.name}
          </span>
          <span style={{ fontSize: "var(--text-sm)", fontWeight: 700,
            color: "var(--color-text-primary)" }}>{p.value}</span>
        </div>
      ))}
      {payload.length > 1 && (
        <div style={{ borderTop: "1px solid var(--color-border)", marginTop: 6, paddingTop: 6,
          display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>Total</span>
          <span style={{ fontSize: "var(--text-sm)", fontWeight: 700,
            color: "var(--color-text-primary)" }}>{total}</span>
        </div>
      )}
    </div>
  );
};

const SERIES = [
  { key: "confirmed", name: "Confirmed", color: "var(--color-success)"  },
  { key: "pending",   name: "Pending",   color: "var(--color-warning)"  },
  { key: "cancelled", name: "Cancelled", color: "var(--color-danger)"   },
] as const;

export function BookingVolumeChart({
  data, stacked = true, height = 280, loading, showTotal,
}: BookingVolumeChartProps) {
  if (loading) {
    return (
      <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center",
        background: "var(--color-surface-base)", borderRadius: "var(--radius-lg)",
        border: "1px solid var(--color-border)" }}>
        <div className="skeleton" style={{ width: "90%", height: height - 40, borderRadius: "var(--radius-md)" }}/>
      </div>
    );
  }

  const activeKeys = SERIES.filter(s => data.some(d => d[s.key] != null && d[s.key]! > 0));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barGap={3}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false}/>
        <XAxis
          dataKey="period"
          tick={{ fontSize: 11, fill: "var(--color-text-tertiary)", fontFamily: "var(--font-sans)" }}
          axisLine={false} tickLine={false} dy={6}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--color-text-tertiary)", fontFamily: "var(--font-sans)" }}
          axisLine={false} tickLine={false} dx={-4} allowDecimals={false} width={40}
        />
        <Tooltip content={<CustomTooltip/>}/>
        <Legend
          iconType="square" iconSize={10}
          wrapperStyle={{ fontSize: "var(--text-xs)", paddingTop: 12, fontFamily: "var(--font-sans)" }}
        />
        {showTotal && (
          <Bar dataKey="total" name="Total" fill="var(--color-brand-300)"
            radius={[4, 4, 0, 0]} maxBarSize={40}/>
        )}
        {!showTotal && activeKeys.map(s => (
          <Bar
            key={s.key} dataKey={s.key} name={s.name}
            fill={s.color}
            stackId={stacked ? "stack" : undefined}
            radius={stacked
              ? s.key === "confirmed" ? [4, 4, 0, 0] : [0, 0, 0, 0]
              : [4, 4, 0, 0]}
            maxBarSize={stacked ? 48 : 18}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
