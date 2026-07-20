import React from "react";
import { View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppCard } from "../../../components/primitives/AppCard";
import { AppText } from "../../../components/primitives/AppText";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { formatCurrency } from "../../../localization/formatters";
import type { SupportedLocale } from "../../../config/app-config";
import type { ValidatedOfferingSummary } from "../domain/offering-schema";

export interface ServiceListItemProps {
  offering: ValidatedOfferingSummary;
  locale: SupportedLocale;
  onPress: (offering: ValidatedOfferingSummary) => void;
}

/**
 * The backend never returns an image for an offering
 * (`_customer_offering_summary` omits `image_url`/`icon_url` even though
 * `MasterOffering` has both columns — CUSTOMER-L5-04-contract-matrix.md) —
 * a generic icon is used instead of fabricating stock imagery.
 */
export function ServiceListItem({ offering, locale, onPress }: ServiceListItemProps) {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");

  const hasStartingPrice = offering.starting_price > 0;

  return (
    <AppCard
      variant="interactive"
      onPress={() => onPress(offering)}
      accessibilityLabel={offering.name}
      style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[4] }}
    >
      <View style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center" }}>
        <AppIcon name="list" size="lg" color="iconPrimary" />
      </View>
      <View style={{ flex: 1, gap: theme.spacing[1] }}>
        <AppText variant="labelLarge" numberOfLines={2}>
          {offering.name}
        </AppText>
        {offering.description ? (
          <AppText variant="bodySmall" color="textSecondary" numberOfLines={2}>
            {offering.description}
          </AppText>
        ) : null}
        {hasStartingPrice ? (
          <AppText variant="labelMedium" color="textLink">
            {t("category.startingFrom", { price: formatCurrency(offering.starting_price, locale) })}
          </AppText>
        ) : null}
      </View>
      <AppIcon name="chevron-forward" size="sm" color="iconSecondary" />
    </AppCard>
  );
}
