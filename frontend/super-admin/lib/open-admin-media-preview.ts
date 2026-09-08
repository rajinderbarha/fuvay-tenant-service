import { mediaAdminApi } from "./api";

/**
 * Load an admin document through the Media workspace's short-lived preview
 * contract.  Do not call /v1/media/:id/view directly here: that route accepts
 * optional authentication for public images and deliberately turns an expired
 * bearer token into an anonymous request.  For a private provider document the
 * resulting access denial is therefore surfaced as a misleading HTTP 404.
 *
 * apiFetch (used by createSignedPreviewUrl) also performs the normal admin
 * access-token refresh before the single-use URL is created.
 */
export async function loadAdminDocument(mediaAssetId: string, signal?: AbortSignal): Promise<Blob> {
  if (signal?.aborted) throw new DOMException("The operation was aborted.", "AbortError");
  const signed = await mediaAdminApi.createSignedPreviewUrl(mediaAssetId);
  if (signal?.aborted) throw new DOMException("The operation was aborted.", "AbortError");
  const blob = await mediaAdminApi.fetchSignedFile(signed.url);
  if (signal?.aborted) throw new DOMException("The operation was aborted.", "AbortError");
  if (!["application/pdf", "image/jpeg", "image/png", "image/webp"].includes(blob.type.split(";")[0])) {
    throw new Error("This file type cannot be previewed safely. Use the Media workspace to inspect it.");
  }
  return blob;
}

export async function openAdminMediaPreview(mediaAssetId: string): Promise<void> {
  // This must happen synchronously inside the click event. Opening a tab only
  // after the authenticated fetch resolves is blocked by modern browsers.
  const preview = window.open("about:blank", "_blank");
  if (!preview) {
    throw new Error("Your browser blocked the document preview. Allow pop-ups for this Admin site and try again.");
  }
  preview.opener = null;

  try {
    const blob = await loadAdminDocument(mediaAssetId);
    const objectUrl = URL.createObjectURL(blob);
    preview.location.replace(objectUrl);
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 5 * 60 * 1000);
  } catch (error) {
    preview.close();
    throw error;
  }
}
