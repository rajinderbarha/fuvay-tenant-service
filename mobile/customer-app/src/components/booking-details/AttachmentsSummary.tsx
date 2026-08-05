import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { CustomerAttachment } from "../../domain/customerBookingDetails";

export function AttachmentsSummary({ attachments, note }: { attachments: CustomerAttachment[]; note: string | null }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Attachments & notes</AppText>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.base, marginTop: theme.spacing.xxs }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          <Icon name="image-outline" size="compact" color={theme.colors.textSecondary} decorative />
          <AppText variant="body">{attachments.length > 0 ? `${attachments.length} photo${attachments.length === 1 ? "" : "s"}` : "No photos"}</AppText>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          <Icon name="document-text-outline" size="compact" color={theme.colors.textSecondary} decorative />
          <AppText variant="body">{note ?? "No additional note"}</AppText>
        </View>
      </View>
    </AppCard>
  );
}
