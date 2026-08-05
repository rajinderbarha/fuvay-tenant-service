import { queryKeys } from "../queryKeys";
import { asServiceBookingId, asServiceJobId, asAddressId, asCustomerId } from "../../domain/ids";

describe("queryKeys", () => {
  it("produces distinct keys for different domains touching similar identifiers", () => {
    const bookingId = asServiceBookingId("shared-id");
    const jobId = asServiceJobId("shared-id");
    const bookingKey = queryKeys.bookings.detail(bookingId);
    const jobKey = queryKeys.serviceJobs.detail(jobId);
    expect(bookingKey).not.toEqual(jobKey);
    expect(bookingKey[0]).toBe("bookings");
    expect(jobKey[0]).toBe("serviceJobs");
  });

  it("includes filters that materially change the result", () => {
    const page1 = queryKeys.bookings.list({ status: "scheduled", page: 1 });
    const page2 = queryKeys.bookings.list({ status: "scheduled", page: 2 });
    const otherStatus = queryKeys.bookings.list({ status: "cancelled", page: 1 });
    expect(page1).not.toEqual(page2);
    expect(page1).not.toEqual(otherStatus);
  });

  it("scopes address keys by customer id to avoid cross-customer cache collisions", () => {
    const a = queryKeys.addresses.list(asCustomerId("customer-a"));
    const b = queryKeys.addresses.list(asCustomerId("customer-b"));
    expect(a).not.toEqual(b);
  });

  it("never embeds anything that looks like a bearer token", () => {
    const key = queryKeys.addresses.detail(asAddressId("addr-1"));
    const serialized = JSON.stringify(key);
    expect(serialized.toLowerCase()).not.toContain("bearer");
    expect(serialized.toLowerCase()).not.toContain("token");
  });
});
