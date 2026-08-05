import { parseServiceBookingDto, adaptServiceBooking } from "../adapters/booking";
import { makeServiceBookingDto } from "../../testing/fixtures";
import { UnknownStatusError } from "../../domain/errors";

describe("ServiceBooking adapter", () => {
  it("adapts a well-formed DTO, extracting the agreed price from price_snapshot", () => {
    const dto = parseServiceBookingDto(makeServiceBookingDto());
    const booking = adaptServiceBooking(dto);
    expect(booking.agreedPrice).toEqual({ minorUnits: 89900, currency: "INR" });
    expect(booking.provider?.providerName).toBe("QuickFix Services");
  });

  it("strips provider fields down to the customer-safe subset only", () => {
    const dto = parseServiceBookingDto(
      makeServiceBookingDto({
        provider_snapshot: { provider_name: "X", rating: 4, public_badges: [] },
      }),
    );
    const booking = adaptServiceBooking(dto);
    expect(Object.keys(booking.provider ?? {})).toEqual(["providerName", "rating", "publicBadges"]);
  });

  it("returns null agreedPrice when price_snapshot has neither known key", () => {
    const dto = parseServiceBookingDto(makeServiceBookingDto({ price_snapshot: { unrelated: true } }));
    const booking = adaptServiceBooking(dto);
    expect(booking.agreedPrice).toBeNull();
  });

  it("rejects an unknown booking status", () => {
    const dto = parseServiceBookingDto(makeServiceBookingDto({ status: "levitating" }));
    expect(() => adaptServiceBooking(dto)).toThrow(UnknownStatusError);
  });
});
