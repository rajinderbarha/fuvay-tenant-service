import React from "react";
import { View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppText } from "../../../components/primitives/AppText";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";

export interface AssistantProgressProps {
  current: number;
  total: number;
}

/** Honest, calm progress — never an indeterminate spinner or a fabricated percentage (CUSTOMER-L5-05 §17). */
export function AssistantProgress({ current, total }: AssistantProgressProps) {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const ratio = total > 0 ? Math.min(current / total, 1) : 0;

  return (
    <View accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: total, now: current }} style={{ gap: theme.spacing[1] }}>
      <AppText variant="caption" color="textTertiary">
        {t("assistant.progress", { current, total })}
      </AppText>
      <View style={{ height: 4, borderRadius: theme.radii.full, backgroundColor: theme.colors.borderSubtle, overflow: "hidden" }}>
        <View style={{ height: "100%", width: `${ratio * 100}%`, backgroundColor: theme.colors.actionPrimary }} />
      </View>
    </View>
  );
}
