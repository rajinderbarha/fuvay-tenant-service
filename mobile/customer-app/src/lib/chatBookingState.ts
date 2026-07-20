/**
 * Typed chat booking-state model — UX-06 Round 3.
 *
 * IMPORTANT design decision (read before changing): the DeepSeek chat reply is
 * free text. The client has no structured access to what the backend's tool
 * calls actually returned (the /v1/customer/ai-chat/sessions/*\/messages
 * response only exposes `tools_called` — an array of TOOL NAMES — and the
 * final synthesized `reply` string; it does NOT return the tools' raw JSON
 * results). Building a state machine that tries to parse canonical IDs out of
 * DeepSeek's natural-language reply would violate the hard rule "never let a
 * translated/free-text label become a database query value."
 *
 * So this state machine is instead driven by REAL, STRUCTURED backend calls
 * the UI makes directly (catalogApi.categories/categoryOfferings,
 * homeServiceDraftApi.*) whenever the customer makes a selection in the chat
 * screen's structured picker UI. Every field below is only ever set from an
 * actual typed API response, never invented or guessed, and the `id`/`slug`
 * fields are what get sent onward — never `name` (display-only, and the only
 * thing that would ever be translated for the selected chat language).
 */
import type { ServiceCategory, ServiceOffering, BookingDraft } from "./api";

export type ChatBookingStep =
  | "idle"
  | "category_selected"
  | "offering_selected"
  | "issue_collected"
  | "address_collected"
  | "serviceability_checked"
  | "price_estimated"
  | "reviewed"
  | "submitted";

export interface ChatBookingState {
  step: ChatBookingStep;
  aiSessionId: string | null;
  category: ServiceCategory | null;
  offering: ServiceOffering | null;
  issueDescription: string | null;
  addressLine: string | null;
  city: string | null;
  zipcode: string | null;
  draft: BookingDraft | null;
  serviceable: boolean | null;
  serviceabilityMessage: string | null;
  priceSnapshot: BookingDraft["price_snapshot"] | null;
  bookingNumber: string | null;
  jobNumber: string | null;
}

export function initialChatBookingState(aiSessionId: string | null = null): ChatBookingState {
  return {
    step: "idle",
    aiSessionId,
    category: null,
    offering: null,
    issueDescription: null,
    addressLine: null,
    city: null,
    zipcode: null,
    draft: null,
    serviceable: null,
    serviceabilityMessage: null,
    priceSnapshot: null,
    bookingNumber: null,
    jobNumber: null,
  };
}

export type ChatBookingAction =
  | { type: "SELECT_CATEGORY"; category: ServiceCategory }
  | { type: "SELECT_OFFERING"; offering: ServiceOffering }
  | { type: "SET_ISSUE"; issueDescription: string }
  | { type: "SET_ADDRESS"; addressLine: string; city: string; zipcode?: string }
  | { type: "DRAFT_STARTED"; draft: BookingDraft }
  | { type: "SERVICEABILITY_RESULT"; serviceable: boolean; message: string; draftStatus: string }
  | { type: "PRICE_RESULT"; priceSnapshot: BookingDraft["price_snapshot"] | null; draftStatus: string }
  | { type: "REVIEWED" }
  | { type: "SUBMITTED"; bookingNumber: string; jobNumber?: string }
  | { type: "RESET"; aiSessionId?: string | null };

// A pure reducer: every transition is driven by a real value from a real API
// response (the caller is responsible for only dispatching after an awaited,
// successful backend call — see DeepSeekChatScreen.tsx). No step here invents
// or advances state without a corresponding real payload.
export function chatBookingReducer(state: ChatBookingState, action: ChatBookingAction): ChatBookingState {
  switch (action.type) {
    case "SELECT_CATEGORY":
      return { ...state, category: action.category, offering: null, step: "category_selected" };
    case "SELECT_OFFERING":
      return { ...state, offering: action.offering, step: "offering_selected" };
    case "SET_ISSUE":
      return { ...state, issueDescription: action.issueDescription, step: "issue_collected" };
    case "SET_ADDRESS":
      return { ...state, addressLine: action.addressLine, city: action.city, zipcode: action.zipcode ?? null, step: "address_collected" };
    case "DRAFT_STARTED":
      return { ...state, draft: action.draft };
    case "SERVICEABILITY_RESULT":
      return {
        ...state,
        serviceable: action.serviceable,
        serviceabilityMessage: action.message,
        step: action.serviceable ? "serviceability_checked" : state.step,
      };
    case "PRICE_RESULT":
      return { ...state, priceSnapshot: action.priceSnapshot, step: "price_estimated" };
    case "REVIEWED":
      return { ...state, step: "reviewed" };
    case "SUBMITTED":
      return { ...state, step: "submitted", bookingNumber: action.bookingNumber, jobNumber: action.jobNumber ?? null };
    case "RESET":
      return initialChatBookingState(action.aiSessionId ?? state.aiSessionId);
    default:
      return state;
  }
}

/** Enforces "canonical ID, never display label" at the type level — callers
 * must pass the real category/offering object from a catalog API response;
 * this helper is what actually gets sent onward to homeServiceDraftApi.start. */
export function canonicalSlugsFor(state: ChatBookingState): { categorySlug: string; offeringSlug: string } | null {
  if (!state.category || !state.offering) return null;
  return { categorySlug: state.category.slug, offeringSlug: state.offering.slug };
}
