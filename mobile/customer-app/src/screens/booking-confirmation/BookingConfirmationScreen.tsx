import React from "react";
import { View } from "react-native";
import { useRoute, RouteProp, useNavigation, CommonActions } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppIconButton } from "../../components/AppIconButton";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { ConfirmationHero } from "../../components/booking-confirmation/ConfirmationHero";
import { BookingReference } from "../../components/booking-confirmation/BookingReference";
import { CurrentStatusCard } from "../../components/booking-confirmation/CurrentStatusCard";
import { BookingTimeline } from "../../components/booking-confirmation/BookingTimeline";
import { FinalizedServiceSummary } from "../../components/booking-confirmation/FinalizedServiceSummary";
import { FinalizedAddressCard } from "../../components/booking-confirmation/FinalizedAddressCard";
import { FinalizedPricingCard } from "../../components/booking-confirmation/FinalizedPricingCard";
import { BookingUpdatesCard } from "../../components/booking-confirmation/BookingUpdatesCard";
import { ReceiptActions } from "../../components/booking-confirmation/ReceiptActions";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { useCustomerBookingQuery } from "../../api/customerBookings/useCustomerBookingQuery";
import { isOffline } from "../../api/networkState";

type Route = RouteProp<CustomerAppStackParamList, "BookingConfirmation">;

/**
 * Loads the real, authenticated booking receipt from `bookingId` alone --
 * no navigation param carries price/provider/address/status (spec section
 * 2). Never re-calls finalization. Replaces the review route in history
 * (see BookingReviewScreen's `navigation.reset`), so the device back
 * button lands on Home, never on a stale confirmation mutation.
 */
export function BookingConfirmationScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const route = useRoute<Route>();
  const { bookingId } = route.params;
  const query = useCustomerBookingQuery(bookingId);

  function goHome() {
    navigation.dispatch(
      CommonActions.reset({ index: 0, routes: [{ name: "CustomerTabs" }] }),
    );
  }

  function viewBooking() {
    // Real Booking Details route (Booking Details phase) -- pushed on top
    // of Home so back returns there, never into the confirmation mutation.
    navigation.dispatch(CommonActions.reset({ index: 0, routes: [{ name: "CustomerTabs" }] }));
    (navigation as { navigate: (name: string, params: unknown) => void }).navigate("BookingDetails", { bookingId });
  }

  if (query.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading your booking" />
      </AppScreen>
    );
  }

  if (isOffline()) {
    return (
      <AppScreen>
        <OfflineBanner />
        <ErrorState title="You're offline" message="Reconnect to see your booking." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  if (query.isError) {
    return (
      <AppScreen>
        <ErrorState title="Something went wrong" message="We couldn't load your booking." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  if (query.data?.kind !== "found") {
    return (
      <AppScreen>
        <ErrorState
          title="We couldn't find this booking"
          message="It may not exist, or it may belong to a different account."
          actionLabel="Go to My Bookings"
          onAction={viewBooking}
        />
      </AppScreen>
    );
  }

  const receipt = query.data.receipt;

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <View style={{ flexDirection: "row", alignItems: "center" }}>
          <View style={{ flex: 1 }} />
          <AppText variant="headingSmall">Booking confirmed</AppText>
          <View style={{ flex: 1, alignItems: "flex-end" }}>
            <AppIconButton name="close" onPress={goHome} accessibilityLabel="Close" />
          </View>
        </View>

        <ConfirmationHero bookingNumber={receipt.bookingNumber} />
        <BookingReference bookingNumber={receipt.bookingNumber} savedToMyBookings />

        <CurrentStatusCard statusLabel={receipt.statusLabel} activityText={receipt.activityText} supportingText={receipt.supportingText} />
        <BookingTimeline currentStage={receipt.currentStage} />

        <View style={{ gap: theme.spacing.sm }}>
          <FinalizedServiceSummary service={receipt.service} />
          <FinalizedAddressCard address={receipt.address} />
          <FinalizedPricingCard pricing={receipt.pricing} />
          <BookingUpdatesCard capability={receipt.notificationCapability} />
        </View>

        <ReceiptActions onViewBooking={viewBooking} onBackToHome={goHome} />
        <AppText variant="caption" color="tertiary" align="center">You can find this request in My Bookings</AppText>
      </View>
    </AppScreen>
  );
}
