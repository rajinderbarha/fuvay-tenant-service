import React, { useEffect, useRef, useState } from "react";
import { View, Animated, Easing, AccessibilityInfo } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface ConfirmationHeroProps {
  bookingNumber: string | null;
}

/**
 * Runs its pulse animation once per mount (spec section 10: "Runs once on
 * initial verified receipt... does not replay on every small refetch") --
 * this component only ever mounts after a verified `kind: "found"` read,
 * so there is no separate "don't replay" flag to thread through; React's
 * own mount/unmount lifecycle already provides that guarantee here.
 */
export function ConfirmationHero({ bookingNumber }: ConfirmationHeroProps) {
  const { theme } = useTheme();
  const pulse = useRef(new Animated.Value(0)).current;
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReducedMotion).catch(() => {});
  }, []);

  useEffect(() => {
    if (reducedMotion) return;
    const anim = Animated.timing(pulse, { toValue: 1, duration: 900, easing: Easing.out(Easing.ease), useNativeDriver: true });
    anim.start();
    return () => anim.stop();
  }, [reducedMotion, pulse]);

  useEffect(() => {
    AccessibilityInfo.announceForAccessibility(
      `Service request confirmed.${bookingNumber ? ` Booking reference ${bookingNumber}.` : ""}`,
    );
  }, [bookingNumber]);

  const ringScale = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.6, 1.4] });
  const ringOpacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.4, 0] });

  return (
    <View style={{ alignItems: "center", gap: theme.spacing.xs }}>
      <View style={{ width: 96, height: 96, alignItems: "center", justifyContent: "center" }}>
        {!reducedMotion ? (
          <Animated.View
            style={{
              position: "absolute", width: 80, height: 80, borderRadius: theme.radius.radiusFull,
              borderWidth: 2, borderColor: theme.colors.brandPrimary,
              transform: [{ scale: ringScale }], opacity: ringOpacity,
            }}
          />
        ) : null}
        <View
          style={{
            width: 64, height: 64, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.brandPrimaryMuted, alignItems: "center", justifyContent: "center",
          }}
        >
          <Icon name="sparkles" size="feature" color={theme.colors.brandPrimaryStrong} decorative />
        </View>
        <View
          style={{
            position: "absolute", bottom: 0, right: 8, width: 24, height: 24, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.statusSuccess, alignItems: "center", justifyContent: "center",
          }}
        >
          <Icon name="checkmark" size="compact" color={theme.colors.brandOnPrimary} decorative />
        </View>
      </View>
      <AppText variant="title" align="center">Service request confirmed</AppText>
      <AppText variant="bodySmall" color="secondary" align="center">Your booking has been created successfully.</AppText>
    </View>
  );
}
