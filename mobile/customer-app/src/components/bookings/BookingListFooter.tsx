import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";

export function BookingListFooter({ message }: { message: string }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
        <Icon name="calendar-outline" size="standard" color={theme.colors.textSecondary} decorative />
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong">No other active bookings</AppText>
          <AppText variant="bodySmall" color="secondary">{message}</AppText>
        </View>
      </View>
    </AppCard>
  );
}
