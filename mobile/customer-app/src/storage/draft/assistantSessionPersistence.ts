/**
 * Non-sensitive persistence of an in-progress Assistant session/draft
 * pointer -- NEVER the conversation content or answers themselves (those
 * live entirely server-side, per the canonical session/draft model).
 * This is only enough to resume across app restarts: an ai_session_id
 * (and, once known, a draft_id) scoped by the entry category so a
 * different service doesn't accidentally resume a stale session.
 */
import { getLocalJSON, setLocalJSON, removeLocalItem } from "../localStorage";
import { CustomerId } from "../../domain/ids";

export const ASSISTANT_SESSION_SCHEMA_VERSION = 1;

export interface StoredAssistantPointer {
  schemaVersion: typeof ASSISTANT_SESSION_SCHEMA_VERSION;
  ownerCustomerId: CustomerId;
  /** "generic" for assistant-card entries with no category. */
  scopeKey: string;
  sessionId: string;
  draftId: string | null;
  updatedAt: string;
}

function storageKey(customerId: CustomerId, scopeKey: string): string {
  return `customer_app_assistant_session_v1_${customerId}_${scopeKey}`;
}

export async function saveAssistantPointer(
  customerId: CustomerId, scopeKey: string, sessionId: string, draftId: string | null,
): Promise<void> {
  const record: StoredAssistantPointer = {
    schemaVersion: ASSISTANT_SESSION_SCHEMA_VERSION,
    ownerCustomerId: customerId,
    scopeKey,
    sessionId,
    draftId,
    updatedAt: new Date().toISOString(),
  };
  await setLocalJSON(storageKey(customerId, scopeKey), record);
}

export async function loadAssistantPointer(
  customerId: CustomerId, scopeKey: string,
): Promise<StoredAssistantPointer | null> {
  const stored = await getLocalJSON<StoredAssistantPointer>(storageKey(customerId, scopeKey));
  if (!stored) return null;
  if (stored.schemaVersion !== ASSISTANT_SESSION_SCHEMA_VERSION || stored.ownerCustomerId !== customerId) {
    await removeLocalItem(storageKey(customerId, scopeKey));
    return null;
  }
  return stored;
}

export async function clearAssistantPointer(customerId: CustomerId, scopeKey: string): Promise<void> {
  await removeLocalItem(storageKey(customerId, scopeKey));
}
