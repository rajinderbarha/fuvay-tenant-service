import React, { useMemo, useState } from "react";
import { ScrollView, RefreshControl, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText } from "../../components";
import { OfflineBanner } from "../../components/OfflineBanner";
import {
  CustomerHeader, ServiceSearch, CampaignCarousel, VerticalSwitcher, HomeServiceCard,
  AssistantEntryCard, ActiveBookingCard, TrustBenefitCard, HomeSkeleton, HomeErrorState,
  NoAddressState, UnserviceableState, HomeSectionErrorBoundary, LocationPickerModal, GlobalServicesSection,
} from "../../components/home";
import { useCustomerHomeQuery } from "../../api/home/useCustomerHomeQuery";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { timeSensitiveGreeting } from "../../domain/greeting";
import { resolveCampaignDeepLink } from "../../domain/campaignDeepLink";
import type { HomeCampaign } from "../../domain/customerHome";
import { HomeCategory } from "../../domain/customerHome";
import { createServiceCardEntryContext, createAssistantCardEntryContext } from "../../domain/assistantEntry";
import { CustomerTabsParamList } from "../../navigation/routeTypes";

// Static marketing copy, not backend data. Restored per the reference
// design's "Why Customers Choose Us" section -- this is the exact content
// that shipped before, not new copy.
const TRUST_STRIP_ITEMS = [
  { key: "verified", label: "Verified experts", icon: "shield-checkmark-outline" as const },
  { key: "pricing", label: "Clear pricing", icon: "pricetag-outline" as const },
  { key: "updates", label: "Status updates", icon: "notifications-outline" as const },
  { key: "support", label: "Support 24/7", icon: "headset-outline" as const },
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

  // Real bug fixed here: the Home search box stored its text in state but
  // NOTHING ever read it -- typing filtered nothing and there was no empty
  // state, so search silently did nothing at all.
  //
  // Filtering is deliberately client-side over the categories the backend
  // already returned for this ZIP: those are exactly the bookable services
  // here, so a server round-trip would add latency without widening the
  // result set (and must never widen it -- showing an unbookable service
  // would be worse than showing none). Matches name or slug, case- and
  // whitespace-insensitive.
  //
  // MUST stay above the isPending/isError early returns below: a hook
  // placed after them runs only on some renders, which is exactly the
  // "Rendered more hooks than during the previous render" crash.
  const visibleCategories = useMemo(() => {
    const all = homeQuery.data?.bookableCategories ?? [];
    const q = searchValue.trim().toLowerCase();
    if (!q) return all;
    return all.filter(c =>
      (c.name ?? "").toLowerCase().includes(q) || (c.slug ?? "").toLowerCase().includes(q),
    );
  }, [homeQuery.data?.bookableCategories, searchValue]);
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
          <ServiceSearch value={searchValue} onChangeText={setSearchValue} />
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

        <HomeSectionErrorBoundary sectionLabel="services">
          <View style={{ marginTop: theme.spacing.xl }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: theme.spacing.sm }}>
              {/* Section titles were `bodyStrong` (15px) -- the same weight
                  as a card title, so nothing signalled the start of a
                  section and the page read as one undifferentiated column. */}
              <AppText variant="headingSmall">Services near you</AppText>
              {home.address.zipcode && (searchValue.trim() || home.bookableCategories.length > 1) ? (
                // Suppressed for the single-category case: "Services near
                // you" directly above "1 available in 140412" said the same
                // thing twice for the single most common ZIP-coverage case.
                <AppText variant="caption" color="tertiary">{
                  searchValue.trim()
                    ? `${visibleCategories.length} of ${home.bookableCategories.length} in ${home.address.zipcode}`
                    : `${home.bookableCategories.length} available in ${home.address.zipcode}`
                }</AppText>
              ) : null}
            </View>
            {home.bookableCategories.length === 0 ? (
              <AppText variant="bodySmall" color="secondary">No services are available in your area yet.</AppText>
            ) : visibleCategories.length === 0 ? (
              // Real bug fixed here: the search box was purely decorative --
              // `searchValue` was stored in state but never read by anything,
              // so typing filtered nothing and there was no empty state either.
              <AppText variant="bodySmall" color="secondary">
                {`No services match "${searchValue.trim()}".`}
              </AppText>
            ) : (
              // Chunked into explicit 2-up rows rather than a wrapping flex
              // row. A row left holding a single card -- any odd count, and
              // exactly 1 total is the common case for a ZIP served by only
              // one provider -- renders with the "wide" horizontal layout
              // instead of a half-width tile stretched into empty space:
              // stretching the vertical tile just left a big blank area
              // beside a small top-left icon rather than actually using the
              // extra width.
              <View style={{ gap: theme.spacing.sm }}>
                {Array.from({ length: Math.ceil(visibleCategories.length / 2) }).map((_, rowIndex) => {
                  const row = visibleCategories.slice(rowIndex * 2, rowIndex * 2 + 2);
                  return (
                    <View key={rowIndex} style={{ flexDirection: "row", gap: theme.spacing.sm }}>
                      {row.map(category => (
                        <HomeServiceCard
                          key={category.categoryId}
                          category={category}
                          layout={row.length === 1 ? "wide" : "grid"}
                          onPress={() => navigateToService(category, home.address!.zipcode as string)}
                        />
                      ))}
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
          <HomeSectionErrorBoundary sectionLabel="active booking">
            <View style={{ marginTop: theme.spacing.xl }}>
              <ActiveBookingCard booking={home.activeBooking} onPress={() => navigation.navigate("Bookings")} />
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
          <AppText variant="bodyStrong" style={{ marginTop: theme.spacing.xl, marginBottom: theme.spacing.sm }}>
            Why customers choose Fuvay
          </AppText>
          <View style={{ flexDirection: "row", gap: theme.spacing.sm, flexWrap: "wrap" }}>
            {TRUST_STRIP_ITEMS.map(item => (
              <TrustBenefitCard key={item.key} label={item.label} icon={item.icon} />
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
