import { ENV } from "../../config/environment";
import { getAccessToken } from "../auth/tokenCoordinator";
import { ApiResult } from "../api/types";
import { safeParseJson, isSuccessEnvelope, isProblemDetail } from "../api/responseParser";
import { mapProblemDetail, mapNetworkFailure, mapUnknownFailure } from "../api/errorMapper";

export interface UploadedMediaAsset {
  id: string;
  content_type?: string;
  size_bytes?: number;
}

/**
 * Evidence photo upload for checklist items (Phase K). Deliberately its own
 * minimal client rather than a change to authenticatedRequest -- that
 * shared client always JSON-encodes the body (services/api/apiClient.ts),
 * and widening it for one multipart caller would touch every existing
 * consumer. Still routes only through the Phase F token accessor
 * (getAccessToken) -- never reads SecureStore directly.
 */
export async function uploadChecklistEvidence(
  jobId: string,
  fileUri: string,
  fileName: string,
  mimeType: string,
): Promise<ApiResult<UploadedMediaAsset>> {
  return _upload(fileUri, fileName, mimeType, "checklist_photo", "service_job", jobId);
}

/** Personal document upload (Phase R) -- owner is the technician's own
 * user identity, never a job. Reuses the existing "provider_document"
 * media context (already validated server-side for PDF/image, 10MB) --
 * never a second storage system or an unregistered context. */
export async function uploadStaffDocument(
  fileUri: string, fileName: string, mimeType: string, ownerUserId: string,
): Promise<ApiResult<UploadedMediaAsset>> {
  return _upload(fileUri, fileName, mimeType, "provider_document", "user", ownerUserId);
}

/** Profile photo upload (Phase R) -- calls the dedicated POST
 * /v1/me/profile-photo endpoint (app/engines/media/new_router.py), which
 * both stores the image under the correct role-specific media context
 * ("staff_profile_photo" for technicians) AND writes User.avatar_url +
 * profile_photo_media_id server-side in one step -- no separate "update
 * avatar_url" call needed afterward. */
export async function uploadProfilePhoto(
  fileUri: string, fileName: string, mimeType: string,
): Promise<ApiResult<{ id: string; preview_url?: string; public_url?: string }>> {
  const accessToken = getAccessToken();
  if (!accessToken) {
    return { ok: false, error: { code: "AUTH_REQUIRED", category: "auth", safeMessage: "Please sign in to continue.", retryable: false } };
  }
  const form = new FormData();
  form.append("file", { uri: fileUri, name: fileName, type: mimeType } as unknown as Blob);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), ENV.apiTimeoutMs);
  try {
    const response = await fetch(new URL("/v1/me/profile-photo", ENV.apiBaseUrl).toString(), {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: form,
      signal: controller.signal,
    });
    const parsed = await safeParseJson(response);
    if (response.ok && isSuccessEnvelope<{ id: string; preview_url?: string; public_url?: string }>(parsed)) {
      return { ok: true, data: parsed.data, meta: parsed.meta, links: parsed.links };
    }
    if (isProblemDetail(parsed)) {
      return { ok: false, error: mapProblemDetail(parsed, "authenticated") };
    }
    return { ok: false, error: mapUnknownFailure(response.status) };
  } catch (err) {
    const aborted = err instanceof Error && err.name === "AbortError";
    return { ok: false, error: mapNetworkFailure(aborted ? "timeout" : "offline") };
  } finally {
    clearTimeout(timeout);
  }
}

async function _upload(
  fileUri: string, fileName: string, mimeType: string,
  mediaContext: string, ownerType: string, ownerId: string,
): Promise<ApiResult<UploadedMediaAsset>> {
  const accessToken = getAccessToken();
  if (!accessToken) {
    return { ok: false, error: { code: "AUTH_REQUIRED", category: "auth", safeMessage: "Please sign in to continue.", retryable: false } };
  }

  const form = new FormData();
  form.append("file", { uri: fileUri, name: fileName, type: mimeType } as unknown as Blob);
  form.append("media_context", mediaContext);
  form.append("owner_type", ownerType);
  form.append("owner_id", ownerId);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), ENV.apiTimeoutMs);
  try {
    const response = await fetch(new URL("/v1/media/upload", ENV.apiBaseUrl).toString(), {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: form,
      signal: controller.signal,
    });
    const parsed = await safeParseJson(response);
    if (response.ok && isSuccessEnvelope<UploadedMediaAsset>(parsed)) {
      return { ok: true, data: parsed.data, meta: parsed.meta, links: parsed.links };
    }
    if (isProblemDetail(parsed)) {
      return { ok: false, error: mapProblemDetail(parsed, "authenticated") };
    }
    return { ok: false, error: mapUnknownFailure(response.status) };
  } catch (err) {
    const aborted = err instanceof Error && err.name === "AbortError";
    return { ok: false, error: mapNetworkFailure(aborted ? "timeout" : "offline") };
  } finally {
    clearTimeout(timeout);
  }
}
