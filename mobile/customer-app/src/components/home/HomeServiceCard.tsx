import React from "react";
import { Pressable, View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeCategory } from "../../domain/customerHome";
import { ServicePriceState, resolveServicePriceDisplay } from "../../domain/servicePricing";
import { resolveCategoryIcon } from "../../domain/categoryIcon";

export interface HomeServiceCardProps {
  category: HomeCategory;
  /** Optional -- Home aggregation currently returns NO price field for
   * categories (see api/contracts/customerHome.ts), so this is almost
   * always undefined today. When undefined, no price row renders at all
   * rather than fabricating one (spec: never infer price from nothing). */
  priceState?: ServicePriceState;
  onPress: () => void;
  /**
   * "grid" (default): vertical tile, icon over text, meant to sit two-up.
   * "wide": horizontal row, icon-text-chevron, meant to fill a full row on
   * its own -- used for a row that ends up with exactly one card (most
   * commonly a ZIP with only one bookable category, since a stretched
   * "grid" tile just leaves empty space beside a top-left icon instead of
   * actually using the extra width).
   */
  layout?: "grid" | "wide";
}

/** Never exposes provider names/counts/matching scores/tenant IDs --
 * `HomeCategory` structurally cannot carry them (see domain/
 * customerHome.ts), so there is nothing to accidentally leak here. */
export function HomeServiceCard({ category, priceState, onPress, layout = "grid" }: HomeServiceCardProps) {
  const { theme } = useTheme();
  const price = priceState ? resolveServicePriceDisplay(priceState) : null;
  const iconEl = category.iconUrl ? (
    <Image source={{ uri: category.iconUrl }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
  ) : (
    // Distinct per-category glyph rather than one generic wrench for
    // everything -- see domain/categoryIcon.ts.
    <Icon name={resolveCategoryIcon(category.slug)} size="standard" color={theme.colors.brandPrimaryStrong} decorative />
  );

  if (layout === "wide") {
    return (
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={`${category.name}${price ? `, ${price.label}` : ""}`}
        style={({ pressed }) => ({
          flexDirection: "row", alignItems: "center", gap: theme.spacing.base,
          padding: theme.spacing.base, borderRadius: theme.radiusUsage.card,
          backgroundColor: theme.colors.surfaceDefault, borderWidth: 1,
          borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle,
          opacity: pressed ? 0.9 : 1,
        })}
      >
        <View
          style={{
            width: 52, height: 52, borderRadius: theme.radiusUsage.input,
            backgroundColor: theme.colors.brandPrimaryMuted, alignItems: "center", justifyContent: "center",
            overflow: "hidden", flexShrink: 0,
          }}
        >
          {iconEl}
        </View>
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong" numberOfLines={1}>{category.name}</AppText>
          <AppText variant="bodySmall" color={price?.isNumericPrice ? "secondary" : "tertiary"} numberOfLines={1} style={{ marginTop: 2 }}>
            {price?.label ?? "Tap to book a visit"}
          </AppText>
        </View>
        <Icon name="chevron-forward" size="compact" color={theme.colors.iconDefault} decorative />
      </Pressable>
    );
  }

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${category.name}${price ? `, ${price.label}` : ""}`}
      style={({ pressed }) => ({
        // Width is set by the parent grid, not here.
        flex: 1,
        padding: theme.spacing.base,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1,
        borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle,
        opacity: pressed ? 0.9 : 1,
      })}
    >
      <View
        style={{
          width: 44, height: 44, borderRadius: theme.radiusUsage.input,
          backgroundColor: theme.colors.brandPrimaryMuted, alignItems: "center", justifyContent: "center",
          marginBottom: theme.spacing.sm, overflow: "hidden",
        }}
      >
        {iconEl}
      </View>
      <AppText variant="bodyStrong" numberOfLines={2}>{category.name}</AppText>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: theme.spacing.xxs }}>
        <AppText variant="bodySmall" color={price?.isNumericPrice ? "secondary" : "tertiary"} numberOfLines={1}>
          {price?.label ?? "Book now"}
        </AppText>
        <Icon name="chevron-forward" size="compact" color={theme.colors.iconDefault} decorative />
      </View>
    </Pressable>
  );
}
