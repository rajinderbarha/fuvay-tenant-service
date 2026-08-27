import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AccessibilityInfo,
  FlatList,
  Image,
  ImageBackground,
  ImageSourcePropType,
  NativeScrollEvent,
  NativeSyntheticEvent,
  Pressable,
  RefreshControl,
  ScrollView,
  ActivityIndicator,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";
import { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import { useNavigation } from "@react-navigation/native";

import { recordHomeCampaignEvent, recordHomeCampaignEvents } from "../../api/home/customerHomeCampaignApi";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useCustomerHomeQuery } from "../../api/home/useCustomerHomeQuery";
import { MIN_QUERY_LENGTH, useCustomerSearchQuery } from "../../api/home/useCustomerSearchQuery";
import { AppScreen, AppText, Icon } from "../../components";
import {
  GlobalServicesSection,
  HomeErrorState,
  HomeSectionErrorBoundary,
  HomeSkeleton,
  LocationPickerModal,
  NoAddressState,
  ProblemCircles,
  ProblemGrid,
  SearchResultsList,
  UnserviceableState,
} from "../../components/home";
import { OfflineBanner } from "../../components/OfflineBanner";
import { HomeGlyph, type HomeGlyphName } from "../../components/home/HomeGlyph";
import { useTheme } from "../../design-system/theme";
import {
  createAssistantCardEntryContext,
  createQuickIssueEntryContext,
  createServiceCardEntryContext,
} from "../../domain/assistantEntry";
import { interpretBookingStatus } from "../../domain/bookingStatus";
import type {
  HomeActiveBooking,
  HomeCampaign,
  HomeCategory,
  HomeMasterService,
  HomeQuickIssue,
  HomeSectionConfig,
  HomeServiceGroup,
} from "../../domain/customerHome";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { useServiceLocationPreference } from "../../hooks/useServiceLocationPreference";
import type { CustomerTabsParamList } from "../../navigation/routeTypes";
import { FuvayIcon } from "../../components/FuvayIcon";
import { MyBookingCard } from "../../components/home/MyBookingCard";

type Navigation = BottomTabNavigationProp<CustomerTabsParamList>;

const GROUP_ICON_RULES: Array<[RegExp, HomeGlyphName]> = [
  [/refriger|fridge/i, "fridge-outline"],
  [/washing/i, "washing-machine"],
  [/chimney|hood/i, "stove"],
  [/purifier|\bro\b/i, "water-circle"],
  [/geyser|heater/i, "water-boiler"],
  [/air|ac|cool/i, "air-conditioner"],
  [/plumb|water|pipe/i, "pipe-wrench"],
  [/electric|power|wire/i, "lightning-bolt-outline"],
  [/clean/i, "spray-bottle"],
  [/appliance/i, "home-lightning-bolt-outline"],
  [/pest/i, "bug-outline"],
];

function groupIcon(name: string): HomeGlyphName {
  return GROUP_ICON_RULES.find(([pattern]) => pattern.test(name))?.[1] ?? "tools";
}

const DEFAULT_HOME_PHOTOS: ImageSourcePropType[] = [
  require("../../../assets/home-campaigns/fuvay-ac-care-hero-v1.png"),
  require("../../../assets/home-campaigns/fuvay-complete-care-spotlight-v1.png"),
  require("../../../assets/home-campaigns/fuvay-chimney-care-story-v1.png"),
];

const SERVICE_ARTWORK_2D = {
  airConditioner: require("../../../assets/service-artwork-2d/air-conditioner-service-v1.png"),
  chimney: require("../../../assets/service-artwork-2d/chimney-service-v1.png"),
  refrigerator: require("../../../assets/service-artwork-2d/refrigerator-service-v1.png"),
  washingMachine: require("../../../assets/service-artwork-2d/washing-machine-service-v1.png"),
  waterHeater: require("../../../assets/service-artwork-2d/water-heater-service-v1.png"),
  waterPurifier: require("../../../assets/service-artwork-2d/water-purifier-service-v1.png"),
} as const;

function serviceArtwork(service: HomeMasterService): ImageSourcePropType {
  const searchableName = `${service.name} ${service.serviceGroupName}`;
  if (/refriger|fridge/i.test(searchableName)) return SERVICE_ARTWORK_2D.refrigerator;
  if (/washing/i.test(searchableName)) return SERVICE_ARTWORK_2D.washingMachine;
  if (/chimney|hood/i.test(searchableName)) return SERVICE_ARTWORK_2D.chimney;
  if (/purifier|\bro\b/i.test(searchableName)) return SERVICE_ARTWORK_2D.waterPurifier;
  if (/geyser|water\s*heater|heater/i.test(searchableName)) return SERVICE_ARTWORK_2D.waterHeater;
  return SERVICE_ARTWORK_2D.airConditioner;
}

function selectDiverseMasterServices(services: HomeMasterService[], limit: number): HomeMasterService[] {
  const selected: HomeMasterService[] = [];
  const deferred: HomeMasterService[] = [];
  const selectedGroupIds = new Set<string>();

  services.forEach(service => {
    if (!selectedGroupIds.has(service.serviceGroupId) && selected.length < limit) {
      selectedGroupIds.add(service.serviceGroupId);
      selected.push(service);
    } else {
      deferred.push(service);
    }
  });

  if (selected.length < limit) {
    selected.push(...deferred.slice(0, limit - selected.length));
  }
  return selected;
}

