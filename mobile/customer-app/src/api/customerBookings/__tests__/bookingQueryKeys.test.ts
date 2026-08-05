import { bookingQueryKeys } from "../bookingQueryKeys";

describe("bookingQueryKeys", () => {
  it("derives detail keys under the shared 'customer','bookings','detail' prefix", () => {
    expect(bookingQueryKeys.detail("b-1")).toEqual(["customer", "bookings", "detail", "b-1"]);
  });

  it("derives list keys under the shared 'customer','bookings','list' prefix, including filters", () => {
    expect(bookingQueryKeys.list({ status: "pending_assignment" })).toEqual([
      "customer", "bookings", "list", { status: "pending_assignment" },
    ]);
  });

  it("lists() and details() both start with all() so a broad invalidation of 'all' catches both", () => {
    expect(bookingQueryKeys.lists().slice(0, bookingQueryKeys.all.length)).toEqual([...bookingQueryKeys.all]);
    expect(bookingQueryKeys.details().slice(0, bookingQueryKeys.all.length)).toEqual([...bookingQueryKeys.all]);
  });

  it("two different booking IDs never collide", () => {
    expect(bookingQueryKeys.detail("b-1")).not.toEqual(bookingQueryKeys.detail("b-2"));
  });
});
