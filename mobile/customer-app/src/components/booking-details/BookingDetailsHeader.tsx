import React, { useState } from "react";
import { View, AccessibilityInfo } from "react-native";
import * as Clipboard from "expo-clipboard";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";

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
    <View style={{ gap: theme.spacing.xxs }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
        <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
        <AppText variant="headingSmall" numberOfLines={1} style={{ flex: 1 }}>Booking details</AppText>
        <AppIconButton
          name="refresh" onPress={onRefresh} accessibilityLabel="Refresh status" disabled={refreshing}
        />
      </View>

      {/* Centered under the title, matching the design -- id + copy on one
          line, the status column label on its own line beneath. */}
      <View style={{ alignItems: "center", gap: theme.spacing.xxs }}>
        {bookingNumber ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
            <AppText
              variant="caption" color="secondary" onPress={handleCopy}
              accessibilityRole="button" accessibilityLabel={`Booking ${bookingNumber}. Copy to clipboard.`}
            >
              {bookingNumber} {copied ? "· Copied" : ""}
            </AppText>
            <AppIconButton
              name={copied ? "checkmark" : "copy-outline"} onPress={handleCopy} accessibilityLabel="Copy booking ID"
            />
          </View>
        ) : null}
        {/* Labels the status card directly below -- purely a section
            header, carries no data of its own and is not a control. */}
        <AppText variant="caption" color="tertiary">CURRENT STATUS</AppText>
      </View>
    </View>
  );
}
