/**
 * Campaign CTA deep-link validation. Mirrors the exact server-side
 * allowlist (app/engines/customer_campaigns/constants.py
 * `ALLOWED_DEEPLINK_PREFIXES`) so a client never navigates on a
 * `cta_deeplink` value that the backend itself would have rejected --
 * this is a defense-in-depth check, not the authority (the backend
 * already refuses to save a campaign with a disallowed prefix).
 */
export const ALLOWED_CAMPAIGN_DEEPLINK_PREFIXES = [
  "app://home",
  "app://category/",
  "app://service/",
  "app://booking/",
  "app://offers",
] as const;

export function isAllowedCampaignDeepLink(deeplink: string | null | undefined): boolean {
  if (!deeplink) return false;
  return ALLOWED_CAMPAIGN_DEEPLINK_PREFIXES.some(prefix => deeplink.startsWith(prefix));
}

/**
 * What a campaign CTA should actually DO.
 *
 * Validation alone was not enough to make the buttons work: every campaign
 * CTA was hard-disabled because no destination had been wired, so an
 * operator could author a banner with a perfectly valid `app://category/...`
 * link and customers still got a dead button.
 *
 * Resolution is deliberately conservative. A link only becomes tappable if
 * it lands somewhere that genuinely exists FOR THIS CUSTOMER — an
 * `app://category/` link is honoured only when its slug matches a category
 * the backend actually returned as bookable in their area. Anything else
 * stays unresolved and the button stays disabled, because a button that
 * navigates into an empty or unserviceable screen is worse than one that
 * is visibly unavailable.
 */
export type CampaignDeepLinkTarget =
  | { kind: "category"; slug: string }
  | { kind: "home" };

/** Prefixes that pass the allowlist but have no destination in this app
 * yet. Listed explicitly so it is obvious what is still missing rather
 * than silently falling through: there is no offers screen, and
 * `app://service/` and `app://booking/` would need an id the campaign
 * author has no reliable way to supply. */
const UNROUTED_PREFIXES = ["app://offers", "app://service/", "app://booking/"] as const;

export function resolveCampaignDeepLink(
  deeplink: string | null | undefined,
  availableCategorySlugs: readonly string[],
): CampaignDeepLinkTarget | null {
  if (!isAllowedCampaignDeepLink(deeplink) || !deeplink) return null;
  if (UNROUTED_PREFIXES.some(p => deeplink.startsWith(p))) return null;

  if (deeplink === "app://home" || deeplink.startsWith("app://home?")) {
    return { kind: "home" };
  }

  if (deeplink.startsWith("app://category/")) {
    const slug = deeplink.slice("app://category/".length).split(/[?#]/)[0].trim();
    if (!slug) return null;
    // Only routable if this customer can actually book it here.
    return availableCategorySlugs.includes(slug) ? { kind: "category", slug } : null;
  }

  return null;
}
