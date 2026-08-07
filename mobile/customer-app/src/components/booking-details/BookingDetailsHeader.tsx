import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";

export interface BookingDetailsHeaderProps {
  onBack: () => void;
  onRefresh: () => void;
  refreshing: boolean;
}

/** The booking id + copy action live in ServiceOverviewCard now, not here
 * -- this header only frames the screen; CurrentStatusCard directly below
 * speaks for itself without a column-header caption pointing at it. */
export function BookingDetailsHeader({ onBack, onRefresh, refreshing }: BookingDetailsHeaderProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <AppText variant="headingSmall" numberOfLines={1} style={{ flex: 1 }}>Booking details</AppText>
      <AppIconButton
        name="refresh" onPress={onRefresh} accessibilityLabel="Refresh status" disabled={refreshing}
      />
    </View>
  );
}
