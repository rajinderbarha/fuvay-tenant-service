/**
 * Date/time handling. Backend truth: `created_at`/`updated_at` are
 * DateTime columns serialized as ISO-8601; `preferred_date`/
 * `scheduled_date` are plain Date columns (no time-of-day, no timezone).
 * Storage representation is always kept separate from localized display
 * -- adapters store the raw ISO string as `ServerTimestamp`, never a
 * device-local `Date` object, so a later display layer can localize
 * without losing the original instant. Device clock is never treated as
 * authoritative for offer/quote expiry -- expiry comparisons must use a
 * server-provided timestamp, never `Date.now()` alone as the source of
 * truth for "has this expired," only as the read side of the comparison.
 */
import { DomainError } from "./errors";

/** An ISO-8601 instant exactly as the backend sent it. */
export type ServerTimestamp = string & { readonly __brand: "ServerTimestamp" };

/** A calendar date with no time-of-day/timezone component (YYYY-MM-DD),
 * matching the backend's plain Date columns. */
export type ServerDate = string & { readonly __brand: "ServerDate" };

const ISO_TIMESTAMP_RE = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/;
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export function parseServerTimestamp(raw: unknown, field: string): ServerTimestamp {
  if (typeof raw !== "string" || !ISO_TIMESTAMP_RE.test(raw)) {
    throw new DomainError({
      category: "CONTRACT_MISMATCH",
      diagnostic: `${field} is not a valid ISO timestamp: ${JSON.stringify(raw)}`,
    });
  }
  return raw as ServerTimestamp;
}

export function parseServerDate(raw: unknown, field: string): ServerDate {
  if (typeof raw !== "string" || !ISO_DATE_RE.test(raw)) {
    throw new DomainError({
      category: "CONTRACT_MISMATCH",
      diagnostic: `${field} is not a valid ISO date: ${JSON.stringify(raw)}`,
    });
  }
  return raw as ServerDate;
}

export function toDisplayDate(value: ServerTimestamp | ServerDate): Date {
  return new Date(value);
}

/** Compares an expiry instant against the current time. The device clock
 * is only ever used as the read side of this comparison -- the expiry
 * value itself must always originate from the server. */
export function isExpired(expiresAt: ServerTimestamp, now: Date = new Date()): boolean {
  return toDisplayDate(expiresAt).getTime() <= now.getTime();
}

/** Formats a real fetch-completion instant (e.g. React Query's own
 * `dataUpdatedAt`, a client-side `Date.now()` snapshot) as "Updated
 * {time}" copy -- `undefined`/`0` (no successful fetch has ever
 * completed) renders nothing rather than a false "just now" claim.
 * Never used for a server-authoritative timestamp; this is purely "how
 * stale is the screen I'm looking at." */
/** Formats a real server timestamp (e.g. a session's `last_active_at`) as
 * "Last active {relative}" copy -- unlike `formatRelativeUpdateTime`, the
 * instant itself is server-authoritative, not a client fetch marker. The
 * device clock is only ever the read side of the comparison. */
export function formatRelativeServerTime(timestamp: ServerTimestamp, now: number = Date.now()): string {
  const diffSeconds = Math.max(0, Math.floor((now - toDisplayDate(timestamp).getTime()) / 1000));
  if (diffSeconds < 60) return "just now";
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes === 1 ? "" : "s"} ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
  return toDisplayDate(timestamp).toLocaleDateString();
}

export function formatRelativeUpdateTime(updatedAtMs: number | undefined, now: number = Date.now()): string | null {
  if (!updatedAtMs) return null;
  const diffSeconds = Math.max(0, Math.floor((now - updatedAtMs) / 1000));
  if (diffSeconds < 10) return "Updated just now";
  if (diffSeconds < 60) return `Updated ${diffSeconds}s ago`;
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `Updated ${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `Updated ${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `Updated ${diffDays}d ago`;
}
