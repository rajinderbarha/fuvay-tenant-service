import React, { useState } from "react";
import { View, AccessibilityInfo } from "react-native";
import * as Clipboard from "expo-clipboard";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";

export interface BookingDetailsHeaderProps {
  bookingNumber: string | null;
  onBack: () => void;
  onRefresh: () => void;
  refreshing: boolean;
}

export function BookingDetailsHeader({ bookingNumber, onBack, onRefresh, refreshing }: BookingDetailsHeaderProps) {
  const { theme } = useTheme();
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!bookingNumber) return;
    await Clipboard.setStringAsync(bookingNumber);
    setCopied(true);
    AccessibilityInfo.announceForAccessibility("Booking ID copied");
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall" numberOfLines={1}>Booking details</AppText>
        {bookingNumber ? (
          <AppText
            variant="caption" color="secondary" onPress={handleCopy}
            accessibilityRole="button" accessibilityLabel={`Booking ${bookingNumber}. Copy to clipboard.`}
          >
            {bookingNumber} {copied ? "· Copied" : ""}
          </AppText>
        ) : null}
      </View>
      <AppIconButton
        name={copied ? "checkmark" : "copy-outline"} onPress={handleCopy} accessibilityLabel="Copy booking ID"
      />
      <AppIconButton
        name="refresh" onPress={onRefresh} accessibilityLabel="Refresh status" disabled={refreshing}
      />
    </View>
  );
}
