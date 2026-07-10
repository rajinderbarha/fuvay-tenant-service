/**
 * Normalized Home Services vertical detection.
 *
 * Root cause this exists to fix: different backend payloads/pages have
 * returned the tenant's vertical under different shapes over time
 * (a raw slug "home_services", a display name "Home Services", nested
 * under `category.slug`/`category.name`, or under `tenant.category_*`)
 * — a naive `=== "home_services"` check on a single field silently
 * blocks a real Home Services tenant whenever the value arrives in a
 * different shape or casing. This normalizer checks every known shape
 * and normalizes case/spacing/hyphens before comparing.
 */
export interface VerticalGuardContext {
  vertical?: string | null;
  vertical_slug?: string | null;
  category?: string | null;
  category_slug?: string | null;
  category_name?: string | null;
  business_category?: string | null;
  categorySlug?: string | null;
  categoryName?: string | null;
  tenant?: {
    vertical?: string | null;
    category_slug?: string | null;
    category_name?: string | null;
  } | null;
}

function normalize(v: unknown): string {
  return String(v).trim().toLowerCase().replace(/[\s-]+/g, "_");
}

export function isHomeServicesTenant(context: VerticalGuardContext | null | undefined): boolean {
  const values = [
    context?.vertical,
    context?.vertical_slug,
    context?.category,
    context?.category_slug,
    context?.category_name,
    context?.business_category,
    context?.categorySlug,
    context?.categoryName,
    context?.tenant?.vertical,
    context?.tenant?.category_slug,
    context?.tenant?.category_name,
  ]
    .filter(Boolean)
    .map(normalize);

  return values.includes("home_services") || values.includes("home_service");
}
