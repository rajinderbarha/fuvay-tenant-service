import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon, IconProps } from "../../../design-system/components/Icon";
import { DocumentRequirementDTO } from "../../../services/documents/types";

const ICONS: Record<string, IconProps["name"]> = {
  technician_identity_proof: "person-outline",
  technician_skill_certificate: "ribbon-outline",
  technician_background_check: "shield-checkmark-outline",
};

type StatusVisual = { label: string; color: "success" | "warning" | "danger" | "tertiary"; icon: IconProps["name"] };

/** Single mapping from (review_status, display_condition) -> label/color/icon
 * (spec section 5) -- the only place this mapping happens, never a second
 * ad-hoc mapping inside a screen. Unknown states fail safe to a neutral
 * "Unavailable" rather than assuming Verified. */
export function resolveDocumentStatus(req: DocumentRequirementDTO): StatusVisual {
  if (req.display_condition === "expired") return { label: "Expired", color: "danger", icon: "alert-circle-outline" };
  if (req.display_condition === "expiring_soon") return { label: `Expires in ${req.days_until_expiry} day${req.days_until_expiry === 1 ? "" : "s"}`, color: "warning", icon: "time-outline" };
  switch (req.review_status) {
    case "verified": return { label: "Verified", color: "success", icon: "checkmark-circle-outline" };
    case "pending_review": return { label: "Under review", color: "tertiary", icon: "time-outline" };
    case "changes_requested": return { label: "Changes requested", color: "warning", icon: "alert-circle-outline" };
    case "rejected": return { label: "Rejected", color: "danger", icon: "close-circle-outline" };
    case "missing": return { label: "Missing", color: "tertiary", icon: "ellipse-outline" };
    case "superseded": return { label: "Superseded", color: "tertiary", icon: "ellipse-outline" };
    default: return { label: "Status unavailable", color: "tertiary", icon: "help-circle-outline" };
  }
}

function statusIconColor(theme: ReturnType<typeof useTheme>["theme"], tone: StatusVisual["color"]): string {
  switch (tone) {
    case "success": return theme.colors.statusSuccess;
    case "warning": return theme.colors.statusWarning;
    case "danger": return theme.colors.statusDanger;
    default: return theme.colors.textTertiary;
  }
}

export function DocumentRow({ requirement, onPress }: { requirement: DocumentRequirementDTO; onPress: () => void }) {
  const { theme } = useTheme();
  const visual = resolveDocumentStatus(requirement);
  const dateLabel = requirement.submitted_at ? new Date(requirement.submitted_at).toLocaleDateString() : null;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${requirement.label}, ${visual.label}`}
      style={{ flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.sm, gap: theme.spacing.sm, minHeight: 44 }}
    >
      <View style={{ width: 36, height: 36, borderRadius: 8, backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center" }}>
        <Icon name={ICONS[requirement.code] ?? "document-text-outline"} size="compact" color={theme.colors.textSecondary} decorative />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="body">{requirement.label}</AppText>
        {dateLabel ? <AppText variant="caption" color="tertiary">Updated {dateLabel}</AppText> : null}
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
        <Icon name={visual.icon} size="compact" color={statusIconColor(theme, visual.color)} decorative />
        <AppText variant="labelStrong" color={visual.color}>{visual.label}</AppText>
      </View>
      <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
    </Pressable>
  );
}
