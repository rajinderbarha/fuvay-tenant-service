import React from "react";
import { Pressable, View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeCategory } from "../../domain/customerHome";
import { ServicePriceState, resolveServicePriceDisplay, classifyRawAmount } from "../../domain/servicePricing";
import { resolveCategoryIcon } from "../../domain/categoryIcon";
import { formatMoney } from "../../domain/money";

export interface HomeServiceCardProps {
  category: HomeCategory;
  /** Legacy per-service pricing hook. The Home payload now carries a real
   * `startingPrice` per category, which takes precedence; this remains for
   * callers that resolve a more specific price themselves. */
  priceState?: ServicePriceState;
  onPress: () => void;
}

/**
 * "Services Nearby" card.
 *
 * Horizontal by design (illustration left, copy right) to match the
 * approved Home layout -- it was previously a vertical tile with a small
 * glyph on top, which is why the grid did not read like the design. The
 * artwork is deliberately oversized relative to its column and vertically
 * centred so the mascot fills the left edge the way the comps show.
 *
 * Never exposes provider names/counts/matching scores/tenant IDs --
 * `HomeCategory` structurally cannot carry them (see domain/
 * customerHome.ts), so there is nothing to accidentally leak here.
 */
export function HomeServiceCard({ category, priceState, onPress }: HomeServiceCardProps) {
  const { theme } = useTheme();
  const legacyPrice = priceState ? resolveServicePriceDisplay(priceState) : null;
  // `starting_price` arrives as a major-unit decimal (₹, matching the
  // backend's Numeric(10,2) columns), so it goes through the same
  // classify-then-format path as every other price in the app. That path
  // treats null/0/negative as "no price", which is why a category with
  // nothing configured renders no price row instead of "₹0".
  const startingState = classifyRawAmount(
    category.startingPrice != null ? Math.round(category.startingPrice * 100) : null,
  );
  const priceLabel = startingState.kind === "valid"
    ? formatMoney(startingState.amount)
    : legacyPrice?.label ?? null;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${category.name}${priceLabel ? `, starting at ${priceLabel}` : ""}`}
      style={({ pressed }) => ({
        flex: 1,
        flexDirection: "row",
        alignItems: "center",
        gap: theme.spacing.xs,
        paddingVertical: theme.spacing.sm,
        paddingRight: theme.spacing.sm,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1,
        borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle,
        opacity: pressed ? 0.9 : 1,
        overflow: "hidden",
        minHeight: 96,
      })}
    >
      <View style={{ width: 62, height: 72, alignItems: "center", justifyContent: "flex-end", flexShrink: 0 }}>
        {category.iconUrl ? (
          <Image
            source={{ uri: category.iconUrl }}
            style={{ width: 62, height: 72 }}
            resizeMode="contain"
            accessibilityElementsHidden
          />
        ) : (
          // Distinct per-category glyph rather than one generic wrench for
          // every card -- see domain/categoryIcon.ts. Only reached until an
          // admin uploads artwork for the category.
          <View
            style={{
              width: 46, height: 46, borderRadius: theme.radiusUsage.input,
              backgroundColor: theme.colors.brandPrimaryMuted,
              alignItems: "center", justifyContent: "center", marginBottom: theme.spacing.xs,
            }}
          >
            <Icon name={resolveCategoryIcon(category.slug)} size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
        )}
      </View>

      <View style={{ flex: 1, minWidth: 0 }}>
        <AppText variant="bodyStrong" numberOfLines={1}>{category.name}</AppText>
        {category.description ? (
          <AppText variant="caption" color="tertiary" numberOfLines={2} style={{ marginTop: 2 }}>
            {category.description}
          </AppText>
        ) : null}
        {priceLabel ? (
          <View style={{ flexDirection: "row", alignItems: "baseline", gap: 4, marginTop: theme.spacing.xs }}>
            <AppText variant="caption" color="tertiary">Starting at</AppText>
            <AppText variant="bodySmall" style={{ color: theme.colors.brandPrimaryStrong, fontWeight: "700" }}>
              {priceLabel}
            </AppText>
          </View>
        ) : null}
      </View>
    </Pressable>
  );
}