export function HomeScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Navigation>();
  const network = useNetworkStatus();
  const serviceLocation = useServiceLocationPreference();
  const { data: customerProfile } = useCustomerProfileQuery();
  const [searchValue, setSearchValue] = useState("");
  const [locationPickerVisible, setLocationPickerVisible] = useState(false);
  const [globalServiceRequestToken, setGlobalServiceRequestToken] = useState(0);
  const deliveredCampaigns = useRef(new Set<string>());

  // One location authority only. Keeping a second screen-local override used
  // to let the modal, query cache and persisted preference disagree during a
  // quick A -> B -> A switch, which was the source of the apparent hang.
  const selectedZipcode = serviceLocation.zipcode ?? undefined;
  const homeQuery = useCustomerHomeQuery(selectedZipcode);
  const home = homeQuery.data;
  const browsingZipcode = home?.serviceability?.zipcode ?? home?.address?.zipcode ?? null;
  const bookableCategoryIds = useMemo(
    () => new Set((home?.bookableCategories ?? []).map(category => String(category.categoryId))),
    [home?.bookableCategories],
  );
  const searchQuery = useCustomerSearchQuery(
    searchValue,
    bookableCategoryIds,
    browsingZipcode ?? undefined,
  );
  const isSearching = searchValue.trim().length >= MIN_QUERY_LENGTH;

  function confirmServiceLocation(zipcode: string) {
    void serviceLocation.setZipcode(zipcode).catch(() => {
      // The provider updates its in-memory state before persistence, so the
      // current-session choice remains active if device storage is unavailable.
    });
  }

  useEffect(() => {
    // A search result is scoped to its ZIP. Never carry a query/result from
    // the previous locality into the newly selected marketplace.
    setSearchValue("");
  }, [selectedZipcode]);

  useEffect(() => {
    const pending = (home?.campaigns ?? []).filter(
      campaign => !deliveredCampaigns.current.has(campaign.campaignId),
    );
    if (pending.length === 0) return;
    for (const campaign of pending) deliveredCampaigns.current.add(campaign.campaignId);
    void recordHomeCampaignEvents(pending.map(campaign => ({
        campaignId: campaign.campaignId,
        eventType: "delivered",
        placement: campaign.placement,
    }))).catch(() => {
      for (const campaign of pending) deliveredCampaigns.current.delete(campaign.campaignId);
    });
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
        <LocationPickerModal
          visible={locationPickerVisible}
          currentZipcode={selectedZipcode ?? null}
          onClose={() => setLocationPickerVisible(false)}
          onConfirm={confirmServiceLocation}
        />
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
        <LocationPickerModal
          visible={locationPickerVisible}
          currentZipcode={home.serviceability.zipcode}
          onClose={() => setLocationPickerVisible(false)}
          onConfirm={confirmServiceLocation}
        />
      </AppScreen>
    );
  }

  const zipcode = browsingZipcode as string;
  const isLocationUpdating = !!selectedZipcode
    && selectedZipcode !== browsingZipcode
    && homeQuery.isFetching;
  const browsingElsewhere = zipcode !== home.address?.zipcode;
  const locationLabel = browsingElsewhere
    ? zipcode
    : home.address?.city
      ? `${home.address.city}, ${home.address.zipcode}`
      : home.address?.zipcode ?? zipcode;
  const heroes = home.campaigns.filter(campaign => campaign.placement === "home_hero").slice(0, 5);
  const stories = home.campaigns.filter(campaign => campaign.placement === "home_story");
  const spotlights = home.campaigns.filter(campaign => campaign.placement === "home_spotlight");
  const banners = home.campaigns.filter(campaign => campaign.placement === "home_banner");
  const mosaics = home.campaigns.filter(campaign => campaign.placement === "home_mosaic").slice(0, 3);
  const collections = home.campaigns.filter(campaign => campaign.placement === "home_collection").slice(0, 8);
  const notices = home.campaigns.filter(campaign => campaign.placement === "home_notice").slice(0, 2);
  const trustPromises = home.campaigns.filter(campaign => campaign.placement === "home_trust").slice(0, 4);
  const globalCampaigns = home.campaigns.filter(campaign => campaign.placement === "home_global").slice(0, 5);
  const recommendationCampaigns = home.campaigns.filter(campaign => campaign.placement === "home_recommendation").slice(0, 8);
  const editorialPhotos: ImageSourcePropType[] = [
    ...recommendationCampaigns,
    ...stories,
    ...spotlights,
    ...banners,
    ...mosaics,
    ...collections,
    ...heroes,
  ]
    .map(campaign => resolveMediaUrl(campaign.imageUrl))
    .filter((url): url is string => !!url)
    .map(uri => ({ uri }));
  const homePhotos = editorialPhotos.length ? editorialPhotos : DEFAULT_HOME_PHOTOS;
  const activeBooking = home.activeBookings[0] ?? null;
  const issueSections = partitionHomeIssues(home.quickIssues);

  function navigateToCategory(category: HomeCategory) {
    if (!category.slug) return;
    navigation.navigate("Assistant", createServiceCardEntryContext({
      categoryId: category.categoryId,
      categoryName: category.name,
      categorySlug: category.slug,
      zipcode,
    }));
  }

  function navigateToGroup(group: HomeServiceGroup) {
    navigation.navigate("Assistant", createServiceCardEntryContext({
      categoryId: group.categoryId,
      categoryName: group.name,
      categorySlug: group.categorySlug,
      serviceGroupSlug: group.slug,
      zipcode,
    }));
  }

  function navigateToMasterService(service: HomeMasterService) {
    navigation.navigate("Assistant", createServiceCardEntryContext({
      categoryId: service.categoryId,
      categoryName: service.serviceGroupName,
      categorySlug: service.categorySlug,
      serviceGroupSlug: service.serviceGroupSlug,
      masterServiceId: service.masterServiceId,
      zipcode,
    }));
  }

  function navigateToIssue(issue: HomeQuickIssue) {
    if (!issue.categorySlug) return;
    navigation.navigate("Assistant", createQuickIssueEntryContext({
      categoryId: issue.categoryId,
      categoryName: issue.categoryName,
      categorySlug: issue.categorySlug,
      zipcode,
      issueId: issue.issueId,
    }));
  }

  function navigateToCampaign(campaign: HomeCampaign) {
    void recordHomeCampaignEvent({
      campaignId: campaign.campaignId,
      eventType: "clicked",
      placement: campaign.placement,
    }).catch(() => {});
    if (campaign.actionUrl?.startsWith("fuvay://global-services")) {
      setGlobalServiceRequestToken(current => current + 1);
      return;
    }
    const group = home!.bookableServiceGroups.find(item => item.slug === campaign.serviceGroupSlug);
    if (group) {
      navigateToGroup(group);
      return;
    }
    const category = home!.bookableCategories.find(item => item.slug === campaign.categorySlug);
    if (category) {
      navigateToCategory(category);
    } else {
      navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }));
    }
  }

  function renderHomeSection(section: HomeSectionConfig) {
    if (!section.enabled) return null;
    const title = section.title;
    const topSpacing = section.spacing === "compact"
      ? theme.spacing.base
      : section.spacing === "generous"
        ? theme.spacing.huge
        : theme.spacing.xl;
    const surfaceColor = section.surface === "subtle"
      ? theme.colors.surfaceSecondary
      : section.surface === "raised"
        ? theme.colors.surfaceRaised
        : section.surface === "brand_tint"
          ? theme.colors.brandPrimaryMuted
          : "transparent";
    const frame = (content: React.ReactNode, inset = false) => content ? (
      <View
        key={section.key}
        style={{
          marginTop: topSpacing,
          marginHorizontal: section.surface === "raised" ? theme.spacing.base : 0,
          paddingHorizontal: section.surface === "raised" ? theme.spacing.base : inset ? theme.spacing.base : 0,
          paddingVertical: section.surface === "canvas" ? 0 : theme.spacing.base,
          borderWidth: section.surface === "raised" ? 1 : 0,
          borderColor: section.surface === "raised" ? theme.colors.borderSubtle : "transparent",
          borderRadius: section.surface === "raised" ? theme.radius.radiusMedium : 0,
          overflow: section.surface === "raised" ? "hidden" : "visible",
          backgroundColor: surfaceColor,
        }}
      >
        {content}
      </View>
    ) : null;
    switch (section.key) {
      case "hero":
        return heroes.length ? frame(
            <HomeSectionErrorBoundary sectionLabel="featured offer">
              <HomeHeroSlider campaigns={heroes.slice(0, section.maxItems)} variant={section.variant} onPress={navigateToCampaign} />
            </HomeSectionErrorBoundary>
          , section.variant !== "edge_to_edge") : null;
      case "service_groups":
        return frame(<>
            <NearbyServicesHeader title={title ?? "Popular Services"} zipcode={zipcode} onAction={() => navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }))} />
            <ServiceGroupRail groups={home!.bookableServiceGroups.slice(0, section.maxItems)} variant={section.variant} onPress={navigateToGroup} />
          </>);
      case "nearby_services":
        return frame(<>
            <NearbyServicesHeader title={title ?? "Services Nearby"} zipcode={zipcode} onAction={() => navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }))} />
            <ServiceGroupRail groups={home!.bookableServiceGroups.slice(0, section.maxItems)} variant={section.variant} onPress={navigateToGroup} />
          </>);
      case "live_booking":
        return activeBooking ? frame(<ActiveBookingTimeline title={title} booking={activeBooking} onPress={() => (navigation.getParent()?.navigate as ((name: string, params: object) => void) | undefined)?.("BookingDetails", { bookingId: activeBooking.bookingId })} />, true) : null;
      case "recent_bookings":
        return home!.activeBookings.length ? frame(<>
            <SectionHeader title={title ?? "My Booking"} actionLabel="View All" onAction={() => navigation.navigate("Bookings")} />
            <View style={{ paddingHorizontal: theme.spacing.base }}>
              <MyBookingCard booking={home!.activeBookings[0]} onPress={() => (navigation.getParent()?.navigate as ((name: string, params: object) => void) | undefined)?.("BookingDetails", { bookingId: home!.activeBookings[0].bookingId })} />
            </View>
          </>) : null;
      case "featured_services":
        return home!.bookableMasterServices.length ? frame(<>
            <SectionHeader title={title ?? "Featured services"} actionLabel="View all" onAction={() => navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }))} />
            {section.variant === "catalog_grid"
              ? <MasterServiceGrid services={selectDiverseMasterServices(home!.bookableMasterServices, section.maxItems)} variant="catalog_grid" onPress={navigateToMasterService} />
              : <FeaturedServiceRail services={home!.bookableMasterServices.slice(0, section.maxItems)} onPress={navigateToMasterService} />}
          </>) : null;
      case "master_services":
        return home!.bookableMasterServices.length ? frame(<>
            <SectionHeader title={title ?? "Recommended for you"} actionLabel="View all" onAction={() => navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }))} />
            <MasterServiceGrid services={home!.bookableMasterServices.slice(0, section.maxItems)} variant={section.variant} photos={homePhotos} onPress={navigateToMasterService} />
          </>) : null;
      case "trust_strip":
        return trustPromises.length ? frame(<CustomerAssuranceStrip campaigns={trustPromises.slice(0, section.maxItems)} variant={section.variant} />, true) : null;
      case "stories":
        return stories.length ? frame(<>
            <SectionHeader title={title ?? "Ideas and offers"} />
            <CampaignStoryRail campaigns={stories.slice(0, section.maxItems)} variant={section.variant} onPress={navigateToCampaign} />
          </>) : null;
      case "spotlight":
        return spotlights.length ? frame(<>
            <SectionHeader title={title ?? spotlights[0]?.sectionTitle ?? "In the spotlight"} />
            <CampaignSpotlight campaigns={spotlights.slice(0, section.maxItems)} variant={section.variant} onPress={navigateToCampaign} />
          </>) : null;
      case "mosaic":
        return mosaics.length ? frame(<>
            <SectionHeader title={title ?? mosaics[0]?.sectionTitle ?? "Fresh ways to care for home"} />
            <CampaignMosaic campaigns={mosaics.slice(0, section.maxItems)} onPress={navigateToCampaign} />
          </>) : null;
      case "global_services":
        return frame(<GlobalServicesSection title={title ?? "Build with Fuvay"} campaigns={globalCampaigns} variant={section.variant} defaultZipcode={null} openRequestToken={globalServiceRequestToken} />, true);
      case "collection":
        return collections.length ? frame(<>
            <SectionHeader title={title ?? collections[0]?.sectionTitle ?? "Curated for you"} />
            <CampaignCollection campaigns={collections.slice(0, section.maxItems)} onPress={navigateToCampaign} />
          </>) : null;
      case "banners":
        return frame(<>{banners.slice(0, section.maxItems).map(campaign => <CampaignEditorialBanner key={campaign.campaignId} campaign={campaign} contained={section.variant === "contained"} onPress={() => navigateToCampaign(campaign)} />)}</>);
      case "assistant":
        return frame(<AskFuvayStrip seasonLabel={home!.seasonLabel} onPress={() => navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }))} />, true);
      case "featured_problems":
        return issueSections.featured.length ? frame(<HomeSectionErrorBoundary sectionLabel="common problems">{section.variant === "photo_cards" ? <ProblemPhotoGrid issues={issueSections.featured.slice(0, section.maxItems)} title={title ?? "What Needs Fixing"} photos={homePhotos} onPressIssue={navigateToIssue} /> : section.variant === "compact_grid" ? <ProblemCircles issues={issueSections.featured.slice(0, section.maxItems)} title={title ?? "What needs fixing?"} variant="compact" onPressIssue={navigateToIssue} /> : <ProblemGrid issues={issueSections.featured.slice(0, section.maxItems)} title={title ?? "What needs fixing?"} onPressIssue={navigateToIssue} />}</HomeSectionErrorBoundary>, true) : null;
      case "active_bookings":
        return home!.activeBookings.length > 1 ? frame(<View style={{ gap: theme.spacing.sm }}>
            <SectionHeader title={title ?? "More active bookings"} inset={false} />
            {home!.activeBookings.slice(1, section.maxItems + 1).map(booking => <CompactActiveBooking key={booking.bookingId} booking={booking} onPress={() => (navigation.getParent()?.navigate as ((name: string, params: object) => void) | undefined)?.("BookingDetails", { bookingId: booking.bookingId })} />)}
            {home!.activeBookingTotal > home!.activeBookings.length ? <InlineAction label={`View all ${home!.activeBookingTotal} active bookings`} icon="calendar-outline" onPress={() => navigation.navigate("Bookings")} /> : null}
          </View>, true) : null;
      case "repair_problems":
        return issueSections.repairs.length ? frame(<ProblemCircles issues={issueSections.repairs.slice(0, section.maxItems)} title={title ?? "Repairs you can book now"} variant="showcase" onPressIssue={navigateToIssue} />, true) : null;
      case "consultation_problems":
        return issueSections.consultations.length ? frame(<ProblemCircles issues={issueSections.consultations.slice(0, section.maxItems)} title={title ?? "Get an expert opinion"} variant="expert" onPressIssue={navigateToIssue} />, true) : null;
      case "more_problems":
        return issueSections.more.length ? frame(<ProblemCircles issues={issueSections.more.slice(0, section.maxItems)} title={title ?? "More ways we can help"} variant="compact" onPressIssue={navigateToIssue} />, true) : null;
      case "notices":
        return frame(<View style={{ gap: theme.spacing.sm }}>{notices.slice(0, section.maxItems).map(campaign => <CampaignNotice key={campaign.campaignId} campaign={campaign} onPress={() => navigateToCampaign(campaign)} />)}</View>, true);
      case "support_actions":
        return frame(<View style={{ gap: theme.spacing.sm }}><InlineAction label={`Services shown for ${locationLabel}`} accessibilityLabel="Change service location" icon="location-outline" onPress={() => setLocationPickerVisible(true)} /><InlineAction label="Help with a booking or service" icon="headset-outline" onPress={() => navigation.navigate("Support")} /></View>, true);
      default:
        return null;
    }
  }

  return (
    <AppScreen style={{ paddingHorizontal: 0 }} edges={["top", "left", "right"]}>
      <OfflineBanner />
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={homeQuery.isRefetching} onRefresh={() => homeQuery.refetch()} tintColor={theme.colors.brandPrimary} />}
        contentContainerStyle={{ paddingBottom: 132 }}
      >
        <View style={{ paddingHorizontal: theme.spacing.base }}>
          <MarketplaceHeader
            customerName={customerProfile?.displayName ?? customerProfile?.fullName ?? null}
            locationLabel={locationLabel}
            unreadCount={home.unreadNotificationCount}
            onLocation={() => setLocationPickerVisible(true)}
            onNotifications={() => (navigation.getParent()?.navigate as ((name: string) => void) | undefined)?.("Notifications")}
            onProfile={() => navigation.navigate("Profile")}
          />
          <MarketplaceSearch
            value={searchValue}
            onChangeText={setSearchValue}
            onAssistant={() => navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }))}
          />
          {isLocationUpdating ? (
            <View
              accessibilityRole="progressbar"
              accessibilityLabel={`Updating services for ${selectedZipcode}`}
              style={{
                marginTop: theme.spacing.xs,
                minHeight: 38,
                paddingHorizontal: theme.spacing.sm,
                flexDirection: "row",
                alignItems: "center",
                gap: theme.spacing.xs,
                borderRadius: theme.radiusUsage.statusPill,
                backgroundColor: theme.colors.statusInfoSurface,
              }}
            >
              <ActivityIndicator size="small" color={theme.colors.statusInfo} />
              <AppText variant="caption" style={{ color: theme.colors.statusInfo, fontWeight: "700" }}>
                Updating services for {selectedZipcode}…
              </AppText>
            </View>
          ) : null}
          {isSearching ? (
            <View style={{ marginTop: theme.spacing.base }}>
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
        </View>

        {!isSearching ? (
          <>
            {home.sections.map(section => renderHomeSection(section))}
          </>
        ) : null}
      </ScrollView>
      <LocationPickerModal visible={locationPickerVisible} currentZipcode={selectedZipcode ?? zipcode} onClose={() => setLocationPickerVisible(false)} onConfirm={confirmServiceLocation} />
    </AppScreen>
  );
}

