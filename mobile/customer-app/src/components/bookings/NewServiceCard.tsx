import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";

export interface NewServiceCardProps {
  onPress: () => void;
}

/** Brand accents, not theme surfaces: the design gives this card a fixed
 * amber badge and blue panel that must read identically in light and dark
 * mode (a "dark mode amber" would make it look like a different card). */
const AMBER = "#C2570C";
const PANEL_BLUE = "#3B82F6";

/** The blue panel is an oversized circle bulging in from the right edge --
 * the closest match to the design's organic wave without adding an SVG
 * dependency to the app for one decorative shape. */
const PANEL_SIZE = 260;

/**
 * Footer prompt on My Bookings: the way back into the Assistant once the
 * customer has scrolled their existing requests.
 *
 * The whole card is still one press target (the previous behaviour), and
 * the button inside it is the same action rather than a second, competing
 * one -- so a tap anywhere does what it looks like it does.
 */
export function NewServiceCard({ onPress }: NewServiceCardProps) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel="Start a new service request with Fuvay Assistant"
      style={({ pressed }) => ({
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        overflow: "hidden",
        opacity: pressed ? 0.9 : 1,
        ...theme.shadow.sm,
      })}
    >
      {/* Decorative only -- it carries no information, so it is not
          announced and never sits above the text in the touch order. */}
      <View
        pointerEvents="none"
        style={{
          position: "absolute",
          right: -PANEL_SIZE * 0.52,
          top: -PANEL_SIZE * 0.15,
          width: PANEL_SIZE,
          height: PANEL_SIZE,
          borderRadius: PANEL_SIZE / 2,
          backgroundColor: PANEL_BLUE,
        }}
      />

      <View style={{ padding: theme.spacing.base, gap: theme.spacing.sm }}>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
          <View
            style={{
              width: 44, height: 44, borderRadius: theme.radius.radiusFull,
              backgroundColor: AMBER, alignItems: "center", justifyContent: "center",
            }}
          >
            <Icon name="sparkles" size="standard" color="#FFFFFF" decorative />
          </View>
          {/* Held to ~62% so the copy never runs under the blue panel. */}
          <View style={{ flex: 1, maxWidth: "72%" }}>
            <AppText variant="bodyStrong">Need help with something else?</AppText>
            <AppText variant="bodySmall" color="secondary">
              Start a new service request with Fuvay Assistant.
            </AppText>
          </View>
        </View>

        <AppButton
          label="Start assistant"
          onPress={onPress}
          style={{ borderRadius: theme.radius.radiusFull, alignSelf: "flex-start" }}
          trailingIcon={<Icon name="arrow-forward" size="compact" color={theme.colors.brandOnPrimary} decorative />}
        />
      </View>
    </Pressable>
  );
}
