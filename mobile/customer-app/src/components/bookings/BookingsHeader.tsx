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
    // headingSmall, not headingLarge, and a caption subtitle: the tab bar already
    // says where the customer is, so restating it at display size spent a
    // disproportionate part of a phone screen on a label.
    <View>
      <AppText variant="headingSmall" accessibilityRole="header">My Bookings</AppText>
      <AppText variant="caption" color="secondary">Track and review your service requests</AppText>
    </View>
  );
}
