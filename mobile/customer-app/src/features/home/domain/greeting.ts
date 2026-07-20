export type DayPeriod = "morning" | "afternoon" | "evening";

export function dayPeriodFromHour(hour: number): DayPeriod {
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}

/** A malformed/empty backend name must never render broken layout — falls back to a generic greeting instead. */
export function safeFirstName(fullName: string | null | undefined): string | null {
  if (!fullName) return null;
  const trimmed = fullName.trim();
  if (trimmed.length === 0) return null;
  const first = trimmed.split(/\s+/)[0];
  if (first.length === 0 || first.length > 40) return null;
  return first;
}
