const TERMINAL_JOB_STATUSES = new Set([
  "completed", "cancelled", "failed", "closed_estimate_declined",
]);

export function canManageJobInDispatch(status: string | null | undefined, isTerminal: boolean): boolean {
  return !isTerminal && !TERMINAL_JOB_STATUSES.has(String(status ?? "").toLowerCase());
}

export function completedJobReviewUrl(status: string | null | undefined, jobNumber: string): string | null {
  if (String(status ?? "").toLowerCase() !== "completed" || !jobNumber) return null;
  return `/home-services/reviews?search=${encodeURIComponent(jobNumber)}`;
}

export function providerJobWorkspaceUrl(jobId: string): string {
  return `/home-services/bookings-jobs?job_id=${encodeURIComponent(jobId)}`;
}
