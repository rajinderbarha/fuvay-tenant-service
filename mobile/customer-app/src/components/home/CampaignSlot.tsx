import React, { useMemo, useRef, useState } from "react";
import {
  View, ScrollView, Dimensions, NativeSyntheticEvent, NativeScrollEvent,
} from "react-native";
import { useTheme } from "../../design-system/theme";
import { HomeCampaign, HomeCampaignPlacement } from "../../domain/customerHome";
import { HeroBanner } from "./HeroBanner";
import { FestivalBanner } from "./FestivalBanner";
import { CampaignStrip } from "./CampaignStrip";

export interface CampaignSlotProps {
  placement: HomeCampaignPlacement;
  campaigns: readonly HomeCampaign[];
  mode: "light" | "dark";
  isCtaRoutable: (campaign: HomeCampaign) => boolean;
  onPressCta: (campaign: HomeCampaign) => void;
}

/** One page per banner, inset by the screen padding on both sides. */
const PAGE_WIDTH = Dimensions.get("window").width - 32;

/**
 * One slot's banners, each drawn in the style the backend chose, as a carousel
 * when there is more than one.
 *
 * Paging is per SLOT rather than per style. An earlier version put only hero
 * banners in a pager and stacked everything else, which meant two festival
 * banners -- a Diwali push and a winter-service push, say -- appeared as two
 * stacked cards and ate half the screen. Now any slot holding several banners
 * swipes, and each page keeps its own treatment: a festival page still gets its
 * accent and badge, a strip page still reads as a quiet line.
 *
 * A single banner renders plainly, with no pager and no dots: a one-page
 * carousel is a card with a swipe gesture that does nothing.
 *
 * `adaptCustomerHome` drops styles this build does not recognise before they get
 * here, so a newer backend adds banners this app simply does not show rather
 * than mis-drawing them.
 */
export function CampaignSlot({
  placement, campaigns, mode, isCtaRoutable, onPressCta,
}: CampaignSlotProps) {
  const { theme } = useTheme();
  const scrollRef = useRef<ScrollView>(null);
  const [pageIndex, setPageIndex] = useState(0);

  const forSlot = useMemo(
    // Already priority-sorted by the adapter; filtering preserves that order.
    () => campaigns.filter(c => c.placement === placement),
    [campaigns, placement],
  );
  if (forSlot.length === 0) return null;

  function renderBanner(campaign: HomeCampaign) {
    if (campaign.style === "festival") {
      return (
        <FestivalBanner
          campaign={campaign} mode={mode}
          isCtaRoutable={isCtaRoutable} onPressCta={onPressCta}
        />
      );
    }
    if (campaign.style === "strip") {
      return (
        <CampaignStrip campaign={campaign} isCtaRoutable={isCtaRoutable} onPressCta={onPressCta} />
      );
    }
    return (
      <HeroBanner
        campaign={campaign} mode={mode}
        isCtaRoutable={isCtaRoutable} onPressCta={onPressCta}
      />
    );
  }

  if (forSlot.length === 1) return renderBanner(forSlot[0]);

  function handleScrollEnd(e: NativeSyntheticEvent<NativeScrollEvent>) {
    setPageIndex(Math.round(e.nativeEvent.contentOffset.x / PAGE_WIDTH));
  }

  return (
    <View>
      <ScrollView
        ref={scrollRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={handleScrollEnd}
        accessibilityLabel={`Promotional offers, ${forSlot.length} available`}
      >
        {forSlot.map(campaign => (
          <View key={campaign.campaignId} style={{ width: PAGE_WIDTH }}>
            {renderBanner(campaign)}
          </View>
        ))}
      </ScrollView>
      {/* Full-width pages give no visual hint that more exist, so the dots carry
          that affordance. Decorative: the pager itself is already announced. */}
      <View
        accessibilityElementsHidden
        style={{ flexDirection: "row", justifyContent: "center", gap: theme.spacing.xs, marginTop: theme.spacing.sm }}
      >
        {forSlot.map((campaign, i) => (
          <View
            key={campaign.campaignId}
            style={{
              width: i === pageIndex ? 16 : 6, height: 6, borderRadius: theme.radius.radiusFull,
              backgroundColor: i === pageIndex ? theme.colors.brandPrimary : theme.colors.borderStrong,
            }}
          />
        ))}
      </View>
    </View>
  );
}
