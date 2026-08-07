import React, { useMemo, useState } from "react";
import { ScrollView, RefreshControl, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText } from "../../components";
import { OfflineBanner } from "../../components/OfflineBanner";
import {
  CustomerHeader, ServiceSearch, CampaignCarousel, VerticalSwitcher, HomeServiceCard,
  AssistantEntryCard, MyBookingSection, TrustBenefitCard, HomeSkeleton, HomeErrorState,
  NoAddressState, UnserviceableState, HomeSectionErrorBoundary, LocationPickerModal, GlobalServicesSection,
  SearchResultsList, QuickIssuesSection,
} from "../../components/home";
import { useCustomerHomeQuery } from "../../api/home/useCustomerHomeQuery";
import { useCustomerSearchQuery, MIN_QUERY_LENGTH } from "../../api/home/useCustomerSearchQuery";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { timeSensitiveGreeting } from "../../domain/greeting";
import { resolveCampaignDeepLink } from "../../domain/campaignDeepLink";
import type { HomeCampaign } from "../../domain/customerHome";
import { HomeCategory } from "../../domain/customerHome";
import { createServiceCardEntryContext, createAssistantCardEntryContext, createQuickIssueEntryContext } from "../../domain/assistantEntry";
import type { HomeQuickIssue } from "../../domain/customerHome";
import { CustomerTabsParamList } from "../../navigation/routeTypes";

// Static marketing copy, not backend data. Restored per the reference
// design's "Why Customers Choose Us" section -- this is the exact content
// that shipped before, not new copy.
/**
 * Static marketing copy -- there is no backend contract for these, so they
 * are declared here rather than faked as API data.
 *
 * `artworkUrl` points at illustrations uploaded through the admin media
 * library (the same pipeline as category artwork), so they can be replaced
 * without a release; each still names a glyph to fall back to if its asset
 * is ever removed. The set matches the three shown in the design -- the
 * previous fourth ("Support 24/7") is dropped rather than invented, since
 * nothing here backs a 24/7 support claim.
 */
const TRUST_STRIP_ITEMS = [
  {
    key: "verified", label: "Verified Expert", icon: "shield-checkmark-outline" as const,
    artworkUrl: "/uploads/global_service_icon/d0fc7c317ee3c5e7bdb041a8.png",
  },
  {
    key: "pricing", label: "Transparent Pricing", icon: "pricetag-outline" as const,
    artworkUrl: "/uploads/global_service_icon/f1a056b66f3a0649b062f939.png",
  },
  {
    key: "updates", label: "Status Update", icon: "notifications-outline" as const,
    artworkUrl: "/uploads/global_service_icon/daf44c94c55cf79bcb7350f6.png",
  },
];

/**
 * Real Home screen consuming GET /v1/customer/home. Confirmed contract
 * gaps this screen honestly works around (not fabricated): no
 * per-category price field, no distinct "offer" campaign type (so no
 * separate "Offers for you" section). Per explicit product direction:
 * per-service prices and "Offers for you" stay absent (pricing belongs
 * later in the booking flow; offers need real eligibility/codes first).
 * ZIP/address selection and service→Assistant navigation (with backend
 * context) ARE implemented this pass; campaign CTAs remain
 * non-interactive since no deep-link routing destination exists yet.
 */
