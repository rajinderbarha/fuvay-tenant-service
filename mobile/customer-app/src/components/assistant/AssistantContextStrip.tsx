import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { AssistantEntryContext } from "../../domain/assistantEntry";

export interface AssistantContextStripProps {
  entryContext: AssistantEntryContext;
  jobTypeLabel: string | null;
}

/**
 * Same green ribbon treatment as Review's `ReviewStatusStrip` -- one
 * visual language for "here is the real context this request is
 * happening in", used at both the start and the end of the same booking
 * flow. Left side is the service instead of Review's "Details complete"
 * (there are no details to complete yet at this step); right side is the
 * identical "Service available in {zip}" copy.
 *
 * Read-only -- no category-change action here by design (spec:
 * service-card entry preserves its category, it is never re-asked).
 */
export function AssistantContextStrip({ entryContext, jobTypeLabel }: AssistantContextStripProps) {
  const { theme } = useTheme();
  if (entryContext.source !== "service_card") return null;
  const serviceLabel = jobTypeLabel ? `${entryContext.categoryName} · ${jobTypeLabel}` : entryContext.categoryName;
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", justifyContent: "space-between",
        padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.statusSuccessSurface,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, flexShrink: 1 }}>
        <Icon name="construct-outline" size="compact" color={theme.colors.statusSuccess} decorative />
        <AppText variant="labelStrong" numberOfLines={1} style={{ color: theme.colors.statusSuccess }}>
          {serviceLabel}
        </AppText>
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, flexShrink: 0 }}>
        <Icon name="location" size="compact" color={theme.colors.statusSuccess} decorative />
        <AppText variant="labelStrong" style={{ color: theme.colors.statusSuccess }}>
          Service available in {entryContext.zipcode}
        </AppText>
      </View>
    </View>
  );
}
