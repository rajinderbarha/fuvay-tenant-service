import React, { useRef, useState } from "react";
import {
  View, Pressable, ScrollView, Dimensions, NativeSyntheticEvent, NativeScrollEvent,
} from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeActiveBooking, HomeCategory } from "../../domain/customerHome";
import { MyBookingCard } from "./MyBookingCard";

export interface MyBookingsStripProps {
  bookings: readonly HomeActiveBooking[];
  /** The REAL number of live bookings, which can exceed `bookings`. Decides
   * whether "View all" is offered at all. */
  total: number;
  categories: readonly HomeCategory[];
  title?: string | null;
  onPressBooking: (booking: HomeActiveBooking) => void;
  onViewAll: () => void;
}

/** One card per page, inset by the screen padding on both sides -- same page
 * width as the banner slots, so the two sliders on Home behave identically. */
const PAGE_WIDTH = Dimensions.get("window").width - 32;

/**
 * The customer's live bookings.
 *
 * Was a single card showing only the newest, with a permanent "View All" beside
 * it: a customer with three jobs in flight could not tell the card was hiding
 * two, and one with a single job was offered a link to a list containing exactly
 * what they were already looking at.
 *
 * Now up to three swipe, with dots when there is more than one, and "View all"
 * appears only when the real total exceeds what is on screen -- so the link
 * always means "there is more", never "here it is again".
 */
export function MyBookingsStrip({
  bookings, total, categories, title, onPressBooking, onViewAll,
}: MyBookingsStripProps) {
  const { theme } = useTheme();
  const scrollRef = useRef<ScrollView>(null);
  const [pageIndex, setPageIndex] = useState(0);

  if (bookings.length === 0) return null;

  const hasMore = total > bookings.length;
  const paged = bookings.length > 1;

  function iconFor(booking: HomeActiveBooking): string | null {
    return categories.find(c => c.name === booking.serviceName)?.iconUrl ?? null;
  }

  function handleScrollEnd(e: NativeSyntheticEvent<NativeScrollEvent>) {
    setPageIndex(Math.round(e.nativeEvent.contentOffset.x / PAGE_WIDTH));
  }

  return (
    <View>
      <View
        style={{
          flexDirection: "row", alignItems: "center", justifyContent: "space-between",
          marginBottom: theme.spacing.sm,
        }}
      >
        <View style={{ flexDirection: "row", alignItems: "baseline", gap: theme.spacing.xs, flex: 1, minWidth: 0 }}>
          <AppText variant="headingSmall">
            {title || (total === 1 ? "My Booking" : "My Bookings")}
          </AppText>
          {/* States what is on screen against the real total, so a swipeable
              strip never looks like the whole picture when it is not. */}
          {paged || hasMore ? (
            <AppText variant="caption" color="tertiary">
              {hasMore ? `${bookings.length} of ${total}` : `${total} active`}
            </AppText>
          ) : null}
        </View>
        {hasMore ? (
          <Pressable
            onPress={onViewAll}
            accessibilityRole="button"
            accessibilityLabel={`View all ${total} bookings`}
            hitSlop={8}
            style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}
          >
            <AppText variant="labelStrong" color="link">View all</AppText>
            <Icon name="arrow-forward" size="compact" color={theme.colors.brandPrimary} decorative />
          </Pressable>
        ) : null}
      </View>

      {paged ? (
        <>
          <ScrollView
            ref={scrollRef}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onMomentumScrollEnd={handleScrollEnd}
            accessibilityLabel={`Your bookings, ${bookings.length} shown of ${total}`}
          >
            {bookings.map(booking => (
              <View key={booking.bookingId} style={{ width: PAGE_WIDTH }}>
                <MyBookingCard
                  booking={booking}
                  iconUrl={iconFor(booking)}
                  onPress={() => onPressBooking(booking)}
                />
              </View>
            ))}
          </ScrollView>
          <View
            accessibilityElementsHidden
            style={{ flexDirection: "row", justifyContent: "center", gap: theme.spacing.xs, marginTop: theme.spacing.sm }}
          >
            {bookings.map((booking, i) => (
              <View
                key={booking.bookingId}
                style={{
                  width: i === pageIndex ? 16 : 6, height: 6, borderRadius: theme.radius.radiusFull,
                  backgroundColor: i === pageIndex ? theme.colors.brandPrimary : theme.colors.borderStrong,
                }}
              />
            ))}
          </View>
        </>
      ) : (
        // One booking: no pager and no dots. A single dot implies a second page.
        <MyBookingCard
          booking={bookings[0]}
          iconUrl={iconFor(bookings[0])}
          onPress={() => onPressBooking(bookings[0])}
        />
      )}
    </View>
  );
}
