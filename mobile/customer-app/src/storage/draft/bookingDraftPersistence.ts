/**
 * Versioned local persistence contract for an in-progress Home Services
 * booking draft, before/between server round-trips to
 * `/v1/customer/home-services/booking-drafts/*`. This is LOCAL_DRAFT-class
 * state (see domain/offline.ts) -- it exists purely so a customer can
 * resume filling in a draft after backgrounding the app; the server draft
 * (once created) remains the source of truth for anything already synced.
 */
import { getLocalJSON, setLocalJSON, removeLocalItem } from "../localStorage";
import { CustomerId, BookingDraftId, CategoryId, ServiceGroupId, MasterServiceId, JobTypeId, AddressId } from "../../domain/ids";

export const BOOKING_DRAFT_SCHEMA_VERSION = 1;

export interface LocalMediaReference {
  /** Local file URI only -- never the uploaded bytes themselves. */
  localUri: string;
  /** Set once MEDIA_UPLOAD has confirmed server storage (see
   * domain/offline.ts) -- undefined means "not yet uploaded". */
  remoteMediaId?: string;
  uploadState: "pending" | "uploading" | "uploaded" | "failed";
}

export interface LocalBookingDraft {
  schemaVersion: typeof BOOKING_DRAFT_SCHEMA_VERSION;
  /** Owning customer -- enforced on read so one signed-in customer can
   * never resume a draft another customer started on the same device. */
  ownerCustomerId: CustomerId;
  createdAt: string;
  updatedAt: string;
  /** Local drafts expire independently of any server draft's own expiry --
   * this is a UI-resume window, not the authoritative booking-draft TTL. */
  expiresAt: string;

  categoryId?: CategoryId;
  serviceGroupId?: ServiceGroupId;
  masterServiceId?: MasterServiceId;
  jobTypeId?: JobTypeId;
  typeSelection?: string;
  brandSelection?: string;
  questionAnswers: Record<string, unknown>;
  media: LocalMediaReference[];
  zipcode?: string;
  scheduleSelection?: { date: string; timeWindow?: string };
  addressId?: AddressId;
  notes?: string;

  /** Set once the backend has created the corresponding server draft --
   * from that point on, every further mutation must round-trip the
   * server; this field existing is what "promotes" local-only input into
   * a synced draft. */
  serverDraftId?: BookingDraftId;
}

const STORAGE_KEY_PREFIX = "customer_app_booking_draft_v1_";
const LOCAL_DRAFT_TTL_MS = 24 * 60 * 60 * 1000;

function storageKey(customerId: CustomerId): string {
  return `${STORAGE_KEY_PREFIX}${customerId}`;
}

export function createEmptyDraft(ownerCustomerId: CustomerId): LocalBookingDraft {
  const now = new Date().toISOString();
  return {
    schemaVersion: BOOKING_DRAFT_SCHEMA_VERSION,
    ownerCustomerId,
    createdAt: now,
    updatedAt: now,
    expiresAt: new Date(Date.now() + LOCAL_DRAFT_TTL_MS).toISOString(),
    questionAnswers: {},
    media: [],
  };
}

/** Reads the persisted draft for `requestingCustomerId` only. Returns null
 * (never someone else's draft) if the stored draft belongs to a different
 * customer, is expired, or fails schema-version migration. */
export async function loadBookingDraft(requestingCustomerId: CustomerId): Promise<LocalBookingDraft | null> {
  const stored = await getLocalJSON<LocalBookingDraft>(storageKey(requestingCustomerId));
  if (!stored) return null;

  if (stored.schemaVersion !== BOOKING_DRAFT_SCHEMA_VERSION) {
    // No migration path defined yet for a hypothetical future version --
    // safe-discard rather than risk misinterpreting an incompatible shape.
    await removeLocalItem(storageKey(requestingCustomerId));
    return null;
  }
  if (stored.ownerCustomerId !== requestingCustomerId) {
    return null;
  }
  if (new Date(stored.expiresAt).getTime() <= Date.now()) {
    await removeLocalItem(storageKey(requestingCustomerId));
    return null;
  }
  return stored;
}

export async function saveBookingDraft(draft: LocalBookingDraft): Promise<void> {
  const updated: LocalBookingDraft = { ...draft, updatedAt: new Date().toISOString() };
  await setLocalJSON(storageKey(draft.ownerCustomerId), updated);
}

export async function discardBookingDraft(ownerCustomerId: CustomerId): Promise<void> {
  await removeLocalItem(storageKey(ownerCustomerId));
}
