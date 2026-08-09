import React, { useCallback, useRef, useState } from "react";
import { View, FlatList, RefreshControl, ActivityIndicator, Pressable, Animated } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { AppText } from "../../components/AppText";
import { BookingsHeader } from "../../components/bookings/BookingsHeader";
import { BookingFilterTabs } from "../../components/bookings/BookingFilterTabs";
import { ActiveBookingCard } from "../../components/bookings/ActiveBookingCard";
import { CompletedBookingCard } from "../../components/bookings/CompletedBookingCard";
import { BookingListEmptyState } from "../../components/bookings/BookingListEmptyState";
import { BookingListFooter } from "../../components/bookings/BookingListFooter";
import { NewServiceCard } from "../../components/bookings/NewServiceCard";
import { NoOtherActiveBookingsCard } from "../../components/bookings/NoOtherActiveBookingsCard";
import { BookingSearchBar } from "../../components/bookings/BookingSearchBar";
import { BookingFilterSheet } from "../../components/bookings/BookingFilterSheet";
import { Icon } from "../../components/Icon";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { bookingStatusFilterLabel } from "../../domain/bookingStatusFilter";
import { useCustomerBookingsListQuery } from "../../api/customerBookings/useCustomerBookingsListQuery";
import { useCustomerHomeQuery } from "../../api/home/useCustomerHomeQuery";
import { BookingListFilter, isActiveBookingStatus } from "../../domain/bookingFilters";
import { CustomerBookingListItem } from "../../domain/bookingList";
import { createAssistantCardEntryContext } from "../../domain/assistantEntry";
import { formatRelativeUpdateTime } from "../../domain/dates";
import { isOffline } from "../../api/networkState";

/**
 * Canonical root My Bookings tab. Every card is adapted real backend data
 * (see api/adapters/bookingList.ts); tab counts come from the backend's
 * own authoritative `counts` (spec closure item 1), never a partial-page
 * guess.
 */
/** Measured height of the title + subtitle block, at the smaller type it now
 * uses (headingSmall + caption rather than headingLarge + bodySmall). */
const HEADER_HEIGHT = 40;
/** Scroll distance over which it folds away. Short enough that the space is
 * reclaimed almost immediately, long enough not to snap. */
const HEADER_COLLAPSE_DISTANCE = 60;

