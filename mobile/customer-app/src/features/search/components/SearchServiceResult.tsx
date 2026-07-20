import React from "react";
import { View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppCard } from "../../../components/primitives/AppCard";
import { AppText } from "../../../components/primitives/AppText";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { formatCurrency } from "../../../localization/formatters";
import type { SupportedLocale } from "../../../config/app-config";
import type { ValidatedOfferingSummary } from "../../category/domain/offering-schema";

export interface SearchServiceResultProps {
  offering: ValidatedOfferingSummary;
  locale: SupportedLocale;
}

/**
 * The search endpoint's offering results carry no `category_id`
 * (`_customer_offering_summary` — CUSTOMER-L5-04-contract-matrix.md), and
 * the real offering-detail endpoint is category-scoped
 * (`/categories/{category_slug}/offerings/{offering_slug}`) — so a
 * cross-category search result cannot be safely deep-linked to its detail
 * screen without inventing a destination the backend cannot actually serve.
 * Rather than guessing a category or building a broken link, this card is
 * intentionally non-navigable and says so — CUSTOMER-L5-04 §20's "validate
 * destination" requirement, applied honestly. See known-gaps.md.
 */
export function SearchServiceResult({ offering, locale }: SearchServiceResultProps) {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const hasStartingPrice = offering.starting_price > 0;

  return (
    <AppCard variant="default" accessibilityLabel={offering.name} style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[4] }}>
      <AppIcon name="list" size="lg" color="iconSecondary" />
      <View style={{ flex: 1, gap: theme.spacing[1] }}>
        <AppText variant="labelLarge" numberOfLines={2}>
          {offering.name}
        </AppText>
        {hasStartingPrice ? (
          <AppText variant="labelMedium" color="textLink">
            {t("category.startingFrom", { price: formatCurrency(offering.starting_price, locale) })}
          </AppText>
        ) : null}
        <AppText variant="caption" color="textTertiary">
          {t("search.openFromCategoryHint")}
        </AppText>
      </View>
    </AppCard>
  );
}
