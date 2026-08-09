import React from "react";
import { View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { HomeCampaign } from "../../domain/customerHome";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { formatCampaignEnds } from "../../domain/campaignWindow";

export interface HeroBannerProps {
  campaign: HomeCampaign;
  mode: "light" | "dark";
  isCtaRoutable: (campaign: HomeCampaign) => boolean;
  onPressCta: (campaign: HomeCampaign) => void;
}

/**
 * One artwork-led promotional card.
 *
 * Extracted from CampaignCarousel so paging belongs to the SLOT rather than to
 * this style: a slot can now mix a hero, a festival card and a strip in one
 * pager, which the carousel-owns-its-own-paging arrangement could not express.
 *
 * An admin-uploaded banner image is the complete visual on its own -- headline,
 * copy and call to action are usually baked into the asset -- so an
 * image-backed campaign renders as JUST the image, tappable as a whole. The
 * text layout is the fallback for a campaign with no artwork, so a banner is
 * never blank.
 */
export function HeroBanner({ campaign, mode, isCtaRoutable, onPressCta }: HeroBannerProps) {
  const { theme } = useTheme();
  const artworkUrl = mode === "dark"
    ? campaign.artworkUrlDark || campaign.artworkUrlLight
    : campaign.artworkUrlLight || campaign.artworkUrlDark;
  const artwork = artworkUrl ? resolveMediaUrl(artworkUrl) : null;
  // A CTA is live only when its deep link resolves to a destination that exists
  // FOR THIS CUSTOMER. A campaign can legitimately target a service the viewer
  // cannot book (a plumbing promo in an AC-only ZIP), and a button that invites
  // a tap and goes nowhere reads as a broken app.
  const ctaEnabled = isCtaRoutable(campaign);
  const endsLabel = formatCampaignEnds(campaign.endsAt);

  if (artwork) {
    return (
      <View
        accessibilityRole={ctaEnabled ? "button" : "image"}
        accessibilityLabel={campaign.title}
        onTouchEnd={ctaEnabled ? () => onPressCta(campaign) : undefined}
        style={{ borderRadius: theme.radiusUsage.card, overflow: "hidden" }}
      >
        <Image
          source={{ uri: artwork }}
          style={{ width: "100%", aspectRatio: 343 / 145 }}
          resizeMode="cover"
        />
      </View>
    );
  }

  return (
    <View
      style={{
        borderRadius: theme.radiusUsage.card, overflow: "hidden",
        backgroundColor: theme.colors.campaignBackground,
        // The flat tint alone gave the card no edge against the page background
        // (near-identical luminance in dark mode), so a promo read as an
        // unstyled block of text. A brand-coloured leading rule anchors it.
        borderLeftWidth: 3, borderLeftColor: theme.colors.brandPrimary,
      }}
      accessibilityRole="summary"
      accessibilityLabel={`Offer. ${campaign.title}. ${campaign.description ?? ""}`}
    >
      <View style={{ padding: theme.spacing.base }}>
        {campaign.eyebrow ? (
          <View
            style={{
              alignSelf: "flex-start", paddingHorizontal: theme.spacing.sm, paddingVertical: 2,
              borderRadius: theme.radiusUsage.statusPill,
              backgroundColor: theme.colors.brandPrimary, marginBottom: theme.spacing.sm,
            }}
          >
            <AppText variant="labelStrong" style={{ color: theme.colors.brandOnPrimary }}>
              {campaign.eyebrow}
            </AppText>
          </View>
        ) : null}
        <AppText variant="headingSmall">{campaign.title}</AppText>
        {campaign.description ? (
          <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>
            {campaign.description}
          </AppText>
        ) : null}
        {endsLabel ? (
          <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xxs }}>
            {endsLabel}
          </AppText>
        ) : null}
        {campaign.ctaLabel && ctaEnabled ? (
          <View style={{ marginTop: theme.spacing.base, alignSelf: "flex-start" }}>
            <AppButton label={campaign.ctaLabel} onPress={() => onPressCta(campaign)} size="compact" />
          </View>
        ) : (
          // The honest presentation for an unreachable destination: drop the
          // button, say why.
          <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.sm }}>
            Not available at your location yet
          </AppText>
        )}
      </View>
    </View>
  );
}
