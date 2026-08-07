import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { CustomerAttachment } from "../../domain/customerBookingDetails";

/**
 * The reference design shows a "View details" link in this card's header.
 * No attachment/notes detail screen exists anywhere in this app (only
 * this summary and the counts it shows), so that link is deliberately
 * NOT rendered here -- a link with nowhere to go is worse than no link.
 * Say the word if a dedicated attachments screen should be built; until
 * then this card is display-only, matching what it actually can do.
 */
export function AttachmentsSummary({ attachments, note }: { attachments: CustomerAttachment[]; note: string | null }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Attachments & notes</AppText>
      <View style={{ flexDirection: "row", gap: theme.spacing.base, marginTop: theme.spacing.sm }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, flex: 1, minWidth: 0 }}>
          <View
            style={{
              width: 36, height: 36, borderRadius: theme.radius.radiusFull,
              backgroundColor: "#7C3AED", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}
          >
            <Icon name="image-outline" size="compact" color="#FFFFFF" decorative />
          </View>
          <AppText variant="bodySmall" numberOfLines={1}>
            {attachments.length > 0 ? `${attachments.length} photo${attachments.length === 1 ? "" : "s"}` : "No photos"}
          </AppText>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, flex: 1, minWidth: 0 }}>
          <View
            style={{
              width: 36, height: 36, borderRadius: theme.radius.radiusFull,
              backgroundColor: "#C2570C", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}
          >
            <Icon name="document-text-outline" size="compact" color="#FFFFFF" decorative />
          </View>
          <AppText variant="bodySmall" numberOfLines={1}>{note ?? "No additional note"}</AppText>
        </View>
      </View>
    </AppCard>
  );
}
