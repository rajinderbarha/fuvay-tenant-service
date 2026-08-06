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
}

/** Never exposes provider names/counts/matching scores/tenant IDs --
 * `HomeCategory` structurally cannot carry them (see domain/
 * customerHome.ts), so there is nothing to accidentally leak here. */
export function HomeServiceCard({ category, priceState, onPress }: HomeServiceCardProps) {
  const { theme } = useTheme();
  const price = priceState ? resolveServicePriceDisplay(priceState) : null;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${category.name}${price ? `, ${price.label}` : ""}`}
      style={({ pressed }) => ({
        // Width is set by the parent grid, not here. It used to be a
        // hardcoded "48%", which meant a ZIP with a single bookable
        // category rendered one half-width tile beside a gaping empty
        // half-row -- correct data, broken-looking layout.
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
        {category.iconUrl ? (
          <Image source={{ uri: category.iconUrl }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
        ) : (
          // Distinct per-category glyph rather than one generic wrench for
          // everything -- see domain/categoryIcon.ts.
          <Icon
            name={resolveCategoryIcon(category.slug)}
            size="standard"
            color={theme.colors.brandPrimaryStrong}
            decorative
          />
        )}
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
