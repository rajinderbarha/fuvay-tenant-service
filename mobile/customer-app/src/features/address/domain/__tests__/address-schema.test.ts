import { parseAddress, parseAddressList, parseDeleteAddressResponse } from "../address-schema";

const validAddress = {
  id: "addr-1",
  customer_id: "cust-1",
  tenant_id: null,
  name: "Ravi Kumar",
  phone: "9876543210",
  address_line_1: "12 MG Road",
  address_line_2: null,
  landmark: "Near City Mall",
  city: "Bengaluru",
  district: "Bengaluru Urban",
  state: "Karnataka",
  country: "India",
  zipcode: "560001",
  latitude: 12.9716,
  longitude: 77.5946,
  is_default: true,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("parseAddress", () => {
  it("accepts a well-formed real-shaped address", () => {
    expect(parseAddress(validAddress)).toEqual(validAddress);
  });

  it("rejects a payload missing a required field", () => {
    const { address_line_1, ...withoutLine1 } = validAddress;
    void address_line_1;
    expect(parseAddress(withoutLine1)).toBeNull();
  });

  it("accepts null latitude/longitude (address without geocoded coordinates)", () => {
    const parsed = parseAddress({ ...validAddress, latitude: null, longitude: null });
    expect(parsed?.latitude).toBeNull();
  });

  it("rejects a malformed payload without throwing", () => {
    expect(parseAddress(null)).toBeNull();
    expect(parseAddress("not an object")).toBeNull();
  });
});

describe("parseAddressList", () => {
  it("accepts a well-formed list envelope", () => {
    const result = parseAddressList({ addresses: [validAddress], total: 1 });
    expect(result?.addresses).toHaveLength(1);
    expect(result?.droppedCount).toBe(0);
  });

  it("drops an individually-invalid address without failing the whole list", () => {
    const { city, ...invalid } = validAddress;
    void city;
    const result = parseAddressList({ addresses: [validAddress, invalid], total: 2 });
    expect(result?.addresses).toHaveLength(1);
    expect(result?.droppedCount).toBe(1);
  });

  it("handles an empty list", () => {
    const result = parseAddressList({ addresses: [], total: 0 });
    expect(result?.addresses).toHaveLength(0);
  });
});

describe("parseDeleteAddressResponse", () => {
  it("accepts the real {address_id, deleted} shape", () => {
    expect(parseDeleteAddressResponse({ address_id: "addr-1", deleted: true })).toEqual({ addressId: "addr-1", deleted: true });
  });
});