function MarketplaceHeader({ customerName, locationLabel, unreadCount, onLocation, onNotifications, onProfile }: {
  customerName: string | null;
  locationLabel: string;
  unreadCount: number;
  onLocation: () => void;
  onNotifications: () => void;
  onProfile: () => void;
}) {
  const { theme } = useTheme();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good Morning" : hour < 17 ? "Good Afternoon" : "Good Evening";
  const firstName = customerName?.trim().split(/\s+/)[0] || "there";
  return (
    <View style={{ flexDirection: "row", alignItems: "center", minHeight: 70, paddingTop: theme.spacing.xs }}>
      <Pressable
        onPress={onLocation}
        accessibilityRole="button"
        accessibilityLabel={`Change service location, currently ${locationLabel}`}
        style={({ pressed }) => ({ flex: 1, minWidth: 0, minHeight: 52, justifyContent: "center", opacity: pressed ? 0.72 : 1 })}
      >
        <View style={{ flexDirection: "row", alignItems: "baseline", minWidth: 0 }}>
          <AppText variant="bodyStrong" numberOfLines={1}>{greeting} </AppText>
          <AppText variant="bodyStrong" numberOfLines={1} style={{ color: theme.colors.brandPrimary }}>{firstName}</AppText>
        </View>
        <View style={{ marginTop: 3, flexDirection: "row", alignItems: "center", gap: 5 }}>
          <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: theme.colors.statusSuccess }} />
          <AppText variant="caption" color="secondary" numberOfLines={1}>{locationLabel}</AppText>
          <HomeGlyph name="chevron-down" size="compact" color={theme.colors.textSecondary} />
        </View>
      </Pressable>
      <Pressable
        onPress={onNotifications}
        accessibilityRole="button"
        accessibilityLabel={`Notifications${unreadCount ? `, ${unreadCount} unread` : ""}`}
        style={{ width: 46, height: 46, borderRadius: 23, marginRight: theme.spacing.xs, backgroundColor: theme.colors.surfaceSecondary, alignItems: "center", justifyContent: "center" }}
      >
        <HomeGlyph name="bell-outline" size="standard" color={theme.colors.textPrimary} />
        {unreadCount > 0 ? (
          <View style={{ position: "absolute", right: 4, top: 2, minWidth: 18, height: 18, paddingHorizontal: 4, borderRadius: 9, backgroundColor: theme.colors.statusDanger, alignItems: "center", justifyContent: "center" }}>
            <AppText variant="caption" color="inverse" style={{ fontWeight: "700" }}>{Math.min(unreadCount, 99)}</AppText>
          </View>
        ) : null}
      </Pressable>
      <Pressable onPress={onProfile} accessibilityRole="button" accessibilityLabel="Open profile" style={{ width: 46, height: 46, borderRadius: 23, backgroundColor: theme.colors.surfaceSecondary, alignItems: "center", justifyContent: "center" }}>
        <View style={{ width: 30, height: 30, borderRadius: 15, alignItems: "center", justifyContent: "center" }}>
          <HomeGlyph name="account-outline" size="compact" color={theme.colors.textPrimary} />
        </View>
      </Pressable>
    </View>
  );
}

function MarketplaceSearch({ value, onChangeText, onAssistant }: {
  value: string;
  onChangeText: (value: string) => void;
  onAssistant: () => void;
}) {
  const { theme } = useTheme();
  return (
    <View style={{ height: 50, flexDirection: "row", alignItems: "center", borderRadius: 25, backgroundColor: theme.colors.surfaceSecondary, paddingLeft: theme.spacing.md }}>
      <HomeGlyph name="magnify" color={theme.colors.textPrimary} />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder="Search for appliance or service"
        placeholderTextColor={theme.colors.textTertiary}
        returnKeyType="search"
        accessibilityLabel="Search services"
        style={{ flex: 1, minWidth: 0, paddingHorizontal: theme.spacing.sm, color: theme.colors.textPrimary, ...theme.typography.body }}
      />
      <Pressable onPress={onAssistant} accessibilityRole="button" accessibilityLabel="Find the right service with Ask Fuvay" style={{ width: 48, height: 44, alignItems: "center", justifyContent: "center" }}>
        <View style={{ width: 32, height: 32, borderRadius: 16, backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: theme.colors.borderSubtle, alignItems: "center", justifyContent: "center" }}>
          <FuvayIcon size={21} accessibilityLabel="Fuvay assistant" />
        </View>
      </Pressable>
    </View>
  );
}

