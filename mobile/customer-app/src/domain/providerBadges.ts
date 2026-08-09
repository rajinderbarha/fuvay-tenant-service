/**
 * Provider trust badges, made safe to render as a list.
 *
 * Two badges with the same display name are ONE claim to a customer. The platform
 * can hold several separately-keyed definitions that happen to share a label, and
 * the customer surfaces all keyed their list on `badge.name` -- so a provider
 * holding five definitions named "L5 Cfg Badge" both printed that label five times
 * and produced React's "two children with the same key" error, which makes React
 * reuse the wrong node: a badge can end up drawn with another's styling, or lose
 * its place when the list changes.
 *
 * The backend now collapses these too (`matching_engine._public_badges`). This is
 * the app's own guarantee, so an older backend, a cached payload, or any future
 * surface cannot reintroduce it.
 */

export interface BadgeLike {
  name: string;
}

/** A customer-visible provider badge, as the backend sends it. */
export interface ProviderBadge {
  name: string;
  icon?: string | null;
  color?: string | null;
  /** Set only on the STANDING badge -- the provider's earned level. Higher levels
   * replace lower ones rather than stacking, so there is never more than one. */
  level?: number | null;
}

/**
 * The provider's standing badge: the one claim a compact surface shows.
 *
 * Identified by carrying a `level`, not by position, so the surface does not depend
 * on the backend's ordering. Null when the provider has earned no level -- and then
 * the surface shows NO badge, rather than promoting an independent badge into a
 * standing it does not represent.
 */
export function standingBadge(badges: readonly ProviderBadge[]): ProviderBadge | null {
  const withLevel = badges.filter(b => typeof b.level === "number" && b.level > 0);
  if (withLevel.length === 0) return null;
  // Highest wins if a payload ever carries more than one -- the ladder supersedes.
  return withLevel.reduce((best, b) => ((b.level ?? 0) > (best.level ?? 0) ? b : best));
}

/** Distinct badges in their original order, first occurrence of a name winning.
 *
 * Order is preserved rather than sorted because the backend sends these
 * most-recently-earned first, which is the order worth showing. */
export function distinctBadges<T extends BadgeLike>(badges: readonly T[]): T[] {
  const seen = new Set<string>();
  const out: T[] = [];
  for (const badge of badges) {
    const name = (badge.name ?? "").trim();
    // An unnamed badge has nothing to show, so it is dropped rather than rendered
    // as an empty pill.
    if (!name || seen.has(name)) continue;
    seen.add(name);
    out.push(badge);
  }
  return out;
}
