export interface BookingConfirmationResult {
  bookingId: string;
  bookingNumber: string;
  /** True when this response came from the idempotency lock (a duplicate
   * confirm attempt), not a fresh creation -- surfaced only for telemetry,
   * never shown differently to the customer (spec: exactly one booking). */
  idempotent: boolean;
}
