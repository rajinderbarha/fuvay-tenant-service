import React from "react";
import { View, ScrollView } from "react-native";
import { useNavigation, useRoute, type RouteProp, CommonActions } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useBookingDetail } from "../queries/booking-confirmation-queries";
import { formatCurrency } from "../../../localization/formatters";
import { getRequestLocale } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { SupportedLocale } from "../../../config/app-config";

type BookingConfirmationRouteProp = RouteProp<RootStackParamList, "BookingSuccess">;

const STATUS_COPY_KEYS: Record<string, string> = {
  pending_assignment: "bookingConfirmation.statusPendingAssignment",
  assigned: "bookingConfirmation.statusAssigned",
  in_progress: "bookingConfirmation.statusInProgress",
  completed: "bookingConfirmation.statusCompleted",
  cancelled: "bookingConfirmation.statusCancelled",
};

/**
 * The real production booking-confirmation screen (CUSTOMER-L5-11).
 * Fetches the canonical `ServiceBooking` via
 * `GET /v1/customer/my-activity/bookings/{bookingId}` rather than trusting
 * the `/confirm` mutation response alone (CUSTOMER-L5-11 §45). Reached
 * only via `navigation.reset()` from `BookingReviewScreen` — the
 * pre-booking stack (Review/Bargain/Pricing/ProviderPreview/...) is
 * discarded so Back cannot resubmit the same draft (§52).
 */
export function BookingConfirmationScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<BookingConfirmationRouteProp>();
  const { bookingId } = route.params;
  const locale = getRequestLocale() as SupportedLocale;

  const bookingQuery = useBookingDetail(bookingId);

  function returnHome() {
    logger.info("booking_return_home_selected", {});
    navigation.dispatch(CommonActions.reset({ index: 0, routes: [{ name: "Home" }] }));
  }

  if (bookingQuery.isPending) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <AppText variant="bodyMedium" color="textSecondary" align="center">
            {t("bookingConfirmation.loading")}
          </AppText>
        </View>
      </SafeAreaView>
    );
  }

  if (bookingQuery.isError || !bookingQuery.data) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppIcon name="alert-circle" size="lg" color="iconWarning" />
            <View style={{ flex: 1 }}>
              <AppText variant="titleLarge">{t("bookingConfirmation.unavailableTitle")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {t("bookingConfirmation.unavailableDescription")}
              </AppText>
            </View>
          </View>
          <View style={{ flex: 1 }} />
          <View style={{ gap: theme.spacing[3] }}>
            <AppButton label={t("bookingConfirmation.retry")} onPress={() => bookingQuery.refetch()} variant="primary" size="large" />
            <AppButton label={t("bookingConfirmation.returnHome")} onPress={returnHome} variant="secondary" size="large" />
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  const booking = bookingQuery.data;
  const statusKey = STATUS_COPY_KEYS[booking.status] ?? "bookingConfirmation.statusGeneric";
  const amount = booking.price_snapshot?.selected_price_amount;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
          <AppIcon name="checkmark-circle" size="lg" color="iconSuccess" />
          <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
            {t("bookingConfirmation.title")}
          </AppText>
        </View>

        <View style={{ gap: theme.spacing[1] }}>
          <AppText variant="bodySmall" color="textTertiary">
            {t("bookingConfirmation.referenceLabel")}
          </AppText>
          <AppText variant="titleLarge" selectable>
            {booking.booking_number}
          </AppText>
        </View>

        <AppText variant="bodyMedium" color="textSecondary">
          {t(statusKey)}
        </AppText>

        <ConfirmationRow label={t("bookingConfirmation.addressLabel")} value={formatBookingAddress(booking)} />
        {booking.preferred_time_window ? <ConfirmationRow label={t("bookingConfirmation.scheduleLabel")} value={booking.preferred_time_window} /> : null}
        {booking.provider_snapshot ? <ConfirmationRow label={t("bookingConfirmation.providerLabel")} value={booking.provider_snapshot.provider_name} /> : null}
        {amount != null ? <ConfirmationRow label={t("bookingConfirmation.priceLabel")} value={formatCurrency(amount, locale, "INR")} /> : null}

        <AppText variant="bodySmall" color="textSecondary">
          {t("bookingConfirmation.paymentPolicyText")}
        </AppText>

        <View style={{ flex: 1 }} />

        <AppButton label={t("bookingConfirmation.returnHome")} onPress={returnHome} variant="primary" size="large" testID="booking-confirmation-return-home" />
      </ScrollView>
    </SafeAreaView>
  );
}

function formatBookingAddress(booking: {
  address_snapshot: { address_line_1: string | null; landmark: string | null; city: string | null; state: string | null; zipcode: string | null } | null;
  city: string | null;
  zipcode: string | null;
}): string {
  const a = booking.address_snapshot;
  if (!a) return [booking.city, booking.zipcode].filter(Boolean).join(", ") || "—";
  return [a.address_line_1, a.landmark, a.city, a.state, a.zipcode].filter(Boolean).join(", ");
}

function ConfirmationRow(props: { label: string; value: string }) {
  const { theme } = useAppTheme();
  return (
    <View style={{ gap: theme.spacing[1] }}>
      <AppText variant="bodySmall" color="textTertiary">
        {props.label}
      </AppText>
      <AppText variant="bodyMedium">{props.value}</AppText>
    </View>
  );
}
