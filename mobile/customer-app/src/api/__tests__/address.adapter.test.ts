import { parseAddressDto, adaptAddress } from "../adapters/addresses";
import { makeAddressDto } from "../../testing/fixtures";

describe("Address adapter", () => {
  it("adapts coordinates as a distinct sub-shape when both lat/lng present", () => {
    const dto = parseAddressDto(makeAddressDto());
    const address = adaptAddress(dto);
    expect(address.coordinates).toEqual({ latitude: 12.9716, longitude: 77.5946 });
  });

  it("returns null coordinates when either lat or lng is missing", () => {
    const dto = parseAddressDto(makeAddressDto({ latitude: null, longitude: null }));
    const address = adaptAddress(dto);
    expect(address.coordinates).toBeNull();
  });

  it("defaults isDefault to false when omitted", () => {
    const dto = parseAddressDto(makeAddressDto({ is_default: undefined }));
    const address = adaptAddress(dto);
    expect(address.isDefault).toBe(false);
  });
});
