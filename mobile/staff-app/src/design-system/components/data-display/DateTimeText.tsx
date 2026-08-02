import React from "react";
import { AppText, AppTextProps } from "../typography/AppText";

export interface DateTimeTextProps extends Omit<AppTextProps, "children"> {
  isoString: string | null | undefined;
  format?: "date" | "time" | "datetime";
}

export function DateTimeText({ isoString, format = "datetime", ...rest }: DateTimeTextProps) {
  if (!isoString) return <AppText {...rest} color="tertiary">—</AppText>;
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return <AppText {...rest} color="tertiary">—</AppText>;

  const opts: Intl.DateTimeFormatOptions =
    format === "date" ? { day: "2-digit", month: "short", year: "numeric" }
    : format === "time" ? { hour: "2-digit", minute: "2-digit" }
    : { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" };

  return <AppText {...rest} style={[{ fontVariant: ["tabular-nums"] }, rest.style]}>{d.toLocaleString("en-IN", opts)}</AppText>;
}

export function RelativeTime({ isoString, ...rest }: Omit<DateTimeTextProps, "format">) {
  if (!isoString) return <AppText {...rest} color="tertiary">—</AppText>;
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return <AppText {...rest} color="tertiary">—</AppText>;

  const diffMs = Date.now() - d.getTime();
  const mins = Math.floor(diffMs / 60000);
  let label: string;
  if (mins < 1) label = "Just now";
  else if (mins < 60) label = `${mins}m ago`;
  else if (mins < 24 * 60) label = `${Math.floor(mins / 60)}h ago`;
  else label = `${Math.floor(mins / (24 * 60))}d ago`;

  return <AppText {...rest}>{label}</AppText>;
}
