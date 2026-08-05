import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { addressListResponseSchema, deleteAddressResponseSchema, customerAddressDtoSchema } from "../contracts/customerAddresses";
import { AddressCreatePayload, AddressUpdatePayload } from "../../domain/addressForm";

const BASE = "/v1/customers/me/addresses";

export async function listMyAddresses() {
  const res = await authenticatedRequest({ method: "GET", path: BASE });
  return parseApiSuccess(res.json, addressListResponseSchema);
}

export async function getMyAddress(addressId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/${addressId}` });
  return parseApiSuccess(res.json, customerAddressDtoSchema);
}

export async function createMyAddress(payload: AddressCreatePayload) {
  const res = await authenticatedRequest({ method: "POST", path: BASE, body: payload });
  return parseApiSuccess(res.json, customerAddressDtoSchema);
}

export async function updateMyAddress(addressId: string, payload: AddressUpdatePayload) {
  const res = await authenticatedRequest({ method: "PUT", path: `${BASE}/${addressId}`, body: payload });
  return parseApiSuccess(res.json, customerAddressDtoSchema);
}

export async function deleteMyAddress(addressId: string) {
  const res = await authenticatedRequest({ method: "DELETE", path: `${BASE}/${addressId}` });
  return parseApiSuccess(res.json, deleteAddressResponseSchema);
}

export async function setDefaultAddress(addressId: string) {
  const res = await authenticatedRequest({ method: "POST", path: `${BASE}/${addressId}/set-default` });
  return parseApiSuccess(res.json, customerAddressDtoSchema);
}
