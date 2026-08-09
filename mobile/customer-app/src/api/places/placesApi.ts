import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  placeAutocompleteResponseSchema, placeDetailResponseSchema,
} from "../contracts/places";

const BASE = "/v1/customer/places";

/**
 * Address autocomplete, PROXIED through our own backend.
 *
 * The Google key deliberately never reaches this app: a key inside a mobile bundle
 * is extractable by anyone who downloads it, and Places is billed per request. The
 * proxy also means the key can be rotated without an app release.
 *
 * `sessionToken` is passed on both calls of a lookup because Google bills an
 * autocomplete SESSION rather than each keystroke -- dropping it turns one address
 * entry into a dozen billable requests.
 */
export async function suggestAddresses(query: string, sessionToken: string) {
  const res = await authenticatedRequest({
    method: "GET",
    path: `${BASE}/autocomplete?q=${encodeURIComponent(query)}&session_token=${encodeURIComponent(sessionToken)}`,
  });
  return parseApiSuccess(res.json, placeAutocompleteResponseSchema);
}

export async function resolveAddress(placeId: string, sessionToken: string) {
  const res = await authenticatedRequest({
    method: "GET",
    path: `${BASE}/${encodeURIComponent(placeId)}?session_token=${encodeURIComponent(sessionToken)}`,
  });
  return parseApiSuccess(res.json, placeDetailResponseSchema);
}
