import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";

/**
 * CLOSURE (2026-08-01): the notification bell was removed -- an icon
 * with no real destination is a dead control and an accessibility trap
 * (spec closure item 3). It returns once Notifications has a real
 * customer route to navigate to; until then, this header shows title
 * copy only.
 */
export function BookingsHeader() {
  return (
    <View>
      <AppText variant="headingLarge" accessibilityRole="header">My Bookings</AppText>
      <AppText variant="bodySmall" color="secondary">Track and review your service requests</AppText>
    </View>
  );
}
