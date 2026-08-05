import { AddressDto } from "../../api/contracts/addresses";

export function makeAddressDto(overrides: Partial<AddressDto> = {}): AddressDto {
  return {
    id: "address-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    label: "Home",
    line1: "221B Baker Street",
    line2: null,
    city: "Bengaluru",
    state: "Karnataka",
    zipcode: "560001",
    latitude: 12.9716,
    longitude: 77.5946,
    is_default: true,
    ...overrides,
  };
}
