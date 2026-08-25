import React, { useCallback, useMemo, useState } from "react";
import { View, FlatList, RefreshControl, ActivityIndicator, Pressable } from "react-native";
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
import { groupByUrgency, countLate } from "../../domain/bookingUrgencyGroups";
import type { BookingUrgency } from "../../domain/bookingList";
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
/** A row in the list: either a group heading or a booking card. */
type BookingRow =
  | { kind: "heading"; urgency: BookingUrgency; title: string; subtitle: string | null; count: number }
  | { kind: "booking"; booking: CustomerBookingListItem };

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

  /**
   * Headings and cards in ONE flat list, so the FlatList keeps recycling rows -- nesting
   * a list per group would render every card at once and lose that.
   *
   * The order and the wording come from `groupByUrgency`, which reads the SERVER's
   * urgency. Nothing here compares a date: the provider's dashboard uses the same rule,
   * and a customer seeing "Today" for a job the provider calls overdue is worse than no
   * grouping at all.
   *
   * Finished bookings have no urgency, so the Completed tab keeps its plain
   * newest-first list with no headings at all.
   */
  const rows: BookingRow[] = useMemo(() => {
    const { groups, ungrouped } = groupByUrgency(query.items);
    const out: BookingRow[] = [];
    for (const group of groups) {
      out.push({
        kind: "heading", urgency: group.urgency, title: group.title,
        subtitle: group.subtitle, count: group.items.length,
      });
      for (const booking of group.items) out.push({ kind: "booking", booking });
    }
    for (const booking of ungrouped) out.push({ kind: "booking", booking });
    return out;
  }, [query.items]);

  const lateCount = countLate(query.items);
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

  const renderItem = useCallback(({ item }: { item: BookingRow }) => {
    if (item.kind === "heading") {
      return (
        <View style={{ marginTop: theme.spacing.base, marginBottom: theme.spacing.xs }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
            {item.urgency === "late" ? (
              <Icon name="alert-circle" size="compact" color={theme.colors.statusDanger} decorative />
            ) : null}
            <AppText
              variant="labelStrong"
              style={item.urgency === "late" ? { color: theme.colors.statusDanger } : undefined}
              accessibilityRole="header"
            >
              {`${item.title} (${item.count})`}
            </AppText>
          </View>
          {item.subtitle ? (
            <AppText variant="caption" color="secondary" style={{ marginTop: 2 }}>{item.subtitle}</AppText>
          ) : null}
        </View>
      );
    }
    const booking = item.booking;
    return isActiveBookingStatus(booking.rawStatus)
      ? <ActiveBookingCard item={booking} onViewDetails={() => goToDetails(booking.bookingId)} onContactSupport={goToSupport} />
      : <CompletedBookingCard item={booking} onViewDetails={() => goToDetails(booking.bookingId)} />;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  if (query.isPending) {
    return (
      <AppScreen>
        <View style={{ flex: 1, gap: theme.spacing.xl }}>
          <BookingsHeader />
          <LoadingState label="Loading your bookings" />
        </View>
      </AppScreen>
    );
  }

  if (query.isError && query.items.length === 0) {
    return (
      <AppScreen>
        <View style={{ flex: 1, gap: theme.spacing.xl }}>
          <BookingsHeader onSearch={() => setSearchRequested(true)} />
          <ErrorState title="We couldn't load your bookings" actionLabel="Try again" onAction={() => query.refetch()} />
        </View>
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
      <View style={{ gap: theme.spacing.md, flex: 1 }}>
        <BookingsHeader
          activeCount={query.counts.active}
          completedCount={query.counts.completed}
          onSearch={() => setSearchRequested(true)}
        />

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

        {/* Says how many need attention BEFORE any scrolling, and only when there are
            any -- "0 past their slot" is noise. Tapping it is not offered: the group is
            already first in the list, so a jump would land where the eye already is. */}
        {lateCount > 0 ? (
          <View
            style={{
              flexDirection: "row", alignItems: "center", gap: theme.spacing.xs,
              paddingVertical: theme.spacing.xs, paddingHorizontal: theme.spacing.sm,
              borderRadius: theme.radiusUsage.card,
              backgroundColor: theme.colors.statusDangerSurface,
            }}
          >
            <Icon name="alert-circle" size="compact" color={theme.colors.statusDanger} decorative />
            <AppText variant="caption" style={{ flex: 1, color: theme.colors.statusDanger }}>
              {lateCount === 1
                ? "1 booking is past its scheduled slot"
                : `${lateCount} bookings are past their scheduled slot`}
            </AppText>
          </View>
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
            data={rows}
            keyExtractor={row => (row.kind === "heading" ? `h:${row.urgency}` : row.booking.bookingId)}
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
