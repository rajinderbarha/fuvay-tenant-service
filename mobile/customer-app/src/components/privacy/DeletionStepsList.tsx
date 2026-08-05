import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";

const STEPS = [
  { title: "Submit your request", subtitle: "Fuvay records your privacy request." },
  { title: "Identity and eligibility review", subtitle: "Additional verification may be required." },
  { title: "Eligible data is anonymized", subtitle: "This happens only after the request is approved." },
];

/** Explanatory only -- not a live progress tracker (spec section 4). No
 * completion dates, SLAs or countdowns are shown since no verified public
 * deadline exists for this request type. */
export function DeletionStepsList() {
  const { theme } = useTheme();
  return (
    <AppCard style={{ gap: 0 }}>
      {STEPS.map((step, index) => (
        <View key={step.title} style={{ flexDirection: "row", gap: theme.spacing.sm, paddingVertical: theme.spacing.sm }}>
          <View style={{ alignItems: "center" }}>
            <View
              style={{
                width: 28, height: 28, borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
                backgroundColor: index === 0 ? theme.colors.brandPrimary : "transparent",
                borderWidth: index === 0 ? 0 : 1, borderColor: theme.colors.borderDefault,
              }}
            >
              <AppText variant="labelStrong" style={{ color: index === 0 ? theme.colors.brandOnPrimary : theme.colors.textSecondary }}>
                {index + 1}
              </AppText>
            </View>
            {index < STEPS.length - 1 ? (
              <View style={{ width: 1, flex: 1, backgroundColor: theme.colors.borderSubtle, marginVertical: theme.spacing.xxs }} />
            ) : null}
          </View>
          <View style={{ flex: 1, gap: theme.spacing.xxs, paddingBottom: index < STEPS.length - 1 ? theme.spacing.sm : 0 }}>
            <AppText variant="bodyStrong">{step.title}</AppText>
            <AppText variant="bodySmall" color="secondary">{step.subtitle}</AppText>
          </View>
        </View>
      ))}
    </AppCard>
  );
}
