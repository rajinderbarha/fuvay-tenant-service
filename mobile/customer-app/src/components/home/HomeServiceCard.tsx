import React from "react";
import { Pressable, View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeCategory } from "../../domain/customerHome";
import { ServicePriceState } from "../../domain/servicePricing";
import { resolveCategoryIcon } from "../../domain/categoryIcon";
import { resolveMediaUrl } from "../../domain/mediaUrl";

export interface HomeServiceCardProps {
  category: HomeCategory;
  /** Legacy per-service pricing hook. The Home payload now carries a real
   * `startingPrice` per category, which takes precedence; this remains for
   * callers that resolve a more specific price themselves. */
  priceState?: ServicePriceState;
  onPress: () => void;
}

/** Artwork panel height. Tall enough for the mascot illustrations to read at
 * a two-up column width without the card dominating the screen. */
const ARTWORK_HEIGHT = 112;

/**
 * "Services Nearby" card.
 *
 * Vertical: a full-width artwork panel on top, then centred name,
 * description and "Starting at <price>". This replaced a horizontal
 * variant (artwork left, copy right) -- the updated design puts the
 * illustration above the text and centres the whole block, which also
 * gives the mascots noticeably more room at a two-up width.
 *
 * Never exposes provider names/counts/matching scores/tenant IDs --
 * `HomeCategory` structurally cannot carry them (see domain/
 * customerHome.ts), so there is nothing to accidentally leak here.
 */
export function HomeServiceCard({ category, onPress }: HomeServiceCardProps) {
  const { theme } = useTheme();
  // `starting_price` arrives as a major-unit decimal (₹, matching the
  // backend's Numeric(10,2) columns), so it goes through the same
  // classify-then-format path as every other price in the app. That path
  // treats null/0/negative as "no price", which is why a category with
  // nothing configured renders no price row instead of "₹0".
  // `icon_url` is server-relative for the local storage driver; RN cannot
  // load a relative URI, so it must be absolutised (see domain/mediaUrl).
  const artworkUri = resolveMediaUrl(category.iconUrl);

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={category.name}
      style={({ pressed }) => ({
        flex: 1,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1,
        borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle,
        opacity: pressed ? 0.9 : 1,
        overflow: "hidden",
      })}
    >
      {/* Tinted panel behind the illustration, so a transparent PNG has a
          consistent backdrop instead of sitting straight on the card. */}
      <View
        style={{
          height: ARTWORK_HEIGHT,
          backgroundColor: theme.colors.surfaceSecondary,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {artworkUri ? (
          <Image
            source={{ uri: artworkUri }}
            style={{ width: "100%", height: "100%" }}
            resizeMode="contain"
            accessibilityElementsHidden
          />
        ) : (
          // Distinct per-category glyph rather than one generic wrench for
          // every card -- see domain/categoryIcon.ts. Only reached until an
          // admin uploads artwork for the category.
          <Icon name={resolveCategoryIcon(category.slug)} size="navigation" color={theme.colors.brandPrimaryStrong} decorative />
        )}
      </View>

      <View style={{ padding: theme.spacing.sm, alignItems: "center" }}>
        <AppText variant="bodyStrong" align="center" numberOfLines={1}>{category.name}</AppText>
        {category.description ? (
          <AppText variant="caption" color="tertiary" align="center" numberOfLines={2} style={{ marginTop: 2 }}>
            {category.description}
          </AppText>
        ) : null}
      </View>
    </Pressable>
  );
}
