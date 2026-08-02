import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { Card } from "../../../design-system/components/foundation/Layout";
import { AppText } from "../../../design-system/components/typography/AppText";
import { ProgressBar } from "../../../design-system/components/feedback/Loading";
import { PrimaryButton } from "../../../design-system/components/actions/Buttons";
import { DocumentsReadinessDTO } from "../../../services/documents/types";

/** Backend-calculated readiness (spec section 3) -- percentage/counts are
 * never computed in React Native. Uses the design system's linear
 * ProgressBar rather than a custom circular ring (no ring primitive exists
 * in the design system today; a deliberate, disclosed visual simplification
 * relative to the reference screenshot's ring). */
export function DocumentsReadinessCard({ readiness, onUpload }: { readiness: DocumentsReadinessDTO; onUpload: () => void }) {
  const { theme } = useTheme();
  return (
    <Card>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: theme.spacing.sm }}>
        <AppText variant="title">{readiness.percentage}%</AppText>
        <PrimaryButton label="Upload document" leadingIcon="cloud-upload-outline" onPress={onUpload} />
      </View>
      <ProgressBar progress={readiness.percentage / 100} />
      <AppText variant="bodyStrong" style={{ marginTop: theme.spacing.sm }}>{readiness.complete} of {readiness.required} complete</AppText>
      {readiness.action_needed > 0 ? (
        <AppText variant="bodySmall" color="warning">{readiness.action_needed} document{readiness.action_needed === 1 ? "" : "s"} needs attention</AppText>
      ) : (
        <AppText variant="bodySmall" color="tertiary">All required documents are in order</AppText>
      )}
    </Card>
  );
}
