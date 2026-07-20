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
import { useBargain } from "../hooks/use-bargain";
import { formatCurrency } from "../../../localization/formatters";
import { getRequestLocale } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { SupportedLocale } from "../../../config/app-config";
import type { PriceTier } from "../domain/bargain-schema";
import type { ValidatedPriceOptions } from "../../pricing/domain/pricing-schema";

type BargainRouteProp = RouteProp<RootStackParamList, "Bargain">;

const TIER_ORDER: readonly PriceTier[] = ["low", "mid", "high"];

/**
 * The real production bargain screen (CUSTOMER-L5-10). This platform has
 * no bargain-session, counteroffer, attempt-limit, or rate-limit engine
 * reachable by customers — exhaustively verified this sprint, including
 * the decisive confirmation that the raw-offer/floor "manual bargain"
 * module is feature-flagged off by product decision
 * (`MANUAL_BARGAIN_RULES_ENABLED = False`). The real, live capability is
 * exactly what this screen implements: pick one of the three
 * backend-computed tiers via `confirm-price-choice`; the backend resolves
 * and stores the exact amount. See CUSTOMER-L5-10-contract-matrix.md and
 * CUSTOMER-L5-10-bargain-architecture.md.
 */
export function BargainScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<BargainRouteProp>();
  const { bookingDraftId } = route.params;
  const locale = getRequestLocale() as SupportedLocale;

  const { state, chooseTier, changeSelection, refreshEstimate } = useBargain(bookingDraftId);

  const header = (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
      <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
        <AppIcon name="chevron-back" size="md" color="iconPrimary" />
      </AppPressable>
      <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
        {t("bargain.title")}
      </AppText>
    </View>
  );

  if (state.kind === "loading_estimate") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <AppText variant="bodyMedium" color="textSecondary" align="center">
            {t("bargain.loadingEstimate")}
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
            label={t("bargain.changeAddress")}
            onPress={() => navigation.navigate("AddressSelection", { draftId: bookingDraftId })}
            variant="secondary"
            size="large"
          />
        </View>
      </SafeAreaView>
    );
  }

  if (state.kind === "estimate_unavailable") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppIcon name="alert-circle" size="lg" color="iconWarning" />
            <View style={{ flex: 1 }}>
              <AppText variant="titleLarge">{t("bargain.unavailableTitle")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {t("bargain.unavailableDescription")}
              </AppText>
            </View>
          </View>
          <View style={{ flex: 1 }} />
          <View style={{ gap: theme.spacing[3] }}>
            <AppButton label={t("bargain.retry")} onPress={refreshEstimate} variant="primary" size="large" />
            <AppButton
              label={t("bargain.changeAddress")}
              onPress={() => navigation.navigate("AddressSelection", { draftId: bookingDraftId })}
              variant="secondary"
              size="large"
            />
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  if (state.kind === "confirmed") {
    const { summary } = state;
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppIcon name="checkmark-circle" size="lg" color="iconSuccess" />
            <View style={{ flex: 1 }}>
              <AppText variant="titleLarge">{t("bargain.confirmedTitle")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {t("bargain.confirmedDescription")}
              </AppText>
            </View>
          </View>

          <AppText variant="numericEmphasis">{formatCurrency(summary.customer_offer, locale, "INR")}</AppText>

          {summary.selected_provider_name ? (
            <AppText variant="bodySmall" color="textSecondary">
              {summary.selected_provider_name}
            </AppText>
          ) : null}

          <AppText variant="bodySmall" color="textSecondary">
            {t("bargain.paymentModeNote")}
          </AppText>

          <AppPressable accessibilityLabel={t("bargain.changeSelection")} onPress={changeSelection}>
            <AppText variant="labelLarge" color="textLink">
              {t("bargain.changeSelection")}
            </AppText>
          </AppPressable>

          <View style={{ flex: 1 }} />

          <AppButton
            label={t("bargain.continue")}
            onPress={() => {
              logger.info("bargain_completed", { tier: summary.selected_price_tier });
              navigation.navigate("BookingReview", { bookingDraftId });
            }}
            variant="primary"
            size="large"
            testID="bargain-continue-button"
          />
        </ScrollView>
      </SafeAreaView>
    );
  }

  const { options, provider } = state;
  const isConfirming = state.kind === "confirming";
  const confirmFailed = state.kind === "confirm_failed";
  const pendingTier = state.kind === "confirming" ? state.tier : null;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        {header}

        <AppText variant="bodySmall" color="textSecondary">
          {provider.provider_name}
        </AppText>

        <AppText variant="bodyMedium" color="textSecondary">
          {t("bargain.chooseInstruction")}
        </AppText>

        {confirmFailed ? (
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
            <AppIcon name="alert-circle" size="sm" color="iconWarning" />
            <View style={{ flex: 1 }}>
              <AppText variant="bodySmall">{t("bargain.confirmFailedTitle")}</AppText>
              <AppText variant="caption" color="textSecondary">
                {t("bargain.confirmFailedDescription")}
              </AppText>
            </View>
          </View>
        ) : null}

        <View style={{ gap: theme.spacing[3] }}>
          {TIER_ORDER.map((tier) => (
            <TierOption
              key={tier}
              tier={tier}
              options={options}
              locale={locale}
              label={t(tierLabelKey(tier))}
              chooseLabel={t("bargain.choose")}
              confirmingLabel={t("bargain.confirming")}
              isPending={isConfirming && pendingTier === tier}
              disabled={isConfirming}
              onChoose={() => chooseTier(tier)}
              theme={theme}
            />
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function tierLabelKey(tier: PriceTier): string {
  if (tier === "low") return "bargain.lowerOption";
  if (tier === "high") return "bargain.upperOption";
  return "bargain.expectedOption";
}

function tierAmount(tier: PriceTier, options: ValidatedPriceOptions): number {
  if (tier === "low") return options.low_price;
  if (tier === "high") return options.high_price;
  return options.mid_price;
}

function TierOption(props: {
  tier: PriceTier;
  options: ValidatedPriceOptions;
  locale: SupportedLocale;
  label: string;
  chooseLabel: string;
  confirmingLabel: string;
  isPending: boolean;
  disabled: boolean;
  onChoose: () => void;
  theme: ReturnType<typeof useAppTheme>["theme"];
}) {
  const { tier, options, locale, label, chooseLabel, confirmingLabel, isPending, disabled, onChoose, theme } = props;
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        padding: theme.spacing[4] as number,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: theme.colors.borderDefault,
      }}
    >
      <View>
        <AppText variant="caption" color="textTertiary">
          {label}
        </AppText>
        <AppText variant="titleLarge">{formatCurrency(tierAmount(tier, options), locale, options.currency)}</AppText>
      </View>
      <AppButton
        label={isPending ? confirmingLabel : chooseLabel}
        onPress={onChoose}
        variant="secondary"
        size="medium"
        disabled={disabled}
        testID={`bargain-choose-${tier}`}
      />
    </View>
  );
}
