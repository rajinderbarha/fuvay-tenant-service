import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { RelativeTime } from "../../../design-system/components/data-display/DateTimeText";
import { resolveEventVisual } from "../eventRegistry";
import { NotificationItemDTO } from "../../../services/notifications/types";

function toneColor(theme: ReturnType<typeof useTheme>["theme"], tone: string) {
  switch (tone) {
    case "danger": return theme.colors.statusDanger;
    case "warning": return theme.colors.statusWarning;
    case "orange": return theme.colors.brandPrimary;
    case "success": return theme.colors.statusSuccess;
    case "info": return theme.colors.statusInfo;
    default: return theme.colors.textTertiary;
  }
}

export interface NotificationRowProps {
  item: NotificationItemDTO;
  onPress: () => void;
}

/** Compact row inside a grouped card (spec section 3) -- read/unread and
 * severity are always paired with text/icon, never color alone. */
export function NotificationRow({ item, onPress }: NotificationRowProps) {
  const { theme } = useTheme();
  const visual = resolveEventVisual(item.event_type, item.severity);
  const color = toneColor(theme, visual.tone);

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${item.title}. ${item.body}. ${item.is_read ? "Read" : "Unread"}.${item.action_required ? " Action needed." : ""}`}
      style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm, paddingVertical: theme.spacing.sm, minHeight: 44 }}
    >
      <View style={{ width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: color + "22" }}>
        <Icon name={visual.icon} size="standard" color={color} decorative />
      </View>
      <View style={{ flex: 1 }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
          <AppText variant={item.is_read ? "body" : "bodyStrong"} numberOfLines={1} style={{ flex: 1 }}>{item.title}</AppText>
          <RelativeTime isoString={item.created_at} variant="caption" color="tertiary" accessibilityLabel={new Date(item.created_at).toLocaleString()} />
        </View>
        <AppText variant="bodySmall" color="secondary" numberOfLines={1}>{item.body}</AppText>
        {item.action_required ? (
          <View style={{ alignSelf: "flex-start", marginTop: 4, paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, borderWidth: 1, borderColor: theme.colors.brandPrimary }}>
            <AppText variant="caption" color="link">Review</AppText>
          </View>
        ) : null}
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
        {!item.is_read ? <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: theme.colors.statusDanger }} /> : null}
        <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
      </View>
    </Pressable>
  );
}
