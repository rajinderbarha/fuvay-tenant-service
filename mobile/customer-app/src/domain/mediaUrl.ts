import { ENV } from "../config/environment";

/**
 * Resolves a backend media URL into something `<Image source={{ uri }}>`
 * can actually load.
 *
 * The media engine returns `public_url` as a SERVER-RELATIVE path for the
 * local storage driver (e.g. "/uploads/category_icon/<id>.png" -- see
 * app/engines/media/storage.py `_store_local`). A browser resolves that
 * against the page origin, but React Native has no origin: a relative URI
 * silently fails to load, which is why admin-uploaded category artwork
 * rendered as blank space rather than falling back to the built-in glyph
 * (the fallback only triggers on a null/empty URL, not a broken one).
 *
 * Cloudinary/S3 drivers already return absolute URLs, and data: URIs are
 * self-contained, so both are passed through untouched.
 */
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  const trimmed = url.trim();
  if (trimmed === "") return null;
  if (/^(https?:)?\/\//i.test(trimmed) || trimmed.startsWith("data:")) return trimmed;
  const base = ENV.apiBaseUrl.replace(/\/+$/, "");
  return `${base}${trimmed.startsWith("/") ? "" : "/"}${trimmed}`;
}

export interface MediaImageSource {
  uri: string;
  headers?: Record<string, string>;
}

/**
 * Builds a React Native image source without leaking credentials to a CDN.
 * Private Media Engine previews live behind `/v1/media/{id}/view`, so a plain
 * `<Image uri>` receives 401 even though the upload/attach request succeeded.
 * Only same-API Media Engine URLs receive the bearer token; Cloudinary, S3,
 * public uploads and data URIs remain credential-free.
 */
export function resolveMediaImageSource(
  url: string | null | undefined,
  accessToken: string | null,
): MediaImageSource | null {
  const uri = resolveMediaUrl(url);
  if (!uri) return null;

  const base = ENV.apiBaseUrl.replace(/\/+$/, "");
  const isProtectedMediaUrl = uri.startsWith(`${base}/v1/media/`);
  if (isProtectedMediaUrl && accessToken) {
    return { uri, headers: { Authorization: `Bearer ${accessToken}` } };
  }
  return { uri };
}
