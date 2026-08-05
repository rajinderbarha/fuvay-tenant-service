import { adaptCustomerSavedAddress } from "../customerAddresses";
import { CustomerAddressDto } from "../../contracts/customerAddresses";

function dto(overrides: Partial<CustomerAddressDto> = {}): CustomerAddressDto {
  return {
    id: "a-1", customer_id: "c-1", tenant_id: null, label: "Home", name: "Rajinder Singh", phone: "+919900024102",
    address_line_1: "House 24, Model Town", address_line_2: null, landmark: null,
    city: "Ludhiana", district: null, state: "Punjab", country: "India", zipcode: "141002",
    latitude: null, longitude: null, is_default: true, is_active: true,
    created_at: "2026-01-01T00:00:00Z", updated_at: null,
    ...overrides,
  };
}

describe("adaptCustomerSavedAddress", () => {
  it("maps the real dedicated `label` column and `name` (recipient) separately -- migration 223 closed the earlier single-column gap", () => {
    const address = adaptCustomerSavedAddress(dto());
    expect(address.label).toBe("Home");
    expect(address.recipientName).toBe("Rajinder Singh");
  });

  it("preserves the backend address id and default flag exactly", () => {
    const address = adaptCustomerSavedAddress(dto({ id: "a-99", is_default: false }));
    expect(address.id).toBe("a-99");
    expect(address.isDefault).toBe(false);
  });

  it("adapts every real address field without inventing coordinates/serviceability", () => {
    const address = adaptCustomerSavedAddress(dto());
    expect(address).not.toHaveProperty("serviceable");
    expect(address).not.toHaveProperty("latitude");
  });
});
