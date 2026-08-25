import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";
import { FuvayIcon } from "../FuvayIcon";

export interface NewServiceCardProps {
  onPress: () => void;
}

const CARD_MIN_HEIGHT = 132;

/**
 * Footer prompt on My Bookings: the way back into the Assistant once the
 * customer has scrolled their existing requests. Also shown on an empty
 * list, where it is the only card.
 *
 * The whole card is one press target, and the button inside it runs the
 * same action rather than a second, competing one -- so a tap anywhere
 * does what it looks like it does.
 */
export function NewServiceCard({ onPress }: NewServiceCardProps) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel="Start a new service request with Fuvay Assistant"
      style={({ pressed }) => ({
        minHeight: CARD_MIN_HEIGHT,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        overflow: "hidden",
        justifyContent: "center",
        opacity: pressed ? 0.9 : 1,
        ...theme.shadow.sm,
      })}
    >
      <View
        style={{
          padding: theme.spacing.base,
          gap: theme.spacing.sm,
        }}
      >
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
          <View
            style={{
              width: 44, height: 44, borderRadius: theme.radius.radiusFull,
              backgroundColor: theme.colors.brandPrimary, alignItems: "center", justifyContent: "center",
            }}
          >
            <FuvayIcon size={30} accessibilityLabel="Fuvay assistant" />
          </View>
          <View style={{ flex: 1, minWidth: 0 }}>
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
