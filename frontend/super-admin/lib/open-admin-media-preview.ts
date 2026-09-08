/** Open an authenticated Media Engine asset without triggering popup blockers. */
export async function loadAdminDocument(mediaAssetId: string, signal?: AbortSignal): Promise<Blob> {
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const token = localStorage.getItem("serviceos_admin_token") ?? "";
  const response = await fetch(`${apiBase}/v1/media/${encodeURIComponent(mediaAssetId)}/view`, {
    headers: { Authorization: `Bearer ${token}` }, signal,
  });
  if (!response.ok) throw new Error(`Document service returned HTTP ${response.status}.`);
  const blob = await response.blob();
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
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const token = localStorage.getItem("serviceos_admin_token") ?? "";
    const response = await fetch(`${apiBase}/v1/media/${encodeURIComponent(mediaAssetId)}/view`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error(`Document service returned HTTP ${response.status}.`);

    const objectUrl = URL.createObjectURL(await response.blob());
    preview.location.replace(objectUrl);
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 5 * 60 * 1000);
  } catch (error) {
    preview.close();
    throw error;
  }
}
