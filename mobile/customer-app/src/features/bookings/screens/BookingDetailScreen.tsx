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
import { ErrorState } from "../../../components/feedback/ErrorState";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useBookingDetail, useBookingTracking, useBookingReviewStatus } from "../queries/bookings-queries";
import { resolveBookingStatus } from "../domain/booking-status-registry";
import { isCancellationAvailable, isRescheduleAvailable } from "../domain/cancellation-reschedule-availability";
import { formatCurrency } from "../../../localization/formatters";
import { getRequestLocale } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { SupportedLocale } from "../../../config/app-config";

type BookingDetailRouteProp = RouteProp<RootStackParamList, "BookingDetail">;

/**
 * The real production booking-detail screen (CUSTOMER-L5-12). Calls the
 * real `GET /v1/customer/bookings/{id}` (detail),
 * `GET /v1/customer/bookings/{id}/tracking` (real lifecycle timeline,
 * built from `ServiceJobAssignmentEvent`), and, only when
 * `status === "completed"`, `GET /v1/customer/bookings/{id}/rating` (to
 * decide review-boundary visibility) — see
 * CUSTOMER-L5-12-contract-matrix.md. Cancellation/reschedule/technician/
 * invoice remain honest, non-interactive informational rows (§28) — no
 * real backend capability or typed route exists for either. "Track
 * provider" was promoted (CUSTOMER-L5-13) to a real button once a job
 * exists, navigating to the real (non-map, status-milestone-based)
 * `ServiceTrackingScreen`. "Parts & additional cost" is promoted this
 * sprint (CUSTOMER-L5-14) the same way, navigating to the real
 * `QuoteDecisionScreen` — see CUSTOMER-L5-14-contract-matrix.md.
 */
