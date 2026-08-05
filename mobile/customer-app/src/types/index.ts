/**
 * App-level shared types. Domain contracts (booking, quote, job, etc.)
 * belong to Phase D and are intentionally absent here -- this phase only
 * establishes the offline-safety classification described in the
 * foundation spec, so later feature code has a place to plug into.
 */

/** How a future mutation must be treated for offline/replay safety.
 * Never invent a fake successful response for any of these locally. */
export type MutationSafetyClass =
  | "LOCAL_DRAFT"
  | "MEDIA_UPLOAD"
  | "IDEMPOTENT_MUTATION"
  | "ONLINE_ONLY_MUTATION";

export interface ApiError {
  status?: number;
  code?: string;
  message: string;
}
