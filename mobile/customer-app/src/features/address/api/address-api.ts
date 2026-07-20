import { apiClient } from "../../../api/api-client";

/**
 * Real backend paths verified against
 * app/engines/serviceability/router.py — see
 * CUSTOMER-L5-07-contract-matrix.md. Deliberately not built on
 * `src/lib/api.ts`'s legacy `addressApi`, which targets a nonexistent
 * endpoint (`/v1/commerce/customers/{cid}/addresses`) with the wrong field
 * shape — see CUSTOMER-L5-07-baseline-verification.md.
 */
export interface AddressPayload {
  name?: string;
  phone?: string;
  address_line_1: string;
  address_line_2?: string;
  landmark?: string;
  city: string;
  district?: string;
  state: string;
  country?: string;
  zipcode: string;
  latitude?: number;
  longitude?: number;
  is_default?: boolean;
}

export const addressApi = {
  listAddresses: (options: { signal?: AbortSignal } = {}) => apiClient.get<unknown>("/v1/customers/me/addresses", { signal: options.signal }),

  getAddress: (addressId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customers/me/addresses/${encodeURIComponent(addressId)}`, { signal: options.signal }),

  createAddress: (payload: AddressPayload, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>("/v1/customers/me/addresses", payload, { signal: options.signal }),

  updateAddress: (addressId: string, payload: Partial<AddressPayload>, options: { signal?: AbortSignal } = {}) =>
    apiClient.put<unknown>(`/v1/customers/me/addresses/${encodeURIComponent(addressId)}`, payload, { signal: options.signal }),

  deleteAddress: (addressId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.delete<unknown>(`/v1/customers/me/addresses/${encodeURIComponent(addressId)}`, { signal: options.signal }),

  setDefaultAddress: (addressId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(`/v1/customers/me/addresses/${encodeURIComponent(addressId)}/set-default`, undefined, { signal: options.signal }),
};
