import React from "react";
import { View, FlatList, RefreshControl, Pressable } from "react-native";
import { useRoute, RouteProp, useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { AppIconButton } from "../../components/AppIconButton";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { Icon } from "../../components/Icon";
import { useCustomerBookingsListQuery } from "../../api/customerBookings/useCustomerBookingsListQuery";
import { CustomerBookingListItem } from "../../domain/bookingList";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { isOffline } from "../../api/networkState";

type Route = RouteProp<CustomerAppStackParamList, "BookingSupportEntry">;
type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "BookingSupportEntry">;

const COPY: Record<Route["params"]["mode"], { title: string; subtitle: string }> = {
  help: { title: "Choose a booking", subtitle: "Select the booking you need help with." },
  safety: { title: "Choose a booking", subtitle: "Select the booking this concern is about." },
};

/**
 * Real My Bookings data only (spec section 5) -- the customer can select
 * only their own booking (query is already owner-scoped), and only
 * `bookingId` crosses into the next screen; nothing provider-internal is
 * ever passed through navigation.
 */
export function BookingSupportEntryScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { mode } = route.params;
  const query = useCustomerBookingsListQuery("all");
  const copy = COPY[mode];

  function handleSelect(bookingId: string) {
    if (mode === "help") {
      navigation.replace("BookingDetails", { bookingId });
    } else {
      navigation.replace("SafetyReport", { bookingId });
    }
  }

  if (query.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading your bookings…" />
      </AppScreen>
    );
  }

  if (query.isError && query.items.length === 0) {
    return (
      <AppScreen>
        <ErrorState title="We couldn't load your bookings." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  return (
    <AppScreen edges={["top", "bottom"]}>
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm, padding: theme.layout.screenHorizontalPadding, paddingBottom: 0 }}>
        <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
        <View style={{ flex: 1 }}>
          <AppText variant="headingSmall" accessibilityRole="header">{copy.title}</AppText>
          <AppText variant="bodySmall" color="secondary">{copy.subtitle}</AppText>
        </View>
      </View>

      {query.items.length === 0 ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: theme.layout.screenHorizontalPadding, gap: theme.spacing.sm }}>
          <Icon name="calendar-outline" size="feature" color={theme.colors.textSecondary} decorative />
          <AppText variant="bodyStrong" align="center">No bookings yet</AppText>
          <AppText variant="bodySmall" color="secondary" align="center">Once you book a service, it will appear here.</AppText>
        </View>
      ) : (
        <FlatList
          data={query.items}
          keyExtractor={item => item.bookingId}
          contentContainerStyle={{ padding: theme.layout.screenHorizontalPadding, gap: theme.spacing.sm }}
          refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => query.refetch()} />}
          renderItem={({ item }: { item: CustomerBookingListItem }) => (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`${item.serviceName ?? "Booking"}, ${item.statusLabel}`}
              onPress={() => handleSelect(item.bookingId)}
            >
              <AppCard style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
                <View style={{ flex: 1 }}>
                  <AppText variant="bodyStrong">{item.serviceName ?? item.bookingNumber ?? "Booking"}</AppText>
                  <AppText variant="bodySmall" color="secondary">{item.statusLabel}</AppText>
                </View>
                <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
              </AppCard>
            </Pressable>
          )}
        />
      )}
    </AppScreen>
  );
}
