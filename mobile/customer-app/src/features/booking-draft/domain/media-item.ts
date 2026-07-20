import type { MediaValidationFailure } from "./media-validation";

/**
 * Deterministic per-item state — no scattered booleans (CUSTOMER-L5-06 §30).
 * Simplified from the spec's aspirational model to match what this backend
 * actually has: no signed-URL step (direct multipart, see contract-matrix.md),
 * no separate "finalization" step (the media engine's `POST /upload` is
 * synchronous and atomic), no malware/moderation states (none exist).
 */
export type MediaItemStatus =
  "SELECTED" | "INVALID" | "PREPARING" | "UPLOADING" | "UPLOAD_FAILED" | "UPLOADED" | "LINKING" | "LINK_FAILED" | "LINKED" | "DELETING" | "DELETED";

export interface MediaItem {
  localId: string;
  status: MediaItemStatus;
  uri: string;
  mimeType: string;
  fileSizeBytes: number | null;
  validationFailure: MediaValidationFailure | null;
  mediaAssetId: string | null;
  errorCategory: string | null;
  retryCount: number;
}

export function createMediaItem(localId: string, uri: string, mimeType: string, fileSizeBytes: number | null): MediaItem {
  return { localId, status: "SELECTED", uri, mimeType, fileSizeBytes, validationFailure: null, mediaAssetId: null, errorCategory: null, retryCount: 0 };
}

function transition(item: MediaItem, patch: Partial<MediaItem>): MediaItem {
  return { ...item, ...patch };
}

export function markInvalid(item: MediaItem, failure: MediaValidationFailure): MediaItem {
  return transition(item, { status: "INVALID", validationFailure: failure });
}

export function markPreparing(item: MediaItem): MediaItem {
  return transition(item, { status: "PREPARING", validationFailure: null });
}

export function markUploading(item: MediaItem): MediaItem {
  return transition(item, { status: "UPLOADING", errorCategory: null });
}

export function markUploadFailed(item: MediaItem, errorCategory: string): MediaItem {
  return transition(item, { status: "UPLOAD_FAILED", errorCategory, retryCount: item.retryCount + 1 });
}

export function markUploaded(item: MediaItem, mediaAssetId: string): MediaItem {
  return transition(item, { status: "UPLOADED", mediaAssetId, errorCategory: null });
}

export function markLinking(item: MediaItem): MediaItem {
  return transition(item, { status: "LINKING", errorCategory: null });
}

export function markLinkFailed(item: MediaItem, errorCategory: string): MediaItem {
  return transition(item, { status: "LINK_FAILED", errorCategory, retryCount: item.retryCount + 1 });
}

export function markLinked(item: MediaItem): MediaItem {
  return transition(item, { status: "LINKED", errorCategory: null });
}

export function markDeleting(item: MediaItem): MediaItem {
  return transition(item, { status: "DELETING" });
}

export function markDeleted(item: MediaItem): MediaItem {
  return transition(item, { status: "DELETED" });
}

export function isRetryable(item: MediaItem): boolean {
  return item.status === "UPLOAD_FAILED" || item.status === "LINK_FAILED";
}

export function isTerminal(item: MediaItem): boolean {
  return item.status === "LINKED" || item.status === "DELETED" || item.status === "INVALID";
}

const MAX_RETRIES = 3;
export function canRetry(item: MediaItem): boolean {
  return isRetryable(item) && item.retryCount < MAX_RETRIES;
}
