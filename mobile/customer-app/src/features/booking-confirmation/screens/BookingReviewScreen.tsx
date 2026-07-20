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
import { useBookingReviewFlow } from "../hooks/use-booking-review";
import { useConfirmBookingFlow } from "../hooks/use-confirm-booking";
import { useInvalidateDraftAfterBooking } from "../queries/booking-confirmation-queries";
import { formatCurrency } from "../../../localization/formatters";
import { getRequestLocale } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { SupportedLocale } from "../../../config/app-config";
import type { ValidatedBookingSummary } from "../domain/review-schema";

type BookingReviewRouteProp = RouteProp<RootStackParamList, "BookingReview">;

/**
 * The real production booking-review screen (CUSTOMER-L5-11). Calls the
 * real `/summary` endpoint (review) then the real, idempotent `/confirm`
 * endpoint (creates a genuine `ServiceBooking`+`ServiceJob`) — see
 * CUSTOMER-L5-11-contract-matrix.md. No consent checkbox is rendered:
 * the real backend has no consent/terms field anywhere in this flow to
 * persist an acknowledgement against (verified this sprint) — building
 * one would be UI with nothing real behind it. See known-gaps.md.
 */
export function BookingReviewScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<BookingReviewRouteProp>();
  const { bookingDraftId } = route.params;
  const locale = getRequestLocale() as SupportedLocale;

  const { state: reviewState, refresh } = useBookingReviewFlow(bookingDraftId);
  const { state: confirmState, confirm } = useConfirmBookingFlow(bookingDraftId);
  const invalidateDraft = useInvalidateDraftAfterBooking();

  const header = (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
      <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
        <AppIcon name="chevron-back" size="md" color="iconPrimary" />
      </AppPressable>
      <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
        {t("bookingReview.title")}
      </AppText>
    </View>
  );

  React.useEffect(() => {
    if (confirmState.kind === "confirmed") {
      logger.info("booking_confirmation_viewed", {});
      invalidateDraft(bookingDraftId);
      navigation.reset({ index: 0, routes: [{ name: "BookingSuccess", params: { bookingId: confirmState.result.booking_id } }] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [confirmState.kind]);

  if (reviewState.kind === "loading") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <AppText variant="bodyMedium" color="textSecondary" align="center">
            {t("bookingReview.loading")}
          </AppText>
        </View>
      </SafeAreaView>
    );
  }

  if (reviewState.kind === "preflight_failed") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <AppIcon name="alert-circle" size="lg" color="iconWarning" />
          <AppText variant="titleLarge" align="center">
            {t(reviewState.reasonKey)}
          </AppText>
          <AppButton
            label={t("bookingReview.changeAddress")}
            onPress={() => navigation.navigate("AddressSelection", { draftId: bookingDraftId })}
            variant="secondary"
            size="large"
          />
        </View>
      </SafeAreaView>
    );
  }

  if (reviewState.kind === "unavailable") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppIcon name="alert-circle" size="lg" color="iconWarning" />
            <View style={{ flex: 1 }}>
              <AppText variant="titleLarge">{t("bookingReview.unavailableTitle")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {t("bookingReview.unavailableDescription")}
              </AppText>
            </View>
          </View>
          <View style={{ flex: 1 }} />
          <AppButton label={t("bookingReview.retry")} onPress={refresh} variant="primary" size="large" />
        </ScrollView>
      </SafeAreaView>
    );
  }

  if (reviewState.kind === "not_ready") {
    const { summary } = reviewState;
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppIcon name="alert-circle" size="lg" color="iconWarning" />
            <View style={{ flex: 1 }}>
              <AppText variant="titleLarge">{t("bookingReview.notReadyTitle")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {t("bookingReview.notReadyDescription")}
              </AppText>
            </View>
          </View>
          <View style={{ gap: theme.spacing[3] }}>
            {summary.serviceability && !summary.serviceability.serviceable ? (
              <NotReadyRow
                label={t("bookingReview.notServiceable")}
                actionLabel={t("bookingReview.changeAddress")}
                onPress={() => navigation.navigate("AddressSelection", { draftId: bookingDraftId })}
              />
            ) : null}
            {!summary.selected_provider ? (
              <NotReadyRow
                label={t("bookingReview.noProvider")}
                actionLabel={t("bookingReview.findProvider")}
                onPress={() => navigation.navigate("ProviderPreview", { draftId: bookingDraftId })}
              />
            ) : null}
            {!summary.selected_price_tier ? (
              <NotReadyRow
                label={t("bookingReview.noPriceChoice")}
                actionLabel={t("bookingReview.choosePrice")}
                onPress={() => navigation.navigate("Bargain", { bookingDraftId })}
              />
            ) : null}
          </View>
          <View style={{ flex: 1 }} />
        </ScrollView>
      </SafeAreaView>
    );
  }

  const { summary } = reviewState;

  if (confirmState.kind === "confirming") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <AppText variant="bodyMedium" color="textSecondary" align="center">
            {t("bookingReview.confirming")}
          </AppText>
        </View>
      </SafeAreaView>
    );
  }

  if (confirmState.kind === "uncertain") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <AppIcon name="information-circle" size="lg" color="iconSecondary" />
          <AppText variant="titleLarge" align="center">
            {t("bookingReview.uncertainTitle")}
          </AppText>
          <AppText variant="bodySmall" color="textSecondary" align="center">
            {t("bookingReview.uncertainDescription")}
          </AppText>
          <AppButton label={t("bookingReview.checkStatus")} onPress={confirm} variant="primary" size="large" testID="booking-review-check-status" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        {header}

        <ReviewSection label={t("bookingReview.serviceLabel")}>
          <AppText variant="bodyMedium">{summary.offering_name ?? "—"}</AppText>
          {summary.issue_summary ? (
            <AppText variant="bodySmall" color="textSecondary">
              {summary.issue_summary}
            </AppText>
          ) : null}
        </ReviewSection>

        <ReviewSection
          label={t("bookingReview.addressLabel")}
          editLabel={t("bookingReview.editAddress")}
          onEdit={() => navigation.navigate("AddressSelection", { draftId: bookingDraftId })}
        >
          <AppText variant="bodyMedium">{formatAddress(summary)}</AppText>
        </ReviewSection>

        <ReviewSection label={t("bookingReview.scheduleLabel")}>
          <AppText variant="bodyMedium">{summary.preferred_time_window ?? t("bookingReview.noScheduleSet")}</AppText>
        </ReviewSection>

        {summary.selected_provider ? (
          <ReviewSection
            label={t("bookingReview.providerLabel")}
            editLabel={t("bookingReview.editProvider")}
            onEdit={() => navigation.navigate("ProviderPreview", { draftId: bookingDraftId })}
          >
            <AppText variant="bodyMedium">{summary.selected_provider.provider_name}</AppText>
            <AppText variant="bodySmall" color="textSecondary">
              {summary.selected_provider.rating != null ? `★ ${summary.selected_provider.rating.toFixed(1)}` : t("bookingReview.ratingNotYet")}
            </AppText>
          </ReviewSection>
        ) : null}

        {summary.customer_offer != null ? (
          <ReviewSection
            label={t("bookingReview.priceLabel")}
            editLabel={t("bookingReview.editPrice")}
            onEdit={() => navigation.navigate("Bargain", { bookingDraftId })}
          >
            <AppText variant="numericEmphasis">{formatCurrency(summary.customer_offer, locale, "INR")}</AppText>
          </ReviewSection>
        ) : null}

        <View style={{ gap: theme.spacing[1] }}>
          <AppText variant="titleSmall">{t("bookingReview.paymentPolicyTitle")}</AppText>
          <AppText variant="bodySmall" color="textSecondary">
            {t("bookingReview.paymentPolicyText")}
          </AppText>
        </View>

        <View style={{ gap: theme.spacing[1] }}>
          <AppText variant="titleSmall">{t("bookingReview.cancellationPolicyTitle")}</AppText>
          <AppText variant="bodySmall" color="textSecondary">
            {t("bookingReview.cancellationPolicyText")}
          </AppText>
        </View>

        {confirmState.kind === "failed" ? (
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
              <AppText variant="bodySmall">{t("bookingReview.confirmFailedTitle")}</AppText>
              <AppText variant="caption" color="textSecondary">
                {t("bookingReview.confirmFailedDescription")}
              </AppText>
            </View>
          </View>
        ) : null}

        <View style={{ flex: 1 }} />

        <AppButton label={t("bookingReview.confirmBooking")} onPress={confirm} variant="primary" size="large" testID="booking-review-confirm-button" />
      </ScrollView>
    </SafeAreaView>
  );
}

