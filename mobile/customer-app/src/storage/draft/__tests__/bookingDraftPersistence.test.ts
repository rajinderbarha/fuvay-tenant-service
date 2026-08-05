import { createEmptyDraft, loadBookingDraft, saveBookingDraft, discardBookingDraft, BOOKING_DRAFT_SCHEMA_VERSION } from "../bookingDraftPersistence";
import { asCustomerId } from "../../../domain/ids";
import * as localStorage from "../../localStorage";

const customerA = asCustomerId("customer-a");
const customerB = asCustomerId("customer-b");

describe("booking draft persistence", () => {
  afterEach(async () => {
    await discardBookingDraft(customerA);
    await discardBookingDraft(customerB);
  });

  it("round-trips a saved draft for its owner", async () => {
    const draft = createEmptyDraft(customerA);
    await saveBookingDraft({ ...draft, zipcode: "560001" });
    const loaded = await loadBookingDraft(customerA);
    expect(loaded?.zipcode).toBe("560001");
    expect(loaded?.schemaVersion).toBe(BOOKING_DRAFT_SCHEMA_VERSION);
  });

  it("never lets one customer load another customer's draft", async () => {
    const draftA = createEmptyDraft(customerA);
    await saveBookingDraft({ ...draftA, notes: "customer A's private note" });
    const loadedByB = await loadBookingDraft(customerB);
    expect(loadedByB).toBeNull();
  });

  it("discards a draft past its expiry rather than returning stale data", async () => {
    const draft = createEmptyDraft(customerA);
    await saveBookingDraft({ ...draft, expiresAt: new Date(Date.now() - 1000).toISOString() });
    const loaded = await loadBookingDraft(customerA);
    expect(loaded).toBeNull();
  });

  it("safe-discards a draft with an incompatible schema version instead of misinterpreting it", async () => {
    const draft = createEmptyDraft(customerA);
    // Simulate a future incompatible version having been written by a
    // newer app build.
    await localStorage.setLocalJSON(`customer_app_booking_draft_v1_${customerA}`, {
      ...draft,
      schemaVersion: 999,
    });
    const loaded = await loadBookingDraft(customerA);
    expect(loaded).toBeNull();
  });

  it("starts with an empty media list and question-answer map", () => {
    const draft = createEmptyDraft(customerA);
    expect(draft.media).toEqual([]);
    expect(draft.questionAnswers).toEqual({});
  });
});
