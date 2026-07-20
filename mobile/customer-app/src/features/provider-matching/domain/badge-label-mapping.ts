import { logger } from "../../../observability/logger";

/**
 * The real, closed set of literal English strings
 * `_public_badges()` (matching_engine.py) can return — see
 * CUSTOMER-L5-08-provider-model.md. These are returned untranslated by the
 * backend with no stable badge ID, so this module maps the known literal
 * strings to translation keys under the `discovery` namespace. An
 * unrecognized string (a future backend addition this client hasn't been
 * updated for) fails safe: it is still rendered as-is rather than dropped,
 * and logged once so the gap is visible without crashing the screen.
 */
const BADGE_TRANSLATION_KEYS: Record<string, string> = {
  Verified: "providerMatch.badge.verified",
  "Highly Rated": "providerMatch.badge.highlyRated",
  "High Completion": "providerMatch.badge.highCompletion",
};

export function resolveBadgeTranslationKey(badge: string): string | null {
  const key = BADGE_TRANSLATION_KEYS[badge];
  if (!key) {
    logger.warn("provider_badge_unmapped", { badge });
    return null;
  }
  return key;
}
