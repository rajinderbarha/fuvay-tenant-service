import React, { useState } from "react";
import { View, Pressable, AccessibilityInfo } from "react-native";
import * as Clipboard from "expo-clipboard";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface BookingReferenceProps {
  bookingNumber: string | null;
  savedToMyBookings: boolean;
}

export function BookingReference({ bookingNumber, savedToMyBookings }: BookingReferenceProps) {
  const { theme } = useTheme();
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!bookingNumber) return;
    await Clipboard.setStringAsync(bookingNumber);
    setCopied(true);
    AccessibilityInfo.announceForAccessibility("Booking ID copied");
    setTimeout(() => setCopied(false), 2000);
  }

  if (!bookingNumber) return null;

  return (
    <View style={{ alignItems: "center", gap: theme.spacing.xxs }}>
      <Pressable
        onPress={handleCopy}
        accessibilityRole="button"
        accessibilityLabel={`Booking ID ${bookingNumber}. Copy to clipboard.`}
        style={{
          flexDirection: "row", alignItems: "center", gap: theme.spacing.xs,
          paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xxs,
          borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.surfaceInteractive,
        }}
      >
        <AppText variant="labelStrong" color="secondary">Booking ID</AppText>
        <AppText variant="labelStrong">{bookingNumber}</AppText>
        <Icon name={copied ? "checkmark" : "copy-outline"} size="compact" color={theme.colors.textSecondary} decorative />
      </Pressable>
      {savedToMyBookings ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative />
          <AppText variant="caption" color="secondary">Saved to My Bookings</AppText>
        </View>
      ) : null}
    </View>
  );
}
