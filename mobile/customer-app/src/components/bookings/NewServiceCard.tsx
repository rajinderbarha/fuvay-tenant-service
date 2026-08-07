import React from "react";
import { View, Pressable, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";

export interface NewServiceCardProps {
  onPress: () => void;
}

/** Brand accent, not a theme surface: the design gives this card a fixed
 * amber badge that must read identically in light and dark mode. */
const AMBER = "#C2570C";

/** Intrinsic size of the supplied artwork (assets/assistant-mascot.png).
 * The blue wave is part of the image, and everything left of it is fully
 * transparent, so it composites onto the card in either theme without a
 * white block behind it. */
const ART_ASPECT = 288 / 266;
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
      {/* Decorative: it carries no information, so it is not announced and
          never sits above the copy in the touch order. */}
      {/* Wrapped in a View purely to carry `pointerEvents` -- Image has no
          such prop -- so the artwork never intercepts the card's press. */}
      <View
        pointerEvents="none"
        accessibilityElementsHidden
        importantForAccessibility="no-hide-descendants"
        style={{ position: "absolute", right: 0, top: 0, bottom: 0 }}
      >
        <Image
          source={require("../../../assets/assistant-mascot.png")}
          resizeMode="contain"
          style={{ height: "100%", aspectRatio: ART_ASPECT }}
        />
      </View>

      <View
        style={{
          padding: theme.spacing.base,
          gap: theme.spacing.sm,
          // Reserve the artwork's width so the copy never runs under the
          // mascot; the art is height-driven, so this tracks the card.
          paddingRight: CARD_MIN_HEIGHT * ART_ASPECT,
        }}
      >
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
          <View
            style={{
              width: 44, height: 44, borderRadius: theme.radius.radiusFull,
              backgroundColor: AMBER, alignItems: "center", justifyContent: "center",
            }}
          >
            <Icon name="sparkles" size="standard" color="#FFFFFF" decorative />
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
