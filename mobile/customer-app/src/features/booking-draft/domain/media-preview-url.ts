import { environment } from "../../../config/environment";
import { resolveAuthToken } from "../../../api/request-context";

/**
 * `preview_url` from the media engine is a relative, access-checked path
 * (`/v1/media/{id}/view`) — private media, never a public CDN URL for this
 * context (`booking_issue_photo` is customer-scoped server-side). React
 * Native's `<Image source>` needs an absolute URL plus the same bearer
 * token every other authenticated request uses; there is no separate
 * signed-URL mechanism to protect here (see contract-matrix.md).
 */
export async function resolveAuthorizedPreviewSource(previewUrl: string): Promise<{ uri: string; headers: Record<string, string> }> {
  const token = await resolveAuthToken();
  const absoluteUrl = previewUrl.startsWith("http") ? previewUrl : `${environment.apiBaseUrl}${previewUrl}`;
  return { uri: absoluteUrl, headers: token ? { Authorization: `Bearer ${token}` } : {} };
}
