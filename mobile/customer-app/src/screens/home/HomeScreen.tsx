import React, { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Alert, RefreshControl, ScrollView, View } from "react-native";
import { type BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import { useNavigation } from "@react-navigation/native";

import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { callAssignedTechnician, cancelCustomerBooking, getBookingActionEligibility } from "../../api/customerBookings/customerBookingsApi";
import { recordHomeCampaignEvent, recordHomeCampaignEvents } from "../../api/home/customerHomeCampaignApi";
import { useCustomerHomeQuery } from "../../api/home/useCustomerHomeQuery";
import { MIN_QUERY_LENGTH, useCustomerSearchQuery } from "../../api/home/useCustomerSearchQuery";
import { AppScreen, AppText } from "../../components";
import {
  FuvayHomeV2,
  GlobalServicesSection,
  HomeErrorState,
  HomeSkeleton,
  LocationPickerModal,
  NoAddressState,
  SearchResultsList,
  UnserviceableState,
} from "../../components/home";
import { OfflineBanner } from "../../components/OfflineBanner";
import { customerExperienceCopy } from "../../content/customerExperience";
import { useTheme } from "../../design-system/theme";
import { createAssistantCardEntryContext, createServiceCardEntryContext } from "../../domain/assistantEntry";
import type { HomeActiveBooking, HomeCampaign, HomeCategory, HomeMasterService, HomeServiceGroup } from "../../domain/customerHome";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { useServiceLocationPreference } from "../../hooks/useServiceLocationPreference";
import type { CustomerTabsParamList } from "../../navigation/routeTypes";

type Navigation = BottomTabNavigationProp<CustomerTabsParamList>;

/**
 * Customer Home v2 owns one render tree. The backend still supplies real
 * availability, bookings and navigation targets; the visual inventory and
 * ordering live in FuvayHomeV2's shared reference-content configuration.
 */
export function HomeScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Navigation>();
  const network = useNetworkStatus();
  const serviceLocation = useServiceLocationPreference();
  const { data: customerProfile } = useCustomerProfileQuery();
  const [searchValue, setSearchValue] = useState("");
  const [locationPickerVisible, setLocationPickerVisible] = useState(false);
  const deliveredCampaigns = useRef(new Set<string>());

  const selectedZipcode = serviceLocation.zipcode ?? undefined;
  const homeQuery = useCustomerHomeQuery(selectedZipcode);
  const home = homeQuery.data;
  const browsingZipcode = home?.serviceability?.zipcode ?? home?.address?.zipcode ?? null;
  const bookableCategoryIds = useMemo(
    () => new Set((home?.bookableCategories ?? []).map(category => String(category.categoryId))),
    [home?.bookableCategories],
  );
  const searchQuery = useCustomerSearchQuery(searchValue, bookableCategoryIds, browsingZipcode ?? undefined);
  const isSearching = searchValue.trim().length >= MIN_QUERY_LENGTH;

  function confirmServiceLocation(zipcode: string) {
    void serviceLocation.setZipcode(zipcode).catch(() => {
      // The in-memory selection remains current if device persistence fails.
    });
  }

  useEffect(() => setSearchValue(""), [selectedZipcode]);

  useEffect(() => {
    const pending = (home?.campaigns ?? []).filter(campaign => !deliveredCampaigns.current.has(campaign.campaignId));
    if (!pending.length) return;
    pending.forEach(campaign => deliveredCampaigns.current.add(campaign.campaignId));
    void recordHomeCampaignEvents(pending.map(campaign => ({
      campaignId: campaign.campaignId,
      eventType: "delivered",
      placement: campaign.placement,
    }))).catch(() => pending.forEach(campaign => deliveredCampaigns.current.delete(campaign.campaignId)));
  }, [home?.campaigns]);

  if (homeQuery.isPending) {
    return (
      <AppScreen scroll style={{ paddingHorizontal: 0 }} edges={["top", "left", "right"]}>
        <View style={{ paddingHorizontal: theme.spacing.base }}><HomeSkeleton /></View>
        <View style={{ marginTop: theme.spacing.xl }}><GlobalServicesSection defaultZipcode={selectedZipcode ?? null} /></View>
      </AppScreen>
    );
  }

  if (homeQuery.isError) {
    return (
      <AppScreen scroll style={{ paddingHorizontal: 0 }} edges={["top", "left", "right"]}>
        {network === "offline" ? <OfflineBanner /> : null}
        <View style={{ minHeight: 280, justifyContent: "center", paddingHorizontal: theme.spacing.base }}>
          <HomeErrorState onRetry={() => homeQuery.refetch()} />
        </View>
        <GlobalServicesSection defaultZipcode={selectedZipcode ?? null} />
      </AppScreen>
    );
  }

  if (!home) return null;

  if (!home.address && !browsingZipcode) {
    return (
      <AppScreen scroll style={{ paddingHorizontal: 0 }} edges={["top", "left", "right"]}>
        <OfflineBanner />
        <View style={{ paddingTop: theme.spacing.xxl, paddingBottom: theme.spacing.xl, paddingHorizontal: theme.spacing.base }}>
          <NoAddressState onAddAddress={() => setLocationPickerVisible(true)} />
        </View>
        <GlobalServicesSection defaultZipcode={null} />
        <LocationPickerModal visible={locationPickerVisible} currentZipcode={selectedZipcode ?? null} onClose={() => setLocationPickerVisible(false)} onConfirm={confirmServiceLocation} />
      </AppScreen>
    );
  }

  if (home.serviceability?.checked === false) {
    return (
      <AppScreen scroll style={{ paddingHorizontal: 0 }} edges={["top", "left", "right"]}>
        <View style={{ minHeight: 360, paddingHorizontal: theme.spacing.base }}>
          <UnserviceableState zipcode={home.serviceability.zipcode} onChangeLocation={() => setLocationPickerVisible(true)} />
        </View>
        <GlobalServicesSection defaultZipcode={home.serviceability.zipcode} />
        <LocationPickerModal visible={locationPickerVisible} currentZipcode={home.serviceability.zipcode} onClose={() => setLocationPickerVisible(false)} onConfirm={confirmServiceLocation} />
      </AppScreen>
    );
  }

  const readyHome = home;
  const zipcode = browsingZipcode as string;
  const isLocationUpdating = Boolean(selectedZipcode && selectedZipcode !== browsingZipcode && homeQuery.isFetching);
  const browsingElsewhere = zipcode !== home.address?.zipcode;
  const locationLabel = browsingElsewhere
    ? zipcode
    : home.address?.city
      ? `${home.address.city}, ${home.address.zipcode}`
      : home.address?.zipcode ?? zipcode;
  const heroes = home.campaigns.filter(campaign => campaign.placement === "home_hero");
  const stories = home.campaigns.filter(campaign => campaign.placement === "home_story");
  const spotlights = home.campaigns.filter(campaign => campaign.placement === "home_spotlight");
  const mosaics = home.campaigns.filter(campaign => campaign.placement === "home_mosaic");
  const banners = home.campaigns.filter(campaign => campaign.placement === "home_banner");

  function navigateToCategory(category: HomeCategory) {
    if (!category.slug) return;
    navigation.navigate("Assistant", createServiceCardEntryContext({ categoryId: category.categoryId, categoryName: category.name, categorySlug: category.slug, zipcode }));
  }

  function navigateToGroup(group: HomeServiceGroup) {
    navigation.navigate("Assistant", createServiceCardEntryContext({ categoryId: group.categoryId, categoryName: group.name, categorySlug: group.categorySlug, serviceGroupSlug: group.slug, zipcode }));
  }

  function navigateToMasterService(service: HomeMasterService) {
    navigation.navigate("Assistant", createServiceCardEntryContext({ categoryId: service.categoryId, categoryName: service.serviceGroupName, categorySlug: service.categorySlug, serviceGroupSlug: service.serviceGroupSlug, masterServiceId: service.masterServiceId, zipcode }));
  }

  function navigateToCampaign(campaign: HomeCampaign) {
    void recordHomeCampaignEvent({ campaignId: campaign.campaignId, eventType: "clicked", placement: campaign.placement }).catch(() => {});
    const group = readyHome.bookableServiceGroups.find(item => item.slug === campaign.serviceGroupSlug);
    if (group) return navigateToGroup(group);
    const category = readyHome.bookableCategories.find(item => item.slug === campaign.categorySlug);
    if (category) return navigateToCategory(category);
    navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }));
  }

  function openBooking(booking: HomeActiveBooking) {
    (navigation.getParent()?.navigate as ((name: string, params: object) => void) | undefined)?.("BookingDetails", { bookingId: booking.bookingId });
  }

  function callBooking(booking: HomeActiveBooking) {
    void callAssignedTechnician(booking.bookingId)
      .then(() => Alert.alert("Connecting your call", "We’re calling you first, then securely connecting the technician."))
      .catch(() => Alert.alert("Calling unavailable", "We couldn’t connect this call right now. Please try again later."));
  }

  function cancelBooking(booking: HomeActiveBooking) {
    Alert.alert(
      "Cancel this booking?",
      "This action can’t be undone.",
      [
        { text: "Keep booking", style: "cancel" },
        {
          text: "Cancel booking",
          style: "destructive",
          onPress: () => {
            void getBookingActionEligibility(booking.bookingId)
              .then(async ({ data }) => {
                if (!data.can_cancel) {
                  Alert.alert("Cancellation unavailable", "This booking can no longer be cancelled from the app.");
                  return;
                }
                await cancelCustomerBooking(booking.bookingId, {
                  reason: data.allowed_cancellation_reasons.includes("changed_mind") ? "changed_mind" : data.allowed_cancellation_reasons[0] ?? "changed_mind",
                  expectedVersion: data.version,
                });
                await homeQuery.refetch();
                Alert.alert("Booking cancelled", "The booking has been removed from your active bookings.");
              })
              .catch(() => Alert.alert("Couldn’t cancel booking", "Please refresh and try again."));
          },
        },
      ],
    );
  }

  return (
    <AppScreen style={{ paddingHorizontal: 0, backgroundColor: theme.fuvay.surfaces.shell }} edges={["top", "left", "right"]}>
      <OfflineBanner />
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={homeQuery.isRefetching} onRefresh={() => homeQuery.refetch()} tintColor={theme.fuvay.accents.a2} />}
        contentContainerStyle={{ paddingBottom: 0 }}
      >
        <FuvayHomeV2
          customerName={customerProfile?.displayName ?? customerProfile?.fullName ?? customerExperienceCopy.home.fallbacks.customerName}
          location={locationLabel}
          unreadCount={home.unreadNotificationCount}
          searchValue={searchValue}
          serviceGroups={home.bookableServiceGroups}
          masterServices={home.bookableMasterServices}
          quickIssues={home.quickIssues}
          activeBookings={home.activeBookings}
          activeBookingTotal={home.activeBookingTotal}
          heroCampaign={heroes[0]}
          spotlightCampaigns={spotlights.length >= 4 ? spotlights : [...spotlights, ...stories, ...mosaics, ...banners].filter((campaign, index, all) => all.findIndex(item => item.campaignId === campaign.campaignId) === index).slice(0, 4)}
          bannerCampaign={banners[0]}
          onSearch={setSearchValue}
          onProfile={() => navigation.navigate("Profile")}
          onLocation={() => setLocationPickerVisible(true)}
          onNotifications={() => (navigation.getParent()?.navigate as ((name: string) => void) | undefined)?.("Notifications")}
          onBooking={openBooking}
          onCallBooking={callBooking}
          onCancelBooking={cancelBooking}
          onServiceGroup={navigateToGroup}
          onMasterService={navigateToMasterService}
          onCampaign={navigateToCampaign}
          onAssistant={() => navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }))}
        />
        {isLocationUpdating ? (
          <View accessibilityRole="progressbar" accessibilityLabel={`Updating services for ${selectedZipcode}`} style={{ marginHorizontal: 18, padding: 12, borderRadius: 14, backgroundColor: theme.fuvay.soft(theme.fuvay.accents.a2), flexDirection: "row", alignItems: "center", gap: 8 }}>
            <ActivityIndicator size="small" color={theme.fuvay.accents.a2} />
            <AppText variant="caption" style={{ color: theme.fuvay.accents.a2 }}>Updating services for {selectedZipcode}…</AppText>
          </View>
        ) : null}
        {isSearching ? (
          <View style={{ marginHorizontal: 18, marginTop: 18 }}>
            <SearchResultsList
              query={searchValue.trim()}
              isPending={searchQuery.isPending}
              isError={searchQuery.isError}
              results={searchQuery.data?.results ?? []}
              onPressCategory={categoryId => {
                const category = home.bookableCategories.find(item => String(item.categoryId) === String(categoryId));
                if (category) navigateToCategory(category);
              }}
            />
          </View>
        ) : null}
      </ScrollView>
      <LocationPickerModal visible={locationPickerVisible} currentZipcode={selectedZipcode ?? zipcode} onClose={() => setLocationPickerVisible(false)} onConfirm={confirmServiceLocation} />
    </AppScreen>
  );
}
