/**
 * Only module types with a real backend-backed data source are listed here
 * (CUSTOMER-L5-03-backend-contract-audit.md found no dedicated Home/modules
 * endpoint — categories are the only real discovery data this backend
 * provides). Adding a new type here requires a real data source; it must
 * never be added "for completeness" alone (CUSTOMER-L5-03 §7).
 */
export const SUPPORTED_MODULE_TYPES = ["category-grid"] as const;
export type SupportedModuleType = (typeof SUPPORTED_MODULE_TYPES)[number];

export function isSupportedModuleType(value: string): value is SupportedModuleType {
  return (SUPPORTED_MODULE_TYPES as readonly string[]).includes(value);
}

/** Envelope metadata every Home module carries, independent of its type-specific payload. */
export interface HomeModuleEnvelope {
  id: string;
  type: string; // intentionally wider than SupportedModuleType — unknown/future types must still parse the envelope so they can be safely skipped, not rejected as malformed
  title?: string;
  order: number;
  critical: boolean;
  requiresAuth: boolean;
  minAppVersion?: string;
  regions?: string[];
}