function HomeHeroSlider({ campaigns, variant, onPress }: {
  campaigns: HomeCampaign[];
  variant: string;
  onPress: (campaign: HomeCampaign) => void;
}) {
  const { theme } = useTheme();
  const { width: windowWidth } = useWindowDimensions();
  const edgeToEdge = variant === "edge_to_edge";
  const slideWidth = Math.max(280, windowWidth - (edgeToEdge ? 0 : theme.spacing.base * 2));
  const listRef = useRef<FlatList<HomeCampaign>>(null);
  const [index, setIndex] = useState(0);
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion).catch(() => {});
  }, []);

  useEffect(() => {
    if (campaigns.length < 2 || reduceMotion) return;
    const timer = setInterval(() => {
      setIndex(current => {
        const next = (current + 1) % campaigns.length;
        listRef.current?.scrollToIndex({ index: next, animated: true });
        return next;
      });
    }, 6000);
    return () => clearInterval(timer);
  }, [campaigns.length, reduceMotion]);

  function finishScroll(event: NativeSyntheticEvent<NativeScrollEvent>) {
    const next = Math.round(event.nativeEvent.contentOffset.x / slideWidth);
    setIndex(Math.max(0, Math.min(campaigns.length - 1, next)));
  }

  function selectSlide(next: number) {
    setIndex(next);
    listRef.current?.scrollToIndex({ index: next, animated: !reduceMotion });
  }

  return (
    <View>
      <FlatList
        ref={listRef}
        data={campaigns}
        horizontal
        pagingEnabled
        bounces={false}
        showsHorizontalScrollIndicator={false}
        keyExtractor={campaign => campaign.campaignId}
        getItemLayout={(_, itemIndex) => ({ length: slideWidth, offset: slideWidth * itemIndex, index: itemIndex })}
        onMomentumScrollEnd={finishScroll}
        renderItem={({ item }) => (
          <View style={{ width: slideWidth }}>
            <CampaignHero campaign={item} variant={variant} onPress={() => onPress(item)} />
          </View>
        )}
      />
      {campaigns.length > 1 ? (
        <View style={{ height: 24, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 }} accessibilityRole="tablist">
          {campaigns.map((campaign, dotIndex) => (
            <Pressable
              key={campaign.campaignId}
              onPress={() => selectSlide(dotIndex)}
              accessibilityRole="tab"
              accessibilityState={{ selected: dotIndex === index }}
              accessibilityLabel={`Show offer ${dotIndex + 1} of ${campaigns.length}`}
              style={{ width: dotIndex === index ? 18 : 6, height: 6, borderRadius: 3, backgroundColor: dotIndex === index ? theme.colors.textPrimary : theme.colors.borderStrong }}
            />
          ))}
        </View>
      ) : null}
    </View>
  );
}

function CampaignHero({ campaign, variant, onPress }: { campaign: HomeCampaign; variant: string; onPress: () => void }) {
  const { theme } = useTheme();
  const edgeToEdge = variant === "edge_to_edge";
  const marketplace = variant === "marketplace";
  const endLabel = campaign.endsAt ? formatCampaignEnd(campaign.endsAt) : null;
  const height = marketplace ? 186 : edgeToEdge ? 236 : 214;
  return (
    <ImageBackground
      source={{ uri: resolveMediaUrl(campaign.imageUrl)! }}
      resizeMode="cover"
      style={{ height, overflow: "hidden", borderRadius: edgeToEdge ? 0 : marketplace ? 14 : theme.radius.radiusSmall }}
      accessibilityIgnoresInvertColors
    >
      <View style={{ height, padding: theme.spacing.base, backgroundColor: theme.colors.mediaScrim }}>
        {!marketplace && campaign.badge ? <View style={{ alignSelf: "flex-start", paddingHorizontal: 9, paddingVertical: 4, borderRadius: 3, backgroundColor: theme.colors.campaignAccent }}>
          <AppText variant="caption" style={{ color: theme.colors.campaignBadgeForeground, fontWeight: "700" }}>{campaign.badge}</AppText>
        </View> : null}
        <View style={{ width: "59%", gap: 3, marginTop: marketplace ? 0 : theme.spacing.sm }}>
          <AppText variant="headingLarge" style={{ color: theme.colors.mediaForeground, fontFamily: marketplace ? undefined : "serif", fontSize: marketplace ? 26 : 29, lineHeight: marketplace ? 29 : 32 }}>{campaign.title}</AppText>
          {marketplace && campaign.subtitle ? <AppText variant="caption" numberOfLines={2} style={{ color: theme.colors.mediaForeground, opacity: 0.88 }}>{campaign.subtitle}</AppText> : null}
          {!marketplace && campaign.offerText ? <AppText variant="title" style={{ color: theme.colors.campaignAccent, fontSize: 17, lineHeight: 21 }}>{campaign.offerText}</AppText> : null}
        </View>
        <View style={{ position: "absolute", left: theme.spacing.base, right: theme.spacing.base, bottom: theme.spacing.base, flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          {endLabel && !marketplace ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
              <Icon name="calendar-outline" size="compact" color={theme.colors.mediaForeground} decorative />
              <AppText variant="caption" style={{ color: theme.colors.mediaForeground }}>{endLabel}</AppText>
            </View>
          ) : <View />}
          <Pressable
            onPress={onPress}
            accessibilityRole="button"
            accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`}
            style={({ pressed }) => ({ minHeight: 38, minWidth: 112, paddingHorizontal: theme.spacing.md, flexDirection: "row", gap: theme.spacing.xs, alignItems: "center", justifyContent: "center", borderRadius: 19, borderWidth: marketplace ? 1 : 0, borderColor: theme.colors.mediaForeground, backgroundColor: marketplace ? "transparent" : theme.colors.surfaceDefault, opacity: pressed ? 0.9 : 1 })}
          >
            <AppText variant="button" style={{ color: marketplace ? theme.colors.mediaForeground : theme.colors.brandPrimary }}>{campaign.actionLabel}</AppText>
            <Icon name="chevron-forward" size="compact" color={marketplace ? theme.colors.mediaForeground : theme.colors.brandPrimary} decorative />
          </Pressable>
        </View>
      </View>
    </ImageBackground>
  );
}

function CampaignMosaic({ campaigns, onPress }: {
  campaigns: HomeCampaign[];
  onPress: (campaign: HomeCampaign) => void;
}) {
  const { theme } = useTheme();
  const [lead, ...rest] = campaigns;
  if (!lead) return null;
  return (
    <View style={{ paddingHorizontal: theme.spacing.base, height: 224, flexDirection: "row", gap: theme.spacing.xs }}>
      <CampaignMosaicTile campaign={lead} onPress={() => onPress(lead)} style={{ flex: 1.38 }} prominent />
      <View style={{ flex: 1, gap: theme.spacing.xs }}>
        {rest.length ? rest.map(campaign => (
          <CampaignMosaicTile key={campaign.campaignId} campaign={campaign} onPress={() => onPress(campaign)} style={{ flex: 1 }} />
        )) : (
          <CampaignMosaicTile campaign={lead} onPress={() => onPress(lead)} style={{ flex: 1 }} mirrored />
        )}
      </View>
    </View>
  );
}

function CampaignMosaicTile({ campaign, onPress, style, prominent, mirrored }: {
  campaign: HomeCampaign;
  onPress: () => void;
  style?: object;
  prominent?: boolean;
  mirrored?: boolean;
}) {
  const { theme } = useTheme();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`} style={({ pressed }) => [{ opacity: pressed ? 0.84 : 1 }, style]}>
      <ImageBackground source={{ uri: resolveMediaUrl(campaign.imageUrl)! }} resizeMode="cover" style={{ flex: 1, overflow: "hidden", borderRadius: theme.radius.radiusSmall }} imageStyle={{ transform: mirrored ? [{ scaleX: -1 }] : undefined }}>
        <View style={{ flex: 1, justifyContent: "flex-end", padding: prominent ? theme.spacing.md : theme.spacing.sm, backgroundColor: theme.colors.mediaScrimStrong }}>
          <AppText variant={prominent ? "title" : "bodyStrong"} numberOfLines={2} style={{ color: theme.colors.mediaForeground }}>{campaign.title}</AppText>
          {prominent && campaign.offerText ? <AppText variant="caption" style={{ marginTop: 3, color: theme.colors.campaignAccent, fontWeight: "700" }}>{campaign.offerText}</AppText> : null}
        </View>
      </ImageBackground>
    </Pressable>
  );
}

function CampaignCollection({ campaigns, onPress }: {
  campaigns: HomeCampaign[];
  onPress: (campaign: HomeCampaign) => void;
}) {
  const { theme } = useTheme();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: theme.spacing.base, gap: theme.spacing.sm }}>
      {campaigns.map(campaign => {
        const palette = campaignPalette(campaign.themeKey, theme.mode);
        return (
          <Pressable key={campaign.campaignId} onPress={() => onPress(campaign)} accessibilityRole="button" accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`} style={({ pressed }) => ({ width: 178, minHeight: 222, opacity: pressed ? 0.84 : 1, backgroundColor: palette.background })}>
            <Image source={{ uri: resolveMediaUrl(campaign.imageUrl)! }} resizeMode="cover" style={{ width: "100%", height: 132 }} accessibilityIgnoresInvertColors />
            <View style={{ flex: 1, padding: theme.spacing.md }}>
              <AppText variant="caption" numberOfLines={1} style={{ color: palette.accent, fontWeight: "800", textTransform: "uppercase" }}>{campaign.badge}</AppText>
              <AppText variant="bodyStrong" numberOfLines={2} style={{ color: palette.foreground, marginTop: 4 }}>{campaign.title}</AppText>
              <View style={{ marginTop: "auto", paddingTop: theme.spacing.sm, flexDirection: "row", alignItems: "center", gap: 4 }}>
                <AppText variant="caption" style={{ color: palette.foreground, fontWeight: "700" }}>{campaign.actionLabel}</AppText>
                <HomeGlyph name="arrow-right" size="compact" color={palette.foreground} />
              </View>
            </View>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

function CampaignNotice({ campaign, onPress }: { campaign: HomeCampaign; onPress: () => void }) {
  const { theme } = useTheme();
  const palette = campaignPalette(campaign.themeKey, theme.mode);
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`}
      style={({ pressed }) => ({ minHeight: 66, paddingHorizontal: theme.spacing.md, paddingVertical: theme.spacing.sm, flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, borderRadius: theme.radius.radiusSmall, backgroundColor: palette.background, opacity: pressed ? 0.84 : 1 })}
    >
      <View style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: palette.accent, alignItems: "center", justifyContent: "center" }}>
        <HomeGlyph name="bell-badge-outline" size="compact" color={palette.background} />
      </View>
      <View style={{ flex: 1, minWidth: 0 }}>
        <AppText variant="bodyStrong" numberOfLines={1} style={{ color: palette.foreground }}>{campaign.title}</AppText>
        <AppText variant="caption" numberOfLines={1} style={{ color: palette.foreground, opacity: 0.76 }}>{campaign.subtitle}</AppText>
      </View>
      <HomeGlyph name="chevron-right" size="standard" color={palette.foreground} />
    </Pressable>
  );
}

