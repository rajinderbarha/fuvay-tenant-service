import React, { useEffect } from "react";
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
import { useMatchProvider } from "../queries/provider-matching-queries";
import { resolveBadgeTranslationKey } from "../domain/badge-label-mapping";
import { logger } from "../../../observability/logger";
import type { RootStackParamList } from "../../../navigation/route-types";

type ProviderPreviewRouteProp = RouteProp<RootStackParamList, "ProviderPreview">;

/**
 * The real production provider-matching/preview screen (CUSTOMER-L5-08).
 * Calls the real, auto-match `POST /{draftId}/match-and-price` endpoint —
 * there is no candidate list to show and no selection step, because the
 * real backend auto-selects exactly one provider (see
 * CUSTOMER-L5-08-contract-matrix.md). Renders only the five real
 * `selected_provider` fields; pricing fields in the same response are never
 * parsed by this sprint's schema at all (CUSTOMER-L5-09 scope).
 */
export function ProviderPreviewScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<ProviderPreviewRouteProp>();
  const { draftId } = route.params;

  const matchProvider = useMatchProvider();
  const hasAttempted = matchProvider.isSuccess || matchProvider.isError;

  useEffect(() => {
    if (!hasAttempted && !matchProvider.isPending) {
      matchProvider.mutate(draftId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once on mount only.
  }, []);

  if (matchProvider.isPending || (!hasAttempted && !matchProvider.isIdle)) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <AppText variant="bodyMedium" color="textSecondary" align="center">
            {t("providerMatch.matching")}
          </AppText>
        </View>
      </SafeAreaView>
    );
  }

  const provider = matchProvider.data?.selected_provider;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
          <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
            <AppIcon name="chevron-back" size="md" color="iconPrimary" />
          </AppPressable>
          <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
            {t("providerMatch.title")}
          </AppText>
        </View>

        {provider ? (
          <View style={{ gap: theme.spacing[4] }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
              <AppIcon name="checkmark-circle" size="lg" color="iconSuccess" />
              <View style={{ flex: 1 }}>
                <AppText variant="titleLarge">{t("providerMatch.matchedTitle")}</AppText>
                <AppText variant="headingMedium">{provider.provider_name}</AppText>
              </View>
            </View>

            <AppText variant="bodyMedium" color="textSecondary">
              {provider.rating != null ? `★ ${provider.rating.toFixed(1)}` : t("providerMatch.ratingNotYet")}
            </AppText>

            {provider.public_badges.length > 0 ? (
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing[2] }}>
                {provider.public_badges.map((badge) => {
                  const key = resolveBadgeTranslationKey(badge);
                  const label = key ? t(key) : badge;
                  return (
                    <View
                      key={badge}
                      style={{
                        paddingHorizontal: theme.spacing[3] as number,
                        paddingVertical: theme.spacing[1] as number,
                        borderRadius: 999,
                        backgroundColor: theme.colors.backgroundSecondary,
                      }}
                    >
                      <AppText variant="caption" color="textSecondary">
                        {label}
                      </AppText>
                    </View>
                  );
                })}
              </View>
            ) : null}

            <View style={{ gap: theme.spacing[1] }}>
              <AppText variant="bodySmall" color="textTertiary">
                {t("providerMatch.reasonLabel")}
              </AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {provider.customer_visible_reason}
              </AppText>
            </View>
          </View>
        ) : (
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppIcon name="alert-circle" size="lg" color="iconWarning" />
            <View style={{ flex: 1 }}>
              <AppText variant="titleLarge">{t("providerMatch.noMatchTitle")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {t("providerMatch.noMatchDescription")}
              </AppText>
            </View>
          </View>
        )}

        <View style={{ flex: 1 }} />

        {provider ? (
          <AppButton
            label={t("providerMatch.continue")}
            onPress={() => {
              logger.info("provider_preview_continue", {});
              navigation.navigate("Pricing", { bookingDraftId: draftId });
            }}
            variant="primary"
            size="large"
            testID="provider-preview-continue-button"
          />
        ) : (
          <View style={{ gap: theme.spacing[3] }}>
            <AppButton label={t("providerMatch.retry")} onPress={() => matchProvider.mutate(draftId)} variant="primary" size="large" />
            <AppButton
              label={t("providerMatch.changeAddress")}
              onPress={() => navigation.navigate("AddressSelection", { draftId })}
              variant="secondary"
              size="large"
            />
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
