const MAX_QUERY_LENGTH = 100;
export const MIN_QUERY_LENGTH = 2;

// eslint-disable-next-line no-control-regex -- deliberately stripping ASCII control characters, not matching a literal range.
const CONTROL_CHARACTERS = /[\x00-\x1F\x7F]/g;

/**
 * Normalizes raw search input before it is ever sent to the backend or used
 * as a cache key: trims, collapses internal whitespace, strips control
 * characters, and enforces a maximum length. Preserves all other Unicode
 * (including Hindi/Punjabi scripts) untouched — CUSTOMER-L5-04 §17.
 */
export function normalizeSearchQuery(raw: string): string {
  return raw.replace(CONTROL_CHARACTERS, "").replace(/\s+/g, " ").trim().slice(0, MAX_QUERY_LENGTH);
}

export function isSearchableQuery(normalized: string): boolean {
  return normalized.length >= MIN_QUERY_LENGTH;
}

/**
 * Safe-for-analytics/logging bucket — never the raw query text
 * (CUSTOMER-L5-04 §25/§53/§55).
 */
export function queryLengthBucket(normalized: string): "short" | "medium" | "long" {
  if (normalized.length <= 5) return "short";
  if (normalized.length <= 20) return "medium";
  return "long";
}

export function resultCountBucket(count: number): "zero" | "few" | "many" {
  if (count === 0) return "zero";
  if (count <= 5) return "few";
  return "many";
}