function campaignPalette(themeKey: string, mode: "light" | "dark") {
  const palettes = mode === "dark"
    ? {
        ink: { background: "#132039", foreground: "#F7F8FC", accent: "#79A7FF" },
        citrus: { background: "#312812", foreground: "#FFF8D6", accent: "#F7C948" },
        coral: { background: "#34201E", foreground: "#FFF1EE", accent: "#FF8A78" },
        mint: { background: "#15302B", foreground: "#EDFFF9", accent: "#72D9B5" },
        violet: { background: "#28203B", foreground: "#F7F0FF", accent: "#B89BFF" },
        sky: { background: "#142D3A", foreground: "#EAF9FF", accent: "#70C9EF" },
        sand: { background: "#30291F", foreground: "#FFF9EF", accent: "#D8B98B" },
      }
    : {
        ink: { background: "#0B1B35", foreground: "#FFFFFF", accent: "#71A3FF" },
        citrus: { background: "#FFF2A8", foreground: "#291E00", accent: "#D07100" },
        coral: { background: "#FFE0DA", foreground: "#341713", accent: "#D94B36" },
        mint: { background: "#DDF7EE", foreground: "#103229", accent: "#168263" },
        violet: { background: "#EAE0FF", foreground: "#281943", accent: "#7046C7" },
        sky: { background: "#DDF3FC", foreground: "#102F3D", accent: "#197A9F" },
        sand: { background: "#F3E7D5", foreground: "#35291D", accent: "#936630" },
      };
  return palettes[themeKey as keyof typeof palettes] ?? palettes.ink;
}

function SectionHeader({ title, inset = true, actionLabel, onAction }: { title: string; inset?: boolean; actionLabel?: string; onAction?: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ paddingHorizontal: inset ? theme.spacing.base : 0, marginBottom: theme.spacing.sm, flexDirection: "row", alignItems: "center" }}>
      <AppText variant="headingSmall">{title}</AppText>
      {actionLabel && onAction ? (
        <Pressable onPress={onAction} accessibilityRole="button" accessibilityLabel={actionLabel} style={{ marginLeft: "auto", minHeight: 36, paddingLeft: theme.spacing.md, flexDirection: "row", alignItems: "center", gap: 2 }}>
          <AppText variant="bodySmall" style={{ fontWeight: "600" }}>{actionLabel}</AppText>
          <Icon name="chevron-forward" size="compact" color={theme.colors.textPrimary} decorative />
        </Pressable>
      ) : null}
    </View>
  );
}

function NearbyServicesHeader({ title, zipcode, onAction }: { title: string; zipcode: string; onAction: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ paddingHorizontal: theme.spacing.base, marginBottom: theme.spacing.sm, flexDirection: "row", alignItems: "baseline" }}>
      <AppText variant="headingSmall">{title}</AppText>
      <AppText variant="caption" color="secondary" numberOfLines={1} style={{ marginLeft: theme.spacing.sm, flex: 1 }}>Based on {zipcode}</AppText>
      <Pressable onPress={onAction} accessibilityRole="button" accessibilityLabel="See all services" style={{ minHeight: 36, justifyContent: "center" }}>
        <AppText variant="bodySmall" style={{ color: theme.colors.brandPrimary, fontWeight: "800" }}>See All</AppText>
      </Pressable>
    </View>
  );
}

function ServiceGroupIcon({ group, size }: { group: HomeServiceGroup; index: number; size: number }) {
  const { theme } = useTheme();
  const dark = theme.mode === "dark";
  const iconUrl = resolveMediaUrl(group.iconUrl);
  const iconColor = dark ? "#F7F7FA" : "#56575D";
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: Math.round(size * 0.3),
        backgroundColor: dark ? "#1D1E22" : "#FAFAFC",
        borderWidth: 1,
        borderColor: dark ? "#292A2F" : "#FFFFFF",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        ...(dark ? {} : theme.shadow.sm),
      }}
    >
      {iconUrl ? (
        <Image source={{ uri: iconUrl }} resizeMode="contain" style={{ width: "60%", height: "60%", tintColor: iconColor }} accessibilityIgnoresInvertColors />
      ) : (
        <HomeGlyph name={groupIcon(group.name)} size={size >= 54 ? "navigation" : "standard"} color={iconColor} />
      )}
    </View>
  );
}

function ServiceGroupRail({ groups, variant, onPress }: { groups: HomeServiceGroup[]; variant: string; onPress: (group: HomeServiceGroup) => void }) {
  const { theme } = useTheme();
  const { width: windowWidth } = useWindowDimensions();
  const dark = theme.mode === "dark";
  const cardBackground = dark ? theme.colors.backgroundSunken : theme.colors.surfaceDefault;
  const cardBorder = dark ? theme.colors.borderDefault : theme.colors.borderSubtle;
  if (groups.length === 0) {
    return <View style={{ paddingHorizontal: theme.spacing.base }}><AppText variant="bodySmall" color="secondary">No services are available at this location yet.</AppText></View>;
  }
  if (variant === "compact_grid") {
    const cardWidth = (Math.min(windowWidth, 560) - theme.spacing.base * 2 - theme.spacing.xs * 3) / 4;
    return (
      <View style={{ paddingHorizontal: theme.spacing.base, flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xs }}>
        {groups.map((group, index) => (
          <Pressable
            key={group.serviceGroupId}
            onPress={() => onPress(group)}
            accessibilityRole="button"
            accessibilityLabel={`Book ${group.name}`}
            style={({ pressed }) => ({ width: cardWidth, minHeight: 94, paddingHorizontal: 3, paddingVertical: theme.spacing.xs, alignItems: "center", justifyContent: "center", borderRadius: 14, borderWidth: 1, borderColor: pressed ? theme.colors.brandPrimary : cardBorder, backgroundColor: cardBackground, opacity: pressed ? 0.76 : 1, ...(dark ? {} : theme.shadow.sm) })}
          >
            <ServiceGroupIcon group={group} index={index} size={44} />
            <AppText variant="caption" align="center" numberOfLines={2} style={{ marginTop: 6, minHeight: 28, fontWeight: "700", lineHeight: 13 }}>{group.name}</AppText>
          </Pressable>
        ))}
      </View>
    );
  }
  if (variant === "two_row") {
    const cardWidth = (Math.min(windowWidth, 560) - theme.spacing.base * 2 - theme.spacing.sm * 3) / 4;
    return (
      <View style={{ paddingHorizontal: theme.spacing.base, flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
        {groups.map((group, index) => (
          <Pressable key={group.serviceGroupId} onPress={() => onPress(group)} accessibilityRole="button" accessibilityLabel={`Book ${group.name}`} style={({ pressed }) => ({ width: cardWidth, alignItems: "center", opacity: pressed ? .75 : 1 })}>
            <View style={{ width: cardWidth, aspectRatio: 1, borderRadius: 16, overflow: "hidden", alignItems: "center", justifyContent: "center", backgroundColor: cardBackground, borderWidth: 1, borderColor: cardBorder, ...(dark ? {} : theme.shadow.sm) }}>
              <ServiceGroupIcon group={group} index={index} size={Math.min(62, cardWidth - 18)} />
            </View>
            <AppText variant="caption" align="center" numberOfLines={2} style={{ marginTop: 6, minHeight: 32, fontWeight: "700" }}>{group.name}</AppText>
          </Pressable>
        ))}
      </View>
    );
  }
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: theme.spacing.base, gap: theme.spacing.sm }}>
      {groups.map((group, index) => (
        <Pressable
          key={group.serviceGroupId}
          onPress={() => onPress(group)}
          accessibilityRole="button"
          accessibilityLabel={`Book ${group.name}`}
          style={({ pressed }) => ({
            width: 126,
            minHeight: 156,
            padding: theme.spacing.xs,
            borderRadius: theme.radius.radiusSmall,
            backgroundColor: pressed ? theme.colors.surfaceRaised : cardBackground,
            borderWidth: 1,
            borderColor: pressed ? theme.colors.brandPrimary : cardBorder,
            opacity: pressed ? 0.9 : 1,
            ...(dark ? {} : theme.shadow.sm),
          })}
        >
          <View style={{
            height: 108,
            borderRadius: Math.max(8, theme.radius.radiusSmall - 4),
            backgroundColor: dark ? theme.colors.surfaceSecondary : theme.colors.backgroundSecondary,
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}>
            <ServiceGroupIcon group={group} index={index} size={68} />
          </View>
          <View style={{ minHeight: 39, paddingHorizontal: 4, paddingTop: theme.spacing.xs, justifyContent: "center" }}>
            <AppText variant="bodySmall" align="center" numberOfLines={2} style={{ fontWeight: "700", lineHeight: 17 }}>
              {group.name}
            </AppText>
          </View>
        </Pressable>
      ))}
    </ScrollView>
  );
}

