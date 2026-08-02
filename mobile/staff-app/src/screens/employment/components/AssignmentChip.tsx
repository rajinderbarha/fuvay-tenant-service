import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";

/** Compact chip for Service Groups / Job Types (spec section 4) -- a
 * neutral outline chip, distinct from StatusBadge (job-workflow-status
 * only) and PriorityBadge (job priority only). */
export function AssignmentChip({ label }: { label: string }) {
  const { theme } = useTheme();
  return (
    <View
      accessibilityRole="text"
      style={{
        paddingHorizontal: theme.spacing.sm, paddingVertical: 4,
        borderRadius: theme.radiusUsage.statusPill, borderWidth: 1, borderColor: theme.colors.brandPrimary,
      }}
    >
      <AppText variant="labelStrong" style={{ color: theme.colors.brandPrimary }}>{label}</AppText>
    </View>
  );
}

/** Skill chip with a real verification icon -- only ever shown for skills
 * whose verification_status is genuinely "verified" server-side; a
 * technician-typed/self-reported skill is never rendered as verified. */
export function SkillChip({ label, verified }: { label: string; verified: boolean }) {
  const { theme } = useTheme();
  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`${label}${verified ? ", verified" : ", pending verification"}`}
      style={{
        flexDirection: "row", alignItems: "center", gap: 4,
        paddingHorizontal: theme.spacing.sm, paddingVertical: 4,
        borderRadius: theme.radiusUsage.statusPill,
        backgroundColor: verified ? theme.colors.statusSuccessSurface : theme.colors.statusNeutralSurface,
      }}
    >
      {verified ? <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative /> : null}
      <AppText variant="labelStrong" color={verified ? "success" : "tertiary"}>{label}</AppText>
    </View>
  );
}
