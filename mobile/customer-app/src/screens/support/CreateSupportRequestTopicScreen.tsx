import React, { useEffect, useState } from "react";
import { View, Pressable, Alert } from "react-native";
import { useRoute, RouteProp, useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { AppButton } from "../../components/AppButton";
import { AppIconButton } from "../../components/AppIconButton";
import { Icon } from "../../components/Icon";
import { useCustomerBookingsListQuery } from "../../api/customerBookings/useCustomerBookingsListQuery";
import { CustomerBookingListItem } from "../../domain/bookingList";
import { SUPPORT_CATEGORIES, resolveSupportCategoryPresentation, SupportCategoryCode } from "../../domain/supportCategoryPresentation";
import { isSupportRequestDraftDirty } from "../../domain/supportRequestDraft";
import { useSupportRequestWizard } from "./SupportRequestWizardContext";
import { SupportRequestWizardParamList } from "../../navigation/supportRequestWizardTypes";

type Route = RouteProp<SupportRequestWizardParamList, "Topic">;
type Nav = NativeStackNavigationProp<SupportRequestWizardParamList, "Topic">;

const STEPS = ["Topic", "Details", "Review"] as const;

/**
 * Step 1 of 3 -- topic + optional booking context. No backend mutation
 * happens anywhere on this screen (spec section 9): "Continue" only
 * advances the shared wizard draft (`SupportRequestWizardContext`).
 * Booking linkage uses the same real, owner-scoped
 * `useCustomerBookingsListQuery` as the rest of the app; a `bookingId`
 * passed in via route params is only ever treated as a pre-selection to
 * look up again from that same owned list -- never trusted or displayed
 * until it's found there, so a forged foreign booking id in navigation
 * params simply fails to match and is treated as no selection (spec
 * section 7).
 */
export function CreateSupportRequestTopicScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const bookingsQuery = useCustomerBookingsListQuery("all");
  const { draft, setDraft } = useSupportRequestWizard();

  const [showBookingPicker, setShowBookingPicker] = useState(false);
  const routeBookingId = route.params?.bookingId;
  useEffect(() => {
    if (routeBookingId) {
      setDraft(d => (d.bookingId ? d : { ...d, bookingId: routeBookingId }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeBookingId]);

  const selectedCategory = draft.categoryCode ? resolveSupportCategoryPresentation(draft.categoryCode) : null;
  const ownedBookings = bookingsQuery.items;
  // A forged/foreign booking id in route params (or a booking that no
  // longer exists) simply never matches this owner-scoped list -- it is
  // never displayed, never trusted (spec section 7).
  const linkedBooking = draft.bookingId ? ownedBookings.find(b => b.bookingId === draft.bookingId) ?? null : null;

  function handleBack() {
    if (isSupportRequestDraftDirty(draft)) {
      confirmDiscard(() => navigation.goBack());
    } else {
      navigation.goBack();
    }
  }

  function confirmDiscard(onDiscard: () => void) {
    Alert.alert("Discard this request?", "Information you've entered will be removed.", [
      { text: "Keep editing", style: "cancel" },
      { text: "Discard", style: "destructive", onPress: onDiscard },
    ]);
  }

  function selectCategory(code: SupportCategoryCode) {
    const presentation = resolveSupportCategoryPresentation(code);
    if (presentation?.reroute) {
      const reroute = presentation.reroute;
      const doReroute = () => (navigation.getParent()?.navigate as (name: string, params?: object) => void)?.(reroute.screen, reroute.params);
      if (isSupportRequestDraftDirty(draft)) {
        confirmDiscard(doReroute);
      } else {
        doReroute();
      }
      return;
    }
    setDraft(d => ({ ...d, categoryCode: code, bookingId: presentation?.bookingApplicable ? d.bookingId : null }));
  }

  function handleContinue() {
    navigation.navigate("Details");
  }

  const canContinue = !!selectedCategory && !selectedCategory.reroute;

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <AppIconButton name="chevron-back" onPress={handleBack} accessibilityLabel="Go back" />
          <View style={{ flex: 1 }}>
            <AppText variant="headingSmall" accessibilityRole="header">Create request</AppText>
            <AppText variant="bodySmall" color="secondary">Tell us what you need help with</AppText>
          </View>
        </View>

        <AppCard style={{ gap: theme.spacing.xs }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <AppText variant="labelStrong">Step 1 of 3</AppText>
            <AppText variant="bodySmall" color="secondary">Topic & context</AppText>
          </View>
          <View
            accessibilityRole="progressbar" accessibilityLabel="Step 1 of 3: Topic & context"
            style={{ height: 4, borderRadius: 2, backgroundColor: theme.colors.surfaceInteractive, overflow: "hidden" }}
          >
            <View style={{ width: "33%", height: "100%", backgroundColor: theme.colors.brandPrimary }} />
          </View>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            {STEPS.map((label, i) => (
              <AppText key={label} variant="caption" color={i === 0 ? "primary" : "tertiary"}>{label}</AppText>
            ))}
          </View>
        </AppCard>

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">What do you need help with?</AppText>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
            {SUPPORT_CATEGORIES.map(cat => {
              const isSelected = draft.categoryCode === cat.code;
              return (
                <Pressable
                  key={cat.code}
                  accessibilityRole="radio" accessibilityState={{ checked: isSelected }}
                  accessibilityLabel={`${cat.label}: ${cat.helperText}`}
                  onPress={() => selectCategory(cat.code)}
                  style={{ flexBasis: "47%", flexGrow: 1 }}
                >
                  <AppCard
                    style={{
                      gap: theme.spacing.xs,
                      borderColor: isSelected ? theme.colors.brandPrimary : theme.colors.borderSubtle,
                      borderWidth: isSelected ? 2 : 1,
                      backgroundColor: isSelected ? theme.colors.brandPrimaryMuted : theme.colors.surfaceDefault,
                    }}
                  >
                    <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <Icon name={cat.icon} size="standard" color={isSelected ? theme.colors.brandPrimary : theme.colors.textSecondary} decorative />
                      {isSelected ? <Icon name="checkmark-circle" size="compact" color={theme.colors.brandPrimaryStrong} decorative /> : null}
                    </View>
                    <AppText variant="bodyStrong">{cat.label}</AppText>
                    <AppText variant="caption" color="secondary">{cat.helperText}</AppText>
                  </AppCard>
                </Pressable>
              );
            })}
          </View>
        </View>

        {selectedCategory?.bookingApplicable ? (
          <View style={{ gap: theme.spacing.xs }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <AppText variant="labelStrong" color="secondary">Link a booking</AppText>
              <AppText variant="caption" color="tertiary">Optional</AppText>
            </View>

            {linkedBooking ? (
              <BookingContextCard booking={linkedBooking} onChange={() => setShowBookingPicker(true)} />
            ) : (
              <AppButton
                label="Choose a booking" tone="secondary"
                onPress={() => setShowBookingPicker(true)}
                disabled={bookingsQuery.isPending}
              />
            )}

            {showBookingPicker ? (
              <AppCard style={{ gap: theme.spacing.xs }}>
                {ownedBookings.length === 0 ? (
                  <AppText variant="bodySmall" color="secondary">You have no bookings to link yet.</AppText>
                ) : (
                  ownedBookings.slice(0, 20).map(b => (
                    <Pressable
                      key={b.bookingId}
                      accessibilityRole="button" accessibilityLabel={`${b.serviceName ?? "Booking"}, ${b.statusLabel}`}
                      onPress={() => { setDraft(d => ({ ...d, bookingId: b.bookingId })); setShowBookingPicker(false); }}
                      style={{ paddingVertical: theme.spacing.xs, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}
                    >
                      <AppText variant="bodyStrong">{b.serviceName ?? b.bookingNumber ?? "Booking"}</AppText>
                      <AppText variant="caption" color="secondary">{b.statusLabel}</AppText>
                    </Pressable>
                  ))
                )}
                <AppButton label="Cancel" tone="tertiary" onPress={() => setShowBookingPicker(false)} />
              </AppCard>
            ) : null}

            <AppText variant="caption" color="tertiary">Linking a booking helps provide the right context.</AppText>
          </View>
        ) : null}

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Before you continue</AppText>
          <AppCard style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
            <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.textSecondary} decorative />
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">Your request is linked to your Fuvay account</AppText>
              <AppText variant="bodySmall" color="secondary">You'll see updates in My support requests.</AppText>
            </View>
          </AppCard>
        </View>

        <View style={{ gap: theme.spacing.sm }}>
          <AppButton label="Continue" tone="primary" onPress={handleContinue} disabled={!canContinue} fullWidth />
          <AppButton
            label="Cancel" tone="tertiary"
            onPress={() => (isSupportRequestDraftDirty(draft) ? confirmDiscard(() => navigation.goBack()) : navigation.goBack())}
            fullWidth
          />
        </View>
      </View>
    </AppScreen>
  );
}

function BookingContextCard({ booking, onChange }: { booking: CustomerBookingListItem; onChange: () => void }) {
  const { theme } = useTheme();
  return (
    <AppCard style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
      <Icon name="build-outline" size="feature" color={theme.colors.textSecondary} decorative />
      <View style={{ flex: 1, gap: theme.spacing.xxs }}>
        <AppText variant="bodyStrong">{booking.serviceName ?? "Service"}</AppText>
        {booking.bookingNumber ? <AppText variant="caption" color="secondary">Booking {booking.bookingNumber}</AppText> : null}
        <AppText variant="caption" color="secondary">{booking.statusLabel}</AppText>
        <AppText variant="caption" color="tertiary">{booking.address.formatted}</AppText>
      </View>
      <AppButton label="Change" tone="secondary" size="compact" onPress={onChange} />
    </AppCard>
  );
}
