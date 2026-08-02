import AsyncStorage from "@react-native-async-storage/async-storage";
import { QueueItem } from "./types";

/**
 * Persisted mutation-queue storage (Phase Z spec sections 5, 8, 18).
 * AsyncStorage is used deliberately (not SecureStore): queue items never
 * contain tokens, passwords, OTP/MFA secrets, or raw auth headers -- only
 * safe operation metadata + the mutation payload the technician typed --
 * so plaintext device storage is an accepted, documented tradeoff rather
 * than a secrets store. If a payload ever needs a genuinely sensitive
 * field (none do today per the operation registry), it must be encrypted
 * before landing here, not stored as-is.
 *
 * Storage is scoped per user+tenant so switching accounts on the same
 * device can never expose or resume a previous technician's queue (spec
 * section 17/18): a different user/tenant reads/writes a completely
 * different key. There is no cross-key migration path -- an orphaned
 * queue under a previous scope key is simply never read again.
 */
const SCHEMA_VERSION = 1;

interface PersistedQueueFile {
  schema_version: number;
  items: QueueItem[];
}

function storageKey(userId: string, tenantId: string): string {
  return `serviceos.staffapp.syncqueue.v${SCHEMA_VERSION}.${userId}.${tenantId}`;
}

/** Migrates an older/foreign shape to the current schema. Unknown/corrupt
 * records are quarantined (dropped) rather than crashing the whole queue
 * load -- spec section 25 item 19-20's "corrupted record" requirement. */
function migrate(raw: unknown): QueueItem[] {
  if (!raw || typeof raw !== "object") return [];
  const file = raw as Partial<PersistedQueueFile>;
  if (!Array.isArray(file.items)) return [];
  if (file.schema_version !== SCHEMA_VERSION) {
    // No prior schema versions exist yet; a mismatched/future version is
    // treated as unreadable rather than guessed-at.
    return [];
  }
  return file.items.filter(isValidQueueItem);
}

function isValidQueueItem(item: unknown): item is QueueItem {
  if (!item || typeof item !== "object") return false;
  const i = item as Record<string, unknown>;
  return (
    typeof i.local_id === "string" &&
    typeof i.operation_type === "string" &&
    typeof i.operation_class === "string" &&
    typeof i.tenant_id === "string" &&
    typeof i.idempotency_key === "string" &&
    Array.isArray(i.dependencies) &&
    typeof i.state === "string" &&
    typeof i.attempt_count === "number"
  );
}

export async function loadQueue(userId: string, tenantId: string): Promise<QueueItem[]> {
  try {
    const raw = await AsyncStorage.getItem(storageKey(userId, tenantId));
    if (!raw) return [];
    return migrate(JSON.parse(raw));
  } catch {
    // Corrupted JSON -- quarantine by returning an empty queue rather than
    // throwing; the corrupt record is overwritten on the next save.
    return [];
  }
}

export async function saveQueue(userId: string, tenantId: string, items: QueueItem[]): Promise<void> {
  const file: PersistedQueueFile = { schema_version: SCHEMA_VERSION, items };
  await AsyncStorage.setItem(storageKey(userId, tenantId), JSON.stringify(file));
}

export async function clearQueue(userId: string, tenantId: string): Promise<void> {
  await AsyncStorage.removeItem(storageKey(userId, tenantId));
}
