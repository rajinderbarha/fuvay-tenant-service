import React, { useMemo, useState } from "react";
import { ScrollView, RefreshControl, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText } from "../../components";
import { OfflineBanner } from "../../components/OfflineBanner";
import {
  CustomerHeader, ServiceSearch, VerticalSwitcher, HomeServiceCard,
  AssistantEntryCard, HomeSkeleton, HomeErrorState,
  NoAddressState, UnserviceableState, HomeSectionErrorBoundary, LocationPickerModal, GlobalServicesSection,
  SearchResultsList,
} from "../../components/home";
// Each banner style is its own component; CampaignSlot picks the one the
// backend asked for, per placement.
import { CampaignSlot } from "../../components/home/CampaignSlot";
import { ProblemGrid } from "../../components/home/ProblemGrid";
import { ProblemCircles } from "../../components/home/ProblemCircles";
import { selectProblems } from "../../domain/problemSelection";
import { MyBookingsStrip } from "../../components/home/MyBookingsStrip";
import { AssuranceSection } from "../../components/home/AssuranceSection";
import { HowItWorksSection } from "../../components/home/HowItWorksSection";
import { useCustomerHomeQuery } from "../../api/home/useCustomerHomeQuery";
import { useCustomerSearchQuery, MIN_QUERY_LENGTH } from "../../api/home/useCustomerSearchQuery";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { timeSensitiveGreeting } from "../../domain/greeting";
import { resolveCampaignDeepLink } from "../../domain/campaignDeepLink";
import type { HomeCampaign, HomeCampaignPlacement } from "../../domain/customerHome";
import { HomeCategory } from "../../domain/customerHome";
import { createServiceCardEntryContext, createAssistantCardEntryContext, createQuickIssueEntryContext } from "../../domain/assistantEntry";
import type { HomeQuickIssue } from "../../domain/customerHome";
import { CustomerTabsParamList } from "../../navigation/routeTypes";

/** Two rows of four in the tile grid, three rows of four in the circles. */
const PROBLEM_TILE_COUNT = 8;
const PROBLEM_CIRCLE_COUNT = 12;
/** Two rows in each intent section: enough to be useful, short enough that the
 * two do not turn the screen into four versions of the same list. */
const INTENT_COUNT = 8;

/** The order this build ships. Used ONLY when the backend sends no sections --
 * an older backend, or a failed section lookup. Intent first: what is already
 * happening to the customer, then the fastest way to book, then everything that
 * merely helps them decide. */
