import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";

const STEPS = [
  { title: "Request confirmed", description: "We'll confirm your request." },
  { title: "Provider assigned", description: "We'll assign the best professional." },
  { title: "Visit scheduled", description: "We'll schedule your visit." },
];

/** Explanatory FUTURE steps, never marked complete before the matching
 * backend event actually happens (spec section 6). */
export function NextSteps() {
  const { theme } = useTheme();
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">What happens next</AppText>
      <View style={{ flexDirection: "row", marginTop: theme.spacing.sm }}>
        {STEPS.map((step, i) => (
          <View key={step.title} style={{ flex: 1, alignItems: "center" }}>
            <View
              style={{
                width: 24, height: 24, borderRadius: theme.radius.radiusFull,
                alignItems: "center", justifyContent: "center",
                backgroundColor: i === 0 ? theme.colors.brandPrimary : theme.colors.surfaceInteractive,
              }}
            >
              <AppText variant="labelStrong" style={{ color: i === 0 ? theme.colors.brandOnPrimary : theme.colors.textSecondary }}>
                {i + 1}
              </AppText>
            </View>
            <AppText variant="caption" align="center" style={{ marginTop: theme.spacing.xxs }}>{step.title}</AppText>
            <AppText variant="caption" color="tertiary" align="center">{step.description}</AppText>
          </View>
        ))}
      </View>
    </AppCard>
  );
}
