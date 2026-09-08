import type { ProviderAvailabilityRule, ProviderAvailabilityPayload } from "./api";
import { twoHourWindows } from "./booking-capacity";

export const WEEK_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
export type DayDraft = { day_of_week: number; is_active: boolean; start_time: string; end_time: string;
  break_start_time: string; break_end_time: string; max_jobs_per_day: string };

export function scheduleDraft(rules: ProviderAvailabilityRule[]): DayDraft[] {
  const newest = [...rules].filter(r => r.scope_type === "provider" && !r.scope_id)
    .sort((a, b) => (a.updated_at || a.created_at || "").localeCompare(b.updated_at || b.created_at || ""));
  return WEEK_DAYS.map((_, day) => {
    const candidates = newest.filter(r => r.day_of_week === day);
    const r = candidates.filter(r => r.is_active).at(-1) || candidates.at(-1);
    return { day_of_week: day, is_active: !!r?.is_active, start_time: r?.start_time?.slice(0, 5) || "09:00",
      end_time: r?.end_time?.slice(0, 5) || "18:00", break_start_time: r?.break_start_time?.slice(0, 5) || "",
      break_end_time: r?.break_end_time?.slice(0, 5) || "", max_jobs_per_day: r?.max_jobs_per_day == null ? "" : String(r.max_jobs_per_day) };
  });
}

export function dayError(day: DayDraft, technicians: number, buffer = 0): string | null {
  const valid = (t: string) => /^([01]\d|2[0-3]):[0-5]\d$/.test(t);
  if (!valid(day.start_time) || !valid(day.end_time)) return "Enter a complete opening and closing time.";
  if (day.start_time >= day.end_time) return "Closing time must be after opening time (same day).";
  if (day.break_start_time || day.break_end_time) {
    if (!valid(day.break_start_time) || !valid(day.break_end_time)) return "Enter both break times, or remove the break.";
    if (day.break_start_time >= day.break_end_time || day.break_start_time < day.start_time || day.break_end_time > day.end_time) return "The break must start and end inside business hours.";
  }
  if (!day.is_active) return null;
  const count = twoHourWindows(day.start_time, day.end_time, day.break_start_time, day.break_end_time, buffer).length;
  if (!count) return "Allow at least one complete two-hour job outside the break.";
  const limit = Number(day.max_jobs_per_day);
  if (day.max_jobs_per_day !== "" && (!Number.isInteger(limit) || limit < 1 || limit > count * technicians)) return `Daily limit must be 1–${count * technicians}, or leave blank for Automatic.`;
  return null;
}

export function schedulePayload(days: DayDraft[]): ProviderAvailabilityPayload[] {
  return days.map(day => ({ ...day, scope_type: "provider", slot_duration_minutes: 120,
    break_start_time: day.break_start_time || null, break_end_time: day.break_end_time || null,
    max_jobs_per_day: day.max_jobs_per_day === "" ? null : Number(day.max_jobs_per_day) }));
}

export function businessDate(timezone = "Asia/Kolkata", date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  return ["year", "month", "day"].map(type => parts.find(p => p.type === type)?.value).join("-");
}