function formatAddress(summary: ValidatedBookingSummary): string {
  const a = summary.address;
  if (!a) return [summary.city, summary.zipcode].filter(Boolean).join(", ") || "—";
  return [a.address_line_1, a.landmark, a.city, a.state, a.zipcode].filter(Boolean).join(", ");
}

function NotReadyRow(props: { label: string; actionLabel: string; onPress: () => void }) {
  const { theme } = useAppTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: theme.spacing[3] }}>
      <AppText variant="bodySmall" color="textSecondary" style={{ flex: 1 }}>
        {props.label}
      </AppText>
      <AppButton label={props.actionLabel} onPress={props.onPress} variant="secondary" size="small" />
    </View>
  );
}

function ReviewSection(props: { label: string; editLabel?: string; onEdit?: () => void; children: React.ReactNode }) {
  const { theme } = useAppTheme();
  return (
    <View style={{ gap: theme.spacing[1] }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <AppText variant="titleSmall" color="textTertiary">
          {props.label}
        </AppText>
        {props.editLabel && props.onEdit ? (
          <AppPressable accessibilityLabel={props.editLabel} onPress={props.onEdit}>
            <AppText variant="labelSmall" color="textLink">
              {props.editLabel}
            </AppText>
          </AppPressable>
        ) : null}
      </View>
      {props.children}
    </View>
  );
}
