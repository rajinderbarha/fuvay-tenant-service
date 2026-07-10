"use client";
import React from "react";
export type DateTimeFormat = "date" | "time" | "datetime" | "relative" | "friendly";
export interface DateTimeCellProps { value: string|Date; format?: DateTimeFormat; size?: "sm"|"md"; }
function relativeTime(d: Date): string {
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`; if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  if (s < 2592000) return `${Math.floor(s/86400)}d ago`;
  return d.toLocaleDateString("en-IN",{day:"numeric",month:"short"});
}
export function DateTimeCell({ value, format = "datetime", size = "md" }: DateTimeCellProps) {
  const d = value instanceof Date ? value : new Date(value);
  const FS: Record<string,React.CSSProperties> = { sm:{fontSize:"var(--text-xs)"}, md:{fontSize:"var(--text-sm)"} };
  const fmt: Record<DateTimeFormat, string> = {
    date:     d.toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"}),
    time:     d.toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"}),
    datetime: d.toLocaleString("en-IN",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}),
    relative: relativeTime(d),
    friendly: d.toLocaleDateString("en-IN",{weekday:"short",day:"numeric",month:"long"}),
  };
  return (
    <time dateTime={d.toISOString()} title={d.toLocaleString("en-IN")}
      style={{ color:"var(--color-text-secondary)", ...FS[size] }}>
      {fmt[format]}
    </time>
  );
}
