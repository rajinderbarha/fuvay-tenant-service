import { PrivacyCapabilities } from "./privacyData";

/**
 * Derived from confirmed real routes in `app/engines/compliance/
 * customer_router.py` (audited this phase):
 * - canRequestExport/canRequestErasure: `POST /v1/me/compliance/requests`
 *   with `request_type` in the real allowed set.
 * - canRequestCorrection: routes to the existing Personal Details screen
 *   (no second profile-edit surface) -- always true, that screen exists.
 * - canManageConsent: `GET /v1/me/compliance/consents` +
 *   `POST /v1/me/compliance/consents/{type}/withdraw` -- real.
 * - canViewRequestHistory/canCancelRequest: `GET .../requests` (paginated)
 *   and `POST .../requests/{id}/cancel` -- both real.
 * - canDownloadExport: `GET /v1/me/compliance/exports/{id}/download` is a
 *   real, ownership-checked, rate-limited customer endpoint -- shown as
 *   available, though its underlying `download_url` is a disclosed
 *   backend limitation (see final report), not something this app can
 *   fix from the client.
 */
export function resolvePrivacyCapabilities(): PrivacyCapabilities {
  return {
    canRequestExport: true,
    canRequestErasure: true,
    canRequestCorrection: true,
    canManageConsent: true,
    canViewRequestHistory: true,
    canCancelRequest: true,
    canDownloadExport: true,
  };
}