const DEFAULT_SECTION_ORDER: { key: string; order: number; title: string | null }[] = [
  { key: "verticals", order: 5, title: null },
  { key: "active_booking", order: 10, title: null },
  { key: "quick_problems", order: 20, title: null },
  { key: "campaign_top", order: 30, title: null },
  { key: "service_grid", order: 40, title: null },
  { key: "campaign_after_services", order: 50, title: null },
  { key: "assistant_entry", order: 60, title: null },
  { key: "campaign_mid", order: 70, title: null },
  { key: "problem_circles", order: 75, title: null },
  { key: "repair_intent", order: 76, title: null },
  { key: "consult_intent", order: 77, title: null },
  { key: "campaign_after_circles", order: 78, title: null },
  { key: "global_services", order: 80, title: null },
  // how_it_works and trust_benefits are NOT in the shipped order: both are
  // switched off in the layout settings, and this fallback should match what a
  // customer actually sees rather than reintroducing them on any build that
  // reaches an older backend. Their renderers stay wired, so turning either back
  // on from Home Layout needs no release.
  { key: "campaign_bottom", order: 90, title: null },
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
    // Same rule as the render path: the ZIP the payload was computed for.
    const zipcode = home?.serviceability?.zipcode ?? home?.address?.zipcode;
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

  /**
   * A ZIP is enough to browse with, whether it came from a saved address or from
   * "Change location".
   *
   * Real bug this fixes: the gate below was `if (!home.address)`, so a customer with no
   * saved address who chose a ZIP got the "add an address" screen even though the
   * backend had answered with a fully serviceable payload for it -- verified live on a
   * brand-new account at 140412: 7 categories and 24 problems returned, and the app
   * threw all of it away. A new customer's first act is picking where they are, and an
   * address is collected later, during the booking, where it is actually needed.
   */
  const browsingZipcode = home.serviceability?.zipcode ?? home.address?.zipcode ?? null;

  if (!home.address && !browsingZipcode) {
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

  /**
   * The ZIP this payload was actually computed FOR, which is not always the saved
   * address's.
   *
   * Real bug this fixes: "Change location" set an override that the backend honoured
   * -- it recomputed serviceability and the bookable catalogue -- but `address` always
   * reports the customer's saved default address, and Home read its ZIP for both the
   * header and every navigation. So changing location looked like it did nothing, and
   * worse, tapping a service afterwards carried the OLD ZIP into the booking: browse
   * one city, get matched in another.
   */
  const zipcode = browsingZipcode as string;

  /** Which problems each of the two sections shows. Shuffled once per payload
   * rather than per render -- see selectProblems -- so tiles do not move under a
   * finger mid-tap, and the two sections do not show the same problem twice. */
  const problems = selectProblems(home.quickIssues, PROBLEM_TILE_COUNT, PROBLEM_CIRCLE_COUNT);
  /** Grouped by what the customer is trying to DO, from the backend's own
   * classification -- the app never re-derives it from the wording. An empty
   * group renders nothing rather than an empty heading. */
  const repairIssues = home.quickIssues.filter(i => i.intent === "repair").slice(0, INTENT_COUNT);
  const consultIssues = home.quickIssues.filter(i => i.intent === "consult").slice(0, INTENT_COUNT);

  function sectionTitle(key: string): string | null {
    return home!.sections.find(s => s.key === key)?.title ?? null;
  }

  function renderServiceGrid() {
    return (
      <View>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", marginBottom: theme.spacing.sm }}>
          <View style={{ flexDirection: "row", alignItems: "baseline", gap: theme.spacing.xs, flex: 1, minWidth: 0 }}>
            <AppText variant="headingSmall">
              {isSearching ? "Results" : sectionTitle("service_grid") || "Services Nearby"}
            </AppText>
            {home!.address?.zipcode ? (
              <AppText variant="caption" color="tertiary" numberOfLines={1}>
                {isSearching ? `for "${searchValue.trim()}"` : `Based on ${home!.address.zipcode}`}
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
              const category = home!.bookableCategories.find(c => String(c.categoryId) === String(categoryId));
              if (category) navigateToService(category, zipcode);
            }}
          />
        ) : home!.bookableCategories.length === 0 ? (
          <AppText variant="bodySmall" color="secondary">No services are available in your area yet.</AppText>
        ) : (
          // Explicit 2-up rows rather than a wrapping flex row: with `flexWrap`
          // plus `space-between`, a trailing row holding one card stretched it
          // across the full width.
          <View style={{ gap: theme.spacing.sm }}>
            {Array.from({ length: Math.ceil(home!.bookableCategories.length / 2) }).map((_, rowIndex) => {
              const row = home!.bookableCategories.slice(rowIndex * 2, rowIndex * 2 + 2);
              return (
                <View key={rowIndex} style={{ flexDirection: "row", gap: theme.spacing.sm }}>
                  {row.map(category => (
                    <HomeServiceCard
                      key={category.categoryId}
                      category={category}
                      onPress={() => navigateToService(category, zipcode)}
                    />
                  ))}
                  {row.length === 1 ? <View style={{ flex: 1 }} /> : null}
                </View>
              );
            })}
          </View>
        )}
      </View>
    );
  }

  function renderCampaignSlot(placement: HomeCampaignPlacement) {
    return (
      <HomeSectionErrorBoundary sectionLabel="promotions">
        <CampaignSlot
          placement={placement}
          campaigns={home!.campaigns}
          mode={mode}
          isCtaRoutable={c => resolveCampaignDeepLink(c.ctaDeeplink, bookableSlugs) !== null}
          onPressCta={handleCampaignCta}
        />
      </HomeSectionErrorBoundary>
    );
  }

  /** Every section this build can draw, keyed the way the backend names them.
   * A section with nothing real to show resolves to null and is skipped, so it
   * contributes no heading and no blank space. */
  const sectionNodes: Record<string, React.ReactNode> = {
    active_booking: home.activeBookings.length > 0 ? (
      <HomeSectionErrorBoundary sectionLabel="my booking">
        <MyBookingsStrip
          bookings={home.activeBookings}
          total={home.activeBookingTotal}
          categories={home.bookableCategories}
          title={sectionTitle("active_booking")}
          onPressBooking={() => navigation.navigate("Bookings")}
          onViewAll={() => navigation.navigate("Bookings")}
        />
      </HomeSectionErrorBoundary>
    ) : null,

    // Five banner slots, each its own section so admin can move, rename or
    // switch any of them off. Each renders as a carousel once it holds more
    // than one banner.
    campaign_top: renderCampaignSlot("campaign_top"),
    campaign_after_problems: renderCampaignSlot("campaign_after_problems"),
    campaign_after_services: renderCampaignSlot("campaign_after_services"),
    campaign_mid: renderCampaignSlot("campaign_mid"),
    campaign_after_circles: renderCampaignSlot("campaign_after_circles"),
    campaign_bottom: renderCampaignSlot("campaign_bottom"),

    // Was in the backend's section vocabulary with nothing wired to draw it, so
    // the payload named a key this screen silently skipped.
    how_it_works: (
      <HomeSectionErrorBoundary sectionLabel="how it works">
        <HowItWorksSection />
      </HomeSectionErrorBoundary>
    ),

    // The shortest route to a booking, which is why it belongs above the
    // category grid: a named problem skips both the category and the
    // issue-picker step.
    quick_problems: (
      <HomeSectionErrorBoundary sectionLabel="quick issues">
        <ProblemGrid
          issues={problems.tiles}
          title={sectionTitle("quick_problems")}
          onPressIssue={issue => navigateToQuickIssue(issue, zipcode)}
        />
      </HomeSectionErrorBoundary>
    ),

    // A second, larger pass at the same real list -- a different selection, in
    // circles, for the customer who did not find their fault in the shortlist.
    repair_intent: (
      <HomeSectionErrorBoundary sectionLabel="repair intent">
        <ProblemGrid
          issues={repairIssues}
          title={sectionTitle("repair_intent") || "Something to repair"}
          onPressIssue={issue => navigateToQuickIssue(issue, zipcode)}
        />
      </HomeSectionErrorBoundary>
    ),

    consult_intent: (
      <HomeSectionErrorBoundary sectionLabel="consult intent">
        <ProblemGrid
          issues={consultIssues}
          title={sectionTitle("consult_intent") || "Get advice or a quote"}
          onPressIssue={issue => navigateToQuickIssue(issue, zipcode)}
        />
      </HomeSectionErrorBoundary>
    ),

    problem_circles: (
      <HomeSectionErrorBoundary sectionLabel="problem circles">
        <ProblemCircles
          issues={problems.circles}
          title={sectionTitle("problem_circles")}
          onPressIssue={issue => navigateToQuickIssue(issue, zipcode)}
        />
      </HomeSectionErrorBoundary>
    ),

    service_grid: (
      <HomeSectionErrorBoundary sectionLabel="services">
        {renderServiceGrid()}
      </HomeSectionErrorBoundary>
    ),

    assistant_entry: (
      <HomeSectionErrorBoundary sectionLabel="assistant">
        <AssistantEntryCard onPress={() => navigateToGenericAssistant(zipcode)} />
      </HomeSectionErrorBoundary>
    ),

    global_services: (
      <HomeSectionErrorBoundary sectionLabel="global services">
        <GlobalServicesSection
          defaultName={customerFirstName !== "there" ? customerFirstName : undefined}
          defaultZipcode={zipcode}
          title={sectionTitle("global_services")}
        />
      </HomeSectionErrorBoundary>
    ),

    trust_benefits: (
      <HomeSectionErrorBoundary sectionLabel="trust">
        <AssuranceSection title={sectionTitle("trust_benefits")} />
      </HomeSectionErrorBoundary>
    ),

    // Self-hiding: a one-option switcher is not a switcher, so with a single
    // vertical this contributes no node and therefore no spacing either.
    verticals: home.enabledVerticals.length > 1 ? (
      <HomeSectionErrorBoundary sectionLabel="verticals">
        <VerticalSwitcher
          verticals={home.enabledVerticals}
          selectedVerticalKey={selectedVerticalKey}
          onSelect={v => setSelectedVerticalKey(v.key)}
        />
      </HomeSectionErrorBoundary>
    ) : null,
  };

  /**
   * What the header says the customer is looking at.
   *
   * While browsing another ZIP it shows that ZIP alone -- NOT the saved address's
   * city, which would be a different place, and not a city guessed from the PIN,
   * which the app has no way to resolve. The saved address keeps its city because
   * that one is known.
   */
  // With no saved address there is no city to pair the ZIP with, and none is guessed
  // from the PIN -- the app cannot resolve one.
  const browsingElsewhere = zipcode !== home.address?.zipcode;
  const locationLabel = browsingElsewhere
    ? zipcode
    : home.address?.city
    ? `${home.address.city} · ${home.address.zipcode}`
    : home.address?.zipcode ?? zipcode;

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

        {/* Section ORDER AND VISIBILITY ARE BACKEND-CONTROLLED (migration 236).
            The layout was fixed here, so re-ordering Home or hiding a section
            needed an app release. `home.sections` is the admin's order; an empty
            list means an older backend sent no instruction, in which case the
            shipped order below is used -- empty is never read as "draw nothing".

            A key this build has no node for is skipped, so a newer backend can
            add a section without breaking this screen. */}
        {(home.sections.length > 0 ? home.sections : DEFAULT_SECTION_ORDER).map(section => {
          const node = sectionNodes[section.key];
          if (!node) return null;
          return (
            <View key={section.key} style={{ marginTop: theme.spacing.xl }}>
              {node}
            </View>
          );
        })}

      </ScrollView>

      <LocationPickerModal
        visible={locationPickerVisible}
        currentZipcode={zipcode}
        onClose={() => setLocationPickerVisible(false)}
        onConfirm={handleConfirmLocation}
      />
    </AppScreen>
  );
}
