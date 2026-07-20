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
import { useServiceTracking } from "../hooks/use-service-tracking";
import { resolveExecutionEventLabelKey } from "../domain/execution-event-labels";
import { resolveBookingStatus } from "../../bookings/domain/booking-status-registry";
import { getRequestLocale } from "../../../api/request-context";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { SupportedLocale } from "../../../config/app-config";

type ServiceTrackingRouteProp = RouteProp<RootStackParamList, "Tracking">;

/**
 * The real production service-tracking screen (CUSTOMER-L5-13). A
 * deliberate, honest **non-map, status-milestone-based** experience — no
 * live GPS location, map, marker, ETA, route, or masked-call action
 * exists anywhere in the real backend for this pipeline (exhaustively
 * verified this sprint, see CUSTOMER-L5-13-baseline-verification.md's
 * Central Findings #4). Renders the real execution timeline from
 * `GET /v1/customer/service-jobs/{jobId}/tracking`.
 */
export function ServiceTrackingScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<ServiceTrackingRouteProp>();
  const { bookingId } = route.params;
  const locale = getRequestLocale() as SupportedLocale;

  const { bookingQuery, jobId, trackingQuery } = useServiceTracking(bookingId);

  const header = (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
      <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
        <AppIcon name="chevron-back" size="md" color="iconPrimary" />
      </AppPressable>
      <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
        {t("serviceTracking.title")}
      </AppText>
    </View>
  );

  if (bookingQuery.isPending) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <AppText variant="bodyMedium" color="textSecondary" align="center">
            {t("serviceTracking.loading")}
          </AppText>
        </View>
      </SafeAreaView>
    );
  }

  if (bookingQuery.isError || !bookingQuery.data) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <AppIcon name="alert-circle" size="lg" color="iconWarning" />
          <AppText variant="titleLarge">{t("serviceTracking.unavailableTitle")}</AppText>
          <AppText variant="bodySmall" color="textSecondary">
            {t("serviceTracking.unavailableDescription")}
          </AppText>
          <AppButton label={t("serviceTracking.retry")} onPress={() => bookingQuery.refetch()} variant="primary" size="large" />
        </ScrollView>
      </SafeAreaView>
    );
  }

  if (!jobId) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
        <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
          {header}
          <AppIcon name="information-circle" size="lg" color="iconSecondary" />
          <AppText variant="titleLarge">{t("serviceTracking.noJobTitle")}</AppText>
          <AppText variant="bodySmall" color="textSecondary">
            {t("serviceTracking.noJobDescription")}
          </AppText>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        {header}

        {trackingQuery.isPending ? (
          <Skeleton height={28} width="70%" />
        ) : trackingQuery.isError || !trackingQuery.data ? (
          <View style={{ gap: theme.spacing[3] }}>
            <AppText variant="bodySmall" color="textSecondary">
              {t("serviceTracking.unavailableDescription")}
            </AppText>
            <AppButton label={t("serviceTracking.retry")} onPress={() => trackingQuery.refetch()} variant="secondary" size="medium" />
          </View>
        ) : (
          <>
            <View style={{ gap: theme.spacing[1] }}>
              <AppText variant="titleSmall" color="textTertiary">
                {t("serviceTracking.currentStatusTitle")}
              </AppText>
              <AppText variant="titleLarge">{t(resolveBookingStatus(trackingQuery.data.status).titleKey)}</AppText>
            </View>

            <View style={{ gap: theme.spacing[3] }}>
              <AppText variant="titleSmall" color="textTertiary">
                {t("serviceTracking.timelineTitle")}
              </AppText>
              {trackingQuery.data.timeline
                .map((event, index) => {
                  const labelKey = resolveExecutionEventLabelKey(event.event_type);
                  if (!labelKey) return null;
                  return (
                    <View key={`${event.event_type}-${index}`} style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing[3] }}>
                      <AppIcon name="checkmark-circle" size="sm" color="iconSuccess" />
                      <View style={{ flex: 1 }}>
                        <AppText variant="bodySmall">{t(labelKey)}</AppText>
                        {event.created_at ? (
                          <AppText variant="caption" color="textTertiary">
                            {new Date(event.created_at).toLocaleString(locale)}
                          </AppText>
                        ) : null}
                      </View>
                    </View>
                  );
                })
                .filter(Boolean)}
            </View>
          </>
        )}

        <View style={{ gap: theme.spacing[1] }}>
          <AppText variant="titleSmall" color="textTertiary">
            {t("serviceTracking.contactTitle")}
          </AppText>
          <AppText variant="caption" color="textTertiary">
            {t("serviceTracking.contactNote")}
          </AppText>
        </View>

        <AppText variant="caption" color="textTertiary">
          {t("serviceTracking.locationNote")}
        </AppText>
      </ScrollView>
    </SafeAreaView>
  );
}
