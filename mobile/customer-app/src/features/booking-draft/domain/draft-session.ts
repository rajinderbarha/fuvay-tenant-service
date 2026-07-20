import { isTerminalDraftStatus, isPastExpiry, type ValidatedBookingDraft } from "./draft-schema";

/**
 * Simplified from CUSTOMER-L5-06 §42's aspirational model to match what
 * this backend actually supports: no `CONFLICT` state (no version/revision
 * column exists anywhere on `HomeServiceBookingDraft` — see
 * contract-matrix.md, so there is nothing to detect a conflict from beyond
 * "the server rejected my mutation"), no formal `BRANCHING`/`RESTORING`
 * split (draft restoration is just `LOADING_DRAFT` against a locally
 * cached ID). `OFFLINE_PENDING` is represented via the existing
 * `OfflineBanner` pattern at the screen level, not a distinct session
 * status, since there is no queued-mutation infrastructure to represent
 * (CUSTOMER-L5-06 §44/§45 — no reliable queue exists, so none is faked).
 */
export type DraftSessionStatus = "IDLE" | "LOADING" | "CREATING" | "READY" | "SAVING" | "SAVE_FAILED" | "EXPIRED" | "CANCELLED" | "ERROR";

export interface DraftSessionState {
  status: DraftSessionStatus;
  draft: ValidatedBookingDraft | null;
  error: { category: string; message: string } | null;
}

export const initialDraftSessionState: DraftSessionState = { status: "IDLE", draft: null, error: null };

export function loadingDraft(): DraftSessionState {
  return { status: "LOADING", draft: null, error: null };
}

export function creatingDraft(): DraftSessionState {
  return { status: "CREATING", draft: null, error: null };
}

/** Fails closed to EXPIRED/CANCELLED if the authoritative draft is already terminal — never presents a closed draft as READY. */
export function draftLoaded(draft: ValidatedBookingDraft): DraftSessionState {
  if (draft.status === "expired" || isPastExpiry(draft)) return { status: "EXPIRED", draft, error: null };
  if (draft.status === "cancelled") return { status: "CANCELLED", draft, error: null };
  return { status: "READY", draft, error: null };
}

export function savingDraft(state: DraftSessionState): DraftSessionState {
  if (state.status !== "READY") return state;
  return { ...state, status: "SAVING", error: null };
}

export function saveSucceeded(state: DraftSessionState, updated: ValidatedBookingDraft): DraftSessionState {
  return draftLoaded(updated);
}

export function saveFailed(state: DraftSessionState, category: string, message: string): DraftSessionState {
  return { ...state, status: "SAVE_FAILED", error: { category, message } };
}

export function loadFailed(category: string, message: string): DraftSessionState {
  return { status: "ERROR", draft: null, error: { category, message } };
}

export function isMutable(state: DraftSessionState): boolean {
  return state.status === "READY" && state.draft !== null && !isTerminalDraftStatus(state.draft.status);
}
