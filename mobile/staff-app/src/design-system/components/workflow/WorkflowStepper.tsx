import React from "react";
import { View, ScrollView } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Icon } from "../Icon";
import { WorkflowStepModel } from "../../types";
import { workflowToneColor } from "../../workflowStatus";

const STATE_TONE: Record<WorkflowStepModel["state"], "completed" | "current" | "upcoming" | "blocked" | "cancelled"> = {
  completed: "completed", current: "current", upcoming: "upcoming", blocked: "blocked", skipped: "cancelled",
};

/**
 * Horizontal workflow stepper -- purely presentational rendering of a
 * backend-provided `workflowSteps` array. Never hardcodes a 7-step
 * pipeline; the number/labels/order of steps come entirely from the model.
 */
export function WorkflowStepper({ steps }: { steps: WorkflowStepModel[] }) {
  const { theme } = useTheme();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} accessibilityRole="progressbar">
      <View style={{ flexDirection: "row", alignItems: "flex-start" }}>
        {steps.map((step, i) => {
          const tone = workflowToneColor(theme, STATE_TONE[step.state]);
          const isLast = i === steps.length - 1;
          return (
            <View key={step.key} style={{ alignItems: "center", width: 84 }}>
              <View style={{ flexDirection: "row", alignItems: "center", width: "100%" }}>
                <View style={{ flex: 1, height: 2, backgroundColor: i === 0 ? "transparent" : theme.colors.borderDefault }} />
                <View
                  style={{
                    width: 28, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center",
                    backgroundColor: step.state === "upcoming" ? theme.colors.surfaceInteractive : tone,
                  }}
                >
                  {step.state === "completed" ? (
                    <Icon name="checkmark" size="compact" color={theme.colors.brandOnPrimary} decorative />
                  ) : (
                    <AppText variant="labelStrong" style={{ color: step.state === "upcoming" ? theme.colors.textTertiary : theme.colors.brandOnPrimary }}>
                      {i + 1}
                    </AppText>
                  )}
                </View>
                <View style={{ flex: 1, height: 2, backgroundColor: isLast ? "transparent" : theme.colors.borderDefault }} />
              </View>
              <AppText
                variant="caption"
                color={step.state === "upcoming" ? "tertiary" : "primary"}
                style={{ textAlign: "center", marginTop: 4 }}
                numberOfLines={2}
              >
                {step.label}
              </AppText>
            </View>
          );
        })}
      </View>
    </ScrollView>
  );
}
