import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

/** Booking-time-only disclaimer -- never a permanent serviceable/
 * unserviceable badge on a saved address (spec section 5: "Do not
 * permanently display Serviceable/Unserviceable/Available services"). */
export function AddressBookingInfo() {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start",
        padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.brandPrimaryMuted, borderWidth: 1, borderColor: theme.colors.borderSubtle,
      }}
    >
      <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong" style={{ color: theme.colors.brandPrimaryStrong }}>Addresses are checked when you book</AppText>
        <AppText variant="caption" color="secondary">Available services can change by ZIP code.</AppText>
      </View>
    </View>
  );
}
