import { adaptCustomerSavedAddress } from "../customerAddresses";
import { CustomerAddressDto, addressListResponseSchema } from "../../contracts/customerAddresses";

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

describe("the saved-address list contract", () => {
  it("accepts the string-encoded coordinates the API really sends", () => {
    // Real bug this pins: the schema said `z.number()`, and the API sends a NUMERIC
    // column as `"30.6861187"` so a Decimal never loses precision to a float. Every
    // address had null coordinates until the Google Places lookup started saving
    // real ones -- null satisfies a nullable number, so the whole saved-address
    // screen broke the moment real data arrived.
    const parsed = addressListResponseSchema.safeParse({
      addresses: [{
        id: "a-1", customer_id: "c-1", tenant_id: null, label: "Home", name: null, phone: null,
        address_line_1: "#5, bassi pathana", address_line_2: null, landmark: "New sarian",
        city: "Bassi Pathana", district: null, state: "Punjab", country: "India",
        zipcode: "140412",
        latitude: "30.6861187", longitude: "76.4042404",
        is_default: true, is_active: true,
        created_at: "2026-08-01T00:00:00Z", updated_at: null,
      }],
      total: 1,
    });

    expect(parsed.success).toBe(true);
    if (!parsed.success) return;
    expect(parsed.data.addresses[0].latitude).toBeCloseTo(30.6861187);
    expect(parsed.data.addresses[0].longitude).toBeCloseTo(76.4042404);
  });

  it("keeps null coordinates as null rather than zero", () => {
    // 0,0 is a real place in the Gulf of Guinea. An address we have no point for must
    // not claim one.
    const parsed = addressListResponseSchema.parse({ addresses: [dto()], total: 1 });
    expect(parsed.addresses[0].latitude).toBeNull();
  });

  it("reduces an unparseable coordinate to null instead of NaN", () => {
    const parsed = addressListResponseSchema.parse({
      addresses: [{ ...dto(), latitude: "not-a-number" }],
      total: 1,
    });
    expect(parsed.addresses[0].latitude).toBeNull();
  });
});