function FeaturedServiceRail({ services, onPress }: { services: HomeMasterService[]; onPress: (service: HomeMasterService) => void }) {
  const { theme } = useTheme();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: theme.spacing.base, gap: theme.spacing.sm }}>
      {services.map((service, index) => {
        const tones = [theme.colors.statusSuccess, theme.colors.statusInfo, theme.colors.accentViolet, theme.colors.statusWarning];
        const surfaces = [theme.colors.statusSuccessSurface, theme.colors.statusInfoSurface, theme.colors.accentVioletSurface, theme.colors.statusWarningSurface];
        return (
          <Pressable
            key={service.masterServiceId}
            onPress={() => onPress(service)}
            accessibilityRole="button"
            accessibilityLabel={`Book ${service.name}`}
            style={({ pressed }) => ({ width: 166, minHeight: 118, padding: theme.spacing.sm, borderRadius: theme.radius.radiusMedium, borderWidth: 1, borderColor: pressed ? tones[index % tones.length] : theme.colors.borderSubtle, backgroundColor: theme.colors.surfaceDefault, opacity: pressed ? .76 : 1 })}
          >
            <View style={{ width: 42, height: 42, borderRadius: 21, alignItems: "center", justifyContent: "center", backgroundColor: surfaces[index % surfaces.length] }}>
              <HomeGlyph name={groupIcon(service.serviceGroupName)} size="standard" color={tones[index % tones.length]} />
            </View>
            <AppText variant="bodySmall" numberOfLines={2} style={{ marginTop: theme.spacing.xs, fontWeight: "800", lineHeight: 17 }}>{service.name}</AppText>
            <AppText variant="caption" color="secondary" numberOfLines={1}>{service.serviceGroupName}</AppText>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

function MasterServiceGrid({ services, variant, photos = DEFAULT_HOME_PHOTOS, onPress }: {
  services: HomeMasterService[];
  variant: string;
  photos?: ImageSourcePropType[];
  onPress: (service: HomeMasterService) => void;
}) {
  const { theme } = useTheme();
  const { width: windowWidth } = useWindowDimensions();
  const gridWidth = Math.min(520, windowWidth - theme.spacing.base * 2);
  const cardWidth = (gridWidth - theme.spacing.sm) / 2;

  if (variant === "catalog_grid") {
    return (
      <View style={{ width: gridWidth, alignSelf: "center", flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
        {services.map(service => (
          <Pressable
            key={service.masterServiceId}
            onPress={() => onPress(service)}
            accessibilityRole="button"
            accessibilityLabel={`Book ${service.name}`}
            style={({ pressed }) => ({
              width: cardWidth,
              minHeight: 234,
              overflow: "hidden",
              borderRadius: 12,
              borderWidth: 1,
              borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle,
              backgroundColor: theme.colors.surfaceDefault,
              opacity: pressed ? 0.86 : 1,
            })}
          >
            <View style={{ height: 136, alignItems: "center", justifyContent: "center", overflow: "hidden", backgroundColor: theme.colors.surfaceRaised }}>
              <Image source={serviceArtwork(service)} resizeMode="contain" style={{ width: "88%", height: "88%" }} accessibilityIgnoresInvertColors />
            </View>
            <View style={{ flex: 1, minHeight: 96, paddingHorizontal: theme.spacing.sm, paddingVertical: 10, alignItems: "center" }}>
              <AppText variant="bodySmall" numberOfLines={2} style={{ fontWeight: "800", lineHeight: 18, textAlign: "center" }}>{service.name}</AppText>
              <AppText variant="caption" color="secondary" numberOfLines={2} style={{ marginTop: 4, lineHeight: 16, textAlign: "center" }}>
                {service.description || `Professional ${service.serviceGroupName.toLowerCase()} care`}
              </AppText>
              <AppText variant="caption" color="link" style={{ marginTop: "auto", paddingTop: 6, fontWeight: "800" }}>Book service</AppText>
            </View>
          </Pressable>
        ))}
      </View>
    );
  }

  if (variant === "recommendation_cards") {
    return (
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: theme.spacing.base, gap: theme.spacing.sm }}>
        {services.map((service, index) => (
          <Pressable
            key={service.masterServiceId}
            onPress={() => onPress(service)}
            accessibilityRole="button"
            accessibilityLabel={`Book ${service.name}`}
            style={({ pressed }) => ({ width: 182, minHeight: 226, overflow: "hidden", borderRadius: 12, backgroundColor: theme.colors.surfaceDefault, borderWidth: 1, borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle, opacity: pressed ? 0.82 : 1 })}
          >
            <Image source={photos[index % photos.length]} resizeMode="cover" style={{ width: "100%", height: 120 }} accessibilityIgnoresInvertColors />
            <View style={{ flex: 1, padding: theme.spacing.sm }}>
              <AppText variant="bodyStrong" numberOfLines={2}>{service.name}</AppText>
              <AppText variant="caption" color="secondary" numberOfLines={2} style={{ marginTop: 3 }}>{service.description || service.serviceGroupName}</AppText>
              <View style={{ marginTop: "auto", paddingTop: theme.spacing.sm, flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
                <AppText variant="caption" color="link" style={{ fontWeight: "800" }}>Book now</AppText>
                <HomeGlyph name="arrow-right" size="compact" color={theme.colors.brandPrimary} />
              </View>
            </View>
          </Pressable>
        ))}
      </ScrollView>
    );
  }

  if (variant === "image_rail") {
    return (
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: theme.spacing.base, gap: theme.spacing.sm }}>
        {services.map((service, index) => (
          <Pressable key={service.masterServiceId} onPress={() => onPress(service)} accessibilityRole="button" accessibilityLabel={`Book ${service.name}`} style={({ pressed }) => ({ width: 270, minHeight: 118, overflow: "hidden", flexDirection: "row", borderRadius: 12, backgroundColor: theme.colors.surfaceDefault, borderWidth: 1, borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle, opacity: pressed ? .82 : 1 })}>
            <Image source={photos[index % photos.length]} resizeMode="cover" style={{ width: 108, minHeight: 116 }} accessibilityIgnoresInvertColors />
            <View style={{ flex: 1, minWidth: 0, padding: theme.spacing.sm }}>
              <AppText variant="bodyStrong" numberOfLines={2}>{service.name}</AppText>
              <AppText variant="caption" color="secondary" numberOfLines={2} style={{ marginTop: 4 }}>{service.description || service.serviceGroupName}</AppText>
              <AppText variant="caption" color="link" style={{ marginTop: "auto", paddingTop: 6, fontWeight: "800" }}>Book now</AppText>
            </View>
          </Pressable>
        ))}
      </ScrollView>
    );
  }
  return (
    <View style={{ width: gridWidth, alignSelf: "center", flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
      {services.map((service, index) => (
          <Pressable key={service.masterServiceId} onPress={() => onPress(service)} accessibilityRole="button" accessibilityLabel={`Book ${service.name}`} style={({ pressed }) => ({ width: cardWidth, minHeight: 226, overflow: "hidden", borderRadius: 12, backgroundColor: theme.colors.surfaceDefault, borderWidth: 1, borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle, opacity: pressed ? .82 : 1 })}>
            <Image source={photos[index % photos.length]} resizeMode="cover" style={{ width: "100%", height: 120 }} accessibilityIgnoresInvertColors />
            <View style={{ flex: 1, padding: theme.spacing.sm }}>
              <AppText variant="bodyStrong" numberOfLines={2}>{service.name}</AppText>
              <AppText variant="caption" color="secondary" numberOfLines={2} style={{ marginTop: 3 }}>{service.description || service.serviceGroupName}</AppText>
              <AppText variant="caption" color="link" style={{ marginTop: "auto", paddingTop: 6, fontWeight: "800" }}>Book now</AppText>
            </View>
          </Pressable>
        ))}
    </View>
  );
}

function ProblemPhotoGrid({ issues, title, photos, onPressIssue }: {
  issues: readonly HomeQuickIssue[];
  title: string;
  photos: ImageSourcePropType[];
  onPressIssue: (issue: HomeQuickIssue) => void;
}) {
  const { theme } = useTheme();
  const tappable = issues.filter(issue => !!issue.categorySlug);
  if (!tappable.length) return null;
  const columns = [
    tappable.filter((_, index) => index % 2 === 0),
    tappable.filter((_, index) => index % 2 === 1),
  ];
  return (
    <View>
      <SectionHeader title={title} inset={false} />
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
        {columns.map((column, columnIndex) => (
          <View key={`problem-column-${columnIndex}`} style={{ flex: 1, gap: theme.spacing.sm }}>
            {column.map((issue, columnItemIndex) => {
              const originalIndex = columnItemIndex * 2 + columnIndex;
              // Alternating portrait and compact crops create the staggered
              // editorial rhythm in the approved Home reference. Content
              // height remains intrinsic, so translated/long labels do not clip.
              const imageHeight = originalIndex % 4 === 0 || originalIndex % 4 === 3 ? 176 : 142;
              return (
                <Pressable
                  key={issue.issueId}
                  onPress={() => onPressIssue(issue)}
                  accessibilityRole="button"
                  accessibilityLabel={`${issue.label}, ${issue.categoryName}`}
                  style={({ pressed }) => ({ overflow: "hidden", borderRadius: 12, borderWidth: 1, borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle, backgroundColor: theme.colors.surfaceDefault, opacity: pressed ? .82 : 1 })}
                >
                  <Image source={photos[originalIndex % photos.length]} resizeMode="cover" style={{ width: "100%", height: imageHeight }} accessibilityIgnoresInvertColors />
                  <View style={{ minHeight: 82, padding: theme.spacing.sm }}>
                    <AppText variant="bodySmall" numberOfLines={2} style={{ fontWeight: "800", lineHeight: 17 }}>{issue.label}</AppText>
                    <AppText variant="caption" color="secondary" numberOfLines={1} style={{ marginTop: 3 }}>{issue.categoryName}</AppText>
                    <AppText variant="caption" color="link" style={{ marginTop: 6, fontWeight: "800" }}>Get help</AppText>
                  </View>
                </Pressable>
              );
            })}
          </View>
        ))}
      </View>
    </View>
  );
}

function CustomerAssuranceStrip({ campaigns, variant }: { campaigns: HomeCampaign[]; variant: string }) {
  const { theme } = useTheme();
  const cards = variant === "compact_cards";
  const promiseIcon = (campaign: HomeCampaign): HomeGlyphName => {
    const text = `${campaign.badge} ${campaign.title}`.toLowerCase();
    if (text.includes("estimate") || text.includes("price")) return "file-document-check-outline";
    if (text.includes("warranty") || text.includes("protect")) return "shield-star-outline";
    if (text.includes("track") || text.includes("location")) return "map-marker-path";
    return "shield-check-outline";
  };
  return (
    <View style={{ flexDirection: "row", gap: cards ? theme.spacing.xs : 0 }}>
      {campaigns.map(campaign => (
        <View key={campaign.campaignId} accessibilityLabel={`${campaign.title}. ${campaign.subtitle}`} style={{ flex: 1, minWidth: 0, minHeight: cards ? 82 : 66, paddingHorizontal: 3, paddingVertical: cards ? theme.spacing.sm : theme.spacing.xs, alignItems: "center", justifyContent: "center", borderRadius: cards ? theme.radius.radiusSmall : 0, backgroundColor: cards ? theme.colors.surfaceDefault : "transparent" }}>
          <HomeGlyph name={promiseIcon(campaign)} size="standard" color={theme.colors.statusSuccess} />
          <AppText variant="caption" align="center" numberOfLines={2} style={{ marginTop: 5, fontWeight: "700", lineHeight: 13 }}>{campaign.title}</AppText>
        </View>
      ))}
    </View>
  );
}

function ActiveBookingTimeline({ title: sectionTitle, booking, onPress }: { title?: string | null; booking: HomeActiveBooking; onPress: () => void }) {
  const { theme } = useTheme();
  const status = interpretBookingStatus(booking.status, booking.assignmentStatus ?? "");
  const stages = [
    { key: "request", label: "Request", complete: true },
    { key: "professional", label: "Professional", complete: ["provider_assigned", "scheduled"].includes(status.stage) },
    { key: "visit", label: "Visit", complete: status.stage === "scheduled" },
  ];
  const title = booking.serviceName ?? booking.issueSummary ?? booking.bookingNumber ?? "Live booking";
  const place = booking.technician?.name ?? booking.provider?.name ?? booking.providerName ?? "Fuvay verified provider";

  return (
    <View>
      <View style={{ flexDirection: "row", alignItems: "center", marginBottom: theme.spacing.sm }}>
        <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: theme.colors.statusSuccess }} />
        <AppText variant="bodyStrong" style={{ marginLeft: theme.spacing.xs }}>{sectionTitle ?? "Live booking"}</AppText>
        <AppText variant="caption" color="secondary" style={{ marginLeft: theme.spacing.xs }}>· Right now</AppText>
      </View>
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={`${title}, ${status.statusLabel}, open tracking`}
        style={({ pressed }) => ({ flexDirection: "row", alignItems: "stretch", borderWidth: 1, borderColor: theme.colors.borderSubtle, borderRadius: theme.radius.radiusMedium, backgroundColor: theme.colors.surfaceDefault, opacity: pressed ? 0.82 : 1 })}
      >
        <View style={{ flex: 1, minWidth: 0, padding: theme.spacing.md }}>
          <View style={{ flexDirection: "row", alignItems: "flex-start" }}>
            {stages.map((stage, index) => (
              <View key={stage.key} style={{ flex: 1, alignItems: index === 0 ? "flex-start" : index === stages.length - 1 ? "flex-end" : "center" }}>
                <View style={{ width: "100%", flexDirection: "row", alignItems: "center" }}>
                  {index > 0 ? <View style={{ flex: 1, height: 1, backgroundColor: stage.complete ? theme.colors.statusSuccess : theme.colors.borderDefault }} /> : null}
                  <View style={{ width: 18, height: 18, borderRadius: 9, borderWidth: 1, borderColor: stage.complete ? theme.colors.statusSuccess : theme.colors.borderStrong, backgroundColor: stage.complete ? theme.colors.statusSuccessSurface : theme.colors.surfaceDefault, alignItems: "center", justifyContent: "center" }}>
                    {stage.complete ? <Icon name="checkmark" size="compact" color={theme.colors.statusSuccess} decorative /> : null}
                  </View>
                  {index < stages.length - 1 ? <View style={{ flex: 1, height: 1, backgroundColor: stages[index + 1]?.complete ? theme.colors.statusSuccess : theme.colors.borderDefault }} /> : null}
                </View>
                <AppText variant="caption" numberOfLines={1} style={{ marginTop: theme.spacing.xs, fontSize: 9 }}>{stage.label}</AppText>
              </View>
            ))}
          </View>
        </View>
        <View style={{ width: 122, borderLeftWidth: 1, borderLeftColor: theme.colors.borderSubtle, padding: theme.spacing.sm, justifyContent: "center" }}>
          <AppText variant="bodySmall" numberOfLines={1} style={{ fontWeight: "700" }}>{title}</AppText>
          <AppText variant="caption" color="secondary" numberOfLines={1}>{place}</AppText>
          <View style={{ marginTop: theme.spacing.xs, flexDirection: "row", alignItems: "center", gap: 2 }}>
            <AppText variant="caption" color="success" numberOfLines={1} style={{ flex: 1, fontWeight: "600" }}>{status.statusLabel}</AppText>
            <Icon name="chevron-forward" size="compact" color={theme.colors.textPrimary} decorative />
          </View>
        </View>
      </Pressable>
    </View>
  );
}

function CompactActiveBooking({ booking, onPress }: { booking: HomeActiveBooking; onPress: () => void }) {
  const { theme } = useTheme();
  const status = interpretBookingStatus(booking.status, booking.assignmentStatus ?? "");
  const person = booking.technician?.name ?? booking.provider?.name ?? booking.providerName;
  const title = booking.serviceName ?? booking.issueSummary ?? booking.bookingNumber ?? "Active booking";
  const photoUrl = booking.technician?.photoUrl;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${title}, ${status.statusLabel}, track booking`}
      style={({ pressed }) => ({ minHeight: 76, borderWidth: 1, borderColor: theme.colors.statusSuccessSurface, borderRadius: theme.radius.radiusLarge, backgroundColor: theme.colors.surfaceDefault, paddingHorizontal: theme.spacing.md, flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, opacity: pressed ? 0.82 : 1 })}
    >
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: theme.colors.statusSuccess }} />
      <View style={{ width: 44, height: 44, borderRadius: 22, overflow: "hidden", alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.brandPrimaryMuted }}>
        {photoUrl ? <Image source={{ uri: resolveMediaUrl(photoUrl)! }} style={{ width: "100%", height: "100%" }} /> : <Icon name="person-outline" color={theme.colors.brandPrimary} decorative />}
      </View>
      <View style={{ flex: 1, minWidth: 0 }}>
        <View style={{ flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 4 }}>
          <AppText variant="bodyStrong" numberOfLines={1}>{title}</AppText>
          <AppText variant="bodySmall" color="success" numberOfLines={1}>· {status.statusLabel}</AppText>
          {booking.provider?.verified ? <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative /> : null}
        </View>
        {person ? <AppText variant="caption" color="secondary" numberOfLines={1}>{person}</AppText> : null}
      </View>
      <AppText variant="button" color="link">Track</AppText>
      <Icon name="chevron-forward" size="compact" color={theme.colors.brandPrimary} decorative />
    </Pressable>
  );
}

function CampaignStoryRail({ campaigns, variant, onPress }: { campaigns: HomeCampaign[]; variant: string; onPress: (campaign: HomeCampaign) => void }) {
  const { theme } = useTheme();
  const { width: viewportWidth } = useWindowDimensions();
  const isSingleStory = campaigns.length === 1;
  const storyWidth = isSingleStory
    ? Math.min(520, viewportWidth - theme.spacing.base * 2)
    : variant === "portrait" ? 172 : 238;
  const storyHeight = isSingleStory ? 214 : variant === "portrait" ? 238 : 156;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: theme.spacing.base, gap: theme.spacing.sm }}>
      {campaigns.map(campaign => (
        <Pressable
          key={campaign.campaignId}
          onPress={() => onPress(campaign)}
          accessibilityRole="button"
          accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`}
          style={({ pressed }) => ({ width: storyWidth, opacity: pressed ? 0.84 : 1 })}
        >
          <ImageBackground source={{ uri: resolveMediaUrl(campaign.imageUrl)! }} resizeMode="cover" style={{ height: storyHeight }}>
            <View style={{ flex: 1, justifyContent: "space-between", padding: theme.spacing.md, backgroundColor: theme.colors.campaignScrim }}>
              <View style={{ alignSelf: "flex-start", paddingHorizontal: 8, paddingVertical: 4, backgroundColor: theme.colors.campaignBadgeScrim }}>
                <AppText variant="caption" style={{ color: theme.colors.campaignAccent, fontWeight: "700" }}>{campaign.badge}</AppText>
              </View>
              <View>
                <AppText variant="title" numberOfLines={2} style={{ color: theme.colors.mediaForeground }}>{campaign.title}</AppText>
                <View style={{ marginTop: 5, flexDirection: "row", alignItems: "center", gap: 4 }}>
                  <AppText variant="labelStrong" style={{ color: theme.colors.mediaForeground }}>{campaign.actionLabel}</AppText>
                  <Icon name="arrow-forward" size="compact" color={theme.colors.mediaForeground} decorative />
                </View>
              </View>
            </View>
          </ImageBackground>
        </Pressable>
      ))}
    </ScrollView>
  );
}

