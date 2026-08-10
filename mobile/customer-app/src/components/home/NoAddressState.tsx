import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";

/**
 * What a customer with no location set sees first.
 *
 * Rebuilt from the generic EmptyState, which gave the title and the button the SAME
 * words ("Choose your location" twice, one above the other) and asked for an address
 * to see a catalogue that only needs a PIN code. That mismatch is why it read as a
 * form gate rather than a first step.
 *
 * It now asks for exactly what the next screen collects -- a PIN -- and says when the
 * full address is needed, because "add an address" as the first thing an app says is a
 * bigger commitment than picking where you are, and people abandon it.
 */
export function NoAddressState({ onAddAddress }: { onAddAddress: () => void }) {
  const { theme } = useTheme();

  return (
    // No horizontal padding of its own: the screen that hosts it already pads, and
    // doubling it made the copy a narrow column in the middle of the page.
    <View style={{ alignItems: "center" }}>
      <View
        style={{
          width: 72, height: 72, borderRadius: theme.radius.radiusFull,
          alignItems: "center", justifyContent: "center",
          backgroundColor: theme.colors.brandPrimaryMuted,
          marginBottom: theme.spacing.lg,
        }}
      >
        <Icon name="location" size="emptyState" color={theme.colors.brandPrimaryStrong} decorative />
      </View>

      <AppText variant="headingSmall" align="center" accessibilityRole="header">
        Where do you need service?
      </AppText>
      <AppText
        variant="bodySmall"
        color="secondary"
        align="center"
        style={{ marginTop: theme.spacing.xs }}
      >
        Enter your 6-digit PIN code and we&apos;ll show what&apos;s available near you.
      </AppText>

      <View style={{ marginTop: theme.spacing.lg, alignSelf: "stretch" }}>
        <AppButton label="Set your location" onPress={onAddAddress} fullWidth />
      </View>

      {/* Says when the rest is needed, so the PIN does not feel like the first step of
          a long form. The address is genuinely collected later, at the booking's own
          address step. */}
      <AppText
        variant="caption"
        color="tertiary"
        align="center"
        style={{ marginTop: theme.spacing.base }}
      >
        Your full address is only needed when you book.
      </AppText>
    </View>
  );
}
