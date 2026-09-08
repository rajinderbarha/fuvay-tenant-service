/** Preview only; the server rechecks funded, ready technicians at booking time. */
export function twoHourWindows(start: string, end: string, breakStart?: string | null, breakEnd?: string | null, bufferMinutes = 0): string[] {
  const minutes = (v: string) => { const [h, m] = v.split(":").map(Number); return h * 60 + m; };
  const label = (v: number) => `${String(Math.floor(v / 60)).padStart(2, "0")}:${String(v % 60).padStart(2, "0")}`;
  const windows: string[] = [];
  const stop = minutes(end);
  for (let cursor = minutes(start); cursor + 120 <= stop;) {
    if (breakStart && breakEnd && cursor < minutes(breakEnd) && cursor + 120 > minutes(breakStart)) {
      cursor = minutes(breakEnd);
      continue;
    }
    windows.push(`${label(cursor)}–${label(cursor + 120)}`);
    cursor += 120 + Math.max(0, bufferMinutes || 0);
  }
  return windows;
}

export function allocateDailySlots(windows: string[], technicians: number, dailyLimit?: number | null) {
  const total = Math.max(0, Math.min(windows.length * technicians, dailyLimit ?? windows.length * technicians));
  const base = windows.length ? Math.floor(total / windows.length) : 0;
  return windows.map((window, index) => ({ window, capacity: base + (index < total % windows.length ? 1 : 0) }));
}
