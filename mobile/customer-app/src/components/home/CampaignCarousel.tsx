import React, { useEffect, useRef, useState } from "react";
import { View, Image, ScrollView, NativeSyntheticEvent, NativeScrollEvent, Dimensions, AccessibilityInfo } from "react-native";
import { useTheme, useReducedMotion } from "../../design-system/theme";
import { AppText, AppButton } from "../index";
import { HomeCampaign } from "../../domain/customerHome";

export interface CampaignCarouselProps {
  campaigns: HomeCampaign[];
  mode: "light" | "dark";
  onPressCta: (campaign: HomeCampaign) => void;
  /** Whether a given campaign's CTA has a destination that genuinely
   * exists for this customer. Resolved by the screen (which knows what is
   * bookable in their area), not guessed here -- a CTA with no reachable
   * destination stays disabled rather than navigating nowhere. */
  isCtaRoutable: (campaign: HomeCampaign) => boolean;
}

const AUTO_ROTATE_MS = 5000;
const CARD_WIDTH = Dimensions.get("window").width - 32;

/**
 * Renders the highest-priority eligible campaigns (already server-side
 * ordered/filtered by ZIP+vertical+category+active-window -- see
 * api/adapters/customerHome.ts). Renders nothing at all when the array is
 * empty (spec: "If there is no eligible campaign, remove the section
 * completely without leaving empty space.").
 *
 * Auto-rotation stops under reduced motion or when a screen reader is
 * active (spec requirement) -- `useReducedMotion` plus a live
 * `AccessibilityInfo.isScreenReaderEnabled` check.
 */
export function CampaignCarousel({ campaigns, mode, onPressCta, isCtaRoutable }: CampaignCarouselProps) {
  const { theme } = useTheme();
  const reduceMotion = useReducedMotion();
  const [screenReaderOn, setScreenReaderOn] = useState(false);
  const [index, setIndex] = useState(0);
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setScreenReaderOn).catch(() => {});
    const sub = AccessibilityInfo.addEventListener("screenReaderChanged", setScreenReaderOn);
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (reduceMotion || screenReaderOn || campaigns.length < 2) return;
    const timer = setInterval(() => {
      setIndex(prev => {
        const next = (prev + 1) % campaigns.length;
        scrollRef.current?.scrollTo({ x: next * CARD_WIDTH, animated: true });
        return next;
      });
    }, AUTO_ROTATE_MS);
    return () => clearInterval(timer);
  }, [reduceMotion, screenReaderOn, campaigns.length]);

  if (campaigns.length === 0) return null;

  function handleScrollEnd(e: NativeSyntheticEvent<NativeScrollEvent>) {
    const next = Math.round(e.nativeEvent.contentOffset.x / CARD_WIDTH);
    setIndex(next);
  }

  return (
    <View>
      <ScrollView
        ref={scrollRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={handleScrollEnd}
        accessibilityLabel={`Promotional offers, ${campaigns.length} available`}
      >
        {campaigns.map((campaign, i) => {
          const artwork = mode === "dark" ? campaign.artworkUrlDark : campaign.artworkUrlLight;
          // A CTA is tappable only when its deep link resolves to a
          // destination that exists FOR THIS CUSTOMER (see
          // resolveCampaignDeepLink). Everything else stays disabled --
          // a button that invites a tap and goes nowhere is a dead button.
          const ctaEnabled = isCtaRoutable(campaign);
          return (
            <View
              key={campaign.campaignId}
              style={{
                width: CARD_WIDTH, borderRadius: theme.radiusUsage.card, overflow: "hidden",
                backgroundColor: theme.colors.campaignBackground,
                // The flat tint alone gave the card no edge against the page
                // background (near-identical luminance in dark mode), so a
                // promo read as an unstyled block of text. A brand-coloured
                // leading rule anchors it without needing artwork, which is
                // optional and usually absent.
                borderLeftWidth: 3, borderLeftColor: theme.colors.brandPrimary,
              }}
              accessibilityRole="summary"
              accessibilityLabel={`Offer ${i + 1} of ${campaigns.length}. ${campaign.title}. ${campaign.description ?? ""}`}
            >
              <View style={{ padding: theme.spacing.base }}>
                {campaign.eyebrow ? (
                  <View
                    style={{
                      alignSelf: "flex-start", paddingHorizontal: theme.spacing.sm, paddingVertical: 2,
                      borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.brandPrimary, marginBottom: theme.spacing.sm,
                    }}
                  >
                    <AppText variant="labelStrong" style={{ color: theme.colors.brandOnPrimary }}>{campaign.eyebrow}</AppText>
                  </View>
                ) : null}
                <AppText variant="headingSmall">{campaign.title}</AppText>
                {campaign.description ? (
                  <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>{campaign.description}</AppText>
                ) : null}
                {artwork ? (
                  <Image
                    source={{ uri: artwork }}
                    style={{ width: "100%", aspectRatio: 16 / 9, borderRadius: theme.radiusUsage.input, marginTop: theme.spacing.sm }}
                    resizeMode="cover"
                    accessibilityElementsHidden
                  />
                ) : null}
                {/* A CTA whose destination isn't available at this ZIP used
                    to render as a greyed-out button with no explanation --
                    permanently dead for that customer, and reading as
                    "broken app" rather than "not offered here". A campaign
                    can legitimately target a service the viewer can't book
                    (e.g. a plumbing promo shown in an AC-only ZIP), so the
                    honest presentation is to drop the button and say why. */}
                {campaign.ctaLabel && ctaEnabled ? (
                  <View style={{ marginTop: theme.spacing.base, alignSelf: "flex-start" }}>
                    <AppButton
                      label={campaign.ctaLabel}
                      onPress={() => onPressCta(campaign)}
                      size="compact"
                    />
                  </View>
                ) : campaign.ctaLabel ? (
                  <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.sm }}>
                    Not available at your location yet
                  </AppText>
                ) : null}
              </View>
            </View>
          );
        })}
      </ScrollView>
      {campaigns.length > 1 ? (
        <View accessibilityElementsHidden style={{ flexDirection: "row", justifyContent: "center", gap: theme.spacing.xs, marginTop: theme.spacing.sm }}>
          {campaigns.map((c, i) => (
            <View
              key={c.campaignId}
              style={{
                width: 6, height: 6, borderRadius: theme.radius.radiusFull,
                backgroundColor: i === index ? theme.colors.brandPrimary : theme.colors.borderStrong,
              }}
            />
          ))}
        </View>
      ) : null}
    </View>
  );
}