export function HomeScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<BottomTabNavigationProp<CustomerTabsParamList>>();
  const { mode } = useTheme();
  const network = useNetworkStatus();
  const [searchValue, setSearchValue] = useState("");
  const [selectedVerticalKey, setSelectedVerticalKey] = useState("home_services");
  const [zipcodeOverride, setZipcodeOverride] = useState<string | undefined>(undefined);
  const [locationPickerVisible, setLocationPickerVisible] = useState(false);

  const homeQuery = useCustomerHomeQuery(zipcodeOverride);
  // Neither GET /v1/customer/home nor /v1/auth/access-context return a
  // display name (confirmed this task) -- a separate, justified query
  // supplies it. Its own loading/error state never blocks the rest of
  // Home; it just falls back to a neutral greeting until it resolves.
  const profileQuery = useCustomerProfileQuery();

  const greeting = useMemo(() => timeSensitiveGreeting(), []);

  // Category ids bookable at this ZIP -- the set the server-side search
  // results get reconciled against (search itself has no zipcode param).
  //
  // MUST stay above the isPending/isError early returns below: a hook
  // placed after them runs only on some renders, which is exactly the
  // "Rendered more hooks than during the previous render" crash.
  const bookableCategoryIds = useMemo(
    () => new Set((homeQuery.data?.bookableCategories ?? []).map(c => String(c.categoryId))),
    [homeQuery.data?.bookableCategories],
  );

  /** Names cycled through the search placeholder. Same ZIP-filtered source
   * as the service grid, so the hint only ever names something bookable. */
  const searchSuggestions = useMemo(
    () => (homeQuery.data?.bookableCategories ?? []).map(c => c.name).filter(Boolean),
    [homeQuery.data?.bookableCategories],
  );

  // Server-side search, replacing a client-side filter over the already
  // loaded categories. That filter could only ever match whole category
  // names, so "gas", "deep clean" or "pipe repair" -- real services people
  // actually search for -- found nothing. The endpoint searches individual
  // services too.
  const searchQuery = useCustomerSearchQuery(
    searchValue,
    bookableCategoryIds,
    homeQuery.data?.address?.zipcode ?? undefined,
  );
  const isSearching = searchValue.trim().length >= MIN_QUERY_LENGTH;
  /** The slugs a campaign CTA is allowed to route into. Same source as the
   * service cards: whatever the backend says is bookable at this ZIP. Kept
   * above the early returns for the same Rules-of-Hooks reason as above. */
  const bookableSlugs = useMemo(
    () => (homeQuery.data?.bookableCategories ?? [])
      .map(c => c.slug)
      .filter((s): s is string => Boolean(s)),
    [homeQuery.data?.bookableCategories],
  );

  const customerFirstName = profileQuery.data?.fullName?.split(" ")[0] || "there";

  /** Changing location re-runs GET /v1/customer/home?zipcode=<new> --
   * this IS the real serviceability re-check and service refresh (the
   * backend recomputes `serviceability` and `bookable_categories` for
   * the new ZIP; nothing is re-derived client-side). */
  function handleConfirmLocation(newZipcode: string) {
    setZipcodeOverride(newZipcode);
  }

  /** `zipcode` is required (non-null) by AssistantEntryContext -- this is
   * only ever called from the "ready" render branch below, where
   * `home.address.zipcode` is already known to be a real value (the
   * NoAddressState/UnserviceableState branches return before this point
   * ever renders anything that could call this). A tap on a category
   * with no resolvable `slug` (the field the backend genuinely requires
   * to start a draft) is silently ignored rather than navigating into a
   * broken state -- see HomeServiceCard, which is the only caller. */
  function navigateToService(category: HomeCategory, zipcode: string) {
    if (!category.slug) return;
    navigation.navigate("Assistant", createServiceCardEntryContext({
      categoryId: category.categoryId,
      categoryName: category.name,
      categorySlug: category.slug,
      zipcode,
    }));
  }

  /** A campaign CTA tap. Only reached for links that already resolved to a
   * real destination (the carousel disables the rest), and re-resolved here
   * rather than trusted so the two can never drift apart. */
  function handleCampaignCta(campaign: HomeCampaign) {
    const home = homeQuery.data;
    const zipcode = home?.address?.zipcode;
    if (!home || !zipcode) return;

    const target = resolveCampaignDeepLink(campaign.ctaDeeplink, bookableSlugs);
    if (!target) return;

    if (target.kind === "home") return; // Already here; nothing to navigate to.

    const category = home.bookableCategories.find(c => c.slug === target.slug);
    if (!category) return;
    navigateToService(category, zipcode);
  }

  /** Same destination as a service-card tap, with the issue carried along
   * so the Assistant can skip its picker. A slug-less issue is dropped by
   * QuickIssuesSection before it can get here. */
  function navigateToQuickIssue(issue: HomeQuickIssue, zipcode: string) {
    if (!issue.categorySlug) return;
    navigation.navigate("Assistant", createQuickIssueEntryContext({
      categoryId: issue.categoryId,
      categoryName: issue.categoryName,
      categorySlug: issue.categorySlug,
      zipcode,
      issueId: issue.issueId,
    }));
  }

  function navigateToGenericAssistant(zipcode: string) {
    navigation.navigate("Assistant", createAssistantCardEntryContext({ zipcode }));
  }

  if (homeQuery.isPending) {
    return (
      <AppScreen scroll>
        <HomeSkeleton />
      </AppScreen>
    );
  }

  if (homeQuery.isError) {
    return (
      <AppScreen>
        {network === "offline" ? <OfflineBanner /> : null}
        <View style={{ flex: 1, justifyContent: "center" }}>
          <HomeErrorState onRetry={() => homeQuery.refetch()} />
        </View>
      </AppScreen>
    );
  }

  const home = homeQuery.data;
  if (!home) return null;

  if (!home.address) {
    return (
      <AppScreen>
        <OfflineBanner />
        <View style={{ flex: 1, justifyContent: "center" }}>
          <NoAddressState onAddAddress={() => setLocationPickerVisible(true)} />
        </View>
        {/* Shown even with no address on file -- Global Services is
            nationwide/fixed, never gated by serviceability (see
            GlobalServicesSection). */}
        <View style={{ paddingHorizontal: theme.layout.screenHorizontalPadding, paddingBottom: theme.spacing.lg }}>
          <GlobalServicesSection defaultName={customerFirstName !== "there" ? customerFirstName : undefined} />
        </View>
        <LocationPickerModal
          visible={locationPickerVisible}
          currentZipcode={zipcodeOverride ?? null}
          onClose={() => setLocationPickerVisible(false)}
          onConfirm={handleConfirmLocation}
        />
      </AppScreen>
    );
  }

  if (home.serviceability?.checked === false) {
    return (
      <AppScreen>
        <UnserviceableState zipcode={home.serviceability.zipcode} onChangeLocation={() => setLocationPickerVisible(true)} />
        <View style={{ paddingHorizontal: theme.layout.screenHorizontalPadding, paddingBottom: theme.spacing.lg }}>
          <GlobalServicesSection
            defaultName={customerFirstName !== "there" ? customerFirstName : undefined}
            defaultZipcode={home.serviceability.zipcode}
          />
        </View>
        <LocationPickerModal
          visible={locationPickerVisible}
          currentZipcode={home.serviceability.zipcode}
          onClose={() => setLocationPickerVisible(false)}
          onConfirm={handleConfirmLocation}
        />
      </AppScreen>
    );
  }

  const locationLabel = home.address.city && home.address.zipcode ? `${home.address.city} · ${home.address.zipcode}` : home.address.zipcode;

  return (
    <AppScreen style={{ paddingHorizontal: 0 }}>
      <OfflineBanner />
      <ScrollView
        contentContainerStyle={{ padding: theme.layout.screenHorizontalPadding, paddingBottom: theme.spacing.xxxl }}
        refreshControl={<RefreshControl refreshing={homeQuery.isRefetching} onRefresh={() => homeQuery.refetch()} tintColor={theme.colors.brandPrimary} />}
      >
        <HomeSectionErrorBoundary sectionLabel="header">
          <CustomerHeader
            greeting={greeting}
            customerFirstName={customerFirstName}
            locationLabel={locationLabel}
            onPressLocation={() => setLocationPickerVisible(true)}
            serviceable={home.serviceability?.checked}
            unreadNotifications={home.unreadNotificationCount > 0}
            onPressNotifications={() =>
              (navigation.getParent()?.navigate as ((name: string) => void) | undefined)?.("Notifications")
            }
          />
        </HomeSectionErrorBoundary>

        <View style={{ marginTop: theme.spacing.base }}>
          {/* Suggestions are the categories genuinely bookable at this ZIP,
              so the rotating hint never advertises something the customer
              cannot actually book here. */}
          <ServiceSearch
            value={searchValue}
            onChangeText={setSearchValue}
            suggestions={searchSuggestions}
          />
        </View>

        {/* Section order below matches the reference design: verticals,
            then the promo banner, then Services Nearby, then Active
            Booking, then Global Services, then the trust strip. (An
            earlier pass here moved Active Booking above the banner for a
            UX reason -- reverted so the app matches the design the way it
            was actually asked for.) The spacer-avoidance comment on
            VerticalSwitcher still applies: it self-hides with one
            vertical, so its wrapper is conditionally rendered too rather
            than always contributing a top margin. */}
        {home.enabledVerticals.length > 1 ? (
          <HomeSectionErrorBoundary sectionLabel="verticals">
            <View style={{ marginTop: theme.spacing.lg }}>
              <VerticalSwitcher
                verticals={home.enabledVerticals}
                selectedVerticalKey={selectedVerticalKey}
                onSelect={v => setSelectedVerticalKey(v.key)}
              />
            </View>
          </HomeSectionErrorBoundary>
        ) : null}

        <HomeSectionErrorBoundary sectionLabel="promotions">
          <View style={{ marginTop: theme.spacing.lg }}>
            {/* CTAs are now live for deep links that resolve to a real
             * destination for THIS customer; the rest stay disabled
             * rather than becoming dead buttons. */}
            <CampaignCarousel
              campaigns={home.campaigns}
              mode={mode}
              isCtaRoutable={c => resolveCampaignDeepLink(c.ctaDeeplink, bookableSlugs) !== null}
              onPressCta={handleCampaignCta}
            />
          </View>
        </HomeSectionErrorBoundary>

        {/* Directly below the banner, deliberately ahead of the category
            grid: this is the shorter route to the same booking, so it
            should be seen before the longer one. Renders nothing when the
            ZIP's categories carry no issues. */}
        <HomeSectionErrorBoundary sectionLabel="quick issues">
          <View style={{ marginTop: theme.spacing.xl }}>
            <QuickIssuesSection
              issues={home.quickIssues}
              onPressIssue={issue => navigateToQuickIssue(issue, home.address!.zipcode as string)}
            />
          </View>
        </HomeSectionErrorBoundary>

        <HomeSectionErrorBoundary sectionLabel="services">
          <View style={{ marginTop: theme.spacing.xl }}>
            {/* Title + inline qualifier on the left, "See All" on the right,
                matching the section header treatment used across the design.
                Section titles were `bodyStrong` (15px) -- the same weight as
                a card title, so nothing signalled the start of a section. */}
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", marginBottom: theme.spacing.sm }}>
              <View style={{ flexDirection: "row", alignItems: "baseline", gap: theme.spacing.xs, flex: 1, minWidth: 0 }}>
                <AppText variant="headingSmall">{isSearching ? "Results" : "Services Nearby"}</AppText>
                {home.address.zipcode ? (
                  <AppText variant="caption" color="tertiary" numberOfLines={1}>
                    {isSearching
                      ? `for "${searchValue.trim()}"`
                      : `Based on ${home.address.zipcode}`}
                  </AppText>
                ) : null}
              </View>
            </View>
            {isSearching ? (
              <SearchResultsList
                query={searchValue.trim()}
                isPending={searchQuery.isPending}
                isError={searchQuery.isError}
                results={searchQuery.data?.results ?? []}
                onPressCategory={categoryId => {
                  const category = home.bookableCategories.find(c => String(c.categoryId) === String(categoryId));
                  if (category) navigateToService(category, home.address!.zipcode as string);
                }}
              />
            ) : home.bookableCategories.length === 0 ? (
              <AppText variant="bodySmall" color="secondary">No services are available in your area yet.</AppText>
            ) : (
              // Explicit 2-up rows rather than a wrapping flex row: with
              // `flexWrap` + `space-between`, a trailing row holding one
              // card stretched it across the full width. The card itself is
              // horizontal now (artwork left, copy right), so a lone card is
              // padded with an equal-flex spacer to keep every tile the same
              // width as the rows above it.
              <View style={{ gap: theme.spacing.sm }}>
                {Array.from({ length: Math.ceil(home.bookableCategories.length / 2) }).map((_, rowIndex) => {
                  const row = home.bookableCategories.slice(rowIndex * 2, rowIndex * 2 + 2);
                  return (
                    <View key={rowIndex} style={{ flexDirection: "row", gap: theme.spacing.sm }}>
                      {row.map(category => (
                        <HomeServiceCard
                          key={category.categoryId}
                          category={category}
                          onPress={() => navigateToService(category, home.address!.zipcode as string)}
                        />
                      ))}
                      {row.length === 1 ? <View style={{ flex: 1 }} /> : null}
                    </View>
                  );
                })}
              </View>
            )}
          </View>
        </HomeSectionErrorBoundary>

        <HomeSectionErrorBoundary sectionLabel="assistant">
          <View style={{ marginTop: theme.spacing.lg }}>
            <AssistantEntryCard onPress={() => navigateToGenericAssistant(home.address!.zipcode as string)} />
          </View>
        </HomeSectionErrorBoundary>

        {home.activeBooking ? (
          <HomeSectionErrorBoundary sectionLabel="my booking">
            <View style={{ marginTop: theme.spacing.xl }}>
              <MyBookingSection
                booking={home.activeBooking}
                onPress={() => navigation.navigate("Bookings")}
                onViewAll={() => navigation.navigate("Bookings")}
                iconUrl={home.bookableCategories.find(
                  c => c.name === home.activeBooking?.serviceName,
                )?.iconUrl ?? null}
              />
            </View>
          </HomeSectionErrorBoundary>
        ) : null}

        {/* Fixed, nationwide section -- never filtered by this ZIP's
            bookable_categories, unlike "Services near you" above (see
            GlobalServicesSection). */}
        <HomeSectionErrorBoundary sectionLabel="global services">
          <View style={{ marginTop: theme.spacing.xl }}>
            <GlobalServicesSection
              defaultName={customerFirstName !== "there" ? customerFirstName : undefined}
              defaultZipcode={home.address.zipcode}
            />
          </View>
        </HomeSectionErrorBoundary>

        <HomeSectionErrorBoundary sectionLabel="trust">
          <AppText variant="headingSmall" style={{ marginTop: theme.spacing.xl, marginBottom: theme.spacing.sm }}>
            Why Customers Choose Us
          </AppText>
          <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
            {TRUST_STRIP_ITEMS.map(item => (
              <TrustBenefitCard key={item.key} label={item.label} icon={item.icon} artworkUrl={item.artworkUrl} />
            ))}
          </View>
        </HomeSectionErrorBoundary>
      </ScrollView>

      <LocationPickerModal
        visible={locationPickerVisible}
        currentZipcode={home.address.zipcode}
        onClose={() => setLocationPickerVisible(false)}
        onConfirm={handleConfirmLocation}
      />
    </AppScreen>
  );
}