export function MyBookingsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const [filter, setFilter] = useState<BookingListFilter>("active");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [filterSheetVisible, setFilterSheetVisible] = useState(false);
  /**
   * Search and the filter control are OFF by default and opened from the tab row.
   *
   * They used to sit permanently above the tabs, spending a fixed slice of a phone
   * screen on controls most visits never touch -- the list itself is what the
   * customer came for. Opened on demand, and it stays open while a term is applied
   * (see `searchOpen` below) so a narrowed list always shows why.
   */
  const [searchRequested, setSearchRequested] = useState(false);
  /**
   * Drives the collapsing title block.
   *
   * The title and its subtitle are worth ~64px, which is a lot of a phone screen
   * spent restating the tab the customer is already on. They now fold away as the
   * list scrolls, while the search box and the tab filters stay pinned -- those
   * are controls, and a control that scrolls out of reach is worse than a title
   * that does.
   *
   * `useNativeDriver` is off because the collapse animates HEIGHT: translating
   * instead would slide the title behind the search box and leave its space
   * behind, which is the gap this is meant to reclaim. One small view on the JS
   * driver is not a scroll-performance problem.
   */
  const scrollY = useRef(new Animated.Value(0)).current;
  const headerHeight = scrollY.interpolate({
    inputRange: [0, HEADER_COLLAPSE_DISTANCE],
    outputRange: [HEADER_HEIGHT, 0],
    extrapolate: "clamp",
  });
  const headerOpacity = scrollY.interpolate({
    // Fades out over the first half of the travel, so the text is gone before
    // the box is, rather than being clipped mid-letter.
    inputRange: [0, HEADER_COLLAPSE_DISTANCE / 2],
    outputRange: [1, 0],
    extrapolate: "clamp",
  });
  // Debounced so typing does not fire a request per keystroke; the term
  // itself is applied server-side (see useCustomerBookingsListQuery).
  /**
   * Open when the customer asked for it, and also whenever a term or status filter is
   * applied -- including one that survived a re-mount. A narrowed list with its
   * controls hidden looks like missing bookings, which is the more expensive mistake
   * than an extra row on screen.
   */
  const searchOpen = searchRequested || search.length > 0 || statusFilter !== null;

  const debouncedSearch = useDebouncedValue(search, 350);
  const query = useCustomerBookingsListQuery(filter, debouncedSearch, statusFilter);
  const { data: home } = useCustomerHomeQuery();

  function goToDetails(bookingId: string) {
    (navigation as { navigate: (name: string, params: unknown) => void }).navigate("BookingDetails", { bookingId });
  }

  function startAssistant() {
    const entryContext = createAssistantCardEntryContext({ zipcode: home?.address?.zipcode ?? "" });
    (navigation as { navigate: (name: string, params: unknown) => void }).navigate("Assistant", entryContext);
  }

  function goToSupport() {
    (navigation as { navigate: (name: string, params: unknown) => void }).navigate("BookingSupportEntry", { mode: "help" });
  }

  const renderItem = useCallback(({ item }: { item: CustomerBookingListItem }) => (
    isActiveBookingStatus(item.rawStatus)
      ? <ActiveBookingCard item={item} onViewDetails={() => goToDetails(item.bookingId)} onContactSupport={goToSupport} />
      : <CompletedBookingCard item={item} onViewDetails={() => goToDetails(item.bookingId)} />
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ), []);

  if (query.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading your bookings" />
      </AppScreen>
    );
  }

  if (query.isError && query.items.length === 0) {
    return (
      <AppScreen>
        <ErrorState title="We couldn't load your bookings" actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  const updatedLabel = formatRelativeUpdateTime(query.dataUpdatedAt);
  const hasAnyBookingsAtAll = query.counts.all > 0;

  return (
    // Bottom edge deliberately excluded: the bottom tab bar already applies its
    // own safe-area inset, so asking for it here too left a blank strip of
    // background between the last card and the tab bar.
    <AppScreen edges={["top"]}>
      {isOffline() ? <OfflineBanner /> : null}
      <View style={{ gap: theme.spacing.sm, flex: 1 }}>
        <Animated.View style={{ height: headerHeight, opacity: headerOpacity, overflow: "hidden" }}>
          <BookingsHeader />
        </Animated.View>

        {searchOpen ? (
          <BookingSearchBar
            value={search}
            onChangeText={setSearch}
            filterActive={statusFilter !== null}
            onPressFilter={() => setFilterSheetVisible(true)}
            autoFocus={searchRequested}
            // Not closeable while a term is applied -- the bar IS the explanation
            // for a shorter list.
            onClose={search.length === 0 ? () => setSearchRequested(false) : undefined}
          />
        ) : null}

        {/* The applied filter stays visible and removable outside the
            sheet -- a narrowed list that looks identical to an unnarrowed
            one is how customers conclude their bookings have vanished. */}
        {statusFilter ? (
          <Pressable
            onPress={() => setStatusFilter(null)}
            accessibilityRole="button"
            accessibilityLabel={`Filter: ${bookingStatusFilterLabel(statusFilter)}. Tap to clear.`}
            style={{
              flexDirection: "row", alignItems: "center", alignSelf: "flex-start",
              gap: theme.spacing.xxs,
              paddingVertical: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm,
              borderRadius: theme.radiusUsage.statusPill,
              backgroundColor: theme.colors.surfaceInteractive,
            }}
          >
            <AppText variant="caption">{bookingStatusFilterLabel(statusFilter)}</AppText>
            <Icon name="close-circle" size="compact" color={theme.colors.iconDefault} decorative />
          </Pressable>
        ) : null}

        {/* The tabs are what customers actually use to switch views, so the search
            affordance rides alongside them rather than taking a row of its own. */}
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
          <View style={{ flex: 1 }}>
            <BookingFilterTabs
              selected={filter}
              onSelect={setFilter}
              activeCount={query.counts.active}
              completedCount={query.counts.completed}
            />
          </View>
          {!searchOpen ? (
            <Pressable
              onPress={() => setSearchRequested(true)}
              accessibilityRole="button"
              accessibilityLabel="Search and filter bookings"
              hitSlop={8}
              style={({ pressed }) => ({
                width: theme.touchTargets.minimum, height: theme.touchTargets.minimum,
                alignItems: "center", justifyContent: "center",
                borderRadius: theme.radiusUsage.input,
                backgroundColor: theme.colors.surfaceSecondary,
                opacity: pressed ? 0.7 : 1,
              })}
            >
              <Icon name="search-outline" size="standard" color={theme.colors.iconDefault} decorative />
            </Pressable>
          ) : null}
        </View>

        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          {/* Never claims "Updated just now" for cached/offline data --
              driven by React Query's real dataUpdatedAt, not a static
              string (spec closure item 4). */}
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
            {/* While a new search term loads, the previous results stay on
                screen and this one line says so -- the list itself no longer
                disappears and reappears on every character typed. */}
            {query.isStale ? (
              <>
                <ActivityIndicator size="small" color={theme.colors.brandPrimaryStrong} />
                <AppText variant="caption" color="tertiary">Updating results…</AppText>
              </>
            ) : (
              <>
                {updatedLabel ? (
                  <Icon name="checkmark-circle-outline" size="compact" color={theme.colors.statusSuccess} decorative />
                ) : null}
                <AppText variant="caption" color="tertiary">{updatedLabel ?? ""}</AppText>
              </>
            )}
          </View>
          <Pressable
            onPress={() => query.refetch()}
            accessibilityRole="button"
            accessibilityLabel="Refresh bookings"
            hitSlop={8}
            style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}
          >
            <AppText variant="labelStrong" color="link">Refresh</AppText>
            <Icon name="refresh-outline" size="compact" color={theme.colors.brandPrimary} decorative />
          </Pressable>
        </View>

        {query.items.length === 0 ? (
          // Only the assistant card here -- "No other active bookings"
          // would be wrong with none at all, since it means "no OTHERS
          // besides the one above".
          <View style={{ gap: theme.spacing.base }}>
            <BookingListEmptyState
              filter={filter}
              hasAnyBookings={hasAnyBookingsAtAll}
              searchTerm={debouncedSearch}
              onStartAssistant={startAssistant}
              onClearFilter={() => { setFilter("all"); setSearch(""); setStatusFilter(null); }}
            />
            <NewServiceCard onPress={startAssistant} />
          </View>
        ) : (
          <FlatList
            data={query.items}
            keyExtractor={item => item.bookingId}
            renderItem={renderItem}
            onScroll={Animated.event(
              [{ nativeEvent: { contentOffset: { y: scrollY } } }],
              { useNativeDriver: false },
            )}
            scrollEventThrottle={16}
            refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => query.refetch()} />}
            onEndReachedThreshold={0.4}
            onEndReached={() => {
              if (query.hasNextPage && !query.isFetchingNextPage) query.fetchNextPage();
            }}
            ItemSeparatorComponent={() => <View style={{ height: theme.spacing.sm }} />}
            ListFooterComponent={
              <View style={{ gap: theme.spacing.sm, marginTop: theme.spacing.sm }}>
                {query.isFetchingNextPage ? <ActivityIndicator color={theme.colors.brandPrimaryStrong} /> : null}
                {/* Authoritative full-set count (never a loaded-page guess,
                    per BookingFilterTabs' own rule) -- exactly one active
                    booking is the only case this card is true for: zero
                    would make "no OTHER" misleading, and two or more means
                    something else genuinely is active. */}
                {filter === "active" && query.counts.active === 1 ? (
                  <NoOtherActiveBookingsCard onViewCompleted={() => setFilter("completed")} />
                ) : null}
                {!query.hasNextPage && filter === "active" ? (
                  <BookingListFooter message="Completed requests will appear in the Completed tab." />
                ) : null}
                <NewServiceCard onPress={startAssistant} />
              </View>
            }
          />
        )}
      </View>

      <BookingFilterSheet
        visible={filterSheetVisible}
        status={statusFilter}
        onClose={() => setFilterSheetVisible(false)}
        onApply={setStatusFilter}
      />
    </AppScreen>
  );
}
