import type { MaintenanceConfig } from "./remote-config-schema";

export type MaintenanceStatus = "none" | "scheduled" | "active" | "expired";

export interface MaintenancePolicyResult {
  status: MaintenanceStatus;
  blocking: boolean;
  readOnly: boolean;
  retryAllowed: boolean;
}

/**
 * Timezone-safe: only compares server-provided absolute ISO timestamps
 * against the caller-provided "now" — never derives a window from local
 * device time zone math.
 */
export function evaluateMaintenancePolicy(maintenance: MaintenanceConfig, nowIso: string = new Date().toISOString()): MaintenancePolicyResult {
  if (!maintenance.enabled || maintenance.type === "none") {
    return { status: "none", blocking: false, readOnly: false, retryAllowed: true };
  }

  const now = new Date(nowIso).getTime();
  const startAt = maintenance.startAt ? new Date(maintenance.startAt).getTime() : undefined;
  const endAt = maintenance.estimatedEndAt ? new Date(maintenance.estimatedEndAt).getTime() : undefined;

  if (startAt !== undefined && now < startAt) {
    return { status: "scheduled", blocking: false, readOnly: false, retryAllowed: true };
  }
  if (endAt !== undefined && now >= endAt) {
    return { status: "expired", blocking: false, readOnly: false, retryAllowed: true };
  }

  const blocking = maintenance.type === "active-blocking";
  const readOnly = maintenance.type === "active-read-only";
  return { status: "active", blocking, readOnly, retryAllowed: maintenance.retryAllowed };
}
