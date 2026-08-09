import React from "react";
import { View, Pressable, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeCampaign } from "../../domain/customerHome";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { formatCampaignEnds } from "../../domain/campaignWindow";
import { onColor } from "../../design-system/contrastText";

export interface FestivalBannerProps {
  campaign: HomeCampaign;
  mode: "light" | "dark";
  /** Same routability check the hero carousel uses: a CTA whose deep link has
   * no destination in this build is dropped rather than rendered dead. */
  isCtaRoutable: (campaign: HomeCampaign) => boolean;
  onPressCta: (campaign: HomeCampaign) => void;
}

/** Hex + alpha suffixes, so one admin-chosen accent produces the whole card
 * rather than needing a palette per campaign. */
const WASH = "1F";   // card background
const EDGE = "59";   // border

/**
 * The seasonal banner: one admin-chosen accent colour, a badge, and a real end
 * date.
 *
 * Distinct from the hero carousel on purpose. A hero sells a service with
 * artwork; a festival banner is a moment -- it earns a stronger colour and a
 * deadline, and it is the only banner style that states when it stops. That
 * date is `ends_at` from the backend: no countdown timer, no "hurry, ends soon"
 * on a campaign with no end at all, because manufactured urgency is the thing
 * that makes every other claim on the screen look manufactured too.
 *
 * Artwork is optional. With none, the accent and the badge carry the card --
 * better than a grey placeholder box where an image was meant to be.
 */
export function FestivalBanner({ campaign, mode, isCtaRoutable, onPressCta }: FestivalBannerProps) {
  const { theme } = useTheme();
  const accent = campaign.accentColor || theme.colors.brandPrimaryStrong;
  const artworkUrl = mode === "dark"
    ? campaign.artworkUrlDark || campaign.artworkUrlLight
    : campaign.artworkUrlLight || campaign.artworkUrlDark;
  const artwork = artworkUrl ? resolveMediaUrl(artworkUrl) : null;
  const routable = !!campaign.ctaLabel && isCtaRoutable(campaign);
  // The accent is admin-chosen, so which text colour is legible on it cannot be
  // known from the theme -- it is computed from the colour itself.
  const onAccent = onColor(accent);
  const endsLabel = formatCampaignEnds(campaign.endsAt);

  return (
    <View
      accessibilityLabel={`Offer: ${campaign.title}`}
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.base,
        padding: theme.spacing.base,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: `${accent}${WASH}`,
        borderWidth: 1, borderColor: `${accent}${EDGE}`,
        overflow: "hidden",
      }}
    >
      <View style={{ flex: 1, minWidth: 0, gap: theme.spacing.xxs }}>
        {campaign.badgeText ? (
          <View
            style={{
              alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
              paddingHorizontal: theme.spacing.xs, paddingVertical: 3,
              borderRadius: theme.radiusUsage.statusPill,
              backgroundColor: accent,
            }}
          >
            <Icon name="sparkles" size="compact" color={onAccent} decorative />
            <AppText variant="caption" style={{ color: onAccent, fontWeight: "700" }}>
              {campaign.badgeText}
            </AppText>
          </View>
        ) : campaign.eyebrow ? (
          <AppText variant="caption" style={{ color: accent, fontWeight: "700", letterSpacing: 0.4 }}>
            {campaign.eyebrow}
          </AppText>
        ) : null}

        <AppText variant="bodyStrong" numberOfLines={2}>{campaign.title}</AppText>

        {campaign.description ? (
          <AppText variant="bodySmall" color="secondary" numberOfLines={2}>{campaign.description}</AppText>
        ) : null}

        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, marginTop: theme.spacing.xxs }}>
          {routable ? (
            <Pressable
              onPress={() => onPressCta(campaign)}
              accessibilityRole="button"
              accessibilityLabel={campaign.ctaLabel!}
              style={({ pressed }) => ({
                flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
                paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.xs,
                borderRadius: theme.radiusUsage.button,
                backgroundColor: accent,
                opacity: pressed ? 0.85 : 1,
              })}
            >
              <AppText variant="labelStrong" style={{ color: onAccent }}>
                {campaign.ctaLabel}
              </AppText>
              <Icon name="arrow-forward" size="compact" color={onAccent} decorative />
            </Pressable>
          ) : (
            // Same honesty rule as the hero carousel: no dead button.
            <AppText variant="caption" color="tertiary">Not available at your location yet</AppText>
          )}

          {endsLabel ? (
            <AppText variant="caption" color="tertiary" numberOfLines={1}>{endsLabel}</AppText>
          ) : null}
        </View>
      </View>

      {artwork ? (
        <Image
          source={{ uri: artwork }}
          style={{ width: 76, height: 76, borderRadius: theme.radiusUsage.input }}
          resizeMode="contain"
        />
      ) : null}
    </View>
  );
}
