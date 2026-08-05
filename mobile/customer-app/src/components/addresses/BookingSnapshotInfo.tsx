import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

/** Only shown because confirmed bookings genuinely use an immutable
 * `address_snapshot` column (verified in the Booking Confirmation/Details
 * phases' audits -- `ServiceBooking.address_snapshot` is copied once at
 * finalize() and never re-derived from the live saved address). */
export function BookingSnapshotInfo() {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
      <Icon name="lock-closed-outline" size="standard" color={theme.colors.textSecondary} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">Existing bookings stay unchanged</AppText>
        <AppText variant="caption" color="secondary">
          Editing or deleting a saved address won't change the address stored on confirmed bookings.
        </AppText>
      </View>
    </View>
  );
}
