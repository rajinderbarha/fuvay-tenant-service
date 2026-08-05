/** Time-sensitive greeting -- pure function of the clock, never a
 * hardcoded literal. Device time only (no backend field for this). */
export function timeSensitiveGreeting(now: Date = new Date()): string {
  const hour = now.getHours();
  if (hour < 12) return "Good morning,";
  if (hour < 17) return "Good afternoon,";
  return "Good evening,";
}
