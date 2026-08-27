// ═══════════════════════════════════════════════════════════════════════════
// Legal documents — public read client (/v1/public/legal/*).
//
// Deliberately does NOT go through lib/api.ts's authenticated `apiFetch`.
// These pages are linked from the signup consent checkbox and the login
// footer, so they are read by people who have no session at all; attaching a
// token (or redirecting on a missing one) would break the one moment they
// matter most.
// ═══════════════════════════════════════════════════════════════════════════
import { API_BASE } from "./api";

export interface PublicLegalDocument {
  id: string;
  doc_type: string;
  audience: string;
  locale: string;
  version: string;
  title: string;
  summary: string | null;
  body: string;
  body_format: string;
  effective_at: string | null;
  published_at: string | null;
}

/**
 * Fetch the document currently in force.
 *
 * Returns null rather than throwing: the caller renders an honest
 * "temporarily unavailable" panel. It must never fall back to a hardcoded
 * copy of the text — a stale second copy of the Terms is exactly the problem
 * this engine exists to remove.
 *
 * Revalidated every 5 minutes so publishing a new version reaches readers
 * without a frontend deploy, while a burst of traffic does not hit the API
 * once per view.
 */
export async function fetchLegalDocument(
  docType: string,
  opts: { audience?: string; locale?: string } = {},
): Promise<PublicLegalDocument | null> {
  const qs = new URLSearchParams();
  if (opts.audience) qs.set("audience", opts.audience);
  if (opts.locale) qs.set("locale", opts.locale);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";

  try {
    const res = await fetch(`${API_BASE}/v1/public/legal/${docType}${suffix}`, {
      headers: { Accept: "application/json" },
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json?.data as PublicLegalDocument) ?? null;
  } catch {
    return null;
  }
}
