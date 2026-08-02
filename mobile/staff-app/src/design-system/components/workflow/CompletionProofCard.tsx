import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Card } from "../foundation/Layout";
import { Icon } from "../Icon";

export interface CompletionProofCardProps {
  workSummary: string;
  photoCount: number;
  requiredPhotoCount: number;
}

export function CompletionProofCard({ workSummary, photoCount, requiredPhotoCount }: CompletionProofCardProps) {
  const { theme } = useTheme();
  const complete = photoCount >= requiredPhotoCount;
  return (
    <Card>
      <AppText variant="bodyStrong" style={{ marginBottom: 4 }}>Work summary</AppText>
      <AppText variant="bodySmall" color="secondary" style={{ marginBottom: theme.spacing.sm }}>{workSummary || "Not yet entered"}</AppText>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
        <Icon name={complete ? "checkmark-circle" : "camera-outline"} size="compact" color={complete ? theme.colors.statusSuccess : theme.colors.textTertiary} decorative />
        <AppText variant="caption" color={complete ? "success" : "tertiary"}>
          {photoCount} of {requiredPhotoCount} completion photos
        </AppText>
      </View>
    </Card>
  );
}
