/**
 * FINAL-L5-01E instrumentation: emits a timestamped, high-resolution event
 * name to the console so real-browser reproduction runs can reconstruct the
 * exact ordering of auth/redirect events across concurrent async work.
 *
 * Never pass tokens, passwords, or headers as the detail argument — this is
 * enabled by a query param / localStorage flag so it can be toggled on for
 * a reproduction run without shipping console noise by default.
 */
export function authTimeline(event: string, detail?: string): void {
  if (typeof window === "undefined") return;
  const enabled =
    window.location.search.includes("authTimeline=1") ||
    localStorage.getItem("serviceos_auth_timeline") === "1";
  if (!enabled) return;
  const t = performance.now().toFixed(1);
  // eslint-disable-next-line no-console
  console.log(`[auth-timeline] t=${t}ms ${event}${detail ? " :: " + detail : ""}`);
}
