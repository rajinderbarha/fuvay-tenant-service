import React from "react";
import { EmptyState } from "../States";
import { BookingListFilter } from "../../domain/bookingFilters";
import { useTheme } from "../../design-system/theme";

export interface BookingListEmptyStateProps {
  filter: BookingListFilter;
  hasAnyBookings: boolean;
  /** The term currently applied to the query, if any. Checked FIRST: with
   * a search active, an empty list means "nothing matched", not "you have
   * no bookings" -- telling a customer with 20 bookings that they have
   * none would be plainly wrong. */
  searchTerm?: string;
  onStartAssistant: () => void;
  onClearFilter: () => void;
}

export function BookingListEmptyState({ filter, hasAnyBookings, searchTerm, onStartAssistant, onClearFilter }: BookingListEmptyStateProps) {
  const { theme } = useTheme();
  if (searchTerm && searchTerm.trim()) {
    return (
      <EmptyState
        icon="search-outline"
        title={`No bookings match "${searchTerm.trim()}"`}
        message="Try a service name or a booking number."
        actionLabel="Clear search"
        onAction={onClearFilter}
      />
    );
  }
  if (!hasAnyBookings) {
    return (
      <EmptyState
        icon="calendar-outline"
        // Violet circle per the design. Only this state gets it: it is the
        // one a new customer lands on, so it carries the emptiness rather
        // than reporting a filter result. Themed (v2 a4) so it is the right
        // violet in both light and dark.
        iconCircleColor={theme.colors.accentViolet}
        title="No bookings yet"
        message="Start a service request with Fuvay Assistant to see it here."
        actionLabel="Start assistant"
        onAction={onStartAssistant}
      />
    );
  }
  if (filter === "active") {
    return <EmptyState icon="checkmark-done-outline" title="No active bookings" message="Completed requests will appear in the Completed tab." />;
  }
  if (filter === "completed") {
    return <EmptyState icon="calendar-outline" title="No completed bookings yet" />;
  }
  return (
    <EmptyState
      icon="search-outline"
      title="No bookings match your filters"
      actionLabel="Clear filters"
      onAction={onClearFilter}
    />
  );
}