function CampaignSpotlight({ campaigns, variant, onPress }: {
  campaigns: HomeCampaign[];
  variant: string;
  onPress: (campaign: HomeCampaign) => void;
}) {
  const { theme } = useTheme();
  const { width: viewportWidth } = useWindowDimensions();
  const split = variant === "split_feature";
  const cardWidth = Math.min(520, viewportWidth - theme.spacing.base * 2);
  return (
    <ScrollView
      horizontal
      pagingEnabled
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ paddingHorizontal: theme.spacing.base, gap: theme.spacing.sm }}
    >
      {campaigns.map(campaign => {
        const palette = campaignPalette(campaign.themeKey, theme.mode);
        return split ? (
          <Pressable
            key={campaign.campaignId}
            onPress={() => onPress(campaign)}
            accessibilityRole="button"
            accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`}
            style={({ pressed }) => ({
              width: cardWidth,
              minHeight: 168,
              flexDirection: "row",
              overflow: "hidden",
              borderWidth: 1,
              borderColor: theme.colors.borderSubtle,
              backgroundColor: palette.background,
              opacity: pressed ? 0.86 : 1,
            })}
          >
            <Image
              source={{ uri: resolveMediaUrl(campaign.imageUrl)! }}
              resizeMode="cover"
              style={{ width: 142, minHeight: 168 }}
              accessibilityIgnoresInvertColors
            />
            <View style={{ flex: 1, padding: theme.spacing.md }}>
              <AppText variant="caption" numberOfLines={1} style={{ color: palette.accent, fontWeight: "800", textTransform: "uppercase" }}>{campaign.badge}</AppText>
              <AppText variant="title" numberOfLines={2} style={{ marginTop: theme.spacing.xs, color: palette.foreground }}>{campaign.title}</AppText>
              <AppText variant="caption" numberOfLines={2} style={{ marginTop: 4, color: palette.foreground, opacity: 0.76 }}>{campaign.subtitle}</AppText>
              <View style={{ marginTop: "auto", paddingTop: theme.spacing.sm, flexDirection: "row", alignItems: "center", gap: 4 }}>
                <AppText variant="caption" style={{ color: palette.foreground, fontWeight: "800" }}>{campaign.actionLabel}</AppText>
                <HomeGlyph name="arrow-right" size="compact" color={palette.foreground} />
              </View>
            </View>
          </Pressable>
        ) : (
          <Pressable
            key={campaign.campaignId}
            onPress={() => onPress(campaign)}
            accessibilityRole="button"
            accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`}
            style={({ pressed }) => ({ width: cardWidth, height: 226, opacity: pressed ? 0.86 : 1 })}
          >
            <ImageBackground
              source={{ uri: resolveMediaUrl(campaign.imageUrl)! }}
              resizeMode="cover"
              style={{ flex: 1, overflow: "hidden", borderRadius: theme.radius.radiusSmall }}
              accessibilityIgnoresInvertColors
            >
              <View style={{ flex: 1, justifyContent: "flex-end", padding: theme.spacing.base, backgroundColor: theme.colors.mediaScrimStrong }}>
                <View style={{ alignSelf: "flex-start", paddingHorizontal: 8, paddingVertical: 4, backgroundColor: theme.colors.campaignAccent }}>
                  <AppText variant="caption" style={{ color: theme.colors.campaignBadgeForeground, fontWeight: "800" }}>{campaign.badge}</AppText>
                </View>
                <AppText variant="headingMedium" numberOfLines={2} style={{ marginTop: theme.spacing.xs, color: theme.colors.mediaForeground }}>{campaign.title}</AppText>
                <View style={{ marginTop: theme.spacing.sm, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: theme.spacing.sm }}>
                  <AppText variant="caption" numberOfLines={2} style={{ flex: 1, color: theme.colors.mediaForegroundMuted }}>{campaign.subtitle}</AppText>
                  <View style={{ minHeight: 34, paddingHorizontal: theme.spacing.sm, flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: theme.colors.surfaceDefault }}>
                    <AppText variant="caption" style={{ color: theme.colors.textPrimary, fontWeight: "800" }}>{campaign.actionLabel}</AppText>
                    <HomeGlyph name="arrow-right" size="compact" color={theme.colors.textPrimary} />
                  </View>
                </View>
              </View>
            </ImageBackground>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

function CampaignEditorialBanner({ campaign, contained, onPress }: { campaign: HomeCampaign; contained: boolean; onPress: () => void }) {
  const { theme } = useTheme();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`} style={({ pressed }) => ({ marginHorizontal: contained ? theme.spacing.base : 0, opacity: pressed ? 0.86 : 1 })}>
      <ImageBackground source={{ uri: resolveMediaUrl(campaign.imageUrl)! }} resizeMode="cover" style={{ height: 176, overflow: "hidden", borderRadius: contained ? theme.radius.radiusSmall : 0 }}>
        <View style={{ flex: 1, padding: theme.spacing.base, justifyContent: "flex-end", backgroundColor: theme.colors.campaignScrim }}>
          <AppText variant="caption" style={{ color: theme.colors.mediaForegroundMuted, opacity: 0.82, fontWeight: "700" }}>{campaign.badge.toUpperCase()}</AppText>
          <AppText variant="headingSmall" numberOfLines={2} style={{ color: theme.colors.mediaForeground, marginTop: 3, maxWidth: "72%" }}>{campaign.title}</AppText>
          {campaign.offerText ? <AppText variant="bodyStrong" style={{ color: theme.colors.campaignAccent, marginTop: 3 }}>{campaign.offerText}</AppText> : null}
          <View style={{ flexDirection: "row", alignItems: "center", gap: 4, marginTop: theme.spacing.sm }}>
            <AppText variant="button" style={{ color: theme.colors.mediaForeground }}>{campaign.actionLabel}</AppText>
            <Icon name="arrow-forward" size="compact" color={theme.colors.mediaForeground} decorative />
          </View>
        </View>
      </ImageBackground>
    </Pressable>
  );
}

function AskFuvayStrip({ seasonLabel, onPress }: { seasonLabel: string | null; onPress: () => void }) {
  const { theme } = useTheme();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel="Ask Fuvay for help choosing a service" style={({ pressed }) => ({ minHeight: 88, borderRadius: theme.radius.radiusLarge, backgroundColor: theme.colors.brandPrimaryMuted, padding: theme.spacing.base, flexDirection: "row", alignItems: "center", gap: theme.spacing.md, opacity: pressed ? 0.82 : 1 })}>
      <View style={{ width: 48, height: 48, borderRadius: 15, alignItems: "center", justifyContent: "center", backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: theme.colors.borderSubtle }}>
        <FuvayIcon size={33} accessibilityLabel="Fuvay booking assistant" />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="title">Not sure what to book?</AppText>
        <AppText variant="bodySmall" color="secondary">{seasonLabel ? `${seasonLabel} · Describe the issue and we'll guide you.` : "Describe the issue and we'll guide you."}</AppText>
      </View>
      <Icon name="chevron-forward" color={theme.colors.brandPrimary} decorative />
    </Pressable>
  );
}

function InlineAction({ label, accessibilityLabel, icon, onPress }: {
  label: string;
  accessibilityLabel?: string;
  icon: React.ComponentProps<typeof Icon>["name"];
  onPress: () => void;
}) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      style={({ pressed }) => ({
        minHeight: 54,
        paddingHorizontal: theme.spacing.base,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceDefault,
        flexDirection: "row",
        alignItems: "center",
        gap: theme.spacing.sm,
        opacity: pressed ? 0.78 : 1,
      })}
    >
      <Icon name={icon} size="standard" color={theme.colors.brandPrimary} decorative />
      <AppText variant="bodyStrong" style={{ flex: 1 }}>{label}</AppText>
      <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
    </Pressable>
  );
}

function partitionHomeIssues(issues: readonly HomeQuickIssue[]) {
  const tappable = issues.filter(issue => issue.categorySlug);
  const featured = tappable.slice(0, 8);
  const remaining = tappable.slice(featured.length);
  return {
    featured,
    repairs: remaining.filter(issue => issue.intent === "repair").slice(0, 8),
    consultations: remaining.filter(issue => issue.intent === "consult").slice(0, 8),
    more: remaining.filter(issue => issue.intent === null).slice(0, 8),
  };
}

function formatCampaignEnd(value: string): string | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return `Ends ${date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}`;
}
