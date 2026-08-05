import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";

const STEPS = [
  { title: "Request your copy", subtitle: "Fuvay records your export request." },
  { title: "We prepare the export", subtitle: "Track progress from Privacy & data." },
  { title: "Download securely", subtitle: "The download appears when it is ready." },
];

/** Explanatory only -- not a live progress tracker (spec section 4). No
 * ETA, guaranteed completion time or file size is shown before generation;
 * the real progress is owned by `PrivacyRequestDetailsScreen`. */
export function ExportStepsList() {
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
