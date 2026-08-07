import React from "react";
import { EmptyState } from "../States";
import { BookingListFilter } from "../../domain/bookingFilters";

export interface BookingListEmptyStateProps {
  filter: BookingListFilter;
  hasAnyBookings: boolean;
  onStartAssistant: () => void;
  onClearFilter: () => void;
}

export function BookingListEmptyState({ filter, hasAnyBookings, onStartAssistant, onClearFilter }: BookingListEmptyStateProps) {
  if (!hasAnyBookings) {
    return (
      <EmptyState
        icon="calendar-outline"
        // Brand violet circle per the design. Only this state gets it: it
        // is the one a new customer lands on, so it carries the emptiness
        // rather than reporting a filter result.
        iconCircleColor="#7C3AED"
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