export function BookingDetailScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<BookingDetailRouteProp>();
  const { bookingId } = route.params;
  const locale = getRequestLocale() as SupportedLocale;

  React.useEffect(() => {
    logger.info("booking_detail_load_started", {});
  }, []);

  const detailQuery = useBookingDetail(bookingId);
  const trackingQuery = useBookingTracking(bookingId);
  const isCompleted = detailQuery.data?.status === "completed";
  const reviewQuery = useBookingReviewStatus(bookingId, isCompleted);

  const header = (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
      <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
        <AppIcon name="chevron-back" size="md" color="iconPrimary" />
      </AppPressable>
      <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
        {t("bookings.detail.title")}
      </AppText>
    </View>
  );

  if (detailQuery.isPending) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
        </View>
      </SafeAreaView>
    );
  }

  if (detailQuery.isError || !detailQuery.data) {
    const isNotFound = (detailQuery.error as { category?: string } | null)?.category === "not_found";
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <ErrorState
            title={isNotFound ? t("bookings.detail.notFoundTitle") : t("bookings.detail.loadErrorTitle")}
            description={isNotFound ? t("bookings.detail.notFoundDescription") : t("bookings.detail.loadErrorDescription")}
            onRetry={isNotFound ? undefined : () => detailQuery.refetch()}
          />
        </ScrollView>
      </SafeAreaView>
    );
  }

  const booking = detailQuery.data;
  const statusDef = resolveBookingStatus(booking.status);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        {header}

        <View style={{ gap: theme.spacing[1] }}>
          <AppText variant="bodySmall" color="textTertiary">
            {booking.booking_number}
          </AppText>
          <AppText variant="titleLarge">{t(statusDef.titleKey)}</AppText>
          {booking.assignment_message ? (
            <AppText variant="bodySmall" color="textSecondary">
              {booking.assignment_message}
            </AppText>
          ) : null}
        </View>

        {booking.issue_summary ? (
          <DetailSection label={t("bookings.detail.serviceLabel")}>
            <AppText variant="bodyMedium">{booking.issue_summary}</AppText>
          </DetailSection>
        ) : null}

        <DetailSection label={t("bookings.detail.addressLabel")}>
          <AppText variant="bodyMedium">{formatBookingAddress(booking.address, booking.city)}</AppText>
        </DetailSection>

        <DetailSection label={t("bookings.detail.scheduleLabel")}>
          <AppText variant="bodyMedium">{booking.scheduled_time_window ?? booking.preferred_time_window ?? t("bookings.detail.noScheduleSet")}</AppText>
        </DetailSection>

        {booking.selected_provider ? (
          <DetailSection label={t("bookings.detail.providerLabel")}>
            <AppText variant="bodyMedium">{booking.selected_provider.provider_name}</AppText>
            <AppText variant="bodySmall" color="textSecondary">
              {booking.selected_provider.rating != null ? `★ ${booking.selected_provider.rating.toFixed(1)}` : t("bookings.detail.ratingNotYet")}
            </AppText>
          </DetailSection>
        ) : null}

        {booking.selected_price_amount != null ? (
          <DetailSection label={t("bookings.detail.priceLabel")}>
            <AppText variant="numericEmphasis">{formatCurrency(booking.selected_price_amount, locale, "INR")}</AppText>
          </DetailSection>
        ) : null}

        <View style={{ gap: theme.spacing[1] }}>
          <AppText variant="titleSmall">{t("bookings.detail.paymentPolicyTitle")}</AppText>
          <AppText variant="bodySmall" color="textSecondary">
            {t("bookings.detail.paymentPolicyText")}
          </AppText>
        </View>

        <View style={{ gap: theme.spacing[2] }}>
          <AppText variant="titleSmall">{t("bookings.detail.timelineTitle")}</AppText>
          {trackingQuery.isPending ? (
            <Skeleton height={60} />
          ) : trackingQuery.isError || !trackingQuery.data ? (
            <AppText variant="bodySmall" color="textSecondary">
              {t("bookings.detail.timelineLoadError")}
            </AppText>
          ) : (
            <View style={{ gap: theme.spacing[3] }}>
              {trackingQuery.data.timeline.map((event, index) => (
                <View key={`${event.event_type ?? "confirmed"}-${index}`} style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing[3] }}>
                  <AppIcon name="checkmark-circle" size="sm" color="iconSuccess" />
                  <View style={{ flex: 1 }}>
                    <AppText variant="bodySmall">{event.event}</AppText>
                    {event.created_at ? (
                      <AppText variant="caption" color="textTertiary">
                        {new Date(event.created_at).toLocaleString(locale)}
                      </AppText>
                    ) : null}
                  </View>
                </View>
              ))}
            </View>
          )}
        </View>

        <View style={{ gap: theme.spacing[2] }}>
          <AppText variant="titleSmall">{t("bookings.detail.actionsTitle")}</AppText>
          {isCancellationAvailable(booking.status) || isRescheduleAvailable(booking.status) ? null : (
            <ActionRow
              label={t("bookings.detail.actionCancelReschedule")}
              note={t("bookings.detail.actionCancelRescheduleNote")}
              testID="booking-detail-cancel-reschedule-row"
            />
          )}
          {booking.job_status ? (
            <AppButton
              label={t("bookings.detail.actionTrack")}
              onPress={() => navigation.navigate("Tracking", { bookingId })}
              variant="secondary"
              size="small"
              testID="booking-detail-track-button"
            />
          ) : (
            <ActionRow label={t("bookings.detail.actionTrack")} note={t("bookings.detail.actionTrackNote")} />
          )}
          <ActionRow label={t("bookings.detail.actionTechnician")} note={t("bookings.detail.actionTechnicianNote")} />
          {booking.job_status ? (
            <AppButton
              label={t("bookings.detail.actionParts")}
              onPress={() => navigation.navigate("QuoteDecision", { bookingId })}
              variant="secondary"
              size="small"
              testID="booking-detail-quote-decision-button"
            />
          ) : (
            <ActionRow label={t("bookings.detail.actionParts")} note={t("bookings.detail.actionPartsNote")} />
          )}
          <ActionRow label={t("bookings.detail.actionInvoice")} note={t("bookings.detail.actionInvoiceNote")} />
          {isCompleted ? (
            reviewQuery.data?.review ? (
              <AppText variant="bodySmall" color="textSecondary">
                {t("bookings.detail.alreadyReviewed")}
              </AppText>
            ) : (
              <AppText variant="bodySmall" color="textSecondary">
                {t("bookings.detail.leaveReview")}
              </AppText>
            )
          ) : null}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function formatBookingAddress(
  address: { address_line_1: string | null; landmark: string | null; city: string | null; state: string | null; zipcode: string | null } | null,
  city: string | null
): string {
  if (!address) return city ?? "—";
  return [address.address_line_1, address.landmark, address.city, address.state, address.zipcode].filter(Boolean).join(", ");
}

function DetailSection(props: { label: string; children: React.ReactNode }) {
  const { theme } = useAppTheme();
  return (
    <View style={{ gap: theme.spacing[1] }}>
      <AppText variant="titleSmall" color="textTertiary">
        {props.label}
      </AppText>
      {props.children}
    </View>
  );
}

function ActionRow(props: { label: string; note: string; testID?: string }) {
  const { theme } = useAppTheme();
  return (
    <View style={{ gap: theme.spacing[1] }} testID={props.testID}>
      <AppText variant="bodySmall">{props.label}</AppText>
      <AppText variant="caption" color="textTertiary">
        {props.note}
      </AppText>
    </View>
  );
}
