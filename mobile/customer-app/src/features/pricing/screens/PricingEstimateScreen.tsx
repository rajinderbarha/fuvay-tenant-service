import React from "react";
import { View, ScrollView } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { usePricingEstimate } from "../hooks/use-pricing-estimate";
import { isSinglePointEstimate } from "../domain/pricing-schema";
import { formatCurrency } from "../../../localization/formatters";
import { getRequestLocale } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { SupportedLocale } from "../../../config/app-config";

type PricingEstimateRouteProp = RouteProp<RootStackParamList, "Pricing">;

/**
 * The real production pricing-estimate screen (CUSTOMER-L5-09). Calls the
 * real, backend-authoritative `POST /{draftId}/match-and-price` endpoint —
 * the same endpoint CUSTOMER-L5-08's ProviderPreviewScreen already uses,
 * now parsing the price-options fields that sprint deliberately ignored.
 * Never computes Low/Mid/High client-side (`mid_price` is a real,
 * backend-computed value) and never exposes internal-only fields
 * (platform fee, allowed-offer bounds) — see
 * CUSTOMER-L5-09-contract-matrix.md.
 */
export function PricingEstimateScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<PricingEstimateRouteProp>();
  const { bookingDraftId } = route.params;
  const locale = getRequestLocale() as SupportedLocale;

  const { state, refresh } = usePricingEstimate(bookingDraftId);

  const header = (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
      <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
        <AppIcon name="chevron-back" size="md" color="iconPrimary" />
      </AppPressable>
      <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
        {t("pricing.title")}
      </AppText>
    </View>
  );

  if (state.kind === "idle" || state.kind === "calculating") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <AppText variant="bodyMedium" color="textSecondary" align="center">
            {state.kind === "calculating" && state.isRevalidating ? t("pricing.revalidating") : t("pricing.calculating")}
          </AppText>
        </View>
      </SafeAreaView>
    );
  }

  if (state.kind === "preflight_failed") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <AppIcon name="alert-circle" size="lg" color="iconWarning" />
          <AppText variant="titleLarge" align="center">
            {t(state.reasonKey)}
          </AppText>
          <AppButton
            label={t("serviceability.changeAddress")}
            onPress={() => navigation.navigate("AddressSelection", { draftId: bookingDraftId })}
            variant="secondary"
            size="large"
          />
        </View>
      </SafeAreaView>
    );
  }

  if (state.kind === "unavailable" || state.kind === "failed") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppIcon name="alert-circle" size="lg" color="iconWarning" />
            <View style={{ flex: 1 }}>
              <AppText variant="titleLarge">{t("pricing.unavailableTitle")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {t("pricing.unavailableDescription")}
              </AppText>
            </View>
          </View>
          <View style={{ flex: 1 }} />
          <View style={{ gap: theme.spacing[3] }}>
            <AppButton label={t("pricing.retry")} onPress={refresh} variant="primary" size="large" />
            <AppButton
              label={t("pricing.changeAddress")}
              onPress={() => navigation.navigate("AddressSelection", { draftId: bookingDraftId })}
              variant="secondary"
              size="large"
            />
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  const { options, provider, revised } = state;
  const singlePoint = isSinglePointEstimate(options);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        {header}

        <AppText variant="bodySmall" color="textSecondary">
          {provider.provider_name}
        </AppText>

        {revised ? (
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: theme.spacing[2] as number,
              padding: theme.spacing[3] as number,
              borderRadius: 8,
              backgroundColor: theme.colors.backgroundSecondary,
            }}
            accessibilityRole="alert"
          >
            <AppIcon name="information-circle" size="sm" color="iconSecondary" />
            <AppText variant="bodySmall" color="textSecondary" style={{ flex: 1 }}>
              {t("pricing.revisedBanner")}
            </AppText>
          </View>
        ) : null}

        {singlePoint ? (
          <View style={{ gap: theme.spacing[1] }}>
            <AppText variant="bodySmall" color="textTertiary">
              {t("pricing.singlePointLabel")}
            </AppText>
            <AppText variant="numericEmphasis">{formatCurrency(options.mid_price, locale, options.currency)}</AppText>
          </View>
        ) : (
          <View style={{ gap: theme.spacing[4] }}>
            <View style={{ gap: theme.spacing[1] }}>
              <AppText variant="bodySmall" color="textTertiary">
                {t("pricing.expectedLabel")}
              </AppText>
              <AppText variant="numericEmphasis">{formatCurrency(options.mid_price, locale, options.currency)}</AppText>
            </View>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <View style={{ gap: theme.spacing[1] }}>
                <AppText variant="caption" color="textTertiary">
                  {t("pricing.lowerLabel")}
                </AppText>
                <AppText variant="titleLarge">{formatCurrency(options.low_price, locale, options.currency)}</AppText>
              </View>
              <View style={{ gap: theme.spacing[1], alignItems: "flex-end" }}>
                <AppText variant="caption" color="textTertiary">
                  {t("pricing.upperLabel")}
                </AppText>
                <AppText variant="titleLarge">{formatCurrency(options.high_price, locale, options.currency)}</AppText>
              </View>
            </View>
          </View>
        )}

        <View style={{ gap: theme.spacing[2] }}>
          <AppText variant="bodySmall" color="textSecondary">
            {t("pricing.paymentModeNote")}
          </AppText>
          <AppText variant="bodySmall" color="textSecondary">
            {t("pricing.taxNote")}
          </AppText>
          <AppText variant="caption" color="textTertiary">
            {t("pricing.finalPriceNote")}
          </AppText>
        </View>

        <AppPressable accessibilityLabel={t("pricing.refresh")} onPress={refresh}>
          <AppText variant="labelLarge" color="textLink">
            {t("pricing.refresh")}
          </AppText>
        </AppPressable>

        <View style={{ flex: 1 }} />

        <AppButton
          label={t("pricing.continue")}
          onPress={() => {
            logger.info("pricing_continue_selected", {});
            navigation.navigate("Bargain", { bookingDraftId });
          }}
          variant="primary"
          size="large"
          testID="pricing-continue-button"
        />
      </ScrollView>
    </SafeAreaView>
  );
}
