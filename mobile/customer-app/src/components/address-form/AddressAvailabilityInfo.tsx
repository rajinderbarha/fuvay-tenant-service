import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

/** Informational only -- never a serviceability result (spec section 6).
 * Serviceability itself is re-checked by the backend at booking time using
 * whichever address the customer picks, never inferred or stored here. */
export function AddressAvailabilityInfo() {
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
        <AppText variant="bodyStrong" style={{ color: theme.colors.brandPrimaryStrong }}>Availability is checked when you book</AppText>
        <AppText variant="caption" color="secondary">Services can vary by ZIP code.</AppText>
      </View>
    </View>
  );
}
