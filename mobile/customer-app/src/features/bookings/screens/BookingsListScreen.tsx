import React from "react";
import { View, FlatList, RefreshControl } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useBookingsListView } from "../hooks/use-bookings-list-view";
import { resolveBookingStatus } from "../domain/booking-status-registry";
import { formatCurrency } from "../../../localization/formatters";
import { getRequestLocale } from "../../../api/request-context";
import type { SupportedLocale } from "../../../config/app-config";
import type { ValidatedBookingListItem } from "../domain/booking-list-schema";

/**
 * The real production My Bookings screen (CUSTOMER-L5-12). Calls the
 * real, already-customer-safe `GET /v1/customer/bookings` endpoint — see
 * CUSTOMER-L5-12-contract-matrix.md. The Active/Past segmented control
 * filters client-side over whatever has been loaded via real pagination
 * so far, since this endpoint has no status/date filter param at all (a
 * real, disclosed backend limitation — see list-architecture.md); this
 * is never a fabricated server-side filter.
 */
export function BookingsListScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const locale = getRequestLocale() as SupportedLocale;

  const { activeGroup, setActiveGroup, items, isLoading, isError, isFetchingNextPage, hasNextPage, loadMore, refresh, isRefreshing } = useBookingsListView();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "left", "right"]}>
      <View style={{ paddingHorizontal: theme.sizes.screenHorizontalPadding as number, paddingTop: theme.spacing[4] as number, gap: theme.spacing[4] }}>
        <AppText variant="headingLarge" accessibilityRole="header">
          {t("bookings.list.title")}
        </AppText>
        <View style={{ flexDirection: "row", gap: theme.spacing[2] }}>
          <SegmentButton label={t("bookings.list.active")} active={activeGroup === "active"} onPress={() => setActiveGroup("active")} />
          <SegmentButton label={t("bookings.list.past")} active={activeGroup === "past"} onPress={() => setActiveGroup("past")} />
        </View>
      </View>

      {isLoading ? (
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[3] }}>
          <Skeleton height={88} />
          <Skeleton height={88} />
          <Skeleton height={88} />
        </View>
      ) : isError ? (
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState title={t("bookings.list.loadError")} onRetry={refresh} />
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.booking_id}
          contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[3], flexGrow: 1 }}
          refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={refresh} />}
          onEndReachedThreshold={0.4}
          onEndReached={loadMore}
          ListEmptyComponent={
            <View style={{ flex: 1, justifyContent: "center", alignItems: "center", gap: theme.spacing[2], paddingTop: theme.spacing[8] as number }}>
              <AppText variant="titleLarge">{t("bookings.list.empty")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {activeGroup === "active" ? t("bookings.list.emptyActiveDescription") : t("bookings.list.emptyPastDescription")}
              </AppText>
            </View>
          }
          ListFooterComponent={
            hasNextPage && isFetchingNextPage ? (
              <AppText variant="bodySmall" color="textSecondary" align="center">
                {t("bookings.list.loadingMore")}
              </AppText>
            ) : null
          }
          renderItem={({ item }) => (
            <BookingCard
              item={item}
              locale={locale}
              viewDetailsLabel={t("bookings.list.viewDetails")}
              statusLabel={t(resolveBookingStatus(item.status).titleKey)}
              onPress={() => navigation.navigate("BookingDetail", { bookingId: item.booking_id })}
            />
          )}
        />
      )}
    </SafeAreaView>
  );
}

function SegmentButton(props: { label: string; active: boolean; onPress: () => void }) {
  const { theme } = useAppTheme();
  return (
    <AppPressable
      accessibilityRole="button"
      accessibilityState={{ selected: props.active }}
      onPress={props.onPress}
      style={{
        paddingHorizontal: theme.spacing[4] as number,
        paddingVertical: theme.spacing[2] as number,
        borderRadius: 999,
        backgroundColor: props.active ? theme.colors.backgroundSecondary : "transparent",
      }}
    >
      <AppText variant="labelLarge" color={props.active ? "textPrimary" : "textSecondary"}>
        {props.label}
      </AppText>
    </AppPressable>
  );
}

function BookingCard(props: { item: ValidatedBookingListItem; locale: SupportedLocale; statusLabel: string; viewDetailsLabel: string; onPress: () => void }) {
  const { theme } = useAppTheme();
  const { item, locale, statusLabel, viewDetailsLabel, onPress } = props;
  return (
    <AppPressable
      accessibilityRole="button"
      accessibilityLabel={`${item.booking_number} — ${statusLabel}`}
      onPress={onPress}
      style={{ padding: theme.spacing[4] as number, borderRadius: 12, borderWidth: 1, borderColor: theme.colors.borderDefault, gap: theme.spacing[1] }}
    >
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <AppText variant="titleSmall">{item.booking_number}</AppText>
        <AppText variant="labelSmall" color="textSecondary">
          {statusLabel}
        </AppText>
      </View>
      {item.issue_summary ? (
        <AppText variant="bodySmall" color="textSecondary">
          {item.issue_summary}
        </AppText>
      ) : null}
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <AppText variant="caption" color="textTertiary">
          {[item.selected_provider?.provider_name, item.city].filter(Boolean).join(" · ")}
        </AppText>
        {item.selected_price_amount != null ? <AppText variant="bodySmall">{formatCurrency(item.selected_price_amount, locale, "INR")}</AppText> : null}
      </View>
      <AppButton label={viewDetailsLabel} onPress={onPress} variant="secondary" size="small" />
    </AppPressable>
  );
}
