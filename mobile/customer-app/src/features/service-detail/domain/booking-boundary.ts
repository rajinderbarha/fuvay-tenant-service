export type BookingBoundaryOutcome = "AVAILABLE" | "AUTH_REQUIRED";

export interface BookingBoundaryContext {
  authenticated: boolean;
}

/**
 * Mirrors the real gate on the `bookingAssistant` route
 * (navigation/route-registry.ts): `access: "authenticated"`. CUSTOMER-L5-05
 * implemented the real diagnostic assistant, so `productionEnabled` is now
 * `true` for that route — this evaluator no longer has a dev-build gate to
 * mirror (see CUSTOMER-L5-04's original `NOT_YET_AVAILABLE` outcome, removed
 * this sprint). Fails closed: any ambiguous input resolves to
 * `AUTH_REQUIRED`, never `AVAILABLE`.
 */
export function evaluateBookingBoundary(context: BookingBoundaryContext): BookingBoundaryOutcome {
  return context.authenticated ? "AVAILABLE" : "AUTH_REQUIRED";
}
