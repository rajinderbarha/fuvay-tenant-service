import React from "react";
import { Pressable, View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeCategory } from "../../domain/customerHome";
import { ServicePriceState, resolveServicePriceDisplay } from "../../domain/servicePricing";

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
      style={{
        width: "48%", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceDefault, borderWidth: 1, borderColor: theme.colors.borderSubtle,
        marginBottom: theme.spacing.sm,
      }}
    >
      <View
        style={{
          width: 40, height: 40, borderRadius: theme.radiusUsage.input,
          backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center",
          marginBottom: theme.spacing.sm, overflow: "hidden",
        }}
      >
        {category.iconUrl ? (
          <Image source={{ uri: category.iconUrl }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
        ) : (
          <Icon name="construct-outline" size="standard" color={theme.colors.iconDefault} decorative />
        )}
      </View>
      <AppText variant="bodyStrong" numberOfLines={1}>{category.name}</AppText>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: theme.spacing.xxs }}>
        <AppText variant="bodySmall" color={price?.isNumericPrice ? "secondary" : "tertiary"} numberOfLines={1}>
          {price?.label ?? "View details"}
        </AppText>
        <Icon name="chevron-forward" size="compact" color={theme.colors.iconDefault} decorative />
      </View>
    </Pressable>
  );
}
