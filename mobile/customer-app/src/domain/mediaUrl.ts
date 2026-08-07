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
