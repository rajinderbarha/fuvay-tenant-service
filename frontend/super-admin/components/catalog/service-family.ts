/** Conservative warning only: never rename records or change a job's type. */
export function namedJobType(name: string): string | null {
  return name.trim().toLowerCase().match(/\b(installation|uninstallation|repair|consultation|inspection)$/)?.[1] ?? null;
}

export function preferredJobType(name: string, links: { job_type_id: string; job_type: { key: string } }[]) {
  const hint = namedJobType(name);
  return links.find(link => link.job_type.key === hint)?.job_type_id ?? links[0]?.job_type_id ?? null;
}
