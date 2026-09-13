export function dispatchUrlForAvailabilityJob(date: string, jobId: string): string {
  const query = new URLSearchParams({ date, job_id: jobId });
  return `/home-services/dispatch?${query}`;
}
