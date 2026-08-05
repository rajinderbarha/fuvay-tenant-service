import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

/** Same immutable-snapshot guarantee as Saved Addresses' disclosure (see
 * `ServiceBooking.address_snapshot`), worded for the form context. */
export function AddressHistoricalNote() {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
      <Icon name="lock-closed-outline" size="standard" color={theme.colors.textSecondary} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">Confirmed bookings stay unchanged</AppText>
        <AppText variant="caption" color="secondary">This address only applies to future service requests.</AppText>
      </View>
    </View>
  );
}
