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

function Pill({ children }: { children: React.ReactNode }) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
        paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xxs,
        borderRadius: theme.radiusUsage.statusPill, borderWidth: 1, borderColor: theme.colors.borderSubtle,
        backgroundColor: theme.colors.surfaceDefault,
      }}
    >
      {children}
    </View>
  );
}

/** Read-only strip -- no category-change action here by design (spec:
 * service-card entry preserves its category, it is never re-asked). */
export function AssistantContextStrip({ entryContext, jobTypeLabel }: AssistantContextStripProps) {
  const { theme } = useTheme();
  if (entryContext.source !== "service_card") return null;
  return (
    <View style={{ flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: theme.spacing.xs }}>
      <Pill>
        <Icon name="construct-outline" size="compact" color={theme.colors.textSecondary} decorative />
        <AppText variant="labelStrong">{entryContext.categoryName}</AppText>
      </Pill>
      {jobTypeLabel ? (
        <Pill>
          <AppText variant="labelStrong" color="secondary">{jobTypeLabel}</AppText>
        </Pill>
      ) : null}
      <Pill>
        <Icon name="location-outline" size="compact" color={theme.colors.textSecondary} decorative />
        <AppText variant="labelStrong" color="secondary">{entryContext.zipcode}</AppText>
      </Pill>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
        <View style={{ width: 7, height: 7, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.statusSuccess }} />
        <AppText variant="caption" color="secondary">Available here</AppText>
      </View>
    </View>
  );
}
