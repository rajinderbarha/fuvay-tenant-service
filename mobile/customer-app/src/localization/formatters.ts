import type { SupportedLocale } from "../config/app-config";

const INTL_LOCALE: Record<SupportedLocale, string> = { en: "en-IN", hi: "hi-IN", pa: "pa-IN" };

export function formatNumber(value: number, locale: SupportedLocale): string {
  return new Intl.NumberFormat(INTL_LOCALE[locale]).format(value);
}

export function formatCurrency(value: number, locale: SupportedLocale, currency = "INR"): string {
  return new Intl.NumberFormat(INTL_LOCALE[locale], { style: "currency", currency }).format(value);
}

export function formatDate(date: Date, locale: SupportedLocale): string {
  return new Intl.DateTimeFormat(INTL_LOCALE[locale], { dateStyle: "medium" }).format(date);
}

export function formatTime(date: Date, locale: SupportedLocale): string {
  return new Intl.DateTimeFormat(INTL_LOCALE[locale], { timeStyle: "short" }).format(date);
}

export function formatRelativeTime(fromDate: Date, locale: SupportedLocale, now: Date = new Date()): string {
  const diffMs = fromDate.getTime() - now.getTime();
  const diffMinutes = Math.round(diffMs / 60000);
  const rtf = new Intl.RelativeTimeFormat(INTL_LOCALE[locale], { numeric: "auto" });

  if (Math.abs(diffMinutes) < 60) return rtf.format(diffMinutes, "minute");
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) return rtf.format(diffHours, "hour");
  const diffDays = Math.round(diffHours / 24);
  return rtf.format(diffDays, "day");
}
