import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { MobileHomeDTO, AvailabilityState, AvailabilityDTO } from "./types";

/** GET /v1/staff/mobile-home (Phase H backend addition, app/engines/execution/mobile_home_router.py). */
export function getMobileHome(signal?: AbortSignal): Promise<ApiResult<MobileHomeDTO>> {
  return authenticatedRequest<MobileHomeDTO>("/v1/staff/mobile-home", { method: "GET", signal });
}

/** PUT /v1/staff/me/availability -- canonical, backend-authoritative
 * presence state (migration 209). Never a local-only toggle. */
export function updateAvailability(state: AvailabilityState): Promise<ApiResult<AvailabilityDTO>> {
  return authenticatedRequest<AvailabilityDTO>("/v1/staff/me/availability", {
    method: "PUT",
    body: { state },
    unsafeToRetry: true, // a mutation -- never silently auto-retried
  });
}
