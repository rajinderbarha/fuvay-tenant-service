import { loadingDraft, creatingDraft, draftLoaded, savingDraft, saveFailed, loadFailed, isMutable, initialDraftSessionState } from "../draft-session";
import { parseBookingDraft } from "../draft-schema";

const baseDraft = {
  id: "draft-1",
  customer_id: "cust-1",
  guest_session_id: null,
  ai_session_id: null,
  category_id: "cat-1",
  offering_id: "svc-1",
  selected_tenant_id: null,
  status: "draft",
  customer_name: null,
  customer_phone: null,
  address_id: null,
  city: null,
  zipcode: null,
  issue_summary: null,
  offering_type_id: null,
  brand_id: null,
  photo_urls: [],
  preferred_date: null,
  preferred_time_window: null,
  serviceability_status: "pending",
  price_status: "pending",
  provider_match_status: "pending",
  failure_code: null,
  failure_message: null,
  expires_at: "2099-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function draft(overrides: Partial<typeof baseDraft> = {}) {
  return parseBookingDraft({ ...baseDraft, ...overrides })!;
}

describe("draft session transitions", () => {
  it("starts IDLE", () => {
    expect(initialDraftSessionState.status).toBe("IDLE");
  });

  it("loadingDraft/creatingDraft set the right status with no draft yet", () => {
    expect(loadingDraft().status).toBe("LOADING");
    expect(creatingDraft().status).toBe("CREATING");
  });

  it("draftLoaded resolves to READY for a normal in-progress draft", () => {
    const state = draftLoaded(draft());
    expect(state.status).toBe("READY");
    expect(isMutable(state)).toBe(true);
  });

  it("draftLoaded fails closed to EXPIRED for a status='expired' draft", () => {
    const state = draftLoaded(draft({ status: "expired" }));
    expect(state.status).toBe("EXPIRED");
    expect(isMutable(state)).toBe(false);
  });

  it("draftLoaded fails closed to EXPIRED when past expires_at even if status has not flipped yet", () => {
    const state = draftLoaded(draft({ expires_at: "2020-01-01T00:00:00Z" }));
    expect(state.status).toBe("EXPIRED");
  });

  it("draftLoaded resolves to CANCELLED for a cancelled draft", () => {
    const state = draftLoaded(draft({ status: "cancelled" }));
    expect(state.status).toBe("CANCELLED");
    expect(isMutable(state)).toBe(false);
  });

  it("savingDraft only transitions from READY", () => {
    const ready = draftLoaded(draft());
    const saving = savingDraft(ready);
    expect(saving.status).toBe("SAVING");

    const notReady = loadingDraft();
    expect(savingDraft(notReady)).toBe(notReady);
  });

  it("saveFailed preserves the draft and records the error", () => {
    const ready = draftLoaded(draft());
    const failed = saveFailed(ready, "network_error", "offline");
    expect(failed.status).toBe("SAVE_FAILED");
    expect(failed.draft).toBe(ready.draft);
    expect(failed.error).toEqual({ category: "network_error", message: "offline" });
  });

  it("loadFailed produces an ERROR state with no draft", () => {
    const state = loadFailed("not_found", "Draft not found.");
    expect(state.status).toBe("ERROR");
    expect(state.draft).toBeNull();
  });

  it("isMutable is false for any terminal-status draft, even in READY-shaped state", () => {
    // draftLoaded itself never leaves a terminal draft in READY, but isMutable is defensive on its own.
    const state = { status: "READY" as const, draft: draft({ status: "confirmed" }), error: null };
    expect(isMutable(state)).toBe(false);
  });
});
