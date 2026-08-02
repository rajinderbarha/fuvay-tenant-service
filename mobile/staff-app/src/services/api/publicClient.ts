import { performRequest } from "./apiClient";
import { buildPublicHeaders } from "./requestHeaders";
import { ApiRequestOptions, ApiResult } from "./types";

/**
 * Public (unauthenticated) request path (Phase F spec section 4): health
 * checks, login, OTP send/verify, MFA verify, password reset, refresh.
 * Never attaches an Authorization header -- authenticatedClient is the
 * only path that does.
 */
export function publicRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<ApiResult<T>> {
  return performRequest<T>({
    path,
    headers: buildPublicHeaders(),
    options,
    context: "public",
  });
}
