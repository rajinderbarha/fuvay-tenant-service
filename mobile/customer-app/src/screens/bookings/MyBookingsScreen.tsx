import React, { useCallback, useEffect, useState } from "react";
import { View, FlatList, RefreshControl, ActivityIndicator, Pressable } from "react-native";
import { useNavigation, useRoute, RouteProp } from "@react-navigation/native";
import { CustomerTabsParamList } from "../../navigation/routeTypes";
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
export function MyBookingsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const route = useRoute<RouteProp<CustomerTabsParamList, "Bookings">>();
  const [filter, setFilter] = useState<BookingListFilter>("active");
  const [search, setSearch] = useState(route.params?.initialSearch ?? "");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [filterSheetVisible, setFilterSheetVisible] = useState(!!route.params?.openFilter);

  // Entry state is consumed once, on the tap that carried it -- an
  // in-place refresh/re-render must not keep reopening the sheet or
  // re-seeding a search the customer has since changed or cleared.
  useEffect(() => {
    if (route.params?.initialSearch || route.params?.openFilter) {
      navigation.setParams({ initialSearch: undefined, openFilter: undefined } as never);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // Debounced so typing does not fire a request per keystroke; the term
  // itself is applied server-side (see useCustomerBookingsListQuery).
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
    <AppScreen edges={["top", "bottom"]}>
      {isOffline() ? <OfflineBanner /> : null}
      <View style={{ gap: theme.spacing.sm, flex: 1 }}>
        <BookingsHeader />

        <BookingSearchBar
          value={search}
          onChangeText={setSearch}
          filterActive={statusFilter !== null}
          onPressFilter={() => setFilterSheetVisible(true)}
        />

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

        <BookingFilterTabs
          selected={filter}
          onSelect={setFilter}
          activeCount={query.counts.active}
          completedCount={query.counts.completed}
        />

        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          {/* Never claims "Updated just now" for cached/offline data --
              driven by React Query's real dataUpdatedAt, not a static
              string (spec closure item 4). */}
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
            {updatedLabel ? (
              <Icon name="checkmark-circle-outline" size="compact" color={theme.colors.statusSuccess} decorative />
            ) : null}
            <AppText variant="caption" color="tertiary">{updatedLabel ?? ""}</AppText>
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
