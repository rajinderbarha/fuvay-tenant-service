"use client";
/**
 * RevenueChart — recharts AreaChart, platform + tenant variants.
 * Reads colour tokens from CSS variables. Zero hardcoded hex.
 */
import React from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

export interface RevenueDataPoint {
  period:     string;
  gmv?:       number;
  commission?: number;
  platform?:  number;
  tenant?:    number;
}

export type RevenueChartVariant = "platform" | "tenant";

export interface RevenueChartProps {
  data:      RevenueDataPoint[];
  variant?:  RevenueChartVariant;
  height?:   number;
  currency?: string;
  loading?:  boolean;
}

function formatINR(v: number, currency = "₹") {
  if (v >= 100000)  return `${currency}${(v / 100000).toFixed(1)}L`;
  if (v >= 1000)    return `${currency}${(v / 1000).toFixed(1)}K`;
  return `${currency}${v.toLocaleString("en-IN")}`;
}

const CustomTooltip = ({ active, payload, label, currency }: {
  active?: boolean; payload?: {name:string; value:number; color:string}[];
  label?: string; currency?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--color-surface-elevated)", border: "1px solid var(--color-border)",
      borderRadius: "var(--radius-lg)", padding: "12px 14px", boxShadow: "var(--shadow-lg)",
      minWidth: 160,
    }}>
      <p style={{ fontSize: "var(--text-xs)", fontWeight: 700, color: "var(--color-text-tertiary)",
        textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 8px" }}>{label}</p>
      {payload.map(p => (
        <div key={p.name} style={{ display: "flex", justifyContent: "space-between",
          gap: 16, marginBottom: 4 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6,
            fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: p.color, flexShrink: 0 }}/>
            {p.name}
          </span>
          <span style={{ fontSize: "var(--text-sm)", fontWeight: 700,
            color: "var(--color-text-primary)" }}>
            {formatINR(p.value, currency)}
          </span>
        </div>
      ))}
    </div>
  );
};

export function RevenueChart({
  data, variant = "platform", height = 280, currency = "₹", loading,
}: RevenueChartProps) {
  if (loading) {
    return (
      <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center",
        background: "var(--color-surface-base)", borderRadius: "var(--radius-lg)",
        border: "1px solid var(--color-border)" }}>
        <div className="skeleton" style={{ width: "90%", height: height - 40, borderRadius: "var(--radius-md)" }}/>
      </div>
    );
  }

  const areas: { key: keyof RevenueDataPoint; name: string; stroke: string; fill: string }[] =
    variant === "platform"
      ? [
          { key: "gmv",        name: "GMV",        stroke: "var(--color-brand-500)", fill: "var(--color-brand-100)" },
          { key: "commission", name: "Commission",  stroke: "var(--color-accent)",    fill: "var(--color-accent-muted)" },
        ]
      : [
          { key: "gmv",    name: "Revenue",  stroke: "var(--color-brand-500)", fill: "var(--color-brand-100)" },
          { key: "tenant", name: "Payout",   stroke: "var(--color-success)",   fill: "var(--color-success-bg)"  },
        ];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          {areas.map(a => (
            <linearGradient key={a.key} id={`grad-${a.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor={a.fill} stopOpacity={0.6}/>
              <stop offset="100%" stopColor={a.fill} stopOpacity={0.05}/>
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--color-border)"
          vertical={false}
        />
        <XAxis
          dataKey="period"
          tick={{ fontSize: 11, fill: "var(--color-text-tertiary)", fontFamily: "var(--font-sans)" }}
          axisLine={false} tickLine={false} dy={6}
        />
        <YAxis
          tickFormatter={v => formatINR(v, currency)}
          tick={{ fontSize: 11, fill: "var(--color-text-tertiary)", fontFamily: "var(--font-sans)" }}
          axisLine={false} tickLine={false} dx={-4} width={56}
        />
        <Tooltip content={<CustomTooltip currency={currency}/>} />
        <Legend
          iconType="circle" iconSize={8}
          wrapperStyle={{ fontSize: "var(--text-xs)", paddingTop: 12, fontFamily: "var(--font-sans)" }}
        />
        {areas.map(a => (
          <Area
            key={a.key}
            type="monotone"
            dataKey={a.key as string}
            name={a.name}
            stroke={a.stroke}
            strokeWidth={2}
            fill={`url(#grad-${a.key})`}
            activeDot={{ r: 5, strokeWidth: 0 }}
            dot={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
