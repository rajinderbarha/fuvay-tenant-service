import { generateIdempotencyKey } from "../client/requestMetadata";
import { getLocalJSON, setLocalJSON, removeLocalItem } from "../../storage/localStorage";
import { IdempotencyKey, asIdempotencyKey } from "../../domain/ids";

/**
 * Typed idempotency-key infrastructure (spec section 25). This phase
 * builds the mechanism only -- no booking/quote/review mutation actually
 * uses it yet (those are later phases). The one CONFIRMED consumer today
 * is `POST /customer/quotes/{id}/approve`, which requires an
 * `Idempotency-Key` header (verified in Phase D's audit of
 * quote_checklist/customer_router.py) -- everything else must keep using
 * this only once a specific endpoint is confirmed to accept the header;
 * see Phase D capability registry `offlinePolicy` field for which
 * operations are `IDEMPOTENT_MUTATION`.
 */
const STORAGE_KEY_PREFIX = "customer_app_idempotency_";
const DEFAULT_TTL_MS = 15 * 60 * 1000;

interface StoredIdempotencyEntry {
  key: string;
  operationScope: string;
  createdAt: string;
  expiresAt: string;
}

function storageKey(operationScope: string): string {
  return `${STORAGE_KEY_PREFIX}${operationScope}`;
}

/**
 * Returns the idempotency key for a logical operation, generating and
 * persisting a new one only if none exists yet (or the existing one
 * expired) -- a retry of the SAME logical operation (e.g. "approve this
 * one quote") must reuse the same key; a different operation (a
 * different quote ID) must never see a stale key from an unrelated one,
 * which is why `operationScope` should always embed the target entity ID
 * (e.g. `quote-approve:${quoteId}`), never be a bare verb.
 */
export async function getOrCreateIdempotencyKey(operationScope: string, ttlMs: number = DEFAULT_TTL_MS): Promise<IdempotencyKey> {
  const existing = await getLocalJSON<StoredIdempotencyEntry>(storageKey(operationScope));
  if (existing && new Date(existing.expiresAt).getTime() > Date.now()) {
    return asIdempotencyKey(existing.key);
  }
  const key = generateIdempotencyKey();
  const entry: StoredIdempotencyEntry = {
    key,
    operationScope,
    createdAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + ttlMs).toISOString(),
  };
  await setLocalJSON(storageKey(operationScope), entry);
  return asIdempotencyKey(key);
}

/** Called once the operation completes (success or terminal failure) --
 * a completed operation must not reuse its key for an unrelated future
 * call to the same scope. */
export async function clearIdempotencyKey(operationScope: string): Promise<void> {
  await removeLocalItem(storageKey(operationScope));
}
