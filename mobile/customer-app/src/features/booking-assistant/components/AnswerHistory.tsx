import React from "react";
import { View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppText } from "../../../components/primitives/AppText";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import type { AnswerRecord } from "../domain/assistant-session";

export interface AnswerHistoryProps {
  answers: AnswerRecord[];
  questionTitles: Partial<Record<string, string>>;
  onEdit: (stepId: string) => void;
}

/** Read-only summary of completed steps — each with a real edit action (CUSTOMER-L5-05 §16/§30). */
export function AnswerHistory({ answers, questionTitles, onEdit }: AnswerHistoryProps) {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");

  if (answers.length === 0) return null;

  return (
    <View style={{ gap: theme.spacing[3] }}>
      {answers.map((answer) => (
        <View key={answer.stepId} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: theme.spacing[3] }}>
          <View style={{ flex: 1 }}>
            <AppText variant="caption" color="textTertiary">
              {questionTitles[answer.stepId] ?? answer.stepId}
            </AppText>
            <AppText variant="bodySmall">{answer.displaySummary}</AppText>
          </View>
          <AppPressable accessibilityLabel={`${t("assistant.edit")} ${questionTitles[answer.stepId] ?? answer.stepId}`} onPress={() => onEdit(answer.stepId)}>
            <AppText variant="labelMedium" color="textLink">
              {t("assistant.edit")}
            </AppText>
          </AppPressable>
        </View>
      ))}
    </View>
  );
}
