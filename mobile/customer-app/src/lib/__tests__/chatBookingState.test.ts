import {
  chatBookingReducer, initialChatBookingState, canonicalSlugsFor,
  type ChatBookingState,
} from "../chatBookingState";
import type { ServiceCategory, ServiceOffering, BookingDraft } from "../api";

const CATEGORY: ServiceCategory = { id:"cat-uuid-1", slug:"ac-repair", name:"AC & Cooling (Hindi label swapped for test)" };
const OFFERING: ServiceOffering = { id:"off-uuid-1", slug:"ac-gas-refill", name:"AC Gas Refill" };
const DRAFT: BookingDraft = { id:"draft-uuid-1", status:"created" };

describe("chatBookingState reducer (Round 3 typed booking-state model)", () => {
  it("starts idle with no selections", () => {
    const state = initialChatBookingState("session-1");
    expect(state.step).toBe("idle");
    expect(state.aiSessionId).toBe("session-1");
    expect(state.category).toBeNull();
  });

  it("SELECT_CATEGORY stores the real category object and clears any prior offering", () => {
    let state = initialChatBookingState();
    state = chatBookingReducer(state, { type:"SELECT_OFFERING", offering: OFFERING });
    state = chatBookingReducer(state, { type:"SELECT_CATEGORY", category: CATEGORY });
    expect(state.category).toEqual(CATEGORY);
    expect(state.offering).toBeNull();
    expect(state.step).toBe("category_selected");
  });

  it("SELECT_OFFERING stores the real offering object", () => {
    let state = initialChatBookingState();
    state = chatBookingReducer(state, { type:"SELECT_CATEGORY", category: CATEGORY });
    state = chatBookingReducer(state, { type:"SELECT_OFFERING", offering: OFFERING });
    expect(state.offering).toEqual(OFFERING);
    expect(state.step).toBe("offering_selected");
  });

  it("walks the full real-data-driven sequence through to submitted", () => {
    let state = initialChatBookingState("session-1");
    state = chatBookingReducer(state, { type:"SELECT_CATEGORY", category: CATEGORY });
    state = chatBookingReducer(state, { type:"SELECT_OFFERING", offering: OFFERING });
    state = chatBookingReducer(state, { type:"SET_ISSUE", issueDescription:"AC not cooling" });
    state = chatBookingReducer(state, { type:"SET_ADDRESS", addressLine:"12 MG Road", city:"Bengaluru" });
    state = chatBookingReducer(state, { type:"DRAFT_STARTED", draft: DRAFT });
    state = chatBookingReducer(state, { type:"SERVICEABILITY_RESULT", serviceable:true, message:"We serve this area.", draftStatus:"serviceability_checked" });
    expect(state.step).toBe("serviceability_checked");
    state = chatBookingReducer(state, { type:"PRICE_RESULT", priceSnapshot:{ display_price:"₹499", final_price:499, currency:"INR" }, draftStatus:"price_estimated" });
    expect(state.step).toBe("price_estimated");
    expect(state.priceSnapshot?.display_price).toBe("₹499");
    state = chatBookingReducer(state, { type:"REVIEWED" });
    expect(state.step).toBe("reviewed");
    state = chatBookingReducer(state, { type:"SUBMITTED", bookingNumber:"BK-1001", jobNumber:"JB-2002" });
    expect(state.step).toBe("submitted");
    expect(state.bookingNumber).toBe("BK-1001");
    expect(state.jobNumber).toBe("JB-2002");
  });

  it("SERVICEABILITY_RESULT with serviceable:false does not advance the step (no false-positive progression)", () => {
    let state = initialChatBookingState();
    state = chatBookingReducer(state, { type:"SELECT_CATEGORY", category: CATEGORY });
    const before = state.step;
    state = chatBookingReducer(state, { type:"SERVICEABILITY_RESULT", serviceable:false, message:"Not serviceable in this area yet.", draftStatus:"not_serviceable" });
    expect(state.step).toBe(before);
    expect(state.serviceable).toBe(false);
    expect(state.serviceabilityMessage).toBe("Not serviceable in this area yet.");
  });

  it("RESET returns to idle but can carry forward the AI session id", () => {
    let state = initialChatBookingState("session-1");
    state = chatBookingReducer(state, { type:"SELECT_CATEGORY", category: CATEGORY });
    state = chatBookingReducer(state, { type:"RESET" });
    expect(state.step).toBe("idle");
    expect(state.category).toBeNull();
    expect(state.aiSessionId).toBe("session-1");
  });
});

describe("canonicalSlugsFor — enforces real backend slug/id, never a display label", () => {
  it("returns null until both category and offering are selected", () => {
    expect(canonicalSlugsFor(initialChatBookingState())).toBeNull();
    const withCategory: ChatBookingState = { ...initialChatBookingState(), category: CATEGORY };
    expect(canonicalSlugsFor(withCategory)).toBeNull();
  });

  it("returns the real category/offering slugs, never the translatable display name", () => {
    const state: ChatBookingState = { ...initialChatBookingState(), category: CATEGORY, offering: OFFERING };
    const slugs = canonicalSlugsFor(state);
    expect(slugs).toEqual({ categorySlug:"ac-repair", offeringSlug:"ac-gas-refill" });
    // Explicit negative assertion: the canonical value must never equal or
    // contain the (possibly translated/display) name field.
    expect(slugs?.categorySlug).not.toBe(CATEGORY.name);
    expect(slugs?.offeringSlug).not.toBe(OFFERING.name);
  });
});
