import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";

export interface AttachmentSummaryProps {
  photoCount: number;
  onReview: () => void;
}

export function AttachmentSummary({ photoCount, onReview }: AttachmentSummaryProps) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <AppText variant="labelStrong" color="secondary">Attachments & notes</AppText>
        <AppText variant="labelStrong" color="link" onPress={onReview}>Review</AppText>
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, marginTop: theme.spacing.xxs }}>
        <Icon name="image-outline" size="compact" color={theme.colors.textSecondary} decorative />
        <AppText variant="body">{photoCount > 0 ? `${photoCount} photo${photoCount === 1 ? "" : "s"} attached` : "No photos attached"}</AppText>
      </View>
    </AppCard>
  );
}
