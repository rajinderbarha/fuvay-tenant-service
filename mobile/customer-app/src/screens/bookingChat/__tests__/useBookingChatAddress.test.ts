import { renderHook, waitFor, act } from "@testing-library/react-native";
import { useBookingChatAddress } from "../useBookingChatAddress";
import * as addressesApi from "../../../api/customerAddresses/customerAddressesApi";
import * as reviewApi from "../../../api/bookingReview/bookingReviewApi";

jest.mock("../../../api/customerAddresses/customerAddressesApi");
jest.mock("../../../api/bookingReview/bookingReviewApi");

function addressDto(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "addr-1", customer_id: "cust-1", tenant_id: null, label: "Home", name: null, phone: null,
    address_line_1: "1 Main St", address_line_2: null, landmark: null, city: "Ludhiana",
    district: null, state: "Punjab", country: "India", postal_code: "141002", zipcode: "141002",
    is_default: true, created_at: "2026-08-01T00:00:00Z", updated_at: null,
    ...overrides,
  };
}

describe("useBookingChatAddress -- zipcode lock", () => {
  afterEach(() => jest.clearAllMocks());

  it("refuses to create an address whose zipcode differs from the request's own zip, without ever calling the backend", async () => {
    // The backend's own update_draft_fields OVERWRITES draft.zipcode from
    // whatever address_id it's given and does not itself reject a
    // mismatched one -- the provider was already matched against the
    // entry zip, so this is the one client-side gate standing between a
    // typo/bypass and a silently wrong provider/zip pairing.
    const { result } = renderHook(() => useBookingChatAddress("draft-1", "141002"));

    await act(async () => {
      await result.current.createNew({
        label: "Home", name: null, address_line_1: "1 Main St", address_line_2: null, landmark: null,
        city: "Ludhiana", state: "Punjab", zipcode: "999999", is_default: false,
      });
    });

    expect(addressesApi.createMyAddress).not.toHaveBeenCalled();
    expect(reviewApi.setDraftAddress).not.toHaveBeenCalled();
    expect(result.current.error).toMatch(/same ZIP/i);
    expect(result.current.resolvedAddressId).toBeNull();
  });

  it("creates and attaches an address whose zip genuinely matches", async () => {
    (addressesApi.createMyAddress as jest.Mock).mockResolvedValue({ data: addressDto() });
    (reviewApi.setDraftAddress as jest.Mock).mockResolvedValue({ data: {} });

    const { result } = renderHook(() => useBookingChatAddress("draft-1", "141002"));
    await act(async () => {
      await result.current.createNew({
        label: "Home", name: null, address_line_1: "1 Main St", address_line_2: null, landmark: null,
        city: "Ludhiana", state: "Punjab", zipcode: "141002", is_default: false,
      });
    });

    expect(addressesApi.createMyAddress).toHaveBeenCalledWith(expect.objectContaining({ zipcode: "141002" }));
    expect(reviewApi.setDraftAddress).toHaveBeenCalledWith("draft-1", "addr-1");
    expect(result.current.resolvedAddressId).toBe("addr-1");
    expect(result.current.error).toBeNull();
  });

  it("attaches an existing saved address without re-validating its zip client-side (the picker already filtered it)", async () => {
    (reviewApi.setDraftAddress as jest.Mock).mockResolvedValue({ data: {} });
    const { result } = renderHook(() => useBookingChatAddress("draft-1", "141002"));
    await act(async () => {
      await result.current.pickExisting("addr-2");
    });
    expect(reviewApi.setDraftAddress).toHaveBeenCalledWith("draft-1", "addr-2");
    expect(result.current.resolvedAddressId).toBe("addr-2");
  });

  it("surfaces a real backend failure rather than silently resolving the address", async () => {
    const { DomainError } = jest.requireActual("../../../domain/errors");
    (reviewApi.setDraftAddress as jest.Mock).mockRejectedValue(
      new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "Address not found." }),
    );
    const { result } = renderHook(() => useBookingChatAddress("draft-1", "141002"));
    await act(async () => {
      await result.current.pickExisting("addr-missing");
    });
    expect(result.current.resolvedAddressId).toBeNull();
    expect(result.current.error).toBe("Address not found.");
  });
});
